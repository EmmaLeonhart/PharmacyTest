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
