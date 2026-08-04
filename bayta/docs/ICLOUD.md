# Connecting Apple iCloud

## Calendars (two-way sync)

Bayta talks to iCloud over CalDAV. Apple requires an **app-specific password**
for this — your normal Apple ID password will not work, by design.

For **each** person whose calendars should appear (you and your wife):

1. Go to [account.apple.com](https://account.apple.com) and sign in.
2. **Sign-In and Security → App-Specific Passwords → Generate**.
3. Name it `Bayta`, copy the `xxxx-xxxx-xxxx-xxxx` password it shows.
4. On Bayta: **Settings → iCloud calendars → Add account**, enter the Apple ID
   email and that password, pick which calendars to show, and assign each one
   to a person (that's what colors the events).

Notes:
- The password is stored **encrypted on the Pi only** — it never leaves your house
  except to talk to Apple.
- Sync runs every ~5 minutes in both directions. Events created on the wall push
  to iCloud and appear on iPhones.
- If you ever change your Apple ID password, app-specific passwords are revoked:
  generate a new one and use the account's re-connect button.

## Photos (shared album)

1. In the Photos app on an iPhone: **Albums → + → New Shared Album**, name it
   (e.g. "Bayta wall"), invite the family.
2. Open the album → the people icon → turn on **Public Website**.
3. **Copy Link** and paste it into Bayta: **Photos → iCloud album**.

Everyone in the family can then add photos from their own phone's Photos app,
and they appear on the wall within ~30 minutes. No passwords involved; turn off
"Public Website" anytime to cut access.
