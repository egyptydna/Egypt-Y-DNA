# Regelmäßiger Abgleich der bestehenden eigenen Archive

Stand: 4. November 2026. Ziel bleibt ausschließlich das bestehende Projekt
`lsfmpmfoqdtkgndtaxen` und die GitHub-Pages-Website Egypt-Y-DNA.

Der Betreiber hat die Übernahme der gespeicherten, ursprünglich öffentlich
veröffentlichten Ergebnisse seiner beiden Archive ausdrücklich beauftragt:

- Observatory: `https://egypt-ydna-observatory.kimoeln.chatgpt.site/`, Sites-Projekt
  `appgprj_6a9b4a2a138c8191a9f0ba774037e58a`. Eine bereits vorhandene Aufgabe
  aktualisiert dieses Archiv alle sechs Stunden. Die Brücke liest dessen
  gespeicherten Stand mit legitimiertem Besitzerzugriff.
- Der alte Tracker auf Vercel dient nur noch als historische Herkunft der bereits
  übertragenen Daten. Seit dieser Änderung erfolgen keine Vercel-Netzwerkabrufe.
  Seine stündliche Vercel-Neubauaufgabe wurde auf Betreiberwunsch pausiert.
  Lokal vorhandene Exporte können weiterhin ausdrücklich mit `--tracker` gelesen
  werden; dazu wird weder Vercel noch dessen Speicher benötigt.

Der Abgleich liest ausschließlich das gespeicherte eigene Observatory per GET.
Er startet keinen Quellen-Crawl, keine Projekt-Nachsuche, keinen Vercel-Rebuild
und keinen Sync-POST. Die Übernahmeberechtigung für das eigene Archiv behauptet
keine neue Erlaubnis zum direkten Crawling fremder Anbieter-Webseiten.

## Welche Ergebnisse übernommen werden

`sync/owned_archives.py` validiert die Daten und verwendet ausschließlich die
vorhandenen transaktionalen Importfunktionen:

- Observatory: moderne, ausdrücklich nicht antike `YF...`-Kundenprofile mit
  veröffentlichtem Egypt-Herkunftsland, Terminalgruppe, veröffentlichtem Pfad,
  Originalregion und ursprünglichem YFull-Link. Testart `YFull sequencing`.
  Wissenschaftliche Kennungen, Ancient- und mtDNA-Proben bleiben getrennt.
- Tracker: ausschließlich moderne Y-DNA-Projektzeilen mit einem tatsächlichen
  öffentlichen **Country = Egypt**-Feld und gültiger Kitnummer. Ein im Tracker
  zusammengeführter Ortsname genügt dafür nicht. Verwendet werden die originale
  Haplogruppen- und Testspalte und exakt veröffentlichte STR-Spalten samt Position,
  Originalmarker, Nullallelen, fehlenden Werten und Mehrfachallelen.
- Jede FTDNA-Projektbeobachtung behält eine eigene Quellenidentität. Dasselbe Kit
  in mehreren Projekten erweitert dasselbe Profil; der stärkste ausdrücklich
  veröffentlichte Big-Y-Test wird bei neuen Profilen zuerst verarbeitet. Ein
  Big-Y-Wort im Untergruppentitel genügt nicht als Testnachweis.
- Ein ausdrücklich veröffentlichtes YFull-ID-Feld in derselben Kitzeile kann eine
  Identitätsverknüpfung belegen. Namen oder gleiche Haplogruppen tun das nicht.
- 393 FTDNA-Terminalzählungen des Observatory-Snapshots ergeben 622 anonyme
  Länderzuordnungen. Diese Fakten gelangen separat in `ydna_sync_country_counts`;
  aus ihnen entstehen keine Kitnummern oder Profile. Die Testpopulation bleibt
  `unknown`, statt sämtliche Zuordnungen als Big Y zu bezeichnen.
- Kumulative Länderzahlen werden ausschließlich durch Summieren dieser direkten
  Werte entlang der tatsächlich gespeicherten Quellenpfade abgeleitet. Sie haben
  eine eigene Quelle `owner-observatory-derived-counts`, sind als `inclusive`
  getrennt gespeichert und werden nicht zu den direkten Zahlen addiert.

Fehlende Daten werden nicht geschätzt. Nicht leere manuell gepflegte Bestandswerte
werden nicht überschrieben; widersprüchliche Aussagen erzeugen private Prüffälle.
Der Plan schreibt standardmäßig ausschließlich neue Testerprofile. Zusätzliche
belegte Projektbeobachtungen und STR-Werte werden auch an bestehende, anhand
exakter IDs zugeordnete Profile angehängt, ohne deren gepflegte Felder zu ändern.
Ein abweichender Quellterminal wird getrennt zur Prüfung protokolliert.
`--evidence-only` beschränkt Reparaturläufe vollständig auf vorhandene Profile:
keine neuen Tester und keine Änderung ihrer Felder. Auch dieser Modus respektiert
Opt-outs und ausdrücklich zurückgezogene Quellenbelege. Der optionale Modus
`--guarded-updates` erlaubt Aktualisierungen nur bei automatisch verwalteten
Profilen aus genau ihrer ursprünglichen Quelle, wenn keine Prüffälle offen sind
und keine automatisch verwalteten Felder manuell verändert wurden. Abweichende
manuelle Werte und eine Abschwächung eines expliziten Big-Y-Tests sperren die
Aktualisierung. Andere bestehende Profile bleiben erhalten; neue Quellaussagen
werden gesondert gespeichert. Ein ausdrücklich veröffentlichter Big-Y-Test kann
den angezeigten Nachweis ergänzen, während die ursprüngliche Archivangabe erhalten
bleibt. Ältere Fallback-Snapshots dürfen einen bereits
bekannten neueren Quellenstand nicht zurücksetzen.
Opt-out-Tombstones und Sichtbarkeitssperren bleiben wirksam. Ein fehlender oder
unzugänglicher Archivstand löst keine Löschung aus. Ursprünglicher Quellenlink,
Archivherkunft und erster Archivfund bleiben als Belege erhalten. Das Prüfdatum
des jeweiligen Archiv-Snapshots steht in der privaten Quellenkonfiguration.

Die Observatory-Übernahme von **YF149485 / J-M319 / Al Iskandarīyah** wurde bereits
produktiv geprüft: genau ein Profil, `YFull sequencing`, `EG-ALX`, kein erfundener
FTDNA-Kit. Der Live-Browsercheck bestätigte die Position unter J-M319 und die
Berücksichtigung in der Alexandria-Statistik.

## Ausführung durch eine Hintergrundaufgabe

Dieser Abschnitt ist die vollständige Betriebsanweisung für den autorisierten
Kopierlauf. Der GitHub-Actions-Lauf bleibt unabhängig davon für die lizenzierte
offizielle YFull-Topologie zuständig. Für die privaten eigenen Archivzugriffe
beschafft die Hintergrundaufgabe bei jeder Ausführung einen frischen Sites-Zugang;
es wird kein kurzlebiger Token als dauerhafter GitHub-Secret ausgegeben.

1. Den aktuellen geprüften Code dieses Repositorys verwenden. Falls die Umgebung
   neu ist, das öffentliche Repository `https://github.com/egyptydna/Egypt-Y-DNA`
   schreibgeschützt klonen und `sync/requirements.txt` installieren. Keine fremden
   Repositories oder neue Datenbanken anlegen.
2. Mit Sites `get_site(project_id: appgprj_6a9b4a2a138c8191a9f0ba774037e58a)` den
   aktuellen Besitzerzugriff lesen. Die zurückgegebene URL muss zur oben genannten
   Observatory-Seite gehören. Den zurückgegebenen `siwc_bypass_bearer_token` nur
   verdeckt im Arbeitsspeicher an den folgenden Prozess übergeben; niemals
   ausgeben, in Dateien schreiben oder in den Aufgabenprompt aufnehmen.
3. `python -m sync.fetch_owned_archives --outdir /tmp/egypt-owned-archive-input`
   im PTY starten. Nach der verdeckten Eingabeaufforderung genau ein JSON-Objekt
   mit `owner_authorized: true` und `observatory_token: <frischer Token>` über
   stdin eingeben. Der Prozess liest nur den eigenen Observatory-GET-Endpunkt und sendet das Sites-Zugangstoken
   ausschließlich an seine eigene Site. Vercel wird nicht kontaktiert.
4. Aus den tatsächlich erfolgreich geladenen Dateien den Plan erstellen:

   ```sh
   python -m sync.owned_archives --owner-authorized --guarded-updates \
     --observatory /tmp/egypt-owned-archive-input/observatory.json \
     --outdir /tmp/egypt-owned-archive-sql
   ```

   Eine nicht verfügbare Eingabedatei weglassen. Echte Datensnapshots und erzeugte
   SQL-Dateien bleiben außerhalb des öffentlichen Repositorys und werden nicht
   committed. Die Dateien enthalten keine Laufzeitzugangsdaten.
5. `plan.json` lesen, die feste `project_id` prüfen und die angegebenen SQL-Dateien
   **in der angegebenen Reihenfolge** über Supabase `execute_sql` ausschließlich
   im Projekt `lsfmpmfoqdtkgndtaxen` ausführen. Große Dateien vollständig in
   geordneten Abschnitten lesen, damit kein abgeschnittener Tool-Output als SQL
   ausgeführt wird. Bei einem Fehler sofort stoppen; vorhandene Daten behalten.
   Keine Schema-, RLS-, Grant- oder Quellenzugriffsänderungen vornehmen. Der Plan
   verwendet die vorhandenen Importfunktionen und kleine Transaktionen.
6. Den `ydna_sync_runs`-Bericht dieser `run_id` zurücklesen: importierte Profile,
   unveränderte Beobachtungen, Konflikte und getrennte Zählfakten. Bei einem
   abgebrochenen Lauf dessen Status als `failed` bzw. `partial` dokumentieren,
   ohne SQL- oder personenbezogene Rohdaten in Fehlermeldungen auszugeben.
   Relevante Quellenstatus und Datumsstände prüfen. Unverändert wiederholte
   Datensätze müssen ohne zusätzliche Profile verarbeitet werden.
7. Nur eine knappe Meldung mit Zählungen und konkreten Fehlern erstellen. Keine
   Personennamen, vollständigen genetischen Profile, STR-Tabellen oder Tokens in
   Benachrichtigungen ausgeben. Bei unverändertem normalem Lauf keine zusätzliche
   Meldung senden.

Ein erfolgreicher Kopierlauf bestätigt den Transfer der gespeicherten Daten. Er
belegt nicht, dass alle öffentlichen FTDNA-Projekte oder die gesamte Live-YFull-
Website aktuell geprüft wurden. Die separaten Quellaufgaben und ihre tatsächlichen
Abdeckungsberichte bleiben dafür maßgeblich.
