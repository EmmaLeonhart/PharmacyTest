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

## Data entry & workflow

- **Supplier / purchase-order tracking.** First-class supplier records and PO references
  on receipts, beyond the current free-text reference field.
- **Barcode / scanner entry.** Select drug/lot and enter quantities via barcode scan to
  speed up and de-error receiving and dispensing.

## Integrity assurance

- **Scheduled integrity checks + tamper alerting (remaining).** The check primitive
  ships as `python -m pharmacy check` (exit 0/1) for operators to schedule via their own
  cron. Still **decision-gated**: an in-app/automatic schedule and a notification channel
  on a detected break (email? log? in-app banner?) — needs a product decision.
