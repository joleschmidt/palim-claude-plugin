#!/usr/bin/env python3
"""Palim SessionStart hook — injects the last thread so a new chat starts informed.

Deterministic counterpart to the `palim_resume` MCP tool: the context is present
before the model's first token, with no tool call and no model decision involved.
Also states the session id this chat should checkpoint into, so the model's
handoff and the Stop hook's live tail end up on the same row.
"""
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import palim_hook_lib as lib  # noqa: E402

WITHIN_HOURS = os.environ.get("PALIM_RESUME_WITHIN_HOURS", "48")

SETUP_HINT = (
    "Palim: the session hooks are inactive because no API key is set. "
    "Create one at https://api.usepalim.com/setup and add it under /plugin > Palim > Configure. "
    "This note is shown once; run /palim:status to check again."
)


def hint_once():
    """Tell a plugin user, one single time, why nothing is happening."""
    # Only the plugin has a place to enter the key, so only there is the hint actionable.
    if not os.environ.get("CLAUDE_PLUGIN_ROOT"):
        return
    marker = lib.STATE_DIR / "setup-hint-shown"
    try:
        lib.STATE_DIR.mkdir(parents=True, exist_ok=True)
        os.close(os.open(marker, os.O_CREAT | os.O_EXCL | os.O_WRONLY))
    except Exception:
        return
    print(json.dumps({"systemMessage": SETUP_HINT}))


def _ok(status):
    return isinstance(status, int) and 200 <= status < 300


def main():
    payload = lib.read_hook_input()
    session_id = payload.get("session_id")
    lib.prune_state()

    if not lib.credentials():
        lib.note("resume", credential=None, result="no credential")
        hint_once()
        return

    source = payload.get("source") or "start"
    if session_id and not lib.claim(session_id, f"resume-{source}"):
        return

    context = lib.fetch_resume(WITHIN_HOURS)
    lib.note(
        "resume",
        credential=lib.credential_source(),
        http=lib.last_status,
        result="thread injected" if context else ("no recent thread" if _ok(lib.last_status) else "request failed"),
    )
    if not context:
        return

    if session_id:
        context += (
            f"\n\nCheckpoint target for this chat: `claude-code-{session_id}`. "
            "Use exactly this `session_id` with `palim_save_context`, so that your handoff "
            "and the automatically updated state end up on the same row."
        )

    print(json.dumps({
        "hookSpecificOutput": {
            "hookEventName": "SessionStart",
            "additionalContext": context,
        }
    }))


if __name__ == "__main__":
    try:
        main()
    except Exception:
        pass
    sys.exit(0)
