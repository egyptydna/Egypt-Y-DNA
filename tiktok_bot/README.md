# Egypt Y-DNA — TikTok Review Bot

## Zweck

Kostenloses Review-first-System mit GitHub Actions, dem bestehenden veröffentlichten
Egypt-Y-DNA-Archiv in Supabase und Buffer Free. **Keine neue einzelne DNA-Probe wird
behauptet, wenn nur ein Haplogruppen-Zähler oder ein YFull-Tree geändert wurde.**

## Ablauf

- Zwei Kontrollen täglich (06:17 und 18:17 UTC), auch wenn die Website geschlossen ist.
- Der Scanner liest ausschließlich bereits öffentlich freigeschaltete, aktive moderne
  Archiveinträge mit ausdrücklich genanntem ägyptischen Ursprung und einem HTTPS-Link zu
  FamilyTreeDNA oder YFull. Vorhandene Altbestände werden beim Start nicht nachgepostet.
- Für neue Archivdatensätze der letzten 7 Tage werden maximal vier GitHub-Review-Issues
  pro Lauf angelegt. Derselbe Archivdatensatz erzeugt nur ein Issue (auch bei Wiederholungen).
- Drei **synthetische, selbst generierte** 1080x1920-PNGs und eine englische Caption
  werden vorbereitet, als 30 Tage verfügbares GitHub-Actions-Artefakt. Kein fremdes
  Kartenmaterial, keine kopierten Anbieter-Screenshots und keine hypothetischen
  Migrationsrouten.
- **Ausdrückliche Freigabe:** Erst wenn der Repository-Eigentümer in
  Actions → Egypt Y-DNA TikTok review → Run workflow den Modus approve
  und die Review-Issue-Nummer eingibt, werden die freigegebenen Grafiken
  unter tiktok/approved/ veröffentlicht und als Buffer-**notification** eingeplant.
- Buffer erinnert zur Veröffentlichung in TikTok; die passende Nasheed ist
  **manuell in TikTok** aus rechtmäßig nutzbaren Tönen auszuwählen.
  Es erfolgt keine direkte automatische Veröffentlichung ohne Musikfreigabe.
- Zur Ablehnung ein Review-Issue schließen. Änderungen am Archivdatensatz nach
  Generierung verhindern die alte Freigabe; dann ist eine neue Prüfung nötig.

## Quellenstatus

Das bestehende Repository enthält bereits eine Synchronisation für den
**offiziell CC-BY-4.0-lizenzierten YFullTeam/YTree-Baum** sowie getrennte
**FTDNA-Länderzahlen**. Die Datei tiktok_bot/alerts.py erstellt daraus
eigene Research-Alerts, wenn ein datierter neuer FTDNA-Gesamtstand oder eine
tatsächliche YFull-Baumänderung erkannt wird. Es wird daraus **kein** neuer
individueller ägyptischer Tester abgeleitet.

Der vorhandene FTDNA-Import untersagt selbst automatische Ergebnisabrufe
ohne zusätzliche Anbieterfreigaben (siehe docs/QUELLENFREIGABE.md).
Der YFull-GitHub-Baum enthält keine individuellen Herkunftsangaben.
Daher ist derzeit **keine garantierte automatische Entdeckung aller neuen
individuellen ägyptischen Proben direkt bei beiden Anbietern** möglich.
Neue individuelle TikTok-Kandidaten stammen nur aus bereits rechtmäßig
veröffentlichten und in das eigene Archiv übernommenen Ergebnissen.

## Geheimnisse und Sicherheit

Das Repository benötigt in Actions bereits:
- SUPABASE_SERVICE_ROLE_KEY (aus dem vorhandenen Sync-Workflow)
- BUFFER_API_KEY (vom Eigentümer hinzugefügt)

Beide bleiben GitHub Actions Secrets; nicht in Chats, Issues oder Code kopieren.
GITHUB_TOKEN wird von GitHub bereitgestellt. Das Bot-Skript nimmt keinen
beliebigen Supabase-Projekt-Endpunkt an und kann nicht automatisch in einem
anderen TikTok-Kanal posten: bei mehreren verknüpften TikTok-Kanälen stoppt
der Approval-Lauf sicher. Ein GitHub-Issue enthält keine Namen oder Kitnummern.

Die Approve-Funktion ist auf den GitHub-Nutzer egyptydna beschränkt.
Im Free-Plan von Buffer gelten Anbietergrenzen. Ein vom Anbieter oder von
GitHub verzögerter Zeitplan wird nicht als Echtzeitüberwachung dargestellt.

## Aktivierung

1. Pull Request begutachten und zusammenführen.
2. GitHub → Actions → Egypt Y-DNA TikTok review → Run workflow → scan
   (oder nächsten planmäßigen Lauf abwarten).
3. In GitHub → Issues einen neuen [TikTok Review]-Eintrag ansehen;
   die Slides liegen unter dem im Issue angegebenen Actions-Artefakt.
4. Nach fachlicher Prüfung Approve-Workflow mit Issue-Nummer starten.
5. In Buffer/TikTok Nasheed auswählen und Beitrag fertigstellen.

Die Grafiken sind ein neutrales funktionierendes Grundlayout, **keine exakte
Reproduktion der früheren Karten- und YFull-Screenshot-Beiträge**. Für genaue
Kartenrouten oder Branch-Darstellungen sind verifizierte räumliche oder
phylogenetische Eingabedaten nötig.
