# JamiesProjevt — Work Queue

**This file is a queue of *concrete, executable steps*, not a state snapshot.** It lists what is being worked on right now. Finished work lives in `devlog.md` (a dated entry) and `git log`; longer-horizon, *abstract* work lives in `todo.md` and gets decomposed into items here when it's ready to execute. **When an item is done, delete it from this file AND append a dated entry to `devlog.md` in the same commit, then push.** Do not add checkmarks, "done" markers, or status indicators in place. If an item is still here, it is not done.

The purpose of this file is also to bound scope. If a task is not in this queue, it is not in scope for the current session. New ideas go at the bottom of the queue (or to `todo.md` if they are longer-term / architectural), not silently into whatever is being worked on.

**Three-cron playbook.** Work runs under three local `CronCreate` jobs — **work-loop at :03** (drains this queue, refills from `todo.md`), **auto-flush at :15** (commit/push backstop), **status-report at :42** (heartbeat). They were started when this v2 queue was created. The **last two items are pinned at the tail**: ensure the crons are running, then an end-of-session summary. See `CLAUDE.md` § "Autonomous productivity loop".

Each item below builds on the v1 pharmacy tracker (modules in `pharmacy/`, tests in `tests/`). Work them top to bottom, TDD, one commit (or a few) per item.

---

## Active — v2 work

_(empty — the next work-loop tick refills this by decomposing the next `todo.md` horizon)_

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
