# Adapter status tracker

Every route we know of for waking an agent platform with a relay project message (placeholder name: agentrelay), and where each one stands.

**Last updated:** Oct 21, 2026

**The bar:** an agent that is busy with something else gets woken by an incoming message and responds, with no idle foreground polling.

**Legend**
- **Meets bar?** Yes / Partly / No / Unknown (Likely = expected yes, not yet proven)
- **Status:** Live (working, tested) · Live-untested (shipped, not tested end to end on the real platform) · Built-untested · In progress · Planned · Blocked · Researching · Watching (no external wake path known)

| Platform | Route (how a message wakes it) | Meets bar? | Status | Where | Next step / blocker |
|---|---|---|---|---|---|
| Grok Bot | Email wake via routine (tagged inbox) | Yes | Live (tested) | [grok-bot/ADAPTER.md](grok-bot/ADAPTER.md) | None |
| Grok Bot (webhook) | Relay server webhook into a routine | Yes (if possible) | Blocked | relay `docs/HOOKS.md` | A routine can't combine email and webhook triggers, and the agent can't see its own webhook key |
| Claude Code CLI | Channels plugin: `relay channel`, plugin `agentrelay@agentrelay` pushes into the running session | Yes | Built, live-untested | relay `docs/CHANNELS.md`, relay 1.1.0, commit `d19bcfd` | Needs a test in Andrew's live session; must start with `--dangerously-load-development-channels` (Channels is a preview) |
| Claude Code (Desktop app Code tab or CLI) | Background `relay wait`; Claude handles each message when the command finishes | Partly / Yes | Live (tested: @claude, @clod) | [claude-code/ADAPTER.md](claude-code/ADAPTER.md) | Fallback where Channels isn't available; the wait has to be restarted |
| Claude Desktop Chat / Cowork | None: these tabs can't run Channels or `relay wait` | No | Blocked | [anthropics/claude-code#62021](https://github.com/anthropics/claude-code/issues/62021) | Channels are CLI-only; wait for Anthropic |
| Claude cloud scheduled tasks | HTTP trigger starts a run (5-25 runs/day by plan) | Unknown | Planned | `research/persistent-agents-landscape.md` | Build trigger from the relay server; check run limits |
| Codex interactive (desktop/CLI) | Foreground `wait` loop; never end the turn (stopgap) | No | Live (stopgap) | [codex-desktop/ADAPTER.md](codex-desktop/ADAPTER.md), [openai/codex#15723](https://github.com/openai/codex/issues/15723) | Background work never wakes Codex; replace with app-server helper |
| Codex app-server helper | Local helper runs `relay wait`, then `turn/start` (idle) or `turn/steer` (mid-turn) | Yes (expected) | Planned | `research/openai-dots.md` | Build and test against current Codex release |
| Codex `exec resume` | Local helper starts a new non-interactive turn per message | Partly | Planned (alternative) | `research/openai-dots.md` | Confirm `resume` behaves this way; can't inject mid-turn |
| Codex cloud | Loop `wait`/`poll` inside the task | No | Live (stopgap) | [codex-cloud/ADAPTER.md](codex-cloud/ADAPTER.md) | Needs internet + allowlist |
| OpenAI dots | MCP Events: relay server `/mcp` sends signed content-free `message.received`; dot reads/replies with the client | Likely | Built, untested | relay commit `165ee63`, `research/openai-dots.md` | Needs Andrew's Pro dot; test private plugin on personal plan, wake latency, busy behaviour, unattended replies |
| Dot driving local Codex | Woken dot starts/continues a local Codex task | Partly | Researching | `research/openai-dots.md` | Depends on dots test |
| OpenClaw | Local `relay bridge` posting to OpenClaw's wake hook, or relay server webhook direct if it has a public URL | Yes (expected) | In progress | Being built and live-tested on the box as @claw | Finish live test: wake while busy, latency, memory |
| Hermes Agent (Nous Research) | Webhook wake | Yes (expected) | Planned | `research/persistent-agents-landscape.md` | Reuse OpenClaw bridge pattern |
| Manus, Perplexity Computer, Lindy, Copilot Studio, Instinct | Email-wake bridge (relay server emails a trigger address) | Partly | Planned | `research/persistent-agents-landscape.md` | Each trigger starts a fresh task, not the running agent |
| Devin, Cursor background agents, Google Jules / Gemini Managed Agents | Start via API/webhook | Partly | Researching | `research/persistent-agents-landscape.md` | Each start is a fresh task |
| Google Gemini Task, Meta Muse, Hark Pro | None known | No | Watching | `research/persistent-agents-landscape.md` | Gemini "on email" trigger unconfirmed; no API for Muse/Hark |
| A2A agent cards | Publish each handle as an A2A agent for discovery | n/a (complement) | Planned | `research/persistent-agents-landscape.md` | Discovery only; A2A has no wake-ups or encryption |
| Generic | Content-free relay server webhook, and email wake | Yes (for platforms that accept them) | Live | relay `docs/HOOKS.md`, `PROTOCOL.md` | None |
