# JamiesProjevt — Devlog

**This file is where "done" lives.** `queue.md` is delete-only: when a queue
item is finished, the item is **deleted from `queue.md`** and a dated entry
is **appended here**, in the same commit as the work, then pushed. Never
tick a box in place — a checked box left in `queue.md` is the failure mode
this file exists to prevent.

Also record releases (tag + a one-line note), notable milestones, and
anything else worth a chronological trail. Newest entries at the bottom.

This is the **same convention as the cleanvibe repo's own `devlog.md`** —
every cleanvibe-scaffolded project gets one for the same reason.

See `CLAUDE.md` § "Workflow Rules" and `queue.md`'s preamble.

---

## 2026-06-08 — Project scaffolded

Scaffolded with `cleanvibe new` (cleanvibe v1.13.1). Future entries
land here as queue items get deleted.

## 2026-06-08 — Pharmacy controlled-substance tracker v1 built

Designed and implemented the project's first product: a local, multi-user
pharmacy controlled-substances tracker with a regulatory-grade audit trail.

- **Design + plan:** `docs/superpowers/specs/2026-06-08-pharmacy-controlled-substance-tracker-design.md`
  and `docs/superpowers/plans/2026-06-08-pharmacy-controlled-substance-tracker.md`.
- **Built via subagent-driven TDD** across 16 plan tasks on branch
  `feature/pharmacy-tracker`, then merged to `main`.
- **What v1 does:** append-only, hash-chained ledger as the single source of
  truth (on-hand is derived, never stored); receive / dispense / dispose /
  reconcile operations with their guards (no-negative stock, distinct witness +
  reason for disposal, audited adjustments); session login with admin/operator
  roles; filterable + printable audit log; a "verify integrity" page that
  re-walks the chain to detect tampering; first-run admin bootstrap; runnable
  with `python -m pharmacy`.
- **Modules:** `pharmacy/` — models, db, ledger, inventory, auth, reports,
  bootstrap, `__main__`, and `web/` (Flask routes + Jinja templates + print.css).
- **Tests:** 32 passing (pytest), heaviest on ledger (hash chain, on-hand
  derivation, tamper detection across edits/deletions) and inventory rules. CI
  workflow runs the suite on push/PR.
- A real defect was caught and fixed during the build: SQLite's `DateTime`
  column drops `tzinfo`, which would have made `verify_chain` flag every
  legitimate ledger as tampered — fixed with a `norm_ts` UTC-normalizer
  mirroring the existing `norm_qty` Decimal normalizer. No test was weakened.

## 2026-06-09 — v2-1: admin-gate catalog management (RBAC step 1)

Closed the access-control gap the v1 final review flagged: roles existed and
actions were attributed, but no route was admin-gated. Added an `admin_required`
decorator in `pharmacy/web/routes.py` (logged-in non-admins get an explicit 403
`forbidden.html` page rather than a login redirect) and applied it to
`/drugs/new` — catalog management is now admin-only. The "Add drug" nav link is
hidden from operators. Tests: an operator POSTing to `/drugs/new` is refused
(403, no drug created); an admin still succeeds. Full suite 34 passing
(was 32). First autonomous work-loop item.

## 2026-06-09 — v2-2: admin user-management page (RBAC step 2)

Admins can now manage users from the web UI instead of only the first-run
bootstrap admin. Added `auth.set_password(session, user, new_password)` and
admin-only routes: `GET /users` (list), `POST /users/new` (create
operator/admin, `AuthError` → flash), `POST /users/<id>/deactivate`, and
`POST /users/<id>/reset-password`. Safety rail: deactivating the **last active
admin** is refused (would otherwise lock everyone out of admin functions).
Added `users.html` and an admin-only "Users" nav link. Tests: admin creates an
operator who can then log in; operator gets 403 on `/users` and doesn't see the
nav link; last-active-admin deactivation refused; deactivate/reset-password
work. Full suite 41 passing (was 34).

## 2026-06-09 — v2-3: self-service password change

Any logged-in user can now change their own password at `GET/POST
/account/password` — they must supply their current password (re-checked via
`auth.authenticate`) before the new one is set via `auth.set_password`. Wrong
current password is refused with a clear flash and the credential is left
unchanged; an empty new password is rejected. Added `account_password.html` and
a "Change password" nav link for all logged-in users. Tests: change succeeds
(old password stops working, new one logs in); wrong current password refused
and password untouched; the page requires login. Full suite 44 passing
(was 41).

## 2026-06-09 — v2-4: expiry & low-stock reporting

Added `reports.alerts(session, *, low_stock_threshold, today=None)` — a pure
function returning one dict per lot needing attention, tagged with all
applicable reasons: `expired` (expiry in the past), `expiring_soon` (within 30
days), `low_stock` (derived on-hand at/below the threshold). Healthy lots are
omitted; lots without an expiry date are only stock-checked. `today` is
injectable so the date logic is deterministically testable. Added a logged-in
`GET /alerts` route (threshold via `?threshold=` query param, default 5),
`alerts.html`, and an "Alerts" nav link. Tests: expired/expiring/low-stock all
flagged and a healthy lot is not; a no-expiry lot reports only `low_stock`; the
page renders and surfaces a low-stock lot. Full suite 47 passing (was 44).

This drained the v2 queue; the next work-loop tick refills it by decomposing
the next `todo.md` horizon.

## 2026-06-09 — v2-5: per-lot transaction history (promoted from todo.md)

First post-v2-batch refill: promoted "per-lot transaction history" from
`todo.md`, decomposed it into `queue.md`, and built it. Added
`reports.lot_history(session, lot_id)` — the lot/drug header plus its full
chronological ledger, each entry annotated with the **running on-hand** after
it (cumulative sum of deltas); the final running balance equals
`ledger.on_hand`. Added a logged-in `GET /lots/<id>` route (unknown lot →
flash + redirect), `lot_history.html`, and made each dashboard lot number a
link to its history. Tests: running balance is correct, ordered, and ends at
on-hand; page renders with the post-dispense balance; unknown lot redirects.
Full suite 50 passing (was 47).

## 2026-06-09 — v2-6: date-range audit filtering + CSV export

Made the audit log usable for record-keeping and regulators. The `/audit` page
now takes `start`/`end` date filters (parsed `YYYY-MM-DD`, end treated as
end-of-day, invalid dates ignored) wired to the existing
`reports.audit_log(start=, end=)`. Added `GET /audit.csv` that streams the same
filtered log as `text/csv` with a `Content-Disposition: attachment` header and a
header row, plus a "Download CSV" link on the audit page. Tests: the page
accepts date params (and shrugs off an invalid one); the CSV endpoint returns
`text/csv`, an attachment disposition, a header row, and one row per entry. Full
suite 52 passing (was 50).

Also corrected a bookkeeping drift flagged in the prior status report: the
shipped "per-lot transaction history" bullet was still lingering in `todo.md`;
removed it (and this item) so `todo.md` only holds not-yet-built horizons.

## 2026-06-09 — v2-7: persist a stable Flask secret key

Fixed a real deployment bug: `__main__` generated a fresh random `secret_key`
on every start, so each restart silently invalidated all logged-in sessions.
Added `bootstrap.load_or_create_secret_key(path)` — reads the key from a file if
present, otherwise generates `secrets.token_hex(32)`, persists it (creating
parent dirs), and returns it. `__main__` now uses `PHARMACY_SECRET_KEY` if set,
else a key file at `PHARMACY_SECRET_KEY_FILE` (default `pharmacy_secret.key`,
gitignored). Tests: the helper returns the same key on a second call (persisted,
not regenerated) and creates nested parent dirs. Full suite 54 passing (was 52).

Bookkeeping: also pruned `todo.md` of items shipped in earlier ticks but left
behind (RBAC, user-management UI, self-service password change, expiry/low-stock
reporting) and narrowed "deployment hardening" to its remaining parts (WSGI
guidance, DB backups). `todo.md` now reflects only not-yet-built work.
