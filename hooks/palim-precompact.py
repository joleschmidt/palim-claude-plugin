#!/usr/bin/env python3
"""Palim PreCompact hook — last guaranteed checkpoint before context is compacted.

Compaction is the moment context is most likely to be lost, so this hook ignores
the debounce and always writes. It also carries the last few user prompts instead
of just one, because a single turn is a thin record of a long session.

This is a floor, not a substitute for a model-written handoff: it stores what was
said, not what it meant.
"""
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import palim_hook_lib as lib  # noqa: E402
from palim_hook_lib import (  # noqa: E402
    note,
    post_checkpoint,
    project_of,
    read_hook_input,
    remember_write,
    scan_transcript,
)

RECENT_PROMPTS = int(os.environ.get("PALIM_PRECOMPACT_PROMPTS", "3"))


def main():
    payload = read_hook_input()
    session_id = payload.get("session_id")
    if not session_id:
        return

    users, turns = scan_transcript(payload.get("transcript_path"), want_user_messages=RECENT_PROMPTS)
    assistant = (payload.get("last_assistant_message") or "").strip()
    user = "\n\n".join(f"- {u.splitlines()[0][:300]}" for u in users if u.strip())

    if not user and not assistant:
        return
    if not lib.credentials():
        note("checkpoint", hook="PreCompact", credential=None, ok=False)
        return

    project = project_of(payload.get("cwd"))
    body = {
        "session_id": f"claude-code-{session_id}",
        "tool_source": "claude",
        "user_message": f"Last requests before compaction:\n{user}" if user else "",
        "assistant_message": assistant,
        "turn_count": turns,
    }
    if project:
        body["project"] = project

    ok = post_checkpoint(body)
    note("checkpoint", hook="PreCompact", credential=lib.credential_source(), http=lib.last_status, ok=ok)
    if ok:
        remember_write(session_id, turns)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass
    sys.exit(0)
