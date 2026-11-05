# Egypt Y-DNA

Bestehende Website: https://egyptydna.github.io/Egypt-Y-DNA/

Die Website liest das bestehende Supabase-Projekt `lsfmpmfoqdtkgndtaxen`.
Der Importdienst läuft unabhängig von Websitebesuchen in GitHub Actions stündlich.
Die [Projektverfolgung](docs/PROJECT-TRACKING.md) speichert fortsetzbare Nachsuchen,
exakte Kit-Mitgliedschaften, getrennte anonyme Linienkandidaten und den Prüfstatus.
Unter **New results** stehen neu hinzugefügte öffentliche Profile für 30 Tage.
Die [Profildetails](docs/PROFILE-DETAILS.md) erklären terminale Pfade, STR-Belege
und CSV-Download sowie die Trennung anonymer Zählungen von identifizierten Proben.
Der neue offizielle YFull-GitHub-Adapter und genehmigte Testerfeeds sind unter
[GitHub-Datenquellen](docs/GITHUB-DATENQUELLEN.md) dokumentiert. Der erste lizenzierte
YFull-Teilbaum ist importiert und der GitHub-Quellenlauf ist auf `main` aktiv. Ein zusätzlicher
[Abgleich der eigenen Archive](docs/OWNED-ARCHIVE-BRIDGE.md) übernimmt bereits
gespeicherte belegte Tester und getrennte FTDNA-Zählungen in dieselbe Datenbank.

**Betrieb, tatsächliche Quellenbeschränkungen, Secrets, Migrationen und erster Importbericht:**
[Synchronisierungsdokumentation](docs/SYNCHRONISIERUNG.md).

```sh
python -m pip install -r sync/requirements.txt
python -m unittest discover -s sync/tests -v
node --test sync/tests/frontend.test.cjs
npm ci --ignore-scripts
npm run build:styles
python -m sync.run
```

Standardmäßig ist dies ein Dry Run. Schreibzugriffe erfordern ein serverseitiges
`SUPABASE_SERVICE_ROLE_KEY` und für automatische Veröffentlichungen eine geprüfte Quellenfreigabe.
