# Proben selbst verwalten

Über **Verwalten** in der Navigation öffnest du den geschützten Bereich.
Erstelle beim ersten Mal ein Konto mit deiner freigeschalteten E-Mail-Adresse,
bestätige die Anmeldemail und melde dich dann an. Dein Passwort wird nicht im
Projektcode gespeichert. Falls die E-Mail-Weiterleitung nicht zur Webseite
führt, kannst du den Bestätigungslink im dafür vorgesehenen Feld prüfen lassen.
Nur eine serverseitig freigeschaltete, verifizierte Adresse mit einer aktiven
Anmeldesitzung erhält Schreibrechte. Andere Besucher und andere angemeldete
Konten erhalten keine Verwaltungsrechte.

- **Neue Probe:** Kategorie wählen, bekannte Angaben eintragen, Gouvernement
  auswählen und die Veröffentlichungsfreigabe bestätigen. Nicht bekannte
  genetische Felder dürfen leer bleiben. Bei Gouvernement-Karten gibt es nach
  der Anmeldung einen direkten Knopf zum Hinzufügen mit vorausgewähltem Gebiet.
- **Bearbeiten:** Nach Name, ID oder Linie suchen, die Probe öffnen und die
  Angaben ändern. Nicht zugeordnete Proben findest du über den Gouvernement-
  Filter. Änderungen werden nicht stillschweigend von älteren Importen ersetzt.
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
