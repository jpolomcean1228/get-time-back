# Accounts & the shared household (multi-user)

The service now supports real user accounts and a persistent shared household,
backed by SQLite (`gtb.db`). When a request is authenticated, the coordination
matcher reads that user's real household; when it isn't, it falls back to the
mock fixture, so the existing demo still works signed-out.

## The flow

```
POST /auth/register   {name, email, password}     -> { token, name }
POST /auth/login      {email, password}            -> { token, name }
POST /auth/logout     (Authorization: Bearer …)    -> { ok }
GET  /auth/me         (Bearer)                      -> the current user

POST /household       {name}            (Bearer)   -> { id, name, code }
POST /household/join  {code}            (Bearer)   -> joins by invite code
PUT  /household/me    {can_drive, shares_availability, accepts_handoffs}
PUT  /household/availability  {busy: [[start_min,end_min], ...]}
GET  /household       (Bearer)                      -> roster + consent
```

Send the token on every authenticated call as `Authorization: Bearer <token>`.
Once you're in a household and members have set availability + consent, `/enrich`
(also with the Bearer header) coordinates over the real, shared data — the same
"Ask Maya" hand-off, now driven by live accounts instead of a fixture.

## This is prototype-grade auth — harden before real users

What's solid: passwords are per-user salted and PBKDF2-hashed (120k rounds);
sessions are random opaque tokens; SQL uses parameterized queries; consent is
closed by default. What to add before production:

- **Token expiry + rotation.** Sessions currently never expire. Add an expiry
  column and refresh, and store a hash of the token rather than the token.
- **Transport + storage.** Serve over HTTPS only; consider HttpOnly cookies
  instead of a Bearer token in JS. Move secrets out of the app DB if it grows.
- **Email verification + password reset**, and basic **rate limiting** on
  `/auth/*` to slow credential stuffing.
- **Per-household authorization checks** on every mutation (a user can only act
  within households they belong to — partially enforced; audit it).
- **Migrations.** The tables are created on first run; once there's real data,
  switch to a migration tool rather than `CREATE TABLE IF NOT EXISTS`.

None of these change the interfaces above — they harden what's behind them.

## The natural next frontend piece

The backend is ready for an account UI: sign-in, "create or join a household,"
and a small panel to set your availability and consent. The demo currently runs
signed-out against the mock; wiring those screens to the endpoints above is the
next step, and the API won't change underneath it.
