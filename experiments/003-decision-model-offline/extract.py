"""Merge per-handle inbox logs into one deduped, time-ordered message list per run."""
import json, glob, os, re, sys
RUNS = {"run1": ("2026-10-21T05:28:00Z", "2026-10-21T05:54:00Z"),
        "run2": ("2026-10-21T07:10:00Z", "2026-10-21T07:21:00Z")}
HDR = re.compile(r"^\[relay\] from @(\S+?)(?: to (.*?))? at (\S+) \(id (\S+?)(?:, re (\S+?))?\)(?: \[[^\]]*\])?: (.*)$", re.S)
msgs = {}
for f in glob.glob(os.path.expanduser("~/.mercury-relay/inbox/*@namelab.jsonl")):
    me = os.path.basename(f).split("@")[0]
    for l in open(f):
        r = json.loads(l); m = HDR.match(r.get("line", ""))
        if not m: continue
        frm, to, ts, mid, re_, body = m.groups()
        e = msgs.setdefault(mid, {"id": mid, "from": frm, "ts": ts, "re": re_, "body": body.replace("\\n", "\n"), "to": set()})
        e["to"].add(me)
out = {}
for run, (a, b) in RUNS.items():
    L = sorted((m for m in msgs.values() if a <= m["ts"] < b), key=lambda m: m["ts"])
    for m in L: m["to"] = sorted(m["to"])
    out[run] = L
json.dump(out, open(sys.argv[1] if len(sys.argv) > 1 else "messages.json", "w"), indent=1)
for r, L in out.items():
    print(r, len(L))
    for i, m in enumerate(L): print(i, m["ts"][11:19], m["from"], "|", m["body"][:90].replace("\n", " "))
