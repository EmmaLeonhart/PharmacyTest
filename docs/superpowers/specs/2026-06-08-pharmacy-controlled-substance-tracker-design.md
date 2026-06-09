# Pharmacy Controlled-Substance Tracker — Design

**Date:** 2026-06-08
**Status:** Approved (design); pending implementation plan

## Summary

A **local, multi-user pharmacy controlled-substances tracker**. A Python (Flask)
web app run on a pharmacy computer; staff log in from a browser and record
**receiving, dispensing, disposal, and physical counts** of drug stock. Its
defining feature is a **regulatory-grade audit trail**: every action is an
immutable, hash-chained ledger entry attributed to a named user, and on-hand
quantities are *derived* from that ledger rather than stored as editable
numbers. Records and reports are printable.

This is v1 — the first usable version.

## Why append-only (Approach A)

Three approaches were considered:

- **A — Append-only ledger as the source of truth (chosen).** Every action is an
  immutable ledger entry; on-hand is derived by summing the ledger; entries are
  hash-chained so tampering with history is detectable. The audit trail *is* the
  inventory.
- **B — Mutable stock table + separate audit log.** Simpler, familiar, but the
  log is a parallel record that can drift from reality and past rows can be
  edited. Too weak for a regulated, audit-grade context.
- **C — Event-sourced JSON API + JavaScript SPA.** Same ledger idea but much
  more code, harder to produce clean printable pages, overkill for a local
  desktop tool used by pharmacy staff.

**A** was chosen because chain-of-custody and tamper-evidence are the whole point
of the product, and server-rendered HTML makes printing trivial.

## Stack

- **Python 3** + **Flask** (server-rendered Jinja templates).
- **SQLite** via **SQLAlchemy**.
- **Werkzeug** password hashing, Flask sessions for login.
- **pytest** for tests; GitHub Actions for CI.
- Run with `python -m pharmacy`, binds to `127.0.0.1:<port>`; staff use a browser.

## Architecture & module boundaries

Each module has one clear job and a well-defined interface:

- **`models.py`** — SQLAlchemy schema: `User`, `Drug`, `Lot`, `LedgerEntry`, `Count`.
- **`ledger.py`** — core domain logic, no Flask. Append a ledger entry, compute
  its hash-chain link, derive on-hand per (drug, lot), and verify chain
  integrity. Maximally testable in isolation.
- **`inventory.py`** — service layer: `receive()`, `dispense()`, `dispose()`,
  `reconcile()`. Validates business rules, then appends ledger entries.
- **`auth.py`** — users, password hashing, login sessions, roles.
- **`reports.py`** — assembles data for printable views (inventory snapshot,
  audit log, reconciliation sheet, transaction receipt).
- **`web/`** — Flask routes + Jinja templates + `print.css`.
- **`__main__.py`** — starts the server.

## Data model

- **User** — `username`, `display_name`, `password_hash`, `role`
  (`admin` | `operator`), `active`.
- **Drug** (catalog) — `name`, `strength`, `form` (tablet/vial/…),
  `code` (NDC or internal), `schedule` (CII–CV), `unit` (unit of measure).
- **Lot** — `drug_id`, `lot_number`, `expiry_date`. Stock is tracked *per lot*.
- **LedgerEntry** (append-only; never updated or deleted) — `id`, `timestamp`,
  `user_id`, `lot_id`, `type` (`receive` | `dispense` | `dispose` | `adjust` |
  `count`), `quantity_delta` (signed), `reason`, `witness_user_id` (required for
  `dispose`), `reference` (prescription/patient/supplier ref), `prev_hash`,
  `entry_hash`.
- **Count** — a reconciliation event: `lot_id`, `counted_qty`, `expected_qty`,
  `discrepancy`, `user_id`, `timestamp`; linked to an `adjust` ledger entry if a
  correction is posted.

**On-hand for a lot = SUM(quantity_delta) over its ledger entries.** Never stored
as a mutable field.

## Core flows

- **Receive** → `+qty` `receive` entry (creates the Lot if new).
- **Dispense** → `−qty` `dispense` entry; rejected if it would drive on-hand
  negative.
- **Dispose / waste** → `−qty` `dispose` entry; **requires a witness** (second
  user) and a reason.
- **Reconcile / count** → record a `count`; if counted ≠ expected, the operator
  may post an `adjust` entry to correct, which is itself audited with a reason.

## Audit & tamper-evidence

Each entry stores `entry_hash = SHA-256(prev_hash + canonical(entry fields))`.
The chain starts from a fixed genesis hash. A **"Verify integrity"** action
re-walks the chain and reports the first entry whose recomputed hash breaks the
chain — so any edit or deletion of history is detectable. The **audit-log view**
is filterable (by drug, user, date, type) and printable.

## Auth & users

Session-based login; passwords hashed. **`admin`** manages users and the drug
catalog; **`operator`** records transactions. Every ledger entry is attributed
to the logged-in user; disposals additionally capture a witness user. First run
creates an initial admin via a first-run setup step.

## Printing

Server-rendered pages plus a dedicated `print.css` give clean output via the
browser's Print → PDF/paper. Printable artifacts:

- Transaction receipt
- Current inventory report
- Audit-log report (filtered)
- Reconciliation count sheet

## Testing

`pytest`, with heaviest coverage on:

- **`ledger.py`** — hash-chain correctness, on-hand derivation, tamper
  detection (mutating a past entry must fail verification).
- **`inventory.py`** — negative-stock rejection, witness-required-for-disposal,
  reconcile/adjust behavior.

CI: `.github/workflows/ci.yml` installs dependencies and runs the suite on push
and pull request.

## Out of scope for v1

- Network/multi-machine hosting beyond a single local host.
- Integration with external pharmacy/EHR systems.
- Barcode scanning hardware.
- Role granularity beyond `admin` / `operator`.
- Automated regulatory report submission.
