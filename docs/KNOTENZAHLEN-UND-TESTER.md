# Gemeldete Knotenzahlen und öffentlich identifizierte Tester

Die gewünschte Darstellung wird auf Knotenebene umgesetzt: Eine gemeldete ägyptische Gesamtzahl und veröffentlichte Testerprofile stehen zusammen am belegten SNP-Knoten. Die Zahlen werden nicht addiert.

## Beispiel 9 / 1 / 8

Das Beispiel **9 gemeldet, 1 passendes öffentliches Kit, 8 rechnerisch nicht identifiziert** ist ein synthetischer Testfall. Es wurde keine aktuelle FTDNA-Zahl für J-FGC1 behauptet oder als Live-Datensatz gespeichert.

Ein veröffentlichtes Kit zeigt weiterhin seine eigenen Details: ID, veröffentlichten Namen, Herkunft, Testtyp, STRs, Quellenaussagen und Aktualisierungsdatum. Anonyme Knotenzahlen erzeugen keine erfundenen Testerprofile, Kitnummern oder Namen. Ein Kit in mehreren Projekten wird einmal berücksichtigt.

Das ist ein **Vergleich auf Ebene der gezählten Gruppe**, keine Identifizierung einer bestimmten anonymen FTDNA-Zeile. Ohne öffentlichen Identitätsnachweis wird kein beliebiger anonymer Datensatz mit einem Namen versehen. Wenn der gezählte Umfang nicht bekannt ist, werden Gesamtzahl und Testerprofile getrennt angezeigt; es wird kein Restwert geschätzt.

## Welche Profile vergleichbar sind

- `ftdna_big_y`: nur moderne Profile mit veröffentlichter FTDNA-Kitnummer und explizitem Big-Y-Nachweis. STR-Vorhersagen, SNP-only und YFull-only belegen keine Mitgliedschaft in dieser gezählten Gruppe.
- `yfull_modern`: moderne Profile mit regulärer YFull-ID. Daraus wird kein Big-Y-Test abgeleitet.
- `unknown`: Die Art der gezählten Proben ist nicht ausreichend belegt. Keine rechnerische Verrechnung mit Testerprofilen.

`direct` gilt nur für den genauen Terminalknoten. `inclusive` schließt Unterzweige ein, aber nur bei einem veröffentlichten oder eindeutig wiederverwendbaren veröffentlichten SNP-Pfad. Pfade, Testarten und Identitätsverknüpfungen werden nicht erfunden. Verschobene Tester werden anhand ihrer aktuellen Zuordnung neu berücksichtigt. Wenn mehr passende bekannte IDs als gemeldete Proben vorliegen, wird die Abweichung sichtbar; kein Profil wird gelöscht und kein negativer Restwert angezeigt.

Jede Quellenzahl behält ihr Beobachtungsdatum und ihre eigene Quelle. Verschiedene Anbieter und übergeordnete/untergeordnete Knotenzahlen werden nicht zusammengerechnet. Nationale und regionale Statistiken der identifizierten Tester erhalten keine anonymen Zusatzzeilen. Gouvernementsfilter blenden landesweite Quellenzahlen aus.

## Datenbank und Import

Die additive Migration `20261104170036_country_count_profile_reconciliation` ergänzt `ydna_sync_country_counts` und eine ausschließlich für `service_role` aufrufbare Importfunktion. RLS erlaubt Browsern nur veröffentlichte aktuelle Zahlen. Frühere Zahlen bleiben als Historie erhalten; ein älterer Export ersetzt keinen neueren Stand. Widersprüche zum gleichen Quellenzeitpunkt gehen in die private Prüfliste. Bestehende Archivtabellen und Profile werden durch die Migration nicht verändert.

Genehmigte JSON-Exporte können innerhalb von `records` zusätzlich `kind: "country_count"` übergeben. Erforderlich sind `namespace`, `node_label`, `country_code: "EG"`, `reported_count`, `count_scope`, `population`, `observed_at` mit Zeitzone und `source_url`. Ein optionaler `snp_path` braucht einen öffentlichen `path_source_url`. Das Schema steht in `sync/exchange.schema.json`. Ohne ausreichend belegte Freigabe bleibt der Datensatz zur Prüfung vorgemerkt.

Die Verarbeitung läuft im vorhandenen Zwölfstunden-Workflow. Diese Erweiterung schaltet **keinen bislang gesperrten direkten FTDNA-/YFull-Abruf frei**. Die in `QUELLENFREIGABE.md` dokumentierten Zugriffsbedingungen bleiben relevant. Es gibt keine zweite Website und keinen Ersatz der bestehenden Haupttabelle.

## Verifikation

Python prüft Zahlen, Umfang, Datum, Anbieterzugehörigkeit und Pfadbelege. JavaScript prüft insbesondere 9/1/8 statt 10, mehrfache Projekte, STR-only, YFull-only, Ancient, direkte versus kumulierte Zahlen, unbekannte Gruppen und abweichende Quellenstände. Postgres-Tests prüfen Idempotenz, Historie, RLS/Grants und dass aus anonymen Zahlen keine Testerzeilen entstehen. Der Browsercheck zeigt eine 9/1/8-Konstellation ausschließlich mit einem klar gekennzeichneten temporären Browser-Testprofil; die echten Bestandsdaten werden dabei nur gelesen.
