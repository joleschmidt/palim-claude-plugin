---
name: handoff
description: Carry working state between AI sessions with Palim. Use at the start of a chat to pick up the last thread, when the user refers to earlier work, decisions or another chat ("where were we", "what did we decide", "continue the refactor"), and after a result or decision worth keeping, to write a handoff the next session can continue from.
---

# Handoff with Palim

Palim holds the user's working state across chats and tools: what was being done, what was
decided, what is still open. Use the Palim connector's tools. Never invent stored content, and
never claim something was saved when the tool call failed or the connector is not connected.

## At the start of a chat

1. Call `palim_resume` with no arguments, before answering, unless the last thread is already
   in your context (in Claude Code the plugin's session hook puts it there).
2. If the thread fits the user's first message, continue from it without asking them to recap.
   If it does not fit, ignore it and do not mention it.
3. For a substantial project, call `palim_get_brain` with no arguments to get the distilled
   decisions and open items for the user's topics.

## When the user refers to earlier work

1. Call `palim_search` with the project or topic. Add `project` or `tags` when you know them.
2. Use `palim_get_context` when you need the full state of one topic.
3. Answer from what came back. Give titles and dates so the user can tell where it is from.
   If nothing came back, say so.

## After a result or a decision

Write a handoff with `palim_save_context`. Do it after a decision, a finished step, or before a
long chat is likely to be cut off, not only when asked.

A handoff is written for a reader who has none of this chat. It contains:

- **Goal**: what the user is trying to get done.
- **State**: what is finished, what is half done, and where exactly work stopped.
- **Decisions**: each one with its reason, in `decisions_made`.
- **Open items**: concrete next steps, in `open_items`. Pass `resolved_open_items` for items
  that are now done, quoting the start of the original item.
- **Constraints**: anything the next session must not undo.
- **Files**: paths that matter, in `referenced_files`.

Rules for the call:

- **One row per chat.** Reuse the same `session_id` for every checkpoint in this chat. In
  Claude Code it is `claude-code-` followed by the client session id; when the session hook
  named a checkpoint target, use exactly that one.
- Pass `continues_from` with the `session_id` of the thread you resumed, so the chain between
  chats stays traceable.
- Set `tool_source` to the client you are running in, and `project` when there is one.

A durable fact or preference that is not tied to one thread ("we use pnpm", "answer in German")
goes to `palim_add_memory` instead.

## What not to store

No passwords, API keys, tokens or payment data. No personal data about children, and no health
records. If the user asks to store such data, say that Palim does not accept it and offer to
store a version without it.
