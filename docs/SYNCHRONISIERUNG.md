# Automatische Synchronisierung – Betriebsdokumentation

Stand: 4. November 2026. Repository: https://github.com/egyptydna/Egypt-Y-DNA

**Aktualisierter Quellenbefund:** Die vollständigen FTDNA-Bedingungen untersagen auch automatisiertes Monitoring und systematische Datenbankübernahme ohne entsprechende Erlaubnis. Weitere Ergebnisabrufe werden deshalb bereits vor dem Netzwerkzugriff gesperrt. Siehe [Quellenbefund und vorbereitete Freigabeanfragen](QUELLENFREIGABE.md). Die ursprünglichen Abrufbefunde unten beschreiben nur die technische Erreichbarkeit im ersten Test, keine erlaubte Dauerüberwachung.

Bereitgestellt in [Pull Request #1](https://github.com/egyptydna/Egypt-Y-DNA/pull/1). Die Live-Website und der geplante Actions-Lauf erhalten den neuen Code erst nach Freigabe und Merge. Die unten aufgeführten Supabase-Migrationen und privaten Prüffälle sind bereits eingerichtet.

## Tatsächlicher Stand

Die bestehende GitHub-Pages-Website und das Supabase-Projekt `lsfmpmfoqdtkgndtaxen` werden weiterverwendet. Es gibt keine zweite Website. Der Importdienst läuft als Python-Prozess in GitHub Actions, unabhängig von Websitebesuchen.

Die Software und die Datenbankerweiterungen sind implementiert. **Ein vollständig freigeschalteter automatischer Datenzuwachs ist noch nicht gegeben:** Der Zugriff auf Actions-Secrets wurde mit HTTP 403 verweigert, und für die technisch auslesbaren FTDNA-Ergebnisse fehlt ein belegter Nachweis zur Weiterveröffentlichung. Dieser Nachweis wird ausdrücklich getrennt von öffentlicher Abrufbarkeit behandelt. YFull verbietet allgemeinen Crawlerzugriff laut robots.txt.

## Ergebnis des ersten realen Laufs

| Ergebnis | Anzahl |
|---|---:|
| Erfasste öffentliche J-M267-Kandidaten mit Herkunftsland Egypt | 127 |
| Eindeutige externe IDs darunter | 127 |
| Duplikate innerhalb dieses Abrufs | 0 |
| Neu ins öffentliche Archiv importierte Tester | 0 |
| Veränderte vorhandene Tester | 0 |
| Private Prüffälle wegen fehlendem Weiterveröffentlichungsnachweis | 127 |
| Zusätzlicher Prüffall für einen bereits vorhandenen doppelten Kit-Eintrag | 1 |
| Vorhandene moderne Archivzeilen nach Migration | 330 |
| Im Frontend nach gleicher Kitnummer deduplizierte moderne Profile | 329 |

Die privaten Prüffälle liegen in `ydna_sync_reviews`. Der initiale kontrollierte Prüflauf übernahm keine Namen, Vorfahrennamen oder STR-Profile in diese Prüfliste. Den öffentlichen Quellenlink und die ID kann die Projektpflege dort nachprüfen. `docs/initial-dry-run.json` enthält nur Zählungen und Quellenstatus, keine Testeridentitäten. Die vorhandenen 330 modernen, 68 antiken, 18 Studien- und 20 verwandten antiken Archivzeilen wurden mit den Sicherungskopien verglichen und blieben inhaltlich unverändert.

## Welche Quellen funktionieren

| Quelle | Geprüftes Ergebnis | Automatischer Weg |
|---|---|---|
| FTDNA J-M267 | Öffentliche HTML-Tabelle und normales öffentliches Länderfilterformular funktionieren; 127 Egypt-Zeilen | Adapter implementiert, Publikationsfreigabe ausstehend |
| FTDNA Egypt | „Results pages are visible to group members only“ | Kein Abruf privater Ergebnisse; zulässiger öffentlicher Export nach Freigabe |
| FTDNA E-M35 | Ungefilterte öffentliche Tabelle erreichbar; gefilterter Lauf ohne unterstützte Ergebnistabelle | Als nicht verfügbar protokolliert; derzeit keine Ergebnisse übernommen |
| FTDNA T | Ergebnisse nur für Mitglieder | Deaktiviert |
| FTDNA G | HTTP 500 bei Prüfung | Deaktiviert, erneut prüfbar |
| FTDNA R1b | Timeout bei Prüfung | Deaktiviert, erneut prüfbar |
| YFull YTree | robots.txt: `User-agent: *`, `Disallow: /` | Allgemeiner Crawl deaktiviert; Adapter für ausdrücklich erlaubte öffentliche JSON-Exporte |
| FTDNA Discover / Haplotree / Group Time Trees | Keine freigegebene individuelle Tester-Datenschnittstelle verifiziert | Kein interner API-Zugriff; freigegebene Pfade/Aliase können über den Exchange importiert werden |

Die kanonische FTDNA-URL ist `https://www.familytreedna.com/public/PROJECT?iframe=ydna-results-overview`. Veraltete `ycolorized`-URLs leiten auf die öffentliche Übersichtsseite um; der Dienst ruft die kanonische HTTPS-URL direkt auf. Er umgeht keine Login-Seite und folgt keinen Redirects. Das Land wird über das normale HTML-Formular gefiltert, einschließlich der dort veröffentlichten Formularfelder. Keine Administrator-Endpunkte, Logins oder privaten APIs werden verwendet.

Der Projektkatalog steht in `sync/data/sources.json`. Der Link-Entdecker sammelt weitere öffentliche Projektlinks in den Laufbericht; neue Projekte werden vor Aktivierung auf Sichtbarkeit, Bedingungen und Publikationsrechte geprüft. Es gibt keine unbeschränkte Suche über sämtliche FTDNA-Projekte. SNP-only-Seiten ohne unterstützte öffentliche Tabelle werden ebenfalls als nicht verfügbar behandelt.

Genehmigte FTDNA-Abrufe beachten robots.txt und mindestens fünf Sekunden Abstand pro Host. Ohne Zugriffserlaubnis finden keine Ergebnisabrufe statt. Temporäre Fehler erhalten maximal drei Versuche mit Wartezeit; 401/403, Formatänderungen, private Seiten und robots-Ausschlüsse werden protokolliert. Die öffentlichen Formularseiten müssen erneut abgerufen werden. **Inkrementell sind die Datensatzänderungen:** unveränderte Beobachtungen werden anhand ihres Inhalts wiedererkannt, statt neue Profile oder Historienzeilen zu erzeugen. ETag-Unterstützung ist für geeignete statische Abrufe vorhanden; es wird keine nicht belegte serverseitige Delta-API behauptet.

## GitHub Actions einschalten und prüfen

1. Unter [Actions-Secrets](https://github.com/egyptydna/Egypt-Y-DNA/settings/secrets/actions) das Secret `SUPABASE_SERVICE_ROLE_KEY` aus genau diesem Supabase-Projekt anlegen. Nicht in HTML, Repository, Issues oder Chat einfügen. Ein Publishable-/Anon-Key reicht zum Importieren nicht.
2. GitHub Actions im Repository aktivieren. `Public Y-DNA synchronization` verwendet `.github/workflows/ydna-sync.yml` und läuft täglich um **00:23 und 12:23 UTC** auf dem Standardbranch. GitHub-Zeitpläne können sich verspäten und bei langer Repository-Inaktivität deaktiviert werden; den letzten erfolgreichen Lauf regelmäßig prüfen.
3. Über **Run workflow** zunächst `apply=false` verwenden. Der Dry Run benötigt keinen Service-Key und verändert die Datenbank nicht. Bericht: Job Summary und Artifact `ydna-sync-report` (14 Tage Aufbewahrung).
4. Erst nach dokumentierter externer Freigabe pro Quelle `automated_access_allowed=true` und `access_permission_url` für den automatisierten Zugriff sowie `publication_allowed=true` und `permission_url` für die Übernahme mit den überprüften Freigabenachweisen im Katalog setzen. Die Zustimmung des Websitebetreibers allein ersetzt keine Rechte des Datenanbieters. Die Freigabefelder sind keine automatisierte rechtliche Bewertung.
5. `apply=true` führt den Import mit dem Secret aus. Planläufe verwenden den Schreibmodus. Nicht freigegebene Treffer bleiben privat zur Prüfung vorgemerkt. Der Prozess schlägt bei fehlendem Schlüssel ausdrücklich fehl.
6. In Supabase `ydna_sync_runs`, `ydna_sync_sources` und `ydna_sync_reviews` kontrollieren. `partial` bedeutet, dass mindestens eine Quelle nicht verfügbar war; andere Quellen werden weiter verarbeitet. Ausfälle löschen keine Bestandsdaten.

Lokal aus dem Repository:

```sh
python -m pip install -r sync/requirements.txt
python -m unittest discover -s sync/tests -v
node --test sync/tests/frontend.test.cjs
python -m sync.run
# SUPABASE_SERVICE_ROLE_KEY ausschließlich als geschützte Umgebungsvariable bereitstellen:
python -m sync.run --apply
```

Der Import verweigert eine andere `SUPABASE_URL`. Gleichzeitige Actions-Läufe werden serialisiert; zusätzlich serialisiert ein Postgres-Advisory-Lock die einzelnen Importtransaktionen.

## Identität, Konflikte und Tree

`Modern_published_samples` bleibt die Frontend-Haupttabelle. Ergänzende Tabellen speichern verifizierte externe IDs, Quellenaussagen und STR-Historie. Eine gleiche FTDNA-Kitnummer identifiziert dasselbe Profil über Projekte hinweg. Eine YFull-ID wird nur bei einem veröffentlichten Verknüpfungsnachweis (`identity_evidence_url` und `verified_ids`) an ein FTDNA-Profil gebunden. Bestehen bereits zwei getrennte widersprüchliche Archivprofile, wird der Fall zur Prüfung vorgemerkt statt eine Zeile zu löschen.

Manuelle Bestandswerte werden nicht überschrieben. Bei automatisch angelegten Profilen darf die ursprüngliche Quelle nur solche Werte aktualisieren, die weiterhin dem zuletzt automatisch veröffentlichten Wert entsprechen. Manuelle Änderungen und abweichende andere Quellen erzeugen Konflikte. Fehlende Angaben überschreiben keine gültigen Angaben.

Der Tree zeigt vorhandene sowie künftig akzeptierte importierte Tester. Big Y wird nur aus einem expliziten Testnachweis abgeleitet; YFull bleibt `YFull sequencing`. STR-Vorhersagen sind gekennzeichnet. Tester ohne belegten vollständigen Pfad bleiben mit ihrer veröffentlichten Terminalbezeichnung sichtbar. Ein eindeutiger vorhandener veröffentlichter Pfad zur gleichen Terminalgruppe kann wiederverwendet werden; widersprüchliche Pfade werden nicht automatisch kombiniert. Die Wurzelansicht eines Terminal-only-Testers behauptet keine direkte phylogenetische Abstammung von der Navigationswurzel.

Explizit belegte Pfade und Aliase können aus erlaubten Exporten importiert werden. Der Dienst erfindet keine Zwischenstufen, leitet keine Individuen aus Knotenzahlen ab und behauptet keine automatische FTDNA/YFull-Nomenklaturauflösung ohne Quellennachweis. Eine vollständige globale SNP-Topologie wird derzeit nicht automatisch geholt. FTDNA-Aggregatzahlen werden daher auch nicht als individuelle Tester angezeigt.

Knoten zeigen direkte moderne Tester sowie kumulierte moderne und bestätigte Big-Y-Tester. Filter: moderne Tester, Big Y, YFull, STR-only, SNP-tested, Gouvernement, Haplogruppe und neue Profile im letzten Synchronisierungslauf. Kit-, Namens-, Orts-, Projekt- und SNP-Suche sind vorhanden. Im Testerfenster stehen öffentliche Quellenaussagen, Aktualisierungsdatum und eine durchsuchbare STR-Tabelle. Mehrere Tester lassen sich über „Add to STR comparison“ gegenüberstellen. Abweichende und frühere Werte bleiben sichtbar; es wird kein genetischer Abstand aus unsicheren Werten errechnet.

## Orte und regionale Statistik

`sync/data/governorates.json` enthält alle 27 Gouvernements mit ISO-3166-2-Schlüsseln, kompatiblen Frontendnamen und Aliasnamen. Port Said und New Valley sind ergänzt. `sync/data/places.json` enthält 12.238 administrative Einheiten und bewohnte Orte aus dem am 4. November 2026 geladenen GeoNames-Egypt-Export. Die 27 Gouvernements sind zusätzlich in `ydna_sync_places` gespeichert. Maßgeblich für die Offline-Ortsauflösung ist die lokale, mitgelieferte Datei; es gibt keine Anfrage an einen externen Geocoder pro Tester.

Lizenz, Quelle und Archivprüfsumme: `sync/data/LICENSE.md` (GeoNames, CC BY 4.0). Aktualisierung nach einem neuen rechtmäßig geladenen Export: `python scripts/build_gazetteer.py /pfad/EG.zip`. Die Daten sind erweiterbar, aber **kein garantiert vollständiges Verzeichnis jedes Dorfes oder historischen Namens**. Das GeoNames-Bezirksfeld wird erhalten, ist aber nicht für jeden Ort gefüllt.

Arabische Diakritika, Alif-Varianten und vorhandene Transliterationen werden normalisiert. Die Zuordnung verwendet exakte Namen bzw. durch Komma/Trennzeichen abgegrenzte Ortsbestandteile. Es gibt keine automatische unscharfe Zuordnung von beliebigem Freitext. Mehrdeutige oder widersprüchliche Ortsangaben landen in der Prüfliste. Ohne belegtes ägyptisches Herkunftsland wird ein international mehrdeutiger Ortsname nicht zur Nationalitätsbestimmung verwendet. Wohnorte werden nicht als väterliche Herkunft ausgewertet.

Eindeutig zugeordnete akzeptierte Tester fließen über dieselbe Haupttabelle in die vorhandenen regionalen Statistiken ein. Das Frontend dedupliziert gleiche Kitnummern und berücksichtigt in regionalen Y-DNA-Verteilungen nur Profile mit Y-DNA-/STR-Nachweis. Unbekanntes Gouvernement bleibt in der landesweiten Y-DNA-Statistik enthalten. Bestehende mtDNA-, Studien- und Ancient-Bereiche bleiben erhalten.

## Erlaubte alternative Importe

`sync/exchange.schema.json` dokumentiert das JSON-Exchangeformat. Es muss sich um ausdrücklich freigegebene öffentliche Angaben handeln, **nicht um private Administrator-Exporte**. Datei unter `sync/imports/` ablegen und im Quellenkatalog einen `public_export`- oder `yfull_export`-Adapter mit Pfad und Freigabenachweis konfigurieren. Für GitHub Actions muss ein zur Veröffentlichung erlaubter Export mit im Checkout vorhanden sein. Nicht zur Repository-Veröffentlichung erlaubte Dateien gehören nicht in das öffentliche Git.

Die Datei benötigt `schema_version: 1`, `permission_url` und `records`. Moderne, wissenschaftliche und antike Proben werden über `sample_kind` unterschieden; nur `modern` wird automatisch in die moderne Haupttabelle übernommen. `origin_kind` muss `paternal` sein. Pfade benötigen `path_source_url`; der letzte Pfadknoten muss die Terminalgruppe sein. Aliase stehen unter `snp_aliases`. Jeder STR-Wert braucht Originalmarkername, geprüften Normalnamen, Originalposition und exakten Stringwert oder `null`. Nullallele `"0"` und Mehrfachallele bleiben erhalten. Externe Identitäten und STR-Werte werden zur Laufzeit validiert; das JSON-Schema ist zusätzlich Dokumentation für Exportanbieter.

Eine Quellenfreigabe führt beim nächsten Lauf zur erneuten Prüfung, nicht zur blinden Übernahme der alten Prüfliste. Unaufgelöste alte Prüffälle können anschließend durch die Pflege mit Begründung auf `resolved` gesetzt werden. Es gibt bewusst keine öffentlich zugängliche Moderationsoberfläche mit Schreibrechten.

## Datenbank und Sicherung

Durchgeführt:

- `20261104151006_public_ydna_sync`: Backup-Schema, additive Haupttabellenspalten, neun ergänzende Tabellen, RLS, Grants, transaktionale Import- und Opt-out-Funktionen.
- `20261104151505_ydna_visibility_and_private_metadata`: explizite Sperrregeln für private Metadaten, Opt-out auch für Altprofile, nachweisbare Sichtbarkeitsrücknahme und Prüffall für den vorhandenen Doppel-Kit-Eintrag.
- `20261104170036_country_count_profile_reconciliation`: getrennte Quellen-Knotenzahlen, Beobachtungshistorie und kontrollierte Importfunktion; siehe [Knotenzahlen und Tester](KNOTENZAHLEN-UND-TESTER.md). Die Anzeige wird mit dem zugehörigen Frontend-PR veröffentlicht; bisher wurden keine Live-Knotenzahlen angelegt.

Die Migrationsdateien entsprechen den tatsächlich gespeicherten Remote-Migrationsversionen. Die lokale CLI konnte in dieser Umgebung keine Migrationsdatei erzeugen; die finalen Dateien wurden deshalb aus den über die Supabase-Integration angewandten, zuvor transaktional geprüften Migrationen übernommen. Keine zweite Datenbank und keine destruktive Schemaänderung wurden angelegt.

Vor den Erweiterungen wurden `ydna_backup.modern_before_sync`, `ancient_before_sync`, `study_before_sync` und `related_before_sync` angelegt. Der Zugriff ist für öffentliche Rollen gesperrt. Das ist eine projektinterne Sicherung, kein Ersatz für unabhängige Backups oder PITR. Vor weiteren produktiven Migrationen zusätzlich einen verschlüsselten externen Daten-/Schemaexport oder ein verfügbares Supabase-Backup sichern. Bestehende RLS-Regeln, Trigger und übrige Anwendungstabellen wurden erhalten.

Alle neuen öffentlichen Tabellen haben RLS. Nur bestätigte veröffentlichte Beobachtungen, ihre STR-Belege, Tree-Knoten und bereinigte Laufberichte sind lesbar; Identitätenregister, Quellenkonfiguration, Opt-out-Tombstones und Prüfliste sind für Browserrollen gesperrt. Schreibfunktionen sind `SECURITY INVOKER` und nur `service_role` zugänglich. Die Sicherheitsprüfung meldete keine neue Warnung für die Importfunktionen. Bereits vorhandene Warnungen zu `rls_auto_enable`, veränderlichen Suchpfaden bestehender Hilfsfunktionen und deaktivierter Passwort-Leak-Prüfung betreffen den Altbestand und wurden nicht außerhalb dieses Auftrags geändert.

## Sichtbarkeitswechsel und Opt-out

Eine nicht erreichbare Quelle oder das Verschwinden aus einer möglicherweise unvollständigen Tabelle beweist keinen Opt-out. Solche Fälle werden nicht zur Löschung benutzt. Die FTDNA-Formularantworten gelten vorsichtshalber als teilweise Snapshots; eine globale Vollständigkeit oder vollständige Erfassung sämtlicher Big-Y-STR-Marker wird nicht behauptet.

Ein erlaubter Export kann `visibility: "withdrawn"` mit `withdrawal_evidence_url` liefern. `ydna_sync_withdraw` sperrt die betroffene Quelle. Fehlt für ein automatisch verwaltetes Profil jede weitere veröffentlichte Beobachtung, wird das Profil ausgeblendet. Manuelle Bestandsprofile bleiben zur Prüfung vorgemerkt. Wiederfreigaben erfolgen nach Prüfung, nicht durch einen Ausfall-/Wiederanlauf-Automatismus.

Ein verifizierter Entfernungswunsch wird serverseitig bearbeitet:

```sql
select public.ydna_sync_opt_out(PROFIL_ID);
```

Dabei werden identifizierende Live-Felder entfernt, öffentliche Sichtbarkeit gesperrt, Quellendetails und zugehörige Prüffälle gelöscht und nicht umkehrbare ID-Hashes gegen Wiederimporte gespeichert. Die Pflege muss den Entfernungswunsch zusätzlich auf private Backups, eventuell exportierte Dateien und weitere eigene Kopien anwenden; die Sicherungskopien werden aus Gründen des Bestandsschutzes nicht pauschal automatisch gelöscht. Den Browsercache nach einer Entfernung neu laden.

## Tests und Verifikation

`Y-DNA checks` führt Python- und JavaScript-Tests aus. Ein separater Postgres-17-CI-Job spielt die Migrationen in eine **wegwerfbare** Datenbank ein und führt die Transaktionsszenarien aus. `sync/tests/baseline.sql` darf niemals im bestehenden Supabase-Projekt ausgeführt werden.

Abgedeckt: neuer Big-Y-Tester, gleiche ID in drei Projekten, belegte YFull/FTDNA-Verknüpfung, YFull ohne Big-Y-Schlussfolgerung, wissenschaftliche/antike Proben, STR-Vorhersage, Terminalwechsel, manuelle Korrekturen, zusätzliche und historische STR-Werte, Mehrfachallele und Nullallele, arabische/transliterierte Orte, Mehrdeutigkeit, Land ohne Gouvernement, vorübergehender Ausfall, Mitgliedersperre, explizite Sichtbarkeitsrücknahme, Opt-out und unveränderter Wiederholungslauf.

Die Postgres-Szenarien wurden zusätzlich im Zielprojekt sowohl privilegiert als auch als `service_role` mit `BEGIN`/`ROLLBACK` ausgeführt. Es blieben keine synthetischen Tester in der Datenbank.

Der Browsercheck `scripts/check_browser.py` liest echte Supabase-Daten und prüft die lokale Codeversion unter der bestehenden Website-Origin. Er prüft Y-Tree, Big-Y-Filter, Testerfenster und mtDNA sowie STR-Suche, Vergleich und Regionalzählung mit einem klar als synthetisch markierten **Browser-Speicher**-Datensatz. Er benötigt Playwright und Chromium und schreibt keine Tester in Supabase.
