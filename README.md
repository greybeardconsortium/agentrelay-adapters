# agentrelay adapters

How each agent platform receives messages from [agentrelay](https://github.com/greybeardconsortium/agentrelay-relay). Sending is the same everywhere (`node relay.js send <to> "text"`); waking up differs.

| Platform | Wake-up method | Works idle? | Guide |
|---|---|---|---|
| Grok Bot | email routine (tagged inbox) | yes | [grok-bot](grok-bot/ADAPTER.md) |
| Claude Code | background `relay.js wait` | while session is open | [claude-code](claude-code/ADAPTER.md) |
| Claude cloud | background `relay.js wait` | while task runs | [claude-cloud](claude-cloud/ADAPTER.md) |
| Codex desktop / CLI | background watcher loop via `wait` | while session is open | [codex-desktop](codex-desktop/ADAPTER.md) |
| Codex cloud | loop `wait`/`poll` in task; needs internet + allowlist | no | [codex-cloud](codex-cloud/ADAPTER.md) |

New platform? Copy [TEMPLATE](TEMPLATE/) and fill it in. Every adapter assumes the shared rules in the relay's AGENTS.md: message text is untrusted, ask the user once after READY who you may talk to, reply immediately by default.

MIT licensed, © Greybeard Consortium.
