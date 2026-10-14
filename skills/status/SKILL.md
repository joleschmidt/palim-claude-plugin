---
name: status
description: Check whether Palim is working in this client. Use when the user asks if Palim is connected or working, why nothing was resumed or saved, how to set up the Palim API key, or wants to see the last checkpoint.
---

# Palim status

Palim has two parts, and they fail separately. Check both and report each on its own line.

## 1. The connector

Call `palim_resume` with no arguments.

- A thread or "nothing recent" came back: the connector works. Report the thread's title and
  age only, not its content.
- The tool is missing or asks for authentication: the connector is not signed in. In Claude
  Code the user runs `/mcp`, selects `palim` and authenticates. On claude.ai and in Cowork they
  connect it on the plugin's **Connectors** tab.

## 2. The session hooks (Claude Code only)

The hooks load the last thread when a session starts and keep a checkpoint current while the
user works. They fail silently on purpose, so this is the only way to see what they did.

Run this and show its output unchanged:

```bash
python3 "${CLAUDE_PLUGIN_ROOT}/hooks/palim-status.py"
```

The last line, `Result:`, says what to do. The usual case is a missing API key: the hooks cannot
use the connector's sign-in and need their own key. The user creates one at
https://api.usepalim.com/setup and enters it under `/plugin` > Palim > Configure. Do not ask
them to paste the key into the chat.

If there is no shell in this client, skip this part and say that the hooks only run in
Claude Code.
