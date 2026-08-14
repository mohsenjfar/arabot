# Claude — Shared Work Log

Persistent handoff point between mohsen and Claude for this repo. After finishing
each task, Claude updates **Last completed**. mohsen writes the next ask under
**Up next** — that's the queue for the following session.

## Last completed

**Manual (non-LLM) button-driven edit + resource-link flow** (2026-08-14, deployed to `arabot-dev`)

The ✏️ and 🧺 buttons on an activity card no longer open an LLM chat - they're
now fully button/text driven, mirroring the old `legacy-bot-version` Django
bot's `task_edit_keyboard` UX but adapted to the current single-row rrule
`Task` model:

- ✏️ opens an edit menu: 🏷️ title, 📋 description, 📆 date (Jalali calendar
  picker, `src/app/bot/shared/jalali_calendar.py`), 🔄 frequency (raw RRULE
  text, validated before saving), 🟠🔵 copy (clones the task + its resource
  links). New conversation states `EDIT_MENU`/`EDIT_FIELD`.
- 🧺 opens a resource-link menu: existing links show with a ✖️ remove button;
  🔍 uses Telegram's inline-query picker (`switch_inline_query_current_chat`)
  to pick an existing resource, then a plain quantity prompt links it. New
  states `RESOURCE_MENU`/`RESOURCE_QTY`.
- `edit_activity`, `create_resource`, `manage_task_resource` stay wired in
  `tools.json`/`instructions.md` for the LLM - only *these two buttons*
  stopped using them. `/report` and `/resource` (defining a new resource
  type) are still LLM-driven.
- No DB schema change. New service helpers: `copy_activity`,
  `update_activity_frequency`, `describe_rrule`, `get_activity_datetime`
  (task_service.py); `list_task_resource_links`, `link_task_resource_by_id`,
  `unlink_task_resource_by_id` (resource_service.py).
- Not yet committed to git (working tree has this + the resource/inventory
  feature below, both already deployed but uncommitted - see `git status`).

**Resource/inventory tracking feature** (2026-08-13, deployed to `arabot-dev`)

Ported from `legacy-bot-version`'s Django resource module, adapted to the
rrule architecture: `Resource`/`Tag`/`ResourceParity`/`ResourcePrice` (full
legacy field set), `TaskResource` (template link: activity → resource with a
fixed signed quantity, set once), `ResourceLog` (dated history row written
every ✔️ confirm, never on ✖️ skip). Deleting an activity with resource
history freezes future recurrences instead of hard-deleting (`skip_future_activities`),
preserving the log. Migrations `ba1771db5274` (initial tables) and
`0ec19298f798` (fixed `resources.user_id` 32-bit overflow, found live in prod).

## Up next

(mohsen: write the next task here)
