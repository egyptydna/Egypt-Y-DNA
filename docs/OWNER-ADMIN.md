# Proben selbst verwalten

**Verwalten** erscheint in der Navigation erst nach einer serverseitig bestätigten
Anmeldung mit dem freigeschalteten Betreiberkonto. Auf einem neuen Gerät öffnest
du zuerst den direkten [Anmeldelink](https://egyptydna.github.io/Egypt-Y-DNA/?share=1&state=1&section=admin).
Die öffentliche Registrierung ist geschlossen; es gibt keinen Knopf zum
Erstellen weiterer Konten. Bestehende andere Konten erhalten keine Verwaltungsrechte.
Die Betreiberfreigabe ist fest an das bereits bestätigte Konto gebunden.
Passwort und Anmeldeadresse sind gegen Änderungen über die Auth-API gesperrt.
Eine spätere Änderung benötigt einen ausdrücklichen Auftrag des Betreibers und
eine kurze, einmalige Freigabe durch die Datenbankverwaltung. Neue Passwörter
werden ausschließlich im geschützten Anmeldedienst eingegeben, nicht im Chat.

- **Neue Probe:** Kategorie wählen, bekannte Angaben eintragen, Gouvernement
  auswählen und die Veröffentlichungsfreigabe bestätigen. Nicht bekannte
  genetische Felder dürfen leer bleiben. Bei Gouvernement-Karten gibt es nach
  der Anmeldung einen direkten Knopf zum Hinzufügen mit vorausgewähltem Gebiet.
- **Bearbeiten:** Nach Name, ID oder Linie suchen, die Probe öffnen und die
  Angaben ändern. Nicht zugeordnete Proben findest du über den Gouvernement-
  Filter. Änderungen werden nicht stillschweigend von älteren Importen ersetzt.
- **Mehrere Proben:** Bis zu 200 Zeilen mit Kopfzeile aus Excel einfügen oder
  eine CSV-/TSV-Datei wählen. Die CSV-Vorlage enthält die passenden Spalten.
  Vor dem Speichern zeigt die Vorschau vorhandene Kitnummern, doppelte Kennungen
  innerhalb der Datei und fehlerhafte Angaben. Nur gültige neue Zeilen werden
  ergänzt. Vorhandene Proben werden weder überschrieben noch automatisch vereinigt.
  Für Zeilen ohne Ortsangabe kann ein gemeinsames Gouvernement gewählt werden.
- **Kitnummer prüfen:** Beim Eingeben einer Kitnummer oder YFull-ID erscheint
  ein Hinweis, wenn die Probe bereits vorhanden ist. „Vorhandene Probe öffnen“
  führt zur Bearbeitung dieses Eintrags.
- **Zusammenführen:** Zwei Proben auswählen. Die Auswahl bleibt beim Wechsel
  der Kategorie erhalten. Bei einer modernen und einer gesammelten Probe bleibt
  die moderne Probe der Hauptdatensatz. Die Vorschau zeigt beide Datensätze;
  bestätige dieselbe Person und gib einen Beleg oder eine Begründung an.
  Gleiche Linien oder ähnliche Namen lösen keine automatische Zusammenführung aus.
  Widersprüchliche Kit- oder YFull-IDs erfordern zuerst eine Identitätsprüfung.
- **Entfernen:** Die Probe wird aus den öffentlichen Ansichten ausgeblendet.
  Über die Anzeige „Entfernte / verknüpfte Proben“ sind entfernte Einträge
  wiederherstellbar. Verknüpfte Proben werden über den Änderungsverlauf getrennt.
- **Änderungsverlauf:** Zeigt die letzten Änderungen und erlaubt die Rückkehr
  zum vorherigen Stand, sofern keine neuere Änderung an der Probe vorliegt.
  Originaldatensätze und Identitätsbelege bleiben im geschützten Verlauf.

Die Verwaltung verändert keine anonymen Ergebniszahlen eines Quellendienstes.
Die bereits vorhandenen Opt-out-Regeln bleiben wirksam. Ein Opt-out kann nicht
über die Verwaltungsoberfläche rückgängig gemacht werden.

## Collected samples

Die vom Betreiber persönlich gesammelten Proben sind echte, mit ausdrücklicher
Freigabe veröffentlichte Proben. Sie heißen in der Oberfläche **Collected
samples** und werden zusammen mit den übrigen Proben im Baum, im Archiv und
in der regionalen Auswertung angezeigt. Verknüpft der Betreiber zwei Einträge
als dieselbe Person, erscheint danach nur noch der Hauptdatensatz.

Die übermittelte Datei entspricht dem bereits importierten Workbook mit 527
Proben. Sie wird nicht erneut dupliziert. Beibehalten werden die freigegebenen
Felder Name, väterlicher Vorfahr / Herkunft und Y-DNA-Endlinie. „About me“,
Surnames und mütterliche Angaben aus der Datei werden nicht zusätzlich kopiert.
Unbekannte Kitnummern, STRs oder mtDNA-Werte bleiben leer.

## Technische Absicherung

Die öffentlichen RPCs sind `SECURITY INVOKER` und nur für angemeldete Nutzer
aufrufbar. Die eigentlichen Vorgänge liegen im nicht exponierten Schema
`ydna_editor`, prüfen die private Administratorfreigabe, die serverseitig
bestätigte E-Mail und die aktive Sitzung und verwenden einen festen Suchpfad.
Es gibt keinen privilegierten Schlüssel im Browser und keine öffentlichen
Schreibrechte auf Probentabellen. Änderungen nutzen Versionsprüfungen,
Transaktionen, idempotente Anfragen und einen privaten Verlauf. Die Freigabe-
Adresse und interne Nutzerkennungen werden nicht ins öffentliche Git geschrieben.

Neue Tabellen verwenden RLS; ausgeblendete Proben erhalten zusätzliche
restriktive Leseregeln. Vorhandene Herkunfts-/Origin-Regeln bleiben bestehen.

## Quellzahlen und Linienlinks

„Egypt … reported results“ bezeichnet anonyme ägyptische Ergebniszahlen eines
FTDNA-Quellenstands, keine zusätzlichen identifizierten Personen. Ihre
Überschneidung mit gesammelten oder namentlichen Proben ist nicht bekannt.
Diese zusätzlichen Ergebniszeilen sind standardmäßig verborgen und lassen sich
über „Show anonymous source-count rows“ einschalten. Die Quelldaten bleiben erhalten.

Linien im Baum und Proben-Popups erhalten automatisch Links zu YFull und bei
Y-DNA zu FamilyTreeDNA Discover. Vorhandene Quellen und eindeutige Zuordnungen
aus der datierten YFull-Referenz werden bevorzugt. Für neue, noch nicht bestätigte
Provider-Zuordnungen zeigt die Oberfläche „Linie prüfen“. Ein solcher Link
behauptet weder eine aktuelle Live-Bestätigung noch eine Identität beim Anbieter.
Bei mtDNA wird keine nicht dokumentierte Discover-Adresse erfunden.
