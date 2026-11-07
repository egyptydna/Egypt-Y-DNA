# Egypt Y-DNA Discord — Redesign (kostenlos)

**Dies ist jetzt die aktive Einrichtung.** Sie nutzt scripts/discord_server_redesign.py und wird durch .github/workflows/discord-server-setup.yml ausgeführt. Die frühere Datei scripts/discord_server_setup.py bleibt als alte Version vorhanden, wird aber nicht mehr vom Workflow gestartet.

## Die neue Serverstruktur

- 📌 START HERE: welcome, rules, announcements, server-guide
- 🧬 Y-DNA RESEARCH: new-results, submit-results (Forum), haplogroup-discussion (Forum), ancient-dna (Forum)
- 🌍 COMMUNITY: english-chat (ZUERST), arabic-chat, introductions
- 🗺️ RESOURCES: egyptian-governorates, project-map, useful-links
- 🔒 STAFF: mod-log, member-review, staff-chat

Die bisherige channel-id und Geschichte existierender Kanäle bleibt erhalten. Bisherige Kategorien werden nach Möglichkeit umbenannt und bekannte Kanäle umgeordnet. Es werden keine Inhalte gelöscht. Alte Extra-Kanäle (z. B. snp-analysis oder Lounge/general) können weiterhin vorhanden sein: Sie werden nicht ungefragt gelöscht.

## Regeln

Die neue #rules-Nachricht wird bei Bedarf veröffentlicht, auch wenn ein rules-Kanal bereits existiert. Themen: Respekt, keine persönlichen Angriffe oder Diskriminierung, sachliche Quellennachweise, keine NSFW-Inhalte, keine unpassenden Religions-/Politikdiskussionen, Datenschutz, Englisch als Hauptsprache und Arabisch im Zusatzkanal.

## Rollen

Management/Status: Founder, Administrator, Moderator, Member, Research Contributor, Verified Y-DNA Tester.

**Eine einzige Herkunftsgruppe; alles freiwillig und ohne genetische Zuweisung:**

Afrika: North Africa, West Africa, Central Africa, East Africa, Southern Africa, Egypt, Maghreb, Nile Valley / Nubia, Horn of Africa.

Europa: Northern Europe, Western Europe, Southern Europe, Eastern Europe.

Asien: Levant, Arabian Peninsula, Mesopotamia, Anatolia, Caucasus, Iranian Plateau, Central Asia, South Asia, East Asia, Southeast Asia.

Amerika: North America, Central America, Caribbean, South America.

Ozeanien/Pazifik: Australia & New Zealand, Melanesia, Micronesia, Polynesia.

Weitere: Indigenous Peoples, Multiple Regions, Prefer Not to Say.

Diese Begriffe sind geographische oder freiwillige kulturelle Selbstbeschreibungen, keine DNA-Beweise oder wissenschaftlich definierte „Rassen“. Mitglieder können mehrere Herkunftsrollen wählen. Alle neu eingerichteten Herkunftsrollen erhalten die gleichen serverweiten Berechtigungen: 0 zusätzliche Rechte.

**Y-DNA-Rollen:**
A–T als grobe Gruppen plus E-M2, E-M35, E-M78, E-M81, E-M123, E-V13, E-V22, E-V32, J1, J1-P58, J2, J2a, J2b, R1a, R1b, R1b-V88, R1b-M269, R2, Q1, Q2, T-M70, T-P77, G1, G2, I1, I2, L1, L2, H1, H2, Not tested, Other / unresolved. **Q1/Q2 und andere alphanumerische Labels können je nach Stammbaumversion variieren**; eine durch SNP identifizierte Untergruppe ist wissenschaftlich präziser. Diese Rollen dienen nur der Selbstbeschreibung, nicht der Validierung eines DNA-Tests.

**Keine Sprachrollen.**

## Mitglieder verifizieren

- Neue Benutzer dürfen die Kanäle in START HERE sehen. Die übrigen neu verwalteten Diskussions-/Forschungskanäle sind bis zur Freigabe gesperrt.
- Moderator/Owner weist nach manueller Prüfung die Rolle **Member** zu. Erst dann werden die betreuten Forschungs- und Communitykanäle sichtbar.
- Die Kategorien/Forschungskanäle und alte #general/#snp-analysis erhalten dafür Kanal-Overwrites. Eigentümer können die Bereiche immer sehen. Andere existierende Sonderrollen oder Kanäle sind separat zu überprüfen.
- Jede Person kann weiterhin Einladungen erstellen: der Workflow schaltet nötigenfalls die allgemeine Berechtigung CREATE_INSTANT_INVITE für @everyone ein.
- Moderatoren brauchen für die Rollenzuweisung die Discord-Berechtigung **Manage Roles** und die passende Position in der Rollen-Hierarchie. Der Script legt Moderator-Rollen aus Sicherheitsgründen zunächst **ohne** Admin-Rechte an. Nur vertrauenswürdigen Personen erlauben.
- Discord bietet **Apply to Join** für eine echte Freigabe *vor* dem Beitritt, aber nur bei dafür freigeschalteten Servern; diese Funktion ist laut Discord schrittweise ausgerollt und wird in der Desktop-App aktiviert. Menü: Server Settings > Access.
- Community-Modus und Regelbestätigung (Rules Screening) getrennt in den Discord-Einstellungen einschalten. Das ist **keine** persönliche Freigabe.
- Optional Community Onboarding in der Desktop-Version konfigurieren, damit Mitglieder ihre Herkunfts-/Y-DNA-Rollen selbst wählen. Onboarding kann bei vielen Rollen durch mehrere übersichtliche Fragen gestaffelt werden.

## Logs und Join-Mitteilungen

- #mod-log ist vorerst ein **privater Notiz- und Moderationskanal**, kein echter automatischer Join-/Leave-Logger. Das Skript läuft einmalig via GitHub Actions, kein Bot läuft dauerhaft.
- Für kostenlose Join-Benachrichtigungen unter Server Settings > Overview/Übersicht > System Messages Channel den Kanal #welcome auswählen. Discord kann dort bei einem Beitritt eine Systemnachricht veröffentlichen.
- Der eingebaute Audit-Log in Server Settings protokolliert wichtige Moderationsaktionen. Ein ausführlicher, privater Join-/Leave-Log würde einen dauerhaft aktiven Bot mit den passenden Events benötigen.
- Die meisten Teamaktionen können in #member-review dokumentiert werden.

## Einrichtung / Neuer Lauf auf dem iPad

Voraussetzung: Dein Discord-Bot ist eingeladen und im GitHub-Repo sind diese **Secrets** hinterlegt:
- DISCORD_BOT_TOKEN (Bot-Token; niemals in ChatGPT, Issues oder Dateien einfügen)
- DISCORD_GUILD_ID (numerische Server-ID)

1. Öffne https://github.com/egyptydna/Egypt-Y-DNA/actions/workflows/discord-server-setup.yml
2. **Run workflow** → **preview** → Run workflow. Das ist lesend und ändert nichts.
3. Prüfe den Log, ob die vorgeschlagenen Änderungen passen.
4. **Run workflow** → **apply** → Run workflow. Erst jetzt werden Änderungen auf dem Server durchgeführt.
5. Öffne Discord und kontrolliere die Kategorien, Reihenfolge, Rollen sowie staff-only und Member-Zugriff.
6. Aktiviere Community; wenn die drei Foren wegen fehlendem Community-Modus übersprungen wurden, run apply erneut.

Das Setup löscht **keine** alten Rollen, Nachrichten, Kanäle oder Kategorien. Es benennt einige alte Projektkategorien/Kanäle um, verschiebt bekannte Kanäle in die neuen Kategorien, erstellt fehlende Einträge, aktualisiert die Leseberechtigung für verifizierte Mitglieder und schreibt die neuen Regeln. **Neue Discord-Kanäle und Rechte werden erst beim Workflow-Lauf apply angelegt.** Mögliche Discord-API-Fehler (z. B. Bot-Rollenposition) sind im Workflow-Protokoll sichtbar.

Die GitHub-Actions-Nutzung ist bei öffentlichen Repositories ohne Actions-Minutenkosten; Discord benötigt für diese Grundfunktionen weder Nitro noch Server-Boosts.

Links:
- Discord Community Onboarding: https://support.discord.com/hc/en-us/articles/11074987197975-Community-Onboarding-FAQ
- Discord Member Applications: https://support.discord.com/hc/en-us/articles/29729107418519-Server-Member-Applications
- Discord Rules Screening: https://support.discord.com/hc/en-us/articles/1500000466882-Rules-Screening-FAQ
- Discord API: https://discord.com/developers/docs/topics/permissions

## Farben für Herkunftsrollen (November 2026)

Jede der 37 Herkunfts-/Regionalrollen bekommt beim nächsten **apply** eine eigene Farbe. Bestehende Rollen werden ebenfalls umgefärbt und behalten ihre Mitglieder und Namen. Zusätzlich werden die bereits früher selbst angelegten Rollen `Copt`, `Amazighi`, `Central Asian`, `European`, `South Asian`, `East Asian`, `Sea Asians` und `Native` in die Farbgestaltung einbezogen, falls sie existieren.

Insgesamt sind **45 verschiedene Farben** fest hinterlegt. Beispiele:

- Egypt: `#C89A2B` (Gold)
- Balkans: `#7754BB` (Violett)
- Copt: `#AD613A` (Terrakotta)
- Amazighi: `#218C79` (Türkisgrün)
- North Africa: `#29D229` (Grün)
- West Africa: `#2929D2` (Blau)
- Levant: `#3C1E96` (Indigo)

Ein bloßer Farbwechsel vergibt keine zusätzlichen Discord-Rechte. Der gesamte Setup-Workflow kann allerdings weiterhin die zuvor geplanten Kanalzugriffsregeln aktualisieren. Die Farbe eines sichtbaren Discord-Namens wird durch die **höchste Rolle mit Farbe** bestimmt, falls ein Mitglied mehrere Herkunftsrollen besitzt. Rollen können über das vorhandene Discord-Onboarding später freiwillig ausgewählt werden; das Anlegen der Rollen allein richtet die Auswahl noch nicht ein.

Bei `preview` erscheint vorerst nur der geplante Änderungsumfang. Erst `apply` führt die Farbänderungen auf Discord aus. Sollte die Discord-API wegen der Rollenhierarchie die Änderung einer Rolle verweigern, steht ein Hinweis im Workflow-Log.
