#!/usr/bin/env python3
"""Palim Stop hook — keeps one checkpoint row per chat current.

Fires after every assistant turn and writes `metadata.live_tail` on the row
`claude-code-<session id>`. The model's own `palim_save_context` writes the
handoff on the same row; the two never touch the same field, so a shallow
mechanical write can never overwrite a rich model-written summary.

Debounced: writes at most every PALIM_CHECKPOINT_MIN_SECONDS (default 180) or
every PALIM_CHECKPOINT_MIN_TURNS turns (default 5), whichever comes first.
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
    should_write,
)

MIN_SECONDS = float(os.environ.get("PALIM_CHECKPOINT_MIN_SECONDS", "180"))
MIN_TURNS = int(os.environ.get("PALIM_CHECKPOINT_MIN_TURNS", "5"))


def main():
    payload = read_hook_input()
    session_id = payload.get("session_id")
    if not session_id:
        return

    assistant = (payload.get("last_assistant_message") or "").strip()
    users, turns = scan_transcript(payload.get("transcript_path"), want_user_messages=1)
    user = users[-1] if users else ""

    if not assistant and not user:
        return
    if not should_write(session_id, turns, MIN_SECONDS, MIN_TURNS):
        return
    if not lib.credentials():
        note("checkpoint", hook="Stop", credential=None, ok=False)
        return

    project = project_of(payload.get("cwd"))
    body = {
        "session_id": f"claude-code-{session_id}",
        "tool_source": "claude",
        "user_message": user,
        "assistant_message": assistant,
        "turn_count": turns,
        # The server defaults to "human" — correct here, because this hook only
        # fires in a live client session. A scheduled runner that knows better
        # sets PALIM_ORIGIN=automation so its own runs stay out of the usage
        # numbers. Without this the retention trend counts the routine as a user.
        "origin": os.environ.get("PALIM_ORIGIN", "human"),
    }
    if project:
        body["project"] = project
        headline = (user or assistant).split("\n", 1)[0][:60]
        body["title"] = f"{project}: {headline}" if headline else project

    ok = post_checkpoint(body)
    note("checkpoint", hook="Stop", credential=lib.credential_source(), http=lib.last_status, ok=ok)
    if ok:
        remember_write(session_id, turns)


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass  # A hook must never break the session.
    sys.exit(0)
