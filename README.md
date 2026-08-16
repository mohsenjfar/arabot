# Ara (arabot) — AI-Assisted Task & Resource Manager for Telegram

*[نسخه فارسی / Persian version](README-fa.md)*

A Telegram bot that lets users manage recurring tasks and household/business resources entirely through natural conversation — in Persian, on the Jalali calendar.

## The problem

Most task-reminder bots are either rigid form-fillers (pick a date, pick a repeat rule from a menu) or a thin wrapper that sends every message straight to an LLM, which is slow, expensive, and unpredictable for something as simple as "remind me to water the plants every 3 days."

## The solution

Ara splits the work by what actually needs a language model and what doesn't:

- **Creating a task is instant and free of any LLM call** — the user just types the task, e.g. "دکتر فردا ساعت ۵"، and it's parsed and scheduled immediately.
- **The LLM only takes over for a handful of well-defined jobs** — editing a task, running a natural-language report ("what do I have this week?"), or defining/attaching a resource — and it's restricted to **six explicit tools**, so it can't take an arbitrary destructive action on the user's data.
- **Resource tracking is layered on top of tasks**: a recurring task like "cook rice" can be linked to a pantry item ("rice"), and every time the task is confirmed done, a timestamped consumption record is created automatically — giving the user a real history of usage, not just a checklist.

## Key features

- Natural-language task creation with Jalali (Persian) calendar support, no LLM in the hot path
- Recurring tasks via iCal `RRULE`, with skip/complete handling per occurrence
- LLM-powered editing & reporting through 6 explicit, auditable tools — never raw model output shown to the user
- Resource & inventory tracking: link a task to a pantry/stock item and get automatic, dated consumption logs
- Built-in Pomodoro timer (`/timer`) reusing the same task/notification engine — no separate code path
- Background reminder loop with idempotent notification state (never double-sends)

## Tech stack

- **Python**, `python-telegram-bot` (`ConversationHandler` + `JobQueue`)
- **PostgreSQL (Supabase)** via SQLAlchemy + Alembic migrations
- **LLM tool-calling** via an OpenAI-compatible endpoint (NVIDIA NIM), restricted to a fixed `tools.json` function set
- **Docker** for deployment

## Architecture highlights

- A two-state conversation machine (`ACTIVITY` / `LLM`): plain messages never reach the model; only explicit user actions (✏️ edit, 🧺 resources, `/report`) route into the LLM state.
- Every write the model can make requires a confirmation step defined in the system prompt — the model must show a preview and get `user_confirmed: true` before calling a mutating tool.
- Deleting a task with resource history doesn't hard-delete it (that would orphan the consumption log); it gets soft-closed instead so the historical `ResourceLog` stays intact.

Full implementation details (data model, conversation state machine, background job design, known limitations) are documented in the [Persian README](README-fa.md).

## Status

Personal project, in active use — not yet built for a paying client, but architected the way I'd build a production automation for one.
