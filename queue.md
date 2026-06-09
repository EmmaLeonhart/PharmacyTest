# JamiesProjevt — Work Queue

**This file is a queue of *concrete, executable steps*, not a state snapshot.** It lists what is being worked on right now. Finished work lives in `devlog.md` (a dated entry) and `git log`; longer-horizon, *abstract* work lives in `todo.md` and gets decomposed into items here when it's ready to execute. **When an item is done, delete it from this file AND append a dated entry to `devlog.md` in the same commit, then push.** Do not add checkmarks, "done" markers, or status indicators in place. If an item is still here, it is not done.

The purpose of this file is also to bound scope. If a task is not in this queue, it is not in scope for the current session. New ideas go at the bottom of the queue (or to `todo.md` if they are longer-term / architectural), not silently into whatever is being worked on.

**Three-cron playbook.** Work runs under three local `CronCreate` jobs — **work-loop at :03** (drains this queue, refills from `todo.md`), **auto-flush at :15** (commit/push backstop), **status-report at :42** (heartbeat). They were started when this v2 queue was created. The **last two items are pinned at the tail**: ensure the crons are running, then an end-of-session summary. See `CLAUDE.md` § "Autonomous productivity loop".

Each item below builds on the v1 pharmacy tracker (modules in `pharmacy/`, tests in `tests/`). Work them top to bottom, TDD, one commit (or a few) per item.

---

## Active — v2 work

1. **Admin user-management page (step 2 of access control).**
   - Add admin-only routes: `GET /users` (list users with username, display name, role, active), `POST /users/new` (create an operator or admin via `auth.create_user`, catching `AuthError` → flash), `POST /users/<id>/deactivate` (set `active=False`; never deactivate the last active admin — enforce and test), `POST /users/<id>/reset-password` (set a new password via a helper in `auth.py`, e.g. `set_password(session, user, new_password)`).
   - Templates: `users.html` (table + create form). Add a nav link visible only to admins.
   - Tests: admin can create an operator who can then log in; operator cannot reach `/users`; deactivating the last active admin is refused. Full suite green, commit, devlog, push.

2. **Self-service password change.**
   - Add `GET/POST /account/password` (any logged-in user): require current password (re-authenticate via `auth.authenticate`), set new password via the `auth.set_password` helper from item 1. Flash on success/failure.
   - Template `account_password.html`; nav link "Change password".
   - Tests: correct current password changes it (old fails, new works on next login); wrong current password is refused. Full suite green, commit, devlog, push.

3. **Expiry & low-stock reporting.**
   - Add `reports.alerts(session, *, low_stock_threshold)` returning lots that are expired, expiring within 30 days, or at/below the threshold on-hand. Pure function over existing models + `ledger.on_hand`; returns dicts tagged with the alert reason(s).
   - Add a logged-in `GET /alerts` route + `alerts.html` template (grouped by reason) + nav link. Threshold configurable via query param, default a sensible constant.
   - Tests in `tests/test_reports.py` (the report fn: expired lot flagged, expiring-soon flagged, low-stock flagged, healthy lot not flagged) and a smoke test for the route. Full suite green, commit, devlog, push.

---

## Always last — ensure the three crons are running and summarize

**These two items stay pinned to the tail of the queue at all times** — below every real work item. They are the closing half of the three-cron lifecycle (`CLAUDE.md` § "Autonomous productivity loop"):

A. **Ensure the three crons are running** — start them if this session never did, restart them if a planning burst / queue re-fill killed them: work-loop (`3 * * * *`), auto-flush (`15 * * * *`), status-report (`42 * * * *`).
B. **Run the status-report action once more, independently** — an end-of-session summary of everything that happened this session.

---

## Pointers

- Long-horizon backlog (abstract goals, source of future queue items): `todo.md`.
- Completed work (chronological, with releases): `devlog.md`.
- Narrative history: `git log`.
