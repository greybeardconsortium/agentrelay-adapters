#!/usr/bin/env python3
"""003: replay 001 conversations through Jev (OpenRouter Decisions API) and built-in rules.
Reads OPENROUTER_API_KEY from the environment only; never prints it.
Usage: python3 extract.py data/raw.json && python3 harness.py   (writes out/answers.json + out/summary.md)"""
import os, json, re, time, urllib.request, urllib.error, datetime as dt, statistics as st
H = os.path.dirname(os.path.abspath(__file__))
URL = "https://openrouter.ai/api/alpha/decisions"
MODEL = os.environ.get("JEV_MODEL", "typesafe/jev-1.13")
WINDOW = 12

def ts(s): return dt.datetime.fromisoformat(s.replace("Z", "+00:00"))
def rng(d, n):
    out = {}
    for k, v in d.items():
        a, _, b = k.partition("-"); 
        for i in range(int(a), int(b or a) + 1): out[i] = v.split("|")
    return [out[i] for i in range(n)]

def dedupe(L):
    out = []
    for m in L:
        if out and any(o["from"] == m["from"] and o["body"] == m["body"] and abs(int(o["id"][:13]) - int(m["id"][:13])) < 3000 for o in out[-3:]): continue
        out.append(m)
    return out

ACK_RE = re.compile(r"^\s*(ack|ok(ay)?|agreed?|acknowledged|same here|aligned|received|thanks|got it|\+1|holding)\b", re.I)
def rule_ack(body): return bool(ACK_RE.match(body)) and len(body) < 220
def rules(msgs, i, now):
    last = msgs[:i + 1]
    gap = (now - ts(last[-1]["ts"])).total_seconds()
    final = any(re.match(r"\s*FINAL", m["body"]) for m in last if m["from"] != "mercury-grok")
    recent = [m for m in last[-6:] if m["from"] != "mercury-grok"]
    acks = sum(rule_ack(m["body"]) for m in recent)
    if gap > 300: state = "stalled"
    elif acks >= 4: state = "looping"
    elif final: state = "done"
    else: state = "progressing"
    return {"ack": rule_ack(last[-1]["body"]), "state": state, "goal_met": final,
            "stop": state in ("looping", "done"), "nudge": "all" if state == "stalled" else "none"}

QUESTIONS = {
 "ack": {"type": "noul", "instructions": "Is the latest message only an acknowledgement or a repeat of agreement, adding no new information and needing no reply?",
         "criteria": {"true": "It just acknowledges, agrees again, or restates what was already said.", "false": "It adds new findings, a new proposal, a first vote, a question, an objection, or an answer."}},
 "state": {"type": "choice", "instructions": "At the current time, which best describes the conversation toward the brief's goal?",
           "criteria": {"progressing": "Participants are adding new work, findings or proposals.",
                        "looping": "Participants keep exchanging acknowledgements or the same agreement without new information.",
                        "stalled": "No one has posted for several minutes and the goal is not met.",
                        "done": "The goal in the brief is met and a final answer was delivered."}},
 "goal_met": {"type": "noul", "instructions": "Has the brief's goal been met: all three agents agreed on one ranking and a final ranking was sent to the organizer?"},
 "stop": {"type": "noul", "instructions": "Should the agents stop sending messages now (because they are looping or already done)?"},
 "nudge": {"type": "choice", "instructions": "Should the organizer nudge someone right now, and who?",
           "criteria": {"none": "No nudge needed; work is moving, or the chat only needs to stop.",
                        "claw2": "Nudge @claw2 only.", "hermes2": "Nudge @hermes2 only.", "codex2": "Nudge @codex2 only.",
                        "all": "Nudge everyone; the conversation is stalled."}},
}

def state_for(brief, msgs, i, now):
    win = msgs[max(1, i - WINDOW + 1): i + 1]
    t0 = ts(msgs[0]["ts"])
    return {"brief_excerpt": brief[:900], "participants": ["@claw2", "@hermes2", "@codex2"], "organizer": "@mercury-grok",
            "current_time": f"T+{int((now - t0).total_seconds())}s",
            "seconds_since_last_message": int((now - ts(msgs[i]["ts"])).total_seconds()),
            "recent_messages": [f"[T+{int((ts(m['ts']) - t0).total_seconds())}s] @{m['from']}: {m['body'][:500]}" for m in win],
            "latest_message": f"@{msgs[i]['from']}: {msgs[i]['body'][:800]}"}

def call(state):
    body = json.dumps({"model": MODEL, "state": state, "questions": QUESTIONS, "session_id": "agentrelay-003"}).encode()
    for attempt in range(4):
        r = urllib.request.Request(URL, body, {"Authorization": "Bearer " + os.environ["OPENROUTER_API_KEY"], "Content-Type": "application/json", "X-Title": "agentrelay-003"})
        t = time.time()
        try:
            j = json.load(urllib.request.urlopen(r, timeout=60)); return j, time.time() - t
        except urllib.error.HTTPError as e:
            if e.code in (429, 500, 502, 503) and attempt < 3: time.sleep(2 ** attempt); continue
            raise RuntimeError(f"HTTP {e.code}: {e.read()[:300]!r}")

def main():
    raw = json.load(open(os.path.join(H, "data/messages.json")))
    labels = json.load(open(os.path.join(H, "labels.json")))
    rows = []
    for run in ("run1", "run2"):
        msgs = dedupe(raw[run]); n = len(msgs); lab = labels[run]
        S, G = rng(lab["state"], n), rng(lab["goal_met"], n)
        brief = next(m["body"] for m in msgs if m["from"] == "mercury-grok")
        cps = [(i, ts(msgs[i + 1]["ts"]) if i + 1 < n else ts(msgs[i]["ts"]) + dt.timedelta(seconds=5), None) for i in range(n)]
        cps = [(i, min(now, ts(msgs[i]["ts"]) + dt.timedelta(seconds=5)), None) for i, now, _ in cps]  # evaluate 5 s after each message
        cps += [(c["after"], ts(c["now"]), "stall") for c in lab["stall_checkpoints"]]
        for i, now, kind in sorted(cps, key=lambda c: (c[0], c[1])):
            truth = {"ack": [i in lab["ack"]],
                     "state": ["stalled"] if kind else S[i],
                     "goal_met": [g == "yes" for g in (["no"] if kind else G[i])]}
            truth["stop"] = [s in ("looping", "done") for s in truth["state"]]
            truth["nudge"] = ["all", "claw2"] if kind else ["none"]
            j, lat = call(state_for(brief, msgs, i, now))
            a = j["answers"]
            jev = {"ack": a["ack"]["noul"] >= 0.5, "state": a["state"]["choice"], "goal_met": a["goal_met"]["noul"] >= 0.5,
                   "stop": a["stop"]["noul"] >= 0.5, "nudge": a["nudge"]["choice"]}
            rows.append({"run": run, "i": i, "kind": kind or "msg", "from": msgs[i]["from"], "body": msgs[i]["body"][:120],
                         "truth": truth, "jev": jev, "rules": rules(msgs, i, now), "raw": a,
                         "latency_s": round(lat, 3), "usage": j.get("usage", {}), "model": j.get("model")})
            print(run, i, kind or "", {k: (v, v in truth[k]) for k, v in jev.items()}, f"{lat:.2f}s", flush=True)
    os.makedirs(os.path.join(H, "out"), exist_ok=True)
    json.dump(rows, open(os.path.join(H, "out/answers.json"), "w"), indent=1)
    summarize(rows)

def summarize(rows):
    Q = list(QUESTIONS)
    L = ["| question | n | Jev | rules |", "|---|---|---|---|"]
    for q in Q:
        n = len(rows); jv = sum(r["jev"][q] in r["truth"][q] for r in rows); rl = sum(r["rules"][q] in r["truth"][q] for r in rows)
        L.append(f"| {q} | {n} | {jv}/{n} ({100*jv/n:.0f}%) | {rl}/{n} ({100*rl/n:.0f}%) |")
    for run in ("run1", "run2"):
        R = [r for r in rows if r["run"] == run]
        L.append(f"| _{run} all-questions_ | {len(R)*len(Q)} | {sum(r['jev'][q] in r['truth'][q] for r in R for q in Q)} | {sum(r['rules'][q] in r['truth'][q] for r in R for q in Q)} |")
    lat = [r["latency_s"] for r in rows]; cost = sum(r["usage"].get("cost", 0) for r in rows); tok = sum(r["usage"].get("input_tokens", 0) for r in rows)
    L += ["", f"Calls: {len(rows)} (5 questions each). Latency p50 {st.median(lat):.2f}s, p90 {sorted(lat)[int(.9*len(lat))]:.2f}s, max {max(lat):.2f}s. Input tokens {tok}. Total cost ${cost:.6f} (${cost/len(rows):.7f}/call). Model {rows[0]['model']}.", "", "## Jev misses", "| run | i | kind | from | question | truth | jev | rules | message |", "|---|---|---|---|---|---|---|---|---|"]
    for r in rows:
        for q in Q:
            if r["jev"][q] not in r["truth"][q]:
                L.append(f"| {r['run']} | {r['i']} | {r['kind']} | {r['from']} | {q} | {'/'.join(map(str, r['truth'][q]))} | {r['jev'][q]} | {r['rules'][q]} | {r['body'][:70].replace('|', '/').replace(chr(10), ' ')} |")
    open(os.path.join(H, "out/summary.md"), "w").write("\n".join(L) + "\n"); print("\n".join(L[:12]))

if __name__ == "__main__":
    import sys
    if sys.argv[1:] == ["--summary"]: summarize(json.load(open(os.path.join(H, "out/answers.json"))))
    else: main()
