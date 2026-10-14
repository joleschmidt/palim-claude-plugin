"""Shared helpers for the Palim Claude Code hooks.

Design rule for every hook in this directory: a hook must never block, slow down
or break a session. Every failure path exits quietly with status 0.
"""
import json
import os
import pathlib
import re
import time
import urllib.error
import urllib.parse
import urllib.request

API_BASE = os.environ.get("PALIM_API_URL", "https://api.usepalim.com").rstrip("/")
TIMEOUT = float(os.environ.get("PALIM_HOOK_TIMEOUT", "5"))
STATE_DIR = pathlib.Path(
    os.environ.get("PALIM_STATE_DIR", os.path.expanduser("~/.palim/hook-state"))
)

_credentials_cache = "unset"

# HTTP status (or exception name) of the most recent request, for palim-status.py.
last_status = None


def _looks_like_key(value):
    """Guard against a placeholder in the environment shadowing a working key.

    Copying a documented example verbatim ("palim_…") is an easy mistake, and the
    env var takes precedence — so an unusable value there would silently disable
    an otherwise working setup. Anything that is not plausibly a real credential
    is ignored in favour of the client config.
    """
    if not value or not value.isascii():
        return False
    return len(value) >= 20 and re.match(r"^(palim|ctxu)_[A-Za-z0-9_-]+$", value) is not None


def _client_config_credentials():
    """Stub for builds that ship without client-config discovery (the plugin)."""
    return None




def credentials():
    """Auth material for Palim requests, or None. Result is cached per process.

    PALIM_API_KEY wins when set, so an explicit key always overrides the plugin
    option and whatever a client config happens to contain.
    """
    global _credentials_cache
    if _credentials_cache != "unset":
        return _credentials_cache

    # CLAUDE_PLUGIN_OPTION_API_KEY is how Claude Code hands the plugin's userConfig key to hooks.
    for name, source in (("PALIM_API_KEY", "PALIM_API_KEY"), ("CLAUDE_PLUGIN_OPTION_API_KEY", "plugin option")):
        key = (os.environ.get(name) or "").strip()
        if _looks_like_key(key):
            _credentials_cache = {"headers": {"Authorization": f"Bearer {key}"}, "source": source}
            return _credentials_cache

    _credentials_cache = _client_config_credentials()
    return _credentials_cache


def credential_source():
    """Where the credential came from, never the credential itself."""
    return (credentials() or {}).get("source")


def build_url(path, params=None):
    """Compose a URL, folding in query-based credentials when that is what we have."""
    query = dict(params or {})
    creds = credentials() or {}
    query.update(creds.get("query") or {})
    suffix = f"?{urllib.parse.urlencode(query)}" if query else ""
    return f"{API_BASE}{path}{suffix}"


def auth_headers():
    return dict((credentials() or {}).get("headers") or {})


def read_hook_input():
    """Parse the hook payload from stdin. Returns {} when anything is off."""
    try:
        raw = os.read(0, 1 << 20).decode("utf-8", "replace")
        return json.loads(raw) if raw.strip() else {}
    except Exception:
        return {}


def _text_of(content):
    """Claude Code message content is either a string or a list of blocks."""
    if isinstance(content, str):
        return content
    if isinstance(content, list):
        chunks = []
        for block in content:
            if isinstance(block, dict) and block.get("type") == "text":
                text = block.get("text")
                if isinstance(text, str):
                    chunks.append(text)
        return "\n".join(chunks)
    return ""


def scan_transcript(path, want_user_messages=1):
    """Return (recent user messages, total turn count) from a JSONL transcript.

    The transcript is written asynchronously and may lag the current turn, so
    callers should treat the user text as best-effort and rely on the hook
    payload's own fields where available.
    """
    users, turns = [], 0
    if not path or not os.path.isfile(path):
        return [], 0
    try:
        with open(path, encoding="utf-8", errors="replace") as handle:
            for line in handle:
                try:
                    event = json.loads(line)
                except Exception:
                    continue
                if event.get("isSidechain"):
                    continue
                message = event.get("message") or {}
                role = message.get("role")
                if role not in ("user", "assistant"):
                    continue
                turns += 1
                if role == "user":
                    text = _text_of(message.get("content")).strip()
                    # Tool results arrive as user turns; they are not prompts.
                    if text and not text.startswith("<"):
                        users.append(text)
    except Exception:
        return [], turns
    return users[-want_user_messages:], turns


def project_of(cwd):
    if not cwd:
        return None
    return os.path.basename(str(cwd).rstrip("/")) or None


def _state_file(session_id):
    safe = "".join(c for c in str(session_id) if c.isalnum() or c in "-_")[:120]
    return STATE_DIR / f"{safe}.json"


def should_write(session_id, turns, min_seconds, min_turns):
    """Debounce: without this a single user costs ~1150 writes/day."""
    try:
        state = json.loads(_state_file(session_id).read_text())
    except Exception:
        return True
    if time.time() - float(state.get("at", 0)) >= min_seconds:
        return True
    return turns - int(state.get("turns", 0)) >= min_turns


def remember_write(session_id, turns):
    try:
        STATE_DIR.mkdir(parents=True, exist_ok=True)
        _state_file(session_id).write_text(json.dumps({"at": time.time(), "turns": turns}))
    except Exception:
        pass


def claim(session_id, tag, window=30):
    """True for the first caller within `window` seconds, False for the rest.

    The plugin and a manual install can both be registered; their copies of a hook
    then fire in parallel for the same event, and only one of them should act.
    """
    try:
        STATE_DIR.mkdir(parents=True, exist_ok=True)
        marker = _state_file(session_id).with_suffix(f".{tag}.claim")
        for _ in range(2):
            try:
                os.close(os.open(marker, os.O_CREAT | os.O_EXCL | os.O_WRONLY))
                return True
            except FileExistsError:
                if time.time() - marker.stat().st_mtime < window:
                    return False
                marker.unlink()
        return False
    except Exception:
        return True  # Bookkeeping must never suppress the actual work.


def note(kind, **fields):
    """Record the outcome of a hook run for palim-status.py. Never holds a secret.

    Hooks fail silently by design, so this is the only place a failure is visible.
    """
    try:
        STATE_DIR.mkdir(parents=True, exist_ok=True)
        target = STATE_DIR / f"status-{kind}.json"
        if not fields.get("credential"):
            # A second install that has a key may just have done the work; its
            # report is the true one and must not be replaced by "no credential".
            try:
                previous = json.loads(target.read_text())
                if previous.get("credential") and time.time() - float(previous.get("at", 0)) < 300:
                    return
            except Exception:
                pass
        fields["at"] = time.time()
        target.write_text(json.dumps(fields))
    except Exception:
        pass


def prune_state(max_age_days=14):
    """Drop per-session state of sessions that are long over."""
    try:
        cutoff = time.time() - max_age_days * 86400
        for entry in os.scandir(STATE_DIR):
            if entry.name.startswith("status-") or entry.name == "setup-hint-shown":
                continue
            if entry.is_file() and entry.stat().st_mtime < cutoff:
                os.unlink(entry.path)
    except Exception:
        pass


def _send(request):
    """Run a request. Returns (status, body); status is None when nothing came back."""
    global last_status
    try:
        with urllib.request.urlopen(request, timeout=TIMEOUT) as response:
            last_status = response.status
            return response.status, response.read()
    except urllib.error.HTTPError as error:
        last_status = error.code
        return error.code, b""
    except Exception as error:
        last_status = type(error).__name__
        return None, b""


def post_checkpoint(body):
    """Fire the turn checkpoint. Returns True on success, never raises."""
    if not credentials():
        return False
    headers = {"Content-Type": "application/json"}
    headers.update(auth_headers())
    request = urllib.request.Request(
        build_url("/api/checkpoint-turn"),
        data=json.dumps(body).encode("utf-8"),
        headers=headers,
        method="POST",
    )
    status, _ = _send(request)
    return status is not None and 200 <= status < 300


def fetch_resume(within_hours):
    """Return the formatted handoff for the last thread, or None."""
    if not credentials():
        return None
    request = urllib.request.Request(
        build_url("/api/resume", {"format": "text", "within_hours": within_hours}),
        headers=auth_headers(),
    )
    status, body = _send(request)
    if status is None or not 200 <= status < 300:
        return None
    return body.decode("utf-8", "replace").strip() or None
