# Experiments

Repeatable multi-agent experiments on the relay: several persistent agents on different
platforms get one brief in a private space and work it out among themselves, woken by relay
messages (no foreground polling). Each experiment folder has everything needed to rerun it verbatim.

## Layout
```
experiments/
  README.md                 this file: how to run any experiment, measurement and scoring
  NNN-short-name/
    EXPERIMENT.md           goal, roles, exact setup, rules, stop condition, metrics, rubric
    brief.md                the brief, verbatim (with {placeholders} filled at run time)
    results/YYYY-MM-DD-runN.md   one log per run
```
Never commit secrets, tokens, invite codes, webhook secrets or message ciphertext.

## Roles
- **Organizer** (one agent, e.g. a Grok Bot): creates the space, posts the brief, answers direct questions factually, never votes or steers. Needs a wake-up (email wake for Grok Bot) or polls as an observer.
- **Researchers** (N agents, ideally on different platforms): do the work and agree. Each must have a real wake path, so they answer while busy:

| Platform | Wake path | Setup |
|---|---|---|
| OpenClaw | `relay bridge openclaw --agent <id>` → Gateway `/hooks/wake` | [openclaw](../openclaw/ADAPTER.md); new agent per run (`openclaw agents add`) for a clean session |
| Hermes Agent | `relay bridge hermes --route <route>` → webhook route | [hermes](../hermes/ADAPTER.md); dedicated route + skill per run; each wake is a fresh run, so give it a notes file |
| Codex CLI | `relay codex --spawn [--headless]` + `codex --remote` | [codex](../codex/ADAPTER.md); restart the helper for a fresh thread |
| Claude Code | channel plugin | [claude-code](../claude-code/ADAPTER.md) / relay docs/CHANNELS.md |
| Grok Bot | email wake routine | [grok-bot](../grok-bot/ADAPTER.md) |

## Running one
1. Pick the experiment and N. Fill the brief's placeholders (participants, assignment split) exactly as EXPERIMENT.md says.
2. Fresh state: new space `<exp>-<date>` (organizer owns it), fresh handles, fresh sessions/threads (see table). Start every process without secrets in its environment (on the reference box: `env -u OPENAI_API_KEY -u __CURSOR_SANDBOX_ENV_RESTORE`).
3. Sanity ping each researcher ("reply pong"); then reset or note any context the ping left.
4. Post the brief as one group message (`send a,b,c "$(cat brief.md)"`). Record the time.
5. Observe without steering. On the box, `~/.mercury-relay/inbox/<handle>.jsonl` (written by the client before every ack) shows what each local agent received and when; bridge/helper logs show wake times.
6. Optional **scripted interruptions** (see 001's section, reusable for any experiment): the organizer sends one researcher at a time an unrelated small request on a fixed schedule, then measures answer latency, correctness and recovery (did it resume unprompted, how long until its next task message, lost context or duplicate work). Results files then get a **Recovery** section.
7. Stop on the experiment's stop condition, the time limit, or a stall/loop (no new message for 15 min, or the same content repeated 3 times).
8. Write `results/YYYY-MM-DD-runN.md` from the template below and commit it.

## Measurement template (results file)
```
# <experiment> run N (YYYY-MM-DD)
Participants: @a (platform, model), ...   Organizer: @x
Brief: verbatim from brief.md at commit <sha>, placeholders: ...
## Timeline (UTC+7)
HH:MM  event
## Metrics
- Time to first reply / to proposal / to agreement / to deliverable
- Messages sent per agent (and total); wakes per agent; median wake → reply latency
- Stalls (gaps > 15 min), loops (repeated content), off-brief actions
- Cost: model, approximate tokens or turns per agent
## Recovery (if interruptions were used)
slot | agent | sent | answered | latency | correct | resumed unprompted | next task msg after | lost context / duplicate work
## Outcome
Deliverable (verbatim or summarized), agreement state
## Score (rubric in EXPERIMENT.md)
## What broke / changes for next run
```

## Scoring (common part, 0–2 each, max 10)
- **Completion:** deliverable produced within the limit (2), late or partial (1), none (0).
- **Agreement:** explicit agreement from all researchers (2), majority (1), none (0).
- **Evidence:** claims checked with real lookups and marked unverified otherwise (2), mixed (1), guesses (0).
- **Collaboration:** agents built on each other's findings, used `--re`, no loops (2), some (1), parallel monologues (0).
- **Autonomy:** no organizer steering or human rescue needed (2), one nudge (1), more (0).
Each experiment adds its own task-specific rubric.
