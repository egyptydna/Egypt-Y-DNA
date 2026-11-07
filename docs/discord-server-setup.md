# Ägypt YDNA — kostenloser Discord-Server-Installer

Dieser einmalige Installer ergänzt deinen BEREITS BESTEHENDEN Discord-Server mit Rollen, Kategorien, Textkanälen, Foren (wenn Community aktiv ist), einem Sprachkanal und Begrüßungstexten.

Er arbeitet nur mit einem eigenständigen Discord-Bot. Niemals einen Discord-Benutzer-Token, Passwort oder Sitzungscode verwenden oder in ChatGPT weitergeben.

## Die drei Schritte auf deinem iPad — ohne PC und ohne Bezahlung

### 1. Kostenlosen Bot erstellen und deinem bestehenden Server hinzufügen

- Öffne https://discord.com/developers/applications und erstelle eine neue Anwendung, zum Beispiel Egypt YDNA Setup.
- Im Reiter Bot einen Bot einrichten und den BOT TOKEN kopieren. Nur in GitHub Secrets speichern (Schritt 2).
- Unter OAuth2 > URL Generator (oder Installation) den Scope bot wählen. Benötigte Bot-Berechtigungen: Manage Channels, Manage Roles, View Channels, Send Messages, Read Message History. Optional: Send Messages in Threads. Du brauchst dafür KEINE Administrator-Vollmacht.
- Den erzeugten Einladungslink öffnen und den Bot dem bestehenden Server Ägypt YDNA hinzufügen.
- In Discord unter Server-Einstellungen den Community-Modus aktivieren. Nur dann können die drei Forumkanäle erstellt werden. Ohne Community-Modus überspringt der Installer diese Kanäle und du kannst ihn später erneut starten.

### 2. Beide Werte sicher in GitHub hinterlegen

Öffne https://github.com/egyptydna/Egypt-Y-DNA/settings/secrets/actions

Unter New repository secret zwei Geheimnisse anlegen:

1. Name: DISCORD_BOT_TOKEN. Wert: dein neu erzeugter Bot-Token.
2. Name: DISCORD_GUILD_ID. Wert: die numerische Server-ID deines bestehenden Servers.

Um die Server-ID zu kopieren, in Discord Entwicklermodus unter Benutzereinstellungen > Erweitert aktivieren und im Kontextmenü deines Servers Server-ID kopieren wählen.

WICHTIG: Weder deinen Bot-Token noch dein Discord-Passwort in einem Chat, in einer GitHub-Datei oder in einer Discord-Nachricht veröffentlichen.

### 3. Automatisch einrichten

Öffne https://github.com/egyptydna/Egypt-Y-DNA/actions/workflows/discord-server-setup.yml

- Klicke auf Run workflow und wähle zuerst preview. Das prüft, was fehlt, verändert aber NICHTS.
- Lies die Ausgaben des Workflow-Runs.
- Klicke erneut Run workflow, wähle apply und starte. Jetzt werden nur die fehlenden Elemente ergänzt.
- Wenn du später Community aktivierst, starte apply einfach erneut, um die fehlenden Foren anzulegen.

## Was wird erstellt?

Kategorien:
- 📌 INFORMATION — welcome, rules, announcements, how-to-submit
- 🧬 Y-DNA RESULTS — new-results, submit-results, haplogroup-discussion, snp-analysis
- 🗺️ EGYPTIAN ORIGINS — governorates, ydna-map, ancient-dna
- 💬 COMMUNITY — general, arabic-chat, english-chat, voice-chat
- 🔒 STAFF ONLY — moderation, sample-review

Rollen:
Founder, Administrator, Moderator, Researcher, Verified Tester, Contributor, Member.

Sicherheitsprinzipien:
- Vorhandene Rollen/Kanäle werden NICHT gelöscht, umbenannt, verschoben oder überschrieben.
- Bereits bestehende Kanalnamen werden erkannt und übersprungen, statt doppelt erstellt.
- Neue Rollen erhalten keinerlei serverweite Sonderrechte. Insbesondere bezeichnet die neue Rolle Administrator zunächst nur den Rollennamen, NICHT eine echte Admin-Vollmacht. Du kannst Berechtigungen bewusst später vergeben.
- Die neu angelegten Staff-Kanäle sind privat und für Eigentümer sowie Administrator-/Moderatorrollen zugänglich. Prüfe nach dem Setup den Zugriff.
- Ankündigungen und verifizierte Ergebnisse werden als schreibgeschützte Kanäle neu angelegt. Dort können Eigentümer, Administrator-/Moderatorrollen und der Bot schreiben.
- Startertexte betonen Quellenprüfung und den Schutz privater DNA-Daten.
- Automatische Verknüpfung mit neuen Y-DNA-Proben ist NICHT enthalten; dazu müsste ein gesonderter, überprüfbarer Veröffentlichungsprozess eingerichtet werden.
- Keine dauerhaft laufenden Bots oder kostenpflichtigen Discord-Dienste erforderlich. GitHub Actions ist bei öffentlichen Repositories kostenlos; private Repositories haben ein Freikontingent.

Wenn ein Kanal mit dem gleichen Namen bereits an einer anderen Stelle existiert, lässt das Script ihn unangetastet. Es überschreibt auch nicht die Rechte schon existierender Kanäle oder Kategorien. Bei unzureichenden Bot-Rechten erscheint ein Fehler im Workflow-Protokoll.

Offizielle Referenzen:
- https://discord.com/developers/docs/topics/permissions
- https://docs.github.com/en/actions/how-tos/manage-workflow-runs/manually-run-a-workflow
