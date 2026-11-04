# Egypt Y-DNA

Bestehende Website: https://egyptydna.github.io/Egypt-Y-DNA/

Die Website liest das bestehende Supabase-Projekt `lsfmpmfoqdtkgndtaxen`.
Der öffentliche Importdienst ist für einen unabhängigen Betrieb in GitHub Actions vorbereitet.
Implementierung: [Pull Request #1](https://github.com/egyptydna/Egypt-Y-DNA/pull/1); Aktivierung nach Merge und Secret-Einrichtung.

**Betrieb, tatsächliche Quellenbeschränkungen, Secrets, Migrationen und erster Importbericht:**
[Synchronisierungsdokumentation](docs/SYNCHRONISIERUNG.md).

```sh
python -m pip install -r sync/requirements.txt
python -m unittest discover -s sync/tests -v
node --test sync/tests/frontend.test.cjs
python -m sync.run
```

Standardmäßig ist dies ein Dry Run. Schreibzugriffe erfordern ein serverseitiges
`SUPABASE_SERVICE_ROLE_KEY` und für automatische Veröffentlichungen eine geprüfte Quellenfreigabe.
