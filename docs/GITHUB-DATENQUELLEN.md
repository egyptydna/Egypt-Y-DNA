# Lizenzierte GitHub-Quellen und genehmigte Testerfeeds

Verifiziert am 4. November 2026. Diese Erweiterung verwendet dieselbe Website und
dasselbe Supabase-Projekt `lsfmpmfoqdtkgndtaxen`. Es gibt drei getrennte Datenarten:
Baumtopologie, anonyme Knotenzahlen und individuell belegte Testerprofile.

## Offizieller YFull-Stammbaum: angebunden

Quelle: [YFullTeam/YTree](https://github.com/YFullTeam/YTree), `master`.
`current_version.txt`, `current_tree.json` und `LICENSE.md` werden bei jedem Lauf
am selben unveränderlichen Git-Commit gelesen. Zum Prüfzeitpunkt:

| Eigenschaft | Tatsächlicher Wert |
|---|---|
| Version | 14.06.0 |
| Letzte Änderung der Baumdatei | 22. September 2026 |
| Commit | `bdc9bb4d8db72abc7658362f258dbc2a63e34789` |
| Umfang | 69.675 benannte Zweige und eine Navigationswurzel |
| Lizenz | CC BY 4.0, YFull / YFullTeam |
| Archivabgleich | 312 unterschiedliche SNP-Bezeichnungen: 137 exakt, 100 eindeutige Markerzuordnungen, 75 ohne Treffer |
| Erster produktiver Teilbaum | 1.054 Knoten einschließlich aller benötigten Vorfahren |
| Neu angelegte / geänderte Tester | 0 / 0 |

Die additive Migration `20261104184412_licensed_github_tree_sources` und der erste
kontrollierte Baumimport sind bereits im Zielprojekt ausgeführt. Lauf-ID:
`334e0fd0-556d-400e-a85a-9190fd6216b6`, Status `completed`.
Die 330 bestehenden modernen Archivzeilen blieben erhalten. Die Website und die
regelmäßige Prüfung erhalten den neuen Code nach Merge dieses Quellenerweiterungs-PRs.

Die komplette Quelldatei wird serverseitig indexiert, über alle enthaltenen
Haplogruppen hinweg. In die Datenbank gelangen die für die vorhandenen
Archivbezeichnungen und freigegebenen Knotenzahlen benötigten Zweige einschließlich
ihrer belegten Vorfahren. So lädt die Website keinen kompletten globalen Baum.
Neue Testerbezeichnungen erweitern diese Auswahl beim nächsten Lauf automatisch.

Übernommen werden kanonische Labels, Elternbeziehungen, veröffentlichte SNP-Blöcke,
Slash-Aliase und Altersangaben mit veröffentlichten Intervallen in `ybp`. Mehrere
kommagetrennte SNPs können denselben Zweig definieren, ohne dass sie dadurch als
derselbe SNP bezeichnet werden. Beispiel aus dieser tatsächlichen Datei: `J-FGC1`
ist ein definierender Marker des YFull-Zweigs `J-Y5320`. Das ist eine belegte
Zweigzuordnung, kein Beweis, dass zwei SNP-Namen identisch sind.

Im bestehenden Y-Tree ist die offizielle Topologie voreingestellt. Ein Umschalter
bietet weiterhin die bisherigen veröffentlichten Pfade. Nicht zuordenbare oder
widersprüchliche Bezeichnungen behalten ihren bisherigen Pfad. Tester bleiben
sichtbar, ihre ursprünglichen Datenbankfelder werden nicht überschrieben. Im
Detailfenster stehen Originalbezeichnung, YFull-Zweig, Pfad, SNP-Blöcke,
Zweigaltersangaben, Quelle und Lizenz. Altersangaben beziehen sich auf den Zweig,
nicht auf das Alter einer getesteten Person. mtDNA verwendet weiterhin seine
bisherige Darstellung.

Der GitHub-Snapshot ist nicht zwingend aktuell zur YFull-Website. Version und
Quellveröffentlichungsdatum werden deshalb ausdrücklich angezeigt. Er enthält
keine individuellen ägyptischen Kundenprofile: Aus ihm entstehen weder neue
YF-IDs noch Kitnummern, Big-Y-Nachweise oder regionale Testerstatistiken.

Die Lizenzdatei wird gegen ihre geprüfte SHA-256-Prüfsumme validiert:
`419896aea50c15d6e40c5b4baf4bd346f78223b9a354c7357ad00262afdc08ec`.
Bei Lizenz-/Formatänderung oder Abruffehler bleibt der letzte vollständige
freigegebene Stand erhalten. Ein neuer Teilbaum wird zunächst unsichtbar gestuft
und erst nach Vollständigkeitsprüfung transaktional veröffentlicht. RLS gibt nur
den aktuellen veröffentlichten Stand für Browser frei.

GitHub Actions zwischenspeichert Dateien unter ihrem unveränderlichen Commit.
Struktur-, SNP- und Altersänderungen werden mit dem letzten angewandten Snapshot
verglichen. Derselbe Quellstand mit denselben Archivbezeichnungen aktualisiert nur
das Prüfdatum. Ein verlorener Cache wird nicht als Beweis für tausende neue Zweige
gewertet; dann weist der Bericht den fehlenden Versionsvergleich aus.

## ftdnastat: Adapter fertig, Datenfreigabe ausstehend

Quelle: [ftdnastat/ftdnastat.github.io](https://github.com/ftdnastat/ftdnastat.github.io).
Die Software steht unter MIT; daraus wird keine pauschale Lizenz für die
verarbeiteten genetischen Daten abgeleitet. Die konfigurierte Quelle ist vor
jedem Netzwerkzugriff gesperrt, solange `publication_allowed=false` oder kein
geprüfter HTTPS-Nachweis in `data_permission_url` eingetragen ist.

Der überprüfte öffentliche Snapshot enthält:

- `data/egypt.y.json`: Gesamtzahl 622 und 393 terminale Zählungen, deren Summe 622 ist.
- 114 kumulative Zählungen, die sich auf den zugehörigen Backbone mit 175 Knoten
  aus `data/compare-tree.y.json` beziehen.
- Daraus erzeugt der getestete Parser 507 getrennte Zählfakten für die vorhandene
  `ydna_sync_country_counts`-Pipeline. Es wurden davon **0 veröffentlicht**.

Die Dateien müssen aus demselben Git-Commit stammen; Indexgrenzen, Backbonegröße,
Duplikate und Summen werden geprüft. Der komprimierte Anzeigebaum wird nicht als
vollständiger unmittelbarer SNP-Pfad ausgegeben. Terminale und inklusive Zahlen
bleiben getrennt. Die erfasste Testpopulation ist `unknown`, bis ein belastbarer
Nachweis eine genauere Einordnung erlaubt; es wird nicht pauschal Big Y behauptet.

Die separate `version.json` meldete einen neueren YFull-Statistikstand 14.07.00.
Diese Information aktualisiert den offiziellen GitHub-Baum 14.06.0 nicht und ist
kein individueller YFull-Testerfeed. 622 FTDNA-Kits und 257 YFull-Proben dürfen
wegen unbekannter Überschneidungen nicht addiert werden.

Nach erteilter Datennutzungsfreigabe deren zulässige Felder und Bedingungen prüfen,
den Nachweis in `sync/data/sources.json` bei `ftdnastat-egypt-counts` eintragen und
`publication_allowed=true` setzen. Der nächste Lauf verwendet die bestehende
Zählpipeline mit Historie und Upserts. Keine anonymen Zahlen werden in
`Modern_published_samples` oder regionale Testerstatistiken umgewandelt.

## Automatischer Kanal für freigegebene einzelne Tester

`github_public_export` liest einen ausdrücklich zur öffentlichen Veröffentlichung
freigegebenen CSV- oder JSON-Feed aus einem konfigurierten öffentlichen Repository.
Das kann ein bereinigter und genehmigter Projekt-Export oder ein freiwillig
bereitgestellter Testerfeed sein. Private Administratorberichte gehören nicht in
ein öffentliches Repository. Der Betreiber muss die Berechtigung für die
veröffentlichten Daten und Felder vorher klären.

Konfigurationsvorlage, **nicht aktiv und ohne erfundene Tester**:

```json
{
  "id": "approved-project-feed",
  "adapter": "github_public_export",
  "repo": "OWNER/APPROVED-PUBLIC-FEED",
  "branch": "main",
  "path": "public-testers.csv",
  "format": "csv",
  "url": "https://github.com/OWNER/APPROVED-PUBLIC-FEED",
  "enabled": false,
  "publication_allowed": false,
  "permission_url": "https://example.org/documented-permission"
}
```

CSV-Pflichtspalten: `namespace`, `external_id`, `country`, `origin_kind`,
`sample_kind`, `publication_consent`, `source_url`. Ein leerer Header wird unter
`sync/imports/approved-public-testers.template.csv` mitgeliefert. Jede Zeile braucht
eine ausdrückliche Zustimmung `true`, `yes` oder `1`, zusätzlich zur Quellenfreigabe.
Weitere unterstützte Felder sind `name`, `ancestor_name`, `origin_raw`, `project`,
`y_dna`, `y_dna_alias`, `test_type`, `haplogroup_status`, `full_snp_path` und
`path_source_url`. STR-Spalten verwenden geprüfte Markerlabels; Spaltenreihenfolge,
Originalbezeichnung, Nullallele `0`, Mehrfachwerte und unbekannte Leerwerte bleiben
erhalten. Ein normaler Rohbericht ohne diese erforderlichen Herkunfts- und
Freigabefelder wird nicht stillschweigend als genehmigt behandelt.

JSON verwendet das vorhandene `sync/exchange.schema.json` inklusive belegter
Identitätsverknüpfungen, Quellpfade, STR-Historie und expliziter Rücknahmen. Der
Adapter importiert akzeptierte Profile über denselben bestehenden Prüf- und
Upsertweg. YFull-IDs begründen weiterhin keinen Big-Y-Test.

**Noch fehlt ein konkreter, regelmäßig aktualisierter genehmigter individueller
Feed.** Daher wurden mit dieser Erweiterung keine neuen Testerprofile importiert.
Der Kanal ist implementiert und getestet; ohne diesen Input kann er keinen
individuellen Datenzuwachs erzeugen.

## Betrieb und Prüfung

Nach Merge startet eine Änderung an `sync/**` sofort einen Actions-Lauf;
anschließend gilt weiterhin **00:23 und 12:23 UTC**. Manuelle Starts über
`Public Y-DNA synchronization` sind möglich; `apply=false` ist ein Dry Run.
Das vorhandene Secret `SUPABASE_SERVICE_ROLE_KEY` genügt, es gibt kein neues Secret.
GitHub-Dateien werden ohne Token über veröffentlichte REST-/Raw-Schnittstellen
gelesen. Direkte FTDNA-/YFull-Webseiten bleiben von den bisherigen Zugriffsgates
geschützt.

`ydna-sync-report` zeigt unter der Quelle `yfull-github` Version, Quellcommit,
Publikationsdatum, ausgewählte Knoten, Abgleiche, Änderungen und Importstatus.
`profiles_created: 0` bei einem Baumimport ist korrekt. `partial` ist bei weiterhin
gesperrten anderen Quellen erwartbar; entscheidend ist ein erfolgreicher
`yfull-github`-Eintrag. In Supabase stehen der aktuelle Baum in
`ydna_sync_tree_releases` / `ydna_sync_official_tree_nodes` und die Laufberichte in
`ydna_sync_runs`.

Verifikation dieser Erweiterung: 53 Python-Tests, 17 JavaScript-Szenarien,
transaktionale Postgres-Tests einschließlich unvollständiger Veröffentlichung,
atomarem Standwechsel und Schreibsperre für Browserrollen. Der Browsercheck lädt
die lokalen Änderungen mit echten öffentlichen Supabase-Daten und prüft
Topologieumschaltung, gleiche Testerzahl, Quelle/Lizenz/Altersangaben sowie die
bisherigen Filter, STR-Details und mtDNA. Die Tests legen keine synthetischen
Tester im produktiven Archiv an.
