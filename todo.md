# JamiesProjevt — Long-horizon backlog

**This file is the project's long-term horizon: abstract destinations, not steps.**
Items here describe *where we want to go*, not *what to type next*. When work begins
on one, it is pulled from this file, decomposed into concrete executable steps in
`queue.md`, mirrored into the task tool, and executed. As `queue.md` drains, refill it
by pulling and decomposing the next item here. See `CLAUDE.md` § "Queue and
longer-horizon work".

The product is a **local, multi-user pharmacy controlled-substances tracker** with an
append-only, hash-chained audit ledger. v1 (receive/dispense/dispose/reconcile, auth,
printable reports, integrity verification, first-run admin) is built and on `main`.
Everything below is v2 and beyond.

---

## Security & access control

- **Role-based access control.** Roles (`admin`/`operator`) exist and every action is
  attributed, but no route is admin-gated yet. Restrict catalog management and (future)
  user management to admins; operators keep day-to-day transaction recording.
- **User management UI.** Admins create operators/admins, deactivate accounts, and reset
  passwords from the web UI — today only the first-run bootstrap admin exists.
- **Self-service password change.** A logged-in user can change their own password.
- **Deployment hardening.** Persist a stable `PHARMACY_SECRET_KEY` instead of a random
  per-start key (random key invalidates sessions on restart); document running behind a
  production WSGI server; guidance on `pharmacy.db` backups.

## Reporting & visibility

- **Expiry & low-stock reporting.** Flag lots that are expired or expiring soon, and
  lots whose derived on-hand is at or below a configurable threshold.

## Data entry & workflow

- **Supplier / purchase-order tracking.** First-class supplier records and PO references
  on receipts, beyond the current free-text reference field.
- **Barcode / scanner entry.** Select drug/lot and enter quantities via barcode scan to
  speed up and de-error receiving and dispensing.

## Integrity assurance

- **Scheduled integrity checks + tamper alerting.** Periodically run `verify_chain` and
  surface/notify on any detected break, rather than only on-demand via the Verify page.
