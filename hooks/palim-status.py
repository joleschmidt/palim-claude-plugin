#!/usr/bin/env python3
"""Palim status — shows whether the hooks are actually doing their job.

The hooks fail silently by design, so a missing key or an unreachable server is
invisible from inside a session. This prints what the hooks last recorded about
themselves, plus whether the server answers. It reads no credential and sends none.
"""
import json
import os
import sys
import time
import urllib.request

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import palim_hook_lib as lib  # noqa: E402


def read(kind):
    try:
        return json.loads((lib.STATE_DIR / f"status-{kind}.json").read_text())
    except Exception:
        return None


def ago(timestamp):
    seconds = max(0, int(time.time() - float(timestamp)))
    if seconds < 90:
        return f"{seconds} s ago"
    if seconds < 5400:
        return f"{seconds // 60} min ago"
    if seconds < 172800:
        return f"{seconds // 3600} h ago"
    return f"{seconds // 86400} days ago"


def server():
    try:
        with urllib.request.urlopen(f"{lib.API_BASE}/health", timeout=lib.TIMEOUT) as response:
            data = json.loads(response.read().decode("utf-8", "replace"))
            return f"reachable ({data.get('status', response.status)})"
    except Exception as error:
        return f"NOT reachable ({type(error).__name__})"


def main():
    resume, checkpoint = read("resume"), read("checkpoint")
    # The plugin build ships without client-config discovery; its key lives in the plugin's settings.
    where = (
        "add it under /plugin > Palim > Configure" if not hasattr(lib, "CLIENT_CONFIGS")
        else "set PALIM_API_KEY, or connect Palim in Claude Code with an x-api-key header"
    )
    lines = [f"Palim status for {lib.API_BASE}", f"Server:            {server()}"]

    if resume:
        lines.append(f"Session start:     {ago(resume['at'])}, {resume.get('result')}")
        lines.append(f"Key used by hooks: {resume.get('credential') or 'NONE FOUND'}")
    else:
        lines.append("Session start:     the hook has not run yet")

    # A keyless second install reports "no key" for a write the other one made; that is no failure.
    failed = bool(checkpoint and not checkpoint.get("ok") and checkpoint.get("credential"))
    if checkpoint:
        outcome = "saved" if checkpoint.get("ok") else f"FAILED ({checkpoint.get('http') or 'no key'})"
        lines.append(f"Last checkpoint:   {ago(checkpoint['at'])}, {outcome}, by the {checkpoint.get('hook')} hook")
    else:
        lines.append("Last checkpoint:   none yet (the first one follows a few turns into a session)")

    if not resume:
        verdict = "Start a new session, then run this again."
    elif not resume.get("credential"):
        verdict = f"No API key. Create one at https://api.usepalim.com/setup and {where}."
    elif resume.get("result") == "request failed" or failed:
        code = checkpoint.get("http") if failed else resume.get("http")
        verdict = (
            f"The server rejected the key (401). Create a new one and {where}."
            if code == 401 else f"Requests are failing ({code}). Check your connection, then try again."
        )
    else:
        verdict = "Working."
    lines.append(f"Result:            {verdict}")
    print("\n".join(lines))


if __name__ == "__main__":
    try:
        main()
    except Exception as error:
        print(f"Palim status could not run: {type(error).__name__}")
    sys.exit(0)
