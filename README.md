# JamiesProjevt

> Scaffolded with [cleanvibe](https://github.com/Immanuelle/cleanvibe).

## About

**A local, multi-user pharmacy controlled-substances tracker with a regulatory-grade audit trail.**

Pharmacy staff log in from a browser to record **receiving, dispensing, disposal, and
physical counts** of drug stock. Every action is an immutable, hash-chained ledger entry
attributed to a named user; on-hand quantities are *derived* from that ledger rather than
stored as editable numbers, so the audit trail and the inventory are one and the same.
Tampering with history is mathematically detectable. Records and reports are printable.

- **Stack:** Python + Flask (server-rendered Jinja), SQLite via SQLAlchemy, pytest.
- **Runs locally:** `python -m pharmacy` serves on `127.0.0.1`; staff use a browser.
- **Design spec:** [`docs/superpowers/specs/2026-06-08-pharmacy-controlled-substance-tracker-design.md`](docs/superpowers/specs/2026-06-08-pharmacy-controlled-substance-tracker-design.md)

## Getting Started

```
pip install -r requirements.txt
python -m pharmacy
```

Then open <http://127.0.0.1:5000>. On first run an admin account is created
(`admin` / `admin` by default — override with `PHARMACY_ADMIN_USER` /
`PHARMACY_ADMIN_PASSWORD`). Log in and add drugs, then record
receive / dispense / dispose / reconcile actions. Use **Verify** to check the
audit chain, and the **Printable** links to print inventory and audit reports.

Configuration via environment variables: `PHARMACY_DB` (default
`sqlite:///pharmacy.db`), `PHARMACY_HOST`, `PHARMACY_PORT`,
`PHARMACY_SECRET_KEY`.

Run the tests with `pytest`.
