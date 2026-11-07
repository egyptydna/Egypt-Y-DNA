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
