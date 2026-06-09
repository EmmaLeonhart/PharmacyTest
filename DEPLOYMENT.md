# Deployment

`python -m pharmacy` runs Flask's **development** server — fine for local use and
evaluation, but not for production (single-threaded, no hardening). For real use,
serve the WSGI app (`pharmacy.wsgi:app`) behind a production WSGI server.

The choice of server is yours; the two below are common, well-supported
**recommendations**, not a requirement baked into the app.

## Run behind a WSGI server

The app is exposed as `pharmacy.wsgi:app`, configured from the same environment
variables as the CLI (`PHARMACY_DB`, `PHARMACY_ADMIN_USER` /
`PHARMACY_ADMIN_PASSWORD`, `PHARMACY_SECRET_KEY` / `PHARMACY_SECRET_KEY_FILE`).

**Waitress** (pure-Python, works on Windows and Linux):

```
pip install waitress
waitress-serve --listen=127.0.0.1:8000 pharmacy.wsgi:app
```

**Gunicorn** (Linux/macOS):

```
pip install gunicorn
gunicorn --bind 127.0.0.1:8000 pharmacy.wsgi:app
```

Put a reverse proxy (nginx, IIS, Caddy) in front if you need TLS or to expose it
beyond localhost. Set a stable `PHARMACY_SECRET_KEY` (or let it persist to
`PHARMACY_SECRET_KEY_FILE`) so sessions survive restarts.

## Backups

State lives in two files (both excluded from git):

- **`pharmacy.db`** — the SQLite database (the entire audit ledger). This is the
  system of record; back it up regularly.
- **`pharmacy_secret.key`** — the session signing key (if you rely on the
  persisted key rather than setting `PHARMACY_SECRET_KEY`).

Back up the database safely with SQLite's online backup (consistent even while
the app is running):

```
sqlite3 pharmacy.db ".backup 'backup-pharmacy.db'"
```

Or simply copy `pharmacy.db` while the app is stopped. Because the ledger is
append-only and hash-chained, you can confirm a restored copy is untampered:

```
PHARMACY_DB="sqlite:///backup-pharmacy.db" python -m pharmacy check
```

(exit code `0` = chain intact, `1` = tampering detected).
