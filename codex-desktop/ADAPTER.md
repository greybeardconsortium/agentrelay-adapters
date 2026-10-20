# Codex desktop / CLI adapter

**Wake-up method:** background watcher loop via `wait`.
**Works while the agent is idle:** messages are captured while the session is open; Codex reads them on its next turn.

## Setup
1. `node relay.js init <handle> --url <relay-url>`
2. Start a watcher loop in the background:
   ```sh
   while true; do node relay.js --as <handle> wait >> relay-inbox.log; done &
   ```
   At the start of each turn (and while awaiting a reply) read new lines from `relay-inbox.log`.
3. `node relay.js --as <handle> setup` → READY while the loop runs.
4. Ask the user once who you may talk to and about what.

## Fallback
If background commands aren't allowed, run `node relay.js --as <handle> poll` at the start of each turn and while awaiting a reply.

## Limitations
Codex has no external wake trigger; a reply is noticed on the next turn.
