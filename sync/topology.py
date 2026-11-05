"""YFull's CC-BY tree: source nomenclature, equivalent SNP blocks and age estimates.

Only topology is emitted. No tester/sample IDs are created or inferred.
"""
import hashlib
import json
import re

LABEL=re.compile(r'[A-Za-z][A-Za-z0-9*.+_\-]*')
SNP=re.compile(r'[A-Za-z][A-Za-z0-9.+_\-]*')


def reference_labels(rows):
    labels=set()
    structural=set('ABCDEFGHIJKLMNOPQRST')|{'BT','CT','CF','DE','GHIJK','HIJK','IJK','IJ','LT','NO','Y-ADAM'}
    for row in rows:
        for key in ('y_dna','y_dna_alias','node_label'):
            for label in re.split(r'[,;/|\s]+',str(row.get(key) or '')):
                if LABEL.fullmatch(label) and not re.fullmatch(r'YF\d+',label,re.I) and (any(c.isdigit() for c in label) or label.upper() in structural):
                    labels.add(label.upper().rstrip('*'))
    return sorted(labels)


def estimate(value):
    if value in (None,'','-','—'): return None
    if isinstance(value,bool) or not isinstance(value,(int,float)) or value<0:
        raise ValueError('Invalid published YFull age estimate')
    return value


class YFullTree:
    def __init__(self,data):
        self.nodes={};self.names={};self.markers={}
        stack=[(data,None)]
        while stack:
            raw,parent=stack.pop()
            if not isinstance(raw,dict): raise ValueError('Invalid YFull tree node')
            label=raw.get('id') or ('Y-Adam' if parent is None else '')
            if not isinstance(label,str) or not LABEL.fullmatch(label) or re.fullmatch(r'YF\d+',label,re.I): raise ValueError('Invalid YFull node label')
            if not {'formed','tmrca','snps'}.issubset(raw): raise ValueError('Unsupported YFull branch schema')
            if label.upper() in self.names: raise ValueError('Duplicate YFull node label')
            groups=[[p.strip() for p in block.split('/') if p.strip()] for block in str(raw.get('snps') or '').split(',') if block.strip()]
            aliases=list(dict.fromkeys(p for group in groups for p in group if SNP.fullmatch(p)))
            age={'unit':'ybp'}
            for key in ('formed','tmrca'):
                values={'estimate':estimate(raw.get(key)),'low':estimate(raw.get(key+'lowage')),'high':estimate(raw.get(key+'highage'))}
                if values['low'] is not None and values['high'] is not None and values['low']>values['high']:
                    raise ValueError('Inverted YFull age interval')
                age[key]=values
            node={'label':label,'parent_label':parent,'aliases':aliases,'snp_groups':groups,'age_estimates':age}
            self.nodes[label]=node;self.names[label.upper()]=label
            for marker in aliases: self.markers.setdefault(marker.upper(),set()).add(label)
            children=raw.get('children',[])
            if not isinstance(children,list): raise ValueError('Invalid YFull children')
            stack.extend((child,label) for child in reversed(children))
        if not self.nodes or 'Y-Adam' not in self.nodes: raise ValueError('Missing YFull root')

    def match(self,query):
        query=query.strip().upper().rstrip('*')
        if query in self.names: return {'status':'exact','label':self.names[query]}
        marker=query.split('-',1)[1] if '-' in query else query
        candidates=self.markers.get(marker,set())
        if '-' in query:
            root=query[0]
            candidates={label for label in candidates if label.upper().startswith(root)}
        if len(candidates)==1: return {'status':'equivalent_snp','label':next(iter(candidates)),'marker':marker}
        return {'status':'ambiguous' if candidates else 'unmatched','candidates':sorted(candidates)}

    def path(self,label):
        path=[]
        while label is not None:
            if label not in self.nodes: raise ValueError('Missing published ancestor')
            path.append(label);label=self.nodes[label]['parent_label']
        return list(reversed(path))

    def select(self,queries):
        matches={q:self.match(q) for q in sorted(set(queries))}
        labels={'Y-Adam'}
        for match in matches.values():
            if match['status'] in ('exact','equivalent_snp'): labels.update(self.path(match['label']))
        nodes=[node for label,node in self.nodes.items() if label in labels]
        return nodes,matches

    def fingerprint(self,label):
        n=self.nodes[label]
        return json.dumps([n['parent_label'],n['snp_groups'],n['age_estimates']],sort_keys=True)

    def diff(self,previous):
        if previous is None: return {'baseline':True,'new_nodes':len(self.nodes),'removed_nodes':0,'moved_nodes':0,'changed_snp_blocks':0,'changed_age_estimates':0}
        old,new=set(previous.nodes),set(self.nodes);shared=old&new
        return {'baseline':False,'new_nodes':len(new-old),'removed_nodes':len(old-new),
            'moved_nodes':sum(self.nodes[k]['parent_label']!=previous.nodes[k]['parent_label'] for k in shared),
            'changed_snp_blocks':sum(self.nodes[k]['snp_groups']!=previous.nodes[k]['snp_groups'] for k in shared),
            'changed_age_estimates':sum(self.nodes[k]['age_estimates']!=previous.nodes[k]['age_estimates'] for k in shared)}


def release_key(tree_sha,queries):
    return hashlib.sha256((tree_sha+'|normalizer-v1|'+json.dumps(sorted(set(queries)))).encode()).hexdigest()
