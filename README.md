# Palim

Palim hands your working state to the next AI session. You open a new chat and it starts
where the last one stopped: what you were doing, what was decided, what is still open. You
do not ask the old chat for a summary and you do not paste one into the new chat.

It works across tools. A thread you leave in Claude Code can be picked up on claude.ai, in
Cursor or in ChatGPT, because the state lives in your Palim account and not in one client.

## What the plugin adds

| Part | What it does | Where it runs |
|---|---|---|
| Palim connector | The Palim tools: resume the last thread, search earlier work, write a handoff, keep durable facts | Claude Code, claude.ai, Cowork |
| `handoff` skill | Tells Claude when to resume, when to search and what a good handoff contains | Claude Code, claude.ai, Cowork |
| `status` skill | Checks the connector and says what is missing | Claude Code, claude.ai, Cowork |

In Claude Code you can add session hooks that load the last thread at session start and keep
a checkpoint current without a tool call. They are a separate plugin, `palim-hooks`, see
[Session hooks for Claude Code](#session-hooks-for-claude-code).

## Set it up

You need a Palim account. Create one at [api.usepalim.com/setup](https://api.usepalim.com/setup).

1. **Install the plugin.** From Anthropic's directory, add Palim under Customize > Plugins. In
   Claude Code you can also install it from the Palim marketplace:

   ```bash
   claude plugin marketplace add joleschmidt/palim-mcp-examples
   claude plugin install palim@palim
   ```

2. **Sign in to the connector.** In Claude Code run `/mcp`, select `palim` and authenticate. On
   claude.ai and in Cowork, connect it on the plugin's Connectors tab. Sign-in uses OAuth, so
   there is no key to copy.

If you already connected Palim to Claude Code by hand, you can keep that entry. Claude Code
connects to the same server only once.

## Use it

Start a session and work. Claude calls `palim_resume` first and continues the last thread
when it fits your first message.

- "Where were we with the billing migration?" searches your earlier sessions.
- "Save where we are" writes a handoff with the goal, the state, decisions and open items.
- `/palim:status` shows whether the connector works, and what to fix if not.

Your sessions, decisions and open items are in the dashboard at
[api.usepalim.com/dashboard](https://api.usepalim.com/dashboard), where you can read, edit
and delete them.

## What the plugin sends

The plugin contains only Markdown, JSON and an icon. It runs no code on your machine.

Claude calls the Palim tools at `https://api.usepalim.com/mcp` with your OAuth sign-in, and the
plugin talks to no other host. What is sent is what Claude puts into a tool call, for example
the text of a handoff.

Stored conversation content is encrypted with AES-256-GCM. Details are in the
[security notes](https://www.usepalim.com/en/docs/security/) and the
[privacy policy](https://www.usepalim.com/en/privacy/).

## Session hooks for Claude Code

The separate plugin `palim-hooks` adds three hooks: one loads the last thread when a session
starts, one keeps a checkpoint current while you work, one saves before Claude Code compacts
its context. They need their own Palim API key and `python3`.

```bash
claude plugin marketplace add joleschmidt/palim-mcp-examples
claude plugin install palim-hooks@palim
```

What they send is described in its
[README](https://github.com/joleschmidt/palim-mcp-examples/tree/main/plugins/palim-hooks).

## Help

Run `/palim:status` first. More in the [documentation](https://www.usepalim.com/en/docs/) and
under [troubleshooting](https://www.usepalim.com/en/docs/troubleshooting/), or write to
hello@usepalim.com. Do not send API keys or private chat content.

## License

MIT. See [LICENSE](LICENSE).
