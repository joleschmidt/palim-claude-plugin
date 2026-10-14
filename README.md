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
| `status` skill | Checks the connector and the hooks and says what is missing | Claude Code, claude.ai, Cowork |
| Session hooks | Load the last thread when a session starts and keep a checkpoint current while you work, without a tool call | Claude Code |

The hooks are the reason to use the plugin in Claude Code. An instruction to save fades over
a long session. A hook fires at turn 400 the same way it fires at turn 1.

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

3. **Give the hooks a key (Claude Code).** The hooks run outside the model and cannot use the
   connector's sign-in. Create an API key on the setup page and enter it when Claude Code asks
   for the plugin's options, or later under `/plugin` > Palim > Configure. Claude Code keeps
   it in your system's secure storage. Without a key the hooks do nothing and the rest of
   the plugin still works.

If you already connected Palim to Claude Code by hand, you can keep that entry. Claude Code
connects to the same server only once. If you registered the Palim hooks by hand in
`~/.claude/settings.json`, remove those three entries so each hook runs once.

## Use it

Start a session and work. In Claude Code the last thread is already in context, so you can
say "continue" and Claude knows with what. Elsewhere Claude calls `palim_resume` first.

- "Where were we with the billing migration?" searches your earlier sessions.
- "Save where we are" writes a handoff with the goal, the state, decisions and open items.
- `/palim:status` shows whether the connector and the hooks work, and what to fix if not.

Your sessions, decisions and open items are in the dashboard at
[api.usepalim.com/dashboard](https://api.usepalim.com/dashboard), where you can read, edit
and delete them.

## What the plugin runs and what it sends

The plugin talks to one host, `api.usepalim.com`, and to nothing else.

**Connector.** Claude calls the Palim tools at `https://api.usepalim.com/mcp` with your OAuth
sign-in. What is sent is what Claude puts into a tool call, for example the text of a handoff.

**Hooks.** Three Python scripts in `hooks/`, started by Claude Code. They use the API key from
the plugin's options, or `PALIM_API_KEY` if you set it. They read no other credential.

| Hook | When | What it sends |
|---|---|---|
| `palim-resume.py` | Session start, and after `/clear` | A request for your last thread from the past 48 hours. The answer is added to Claude's context. |
| `palim-checkpoint-turn.py` | After a turn, once 3 minutes or 5 turns have passed since the last checkpoint | Your last prompt, Claude's last answer, the session id, the turn count and the name of the project folder |
| `palim-precompact.py` | Before Claude Code compacts the context | The first line of your last 3 prompts, Claude's last answer, the session id, the turn count and the name of the project folder |

To find your last prompt, the checkpoint hooks read the session transcript that Claude Code
keeps on your machine. They send no file contents, no tool output and no other part of the
transcript.

**Status.** `hooks/palim-status.py` runs only when you ask for the status. It reads the notes
described below and requests `https://api.usepalim.com/health` without a credential.

**On your machine.** The hooks keep small files in `~/.palim/hook-state`: when a session was
last written, and the outcome of the last hook run. These files never contain your key or
your prompts. Files of old sessions are deleted after 14 days.

**On the server.** Stored conversation content is encrypted with AES-256-GCM. Details are in
the [security notes](https://www.usepalim.com/en/docs/security/) and the
[privacy policy](https://www.usepalim.com/en/privacy/).

Every hook exits with status 0 whatever happens: no key, no network, a timeout, broken
input. A hook cannot block a session, and it gives up on a request after 5 seconds.

## Requirements

- Claude Code with plugin options support for the hooks, and `python3` (3.8 or later) on
  your `PATH`. The scripts use the standard library only.
- On claude.ai and in Cowork the connector and the skills work without any of that.

## Settings

Environment variables for the hooks. All are optional.

| Variable | Default | Effect |
|---|---|---|
| `PALIM_API_KEY` | not set | Used in place of the key from the plugin's options |
| `PALIM_API_URL` | `https://api.usepalim.com` | Another Palim server, for testing |
| `PALIM_CHECKPOINT_MIN_SECONDS` | `180` | Minimum time between two turn checkpoints |
| `PALIM_CHECKPOINT_MIN_TURNS` | `5` | Turns after which a checkpoint is written anyway |
| `PALIM_RESUME_WITHIN_HOURS` | `48` | Older threads are not loaded at session start |
| `PALIM_PRECOMPACT_PROMPTS` | `3` | Prompts included in the checkpoint before compaction |
| `PALIM_STATE_DIR` | `~/.palim/hook-state` | Where the hooks keep their local files |
| `PALIM_HOOK_TIMEOUT` | `5` | Seconds after which a hook gives up on a request |

## What it does not do

The hooks record what was said, not what it meant. The handoff that a later session can
really work from is the one Claude writes with `palim_save_context`. The hooks make sure
there is a current state even when that did not happen.

## Help

Run `/palim:status` first. More in the [documentation](https://www.usepalim.com/en/docs/) and
under [troubleshooting](https://www.usepalim.com/en/docs/troubleshooting/), or write to
hello@usepalim.com. Do not send API keys or private chat content.

## License

MIT. See [LICENSE](LICENSE).
