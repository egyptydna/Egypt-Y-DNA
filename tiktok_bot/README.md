# Egypt Y-DNA – External source watch (kein Archivscan)

## Ziel

Zweimal pro Tag prüfen, ob in **extern veröffentlichten Datensnapshots**
zu FamilyTreeDNA und YFull neue ägyptische Y-DNA-Ergebnisse sichtbar sind.
Das bestehende Egypt-Y-DNA-Archiv ist **nicht** Eingabe dieser Prüfung.

Die GitHub Action ist unter
`.github/workflows/egypt-tiktok-review.yml` eingerichtet:
06:17 und 18:17 UTC. Manuell auch über Actions → Egypt Y-DNA external source watch.

## Tatsächliche Quelle und Einschränkungen

Zugriff auf die selbst von FTDNA und YFull betriebenen Tester-Datenbanken
per automatischem Crawling ist derzeit **nicht** freigegeben:
- [FTDNA ToS](https://www.familytreedna.com/legal/terms-of-service): Automatisiertes
  Crawlen/Monitoring und systematisches Kopieren ist ohne entsprechende
  Freigabe beschränkt.
- [YFull robots.txt](https://www.yfull.com/robots.txt): Allgemeiner Crawl-Zugriff
  ist gesperrt.

Wir umgehen keine Sperren. Stattdessen liest der Bot die **datierten
öffentlichen Auswertungen** von [ftdnastat für Ägypten]
(https://ftdnastat.github.io/en/c/egypt/), veröffentlicht als statische
Dateien auf GitHub:

- `data/egypt.y.json` – FTDNA-Länder-Gesamtzahl, keine Testeridentitäten
- `en/c/egypt/index.html` – YFull-Abschnitt „New Y-DNA samples in YFull“
  mit Zweigbezeichnungen, sowie FTDNA/YFull Snapshot-Daten
- `version.json` – Datumsabgleich der YFull-Veröffentlichung

Der Bot erkennt:
- YFull-Zweige, die im **datierten Snapshot** als mit neuen Proben
  versehen markiert sind; der eigentliche Tester und seine ID sind damit
  **nicht** belegt.
- Erhöhte oder verringerte FTDNA-Länder-Gesamtzahlen seit dem letzten
  gespeicherten Snapshot; **keine** individuelle neue FTDNA-Kitnummer.

Ein neuer Zweig ist nicht gleichbedeutend mit einer bestimmten neuen
Person, und die Auswertung ist nicht in Echtzeit. Datum, Quelle,
Unsicherheit und Art des Ereignisses stehen in jedem Issue.

## Review und Veröffentlichung

Bei einem relevanten externen Signal wird ein **GitHub-Issue
[TikTok Source Review]** erstellt, mit SNP-Zweig, Datum und Quellen.
Es werden nur einmal je datiertem YFull-Eintrag bzw. FTDNA-Snapshot
Prüf-Issues angelegt. Der Prüfer verifiziert zuerst den originalen
Tester-Nachweis. Die bloße Drittquellen-Auswertung reicht nicht
für einen individuellen TikTok-Post.

Diese Ausbaustufe veröffentlicht **nichts** an Buffer oder TikTok. Die
vorherige Archiv-basierte Scan-/Approve-Funktion wurde aus dem aktiven
GitHub-Workflow entfernt. Die vorhandene Buffer-API-Secret bleibt
unverändert für eine spätere freigegebene Posting-Stufe.

## Speicherung

Der letzte externe Stand wird als kompakte JSON-Metadaten in
`tiktok_bot/state/provider_watch.json` im Repository gespeichert.
Es werden keine individuellen Profile oder vollständigen fremden
Datenbanken übernommen. Ein fehlerhafter oder veralteter Upstream
liefert eine Fehlermeldung statt eine Behauptung über neue Tests.
