# 003 Decision model offline (Jev vs built-in rules)

Goal: before wiring a decision model into the client, check offline whether Jev (TypeSafe's System One model, via OpenRouter) can make the guardrail calls agentrelay needs, compared with simple built-in rules. Data: the real conversations from 001-pick-a-name run 1 and run 2.

## API
- `POST https://openrouter.ai/api/alpha/decisions`, `Authorization: Bearer $OPENROUTER_API_KEY`, model `typesafe/jev-1.13` (answered by build `typesafe/jev-1.13-20260917`).
- Body: `{model, state, questions}`; `questions` is an object keyed by our ids; types `noul` (0-1), `choice` (criteria = option→description), `score` (ordered criteria). Each question is evaluated independently against the same state.
- Response: `answers.<id>.{type, noul | choice+probabilities+confidence}`, `usage.{input_tokens, output_tokens, cost}` (USD).
- Same body works on TypeSafe directly at `https://api.typesafe.ai/v1/systemone` (and OpenRouter `/api/v1/systemone` for the TypeSafe SDK). Not on `/api/v1/chat/completions`.

## Steps (word for word)
1. `export OPENROUTER_API_KEY=...` (never commit it; the scripts only read it from the env).
2. `python3 extract.py data/messages.json`: merges `~/.mercury-relay/inbox/*@namelab.jsonl` into one list per run (run windows hard-coded). Already committed, so you can skip this step.
3. `python3 harness.py`: dedupes group fan-out (one logical message per sender+body), then for each message, evaluated 5 s after it, plus 3 synthetic "silence" checkpoints during run 1's 9-min stall (T+7.6, +9.6, +11.8 min), sends one call with 5 questions:
   - `ack` (noul): is the latest message only an acknowledgement or a repeat of agreement?
   - `state` (choice): progressing / looping / stalled / done
   - `goal_met` (noul): 3/3 agreed and a final sent to the organizer?
   - `stop` (noul): should agents stop sending now?
   - `nudge` (choice): none / claw2 / hermes2 / codex2 / all
   State = brief excerpt, participants, current T+, seconds since last message, the last 12 messages, latest message.
4. Writes `out/answers.json` (every raw answer, latency, usage) and `out/summary.md`. `python3 harness.py --summary` rebuilds the summary.

Ground truth: `labels.json`, hand-labelled from the 001 results files. `a|b` = either accepted. Rules baseline (`rules()` in harness.py): ack regex `^(ack|ok|agreed?|acknowledged|same here|aligned|received|thanks|got it|+1|holding)\b` and <220 chars; looping = ≥4 of last 6 agent messages match it; stalled = >5 min silence; done/goal = a message starting `FINAL`; nudge all when stalled.
Caveat: the rules and the labels were both written after reading these logs, so the rules are tuned to this data (an upper bound for rules). Jev got no examples.
