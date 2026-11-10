---
name: status
description: Check whether Palim is working in this client. Use when the user asks if Palim is connected or working, or why nothing was resumed or saved.
---

# Palim status

Call `palim_resume` with no arguments.

- A thread or "nothing recent" came back: the connector works. Report the thread's title and
  age only, not its content.
- The tool is missing or asks for authentication: the connector is not signed in. In Claude
  Code the user runs `/mcp`, selects `palim` and authenticates. On claude.ai and in Cowork they
  connect it on the plugin's **Connectors** tab.

If the user expected the last thread to be loaded automatically at the start of a Claude Code
session, that is the separate `palim-hooks` plugin. It is installed with
`claude plugin marketplace add joleschmidt/palim-mcp-examples` and
`claude plugin install palim-hooks@palim`, and has its own `/palim-hooks:status`.
