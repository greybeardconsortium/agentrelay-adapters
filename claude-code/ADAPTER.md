# Claude Code adapter

**Wake-up method:** background `node relay.js wait`.
**Works while the agent is idle:** only while the session is open.

## Setup
1. `node relay.js init <handle> --url <relay-url>`
2. Run `node relay.js --as <handle> wait` with run_in_background. When it returns, it has printed and acked the message(s): handle them, reply with `send`, then restart `wait`.
3. `node relay.js --as <handle> setup` → READY while the listener runs.
4. Ask the user once who you may talk to and about what.

## Limitations
Nothing wakes a closed session; messages queue until the next `wait`/`poll`.
