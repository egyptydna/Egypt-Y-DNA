# Sofortige Carl-bot-Rollen — aktuelle Fehlerbehebung

**Neuer Fix:** Der GitHub-Workflow erkennt Carl-bots Discord-eigene, verwaltete Integrationsrolle und erteilt ausschließlich diesem Botkonto im Channel `#choose-roles` die Rechte **View Channel, Read Message History, Add Reactions**. Das bleibt so, auch wenn die normale Verification-Einrichtung später erneut läuft. Unverifizierte menschliche Mitglieder dürfen den Kanal weiterhin NICHT sehen.

**Den Kanal-Fix auf Discord aktivieren:**
https://github.com/egyptydna/Egypt-Y-DNA/actions/workflows/discord-role-menu-update.yml

**Run workflow → preview → danach apply**. Prüfe den Eintrag `[CHECK] Carl-bot account detected`. Falls stattdessen `[ACTION REQUIRED] Could not identify Carl-bot` erscheint, füge Carl-bot manuell zu den Kanalberechtigungen von `#choose-roles` hinzu (nur Ansicht, Nachrichtenverlauf, Reaktionen).

**Unbedingt zusätzlich einmal im Carl-bot Dashboard konfigurieren:** `https://carl.gg/` → Egypt Y-DNA → Reaction Roles → **Create new reaction role → Use ID** → die Nachrichten-ID einer *tatsächlichen Emoji-Auswahlnachricht* aus `#choose-roles` → Emoji mit Rolle verknüpfen → Speichern. Der GitHub-Workflow kann das nicht im Carl-bot-System speichern.

**Fehlerdiagnose für den eigenen GitHub-Bot:** Der Role Self-Selection-Workflow wurde verbessert: er akzeptiert auch Serverinhaber ohne das Verified-Abzeichen und erkennt menschliche Reaktionen, selbst wenn die ursprüngliche Reaktion des Bots fehlt. Bei manueller Ausführung protokolliert er `[SUMMARY]` und `[ACTION REQUIRED]`, falls z. B. die Zielrolle oberhalb des Bots liegt, unsichere Altberechtigungen hat oder das Menü veraltet ist.

---

# Wichtig: Carl-bot-Berechtigungen allein vergeben noch keine Rollen!

Die Rolle von Carl-bot darf **Manage Roles** haben, trotzdem passiert beim Emoji-Klick nichts, solange die Emoji-zu-Rolle-Zuordnungen **nicht unter Carl-bot → Reaction Roles gespeichert** sind. GitHub hat keinen Zugriff auf Carl-bots eigene Datenbank; das Anlegen eines Emoji-Posts durch den Egypt YDNA Bot verbindet ihn NICHT automatisch mit Carl-bot.

## Carl-bot auf dem bestehenden Discord-Post konfigurieren (kostenlos)

1. Öffne https://carl.gg und wähle deinen **Egypt Y-DNA** Server.
2. Öffne **Reaction Roles → Create new reaction role**.
3. Wähle **Use ID / ID / Existing message**, NICHT „Post embed“, denn `#choose-roles` enthält bereits fertige Nachrichten unseres Egypt YDNA Bots.
4. Wähle den Kanal **#choose-roles**, kopiere die **Nachrichten-ID der jeweiligen Auswahl-Nachricht** und füge sie im Carl-bot-Feld ein. In Discord: Entwickler-Modus aktivieren, lange auf die *tatsächliche Emoji-Auswahl-Nachricht* drücken → **ID kopieren**. Nicht die angepinnte Übersichts-Nachricht verwenden.
5. Verknüpfe die Emojis einzeln: `🇪🇬 → Egypt`, `🇲🇦 → Morocco`, `🧬 → J1`, `🟢 → J1-P58`, `🌊 → E-V12`, `🔵 → Male` (jeweils auf der korrekten Nachricht) usw. Für mehrere Emojis derselben Nachricht ein gemeinsames Reaction-Role-Set.
6. **Save / Create** drücken. Für die Y-DNA-Nachrichten nach Möglichkeit „Unique“ einstellen, damit eine Person nur einen väterlichen Zweig wählt. Bei getrennten Y-DNA-Nachrichten zusätzlich die Link-Funktion verwenden oder Rollenwechsel durch Moderation prüfen.
7. In Discord → Servereinstellungen → Rollen: **Carl-bot über Herkunfts-, Geschlechts- und Y-DNA-Rollen**, aber **unter Founder, Administrator, Moderator und Verified** positionieren. `Manage Roles` aktiv, `Administrator` aus. Carl-bot braucht Lesezugriff auf `#choose-roles`.
8. Mit einem Testmitglied, das bereits **Verified** hat, auf ein Emoji reagieren. Carl-bot sollte unmittelbar die Rolle vergeben. Einstellungen unter `Reaction Roles` prüfen, falls nicht.

Offizielle Carl-bot-Dokumentation: https://github.com/botlabs-gg/carlbot-docs/blob/master/docs/roles.md
Das Dashboard unterstützt die Verknüpfung mit einer fremden, bestehenden Nachricht über die Nachrichten-ID.

## Alternativ: unser GitHub-Bot ohne Carl-bot verwenden

Der vorhandene Workflow https://github.com/egyptydna/Egypt-Y-DNA/actions/workflows/discord-role-selection.yml
vergibt Rollen **automatisch, aber nicht sofort**. Manuell **Run workflow** starten, dann im Job **Process role reactions** die neue `[SUMMARY]`-Zeile ansehen.

- `not Verified` → Der Reagierende hat noch keine Verified-Rolle (Serverinhaber wird jetzt als Ausnahme berücksichtigt).
- `unsafe/unmanageable roles` → Die Zielrolle liegt über dem Bot oder hat alte Server-Berechtigungen. Als Serverinhaber korrigieren.
- `outdated/missing menus` → Erneut den Role Menu & New Results Workflow mit `apply` ausführen.
- `roles granted: 0` und `human selections checked: 0` → Reaktion auf die tatsächliche Bot-Auswahl-Nachricht prüfen; nicht nur auf die Hauptübersicht.
- Bei Discord HTTP 403 steht der fehlgeschlagene API-Aufruf im Log.

**Wichtig:** Nach erfolgreicher Carl-bot-Konfiguration empfehlen wir, den GitHub-Schedule für `discord-role-selection.yml` zu deaktivieren, damit nicht zwei unabhängige Systeme konkurrieren. Die GitHub-Setup-Workflows für Regeln/Verifizierung bleiben aktiv.

---

# Instant reaction roles for Egypt Y-DNA (free)

**Current GitHub Actions role selector is already automatic, but NOT instant.** It reads reactions to the messages in `#choose-roles` and assigns roles only on its approximately 5-minute scheduled runs. GitHub cron cannot run every second. No manual staff action is required once the workflow is enabled.

**J1 is now included**, separate from J1-P58. Select **J1** if the test is confirmed as J1 but the downstream P58 branch is unknown or not applicable. Select **J1-P58** only if confirmed/predicted accordingly. Our scheduled worker allows only **one** detailed Y-DNA role per user to prevent contradictory claims.

## Truly instant emoji → role with no hosting fees

Discord sends emoji-reaction notifications in real time only to a connected Gateway bot. A repository of scheduled GitHub Actions cannot receive these events instantly. To get the role *immediately* after the click with **no server to host**, use an established **free hosted reaction-role bot**, such as Carl-bot:

- [Carl-bot](https://carl.gg/) (official)
- [Carl-bot reaction-role documentation](https://docs.carl.gg/)
- Carl-bot's free plan provides **up to 250 reaction-role mappings per server**, according to its official pricing documentation. There are fewer than 100 mappings in the Egypt Y-DNA selector.

### Step-by-step

1. Invite Carl-bot to your existing Egypt Y-DNA Discord server using the official Carl-bot site. Do **not** share your Discord password, GitHub Secrets, or Egypt YDNA Bot token.
2. In Discord **Server Settings → Roles**, put the Carl-bot role **above the self-selectable origins, gender and Y-DNA roles** so it can grant them, but **below Founder, Administrator and Moderator** so it cannot hand out leadership roles. Give it **Manage Roles** and normal read/reaction access to `#choose-roles`. Do **not** give it Administrator.
3. Run [Egypt Y-DNA Role Menu & New Results](https://github.com/egyptydna/Egypt-Y-DNA/actions/workflows/discord-role-menu-update.yml) with `preview` then `apply` so every emoji/menu and (if missing) J1 is published.
4. Open the successful GitHub Actions log. Each mapping now prints `[INSTANT REACTION BOT MAPPING] message_id=... emoji=... role=... channel_id=...`. These IDs show the precise existing messages and emoji associations.
5. In Carl-bot's Dashboard → **Reaction Roles**, associate each emoji with its matching Discord role on the indicated existing message ID. The slash-command `/reactionrole add` is another supported way to attach emoji/role pairs to existing messages. Repeat for the desired menus. For Y-DNA options, use **unique** mode within the menu where available; the user should have only one paternal-lineage role overall.
6. Test with an already **Verified** member. A reaction should now assign the role without waiting for a GitHub scheduled check. The role should appear in Discord's member profile after the bot processes it.

**Important:** This last Carl-bot configuration cannot be done by our current GitHub workflow on your behalf; Carl-bot's own app must be authorized/configured separately by the Discord server owner. Until then, the existing scheduled workflow automatically assigns roles, but only after its next scheduled run.

### Security and role notes

- Only **Verified** members can view the role-selection channel; this does not replace manual newcomer approval.
- **Founder, Administrator, Moderator, Verified, Bot and Verified Y-DNA Tester** are never offered in the picker.
- Before enabling a reaction-role mapping, ensure the corresponding origin/DNA/gender role has **zero server management permissions**; the GitHub setup attempts to clear unsafe legacy origin permissions and reports errors.
- The scheduled GitHub worker currently adds a role after a reaction and does not automatically remove it when a reaction is removed. Carl-bot reaction-role mode can support automatic removal on unreact depending on its configuration. If you use the instant bot, make it the **single source of truth** for role selection; turn off the scheduled GitHub role-selection workflow after Carl-bot is fully configured to avoid two independent assigners.
