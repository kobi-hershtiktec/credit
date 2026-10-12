# Agamim apartments board

Shared, login-free tracker for apartments for sale in Agamim, Ashkelon.

- `public/index.html` — the whole site (no build). Data lives in Firestore under
  `boards/<boardId>/apartments`; the board id is the part of the link after `#`
  and is intentionally not stored in this repo.
- `firestore.rules` — only that path is open; listing fields are read-only,
  only status/checkedBy/contact/notes/updatedAt can change, and new apartments
  must match the add-form schema.
- `seed.mjs <boardId>` — one-time seed of the original 15 listings (never overwrites).

Deploy: `firebase deploy --project agamim-apartments` (hosting + rules).
