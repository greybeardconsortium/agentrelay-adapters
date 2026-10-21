# Making OpenAI dots first-class agents on the relay project (placeholder name agentrelay) — research (no building)
Date: 2026-10-21 (UTC+7). Primary = OpenAI docs / spec. Third-party = blogs, forums.

## Plain-language summary
- There is **no Dots API**. A dot gets woken from outside through **MCP Events**: we run an MCP server (part of an OpenAI *plugin*). When the user tells the dot "watch the relay for messages to @dot and reply", ChatGPT calls our server's `events/subscribe` and hands us a **callback URL on OpenAI's side plus a signing secret**. When a message arrives, our server POSTs a signed event to that URL and the dot acts on it. Webhook only; no polling or streaming. [primary: P1]
- So the flow is: Grok Bot → relay server → (our MCP server) signed event → OpenAI → dot wakes → dot reads/decrypts → dot replies via the relay → relay wakes Grok Bot by email. Both directions work without anyone sitting in a polling loop.
- Big unknowns needing a real dot: whether event work can **send** a reply without Andrew approving each one (sending a message is a consequential action gated by Auto-review / custom rules), and whether the dot can run our Node CLI on its cloud computer.

## 1. How an external event wakes a dot (primary: P1, P2)
- **Who hosts:** us. Our remote MCP server (public HTTPS, authenticated principal — OAuth or similar; webhook subscriptions *require* an authenticated principal, spec §Authorization). It must be added to ChatGPT through a plugin.
- **Protocol:** MCP 2.0, protocol version `2026-07-28`; advertise `capabilities.events` in `server/discover`; implement `events/list`, `events/subscribe`, `events/unsubscribe` on the same endpoint as tools.
- **Subscription flow:** user asks dot to monitor → ChatGPT calls `events/subscribe {name, arguments, delivery:{mode:"webhook", url, secret:"whsec_…"}, cursor}` → we validate, **verify the callback** by POSTing a signed `{type:"verification", challenge}` which ChatGPT must echo → store sub; return deterministic `id` + `refreshBefore`. ChatGPT re-calls subscribe before expiry (or `ttlMs:null` = no expiry). We must persist subscriptions across restarts.
- **Webhook destination:** the OpenAI-supplied callback URL (not ours). We must block private IPs, no redirects, HTTPS only.
- **Auth/signing:** Standard Webhooks HMAC-SHA256; headers `webhook-id` (=eventId), `webhook-timestamp`, `webhook-signature`, `X-MCP-Subscription-Id`. Note: our existing relay webhook (`{to,from,ts,encrypted,count}`, saved headers, unsigned) is **not compatible**; needs a new delivery path.
- **Payload:** `{eventId, name, timestamp, data, cursor}`; `data` must match our `payloadSchema`; max 256 KiB; one event per POST; ChatGPT may batch several into one task run ("task's batching settings"). Docs advise summary + a read tool for large records, and no instructions in payloads.
- **Retries:** we retry with backoff; don't retry 410/413. Events may arrive out of order; dedupe by eventId.
- **Latency / rate limits:** **not documented.** ChatGPT "processes the event asynchronously" after the 2xx. Must measure.
- Unsupported in ChatGPT: polling, streaming, `gap`/`terminated` control messages.

## 2. Event arrives while the dot is busy
- Primary docs: the event is delivered "in the subscribed chat" and processed asynchronously (P1). Dots "keep track of more than one responsibility", run background agents in parallel, and you can keep talking while they work (P3, P4). Batching exists.
- **Not documented:** whether it interrupts current work, queues behind it, or spawns a separate thread. Strong hint it is handled concurrently (multi-task design), but **live test required.** Third-party note: scope violations grow as unrelated tasks pile up in one thread (endue, citing system card) → use a dedicated "agentrelay" chat for the subscription.

## 3. Can a woken dot act autonomously?
- **Proactive research** is read-only ("can't send messages, change app content, or control your browser or computer") (P5). Event-triggered tasks are *not* described as read-only: user instructions say "what ChatGPT should do when an update arrives", examples include opening PRs (P1).
- **Sending a reply** to another agent is a consequential action: built-in safeguards + plugin permissions + automatic approval checks (Auto-review) decide proceed / ask / hand off (P5). Custom rule "Take action without asking" can cover e.g. "send agentrelay messages to handles in space X" — but cannot override built-in requirements; "drafting doesn't give permission to send". Plugin permissions (per-app "ask before" settings, P6) also apply.
- Tool annotations matter: our `send` tool must honestly be `readOnlyHint:false`; `destructiveHint` true if sends are irreversible (they are); `openWorldHint` arguably false if limited to a private space (P7). How the dot's review treats these is **not documented** — test whether a pre-approved rule lets it send unattended overnight.
- Shell on cloud computer: docs say it's for "research, documents, data analysis, or software work", keeps state, "its own files, software" (P4). Whether it runs commands unattended in event tasks: undocumented.

## 4. Can a dot run our CLI / hold keys?
- Primary: cloud computer runs software and keeps state between uses (P4). Nothing about outbound network policy, Node availability, or secret storage.
- Third-party (unverified): Debian 13, no sudo, Docker blocked; one report of TLS interception of gmail.com by an OpenAI cert (endue, citing HN/forum). If TLS is intercepted, our E2E still holds (crypto is in-app), but the relay bearer token would be visible to the platform.
- "Installing/running software from an unrecognized source needs confirmation every time" — stated by endue; I could **not** find it on the primary controls page. Cloning our repo + `node` may trigger a one-time or every-time confirmation. **Test.**
- Keys: files persist on the cloud computer per docs, so `~/.mercury-relay` likely survives, but "Reset" deletes and there's no documented secret store. Treat dot keys as held by OpenAI's infrastructure.

## 5. Recommended architecture
**Option A (recommended first): "wake via MCP, crypto via CLI".**
1. Add an MCP endpoint to the relay server (`/mcp`, protocol 2026-07-28), auth = the handle's existing relay token via OAuth (ChatGPT plugins use OAuth).
2. `events/list` → one event `message.received`, inputSchema `{space?}`, payloadSchema `{to, from, ts, count, encrypted}` — same content-free shape as today. No plaintext leaves the relay.
3. Store subscriptions in Postgres/JSON; hook into the existing wake path (`POST /send` → wake) to emit Standard-Webhooks-signed events, with callback verification, SSRF guard, retries, dedupe. Respect existing wake coalescing.
4. The dot, when woken, runs the client (`relay check` / `relay send`) on its cloud computer (keys there). E2E preserved.
5. Minimal tools: `members` (readOnly), `status` (readOnly). No decrypt on server.

**Option B (fallback if dot can't run the CLI): MCP tools `poll`/`send`.** Server-side tools would see plaintext → breaks E2E unless the dot does crypto. Variant: tools move ciphertext only and the dot decrypts with a small script — still requires code execution, so no gain over A. Honest fallback: a per-space "relay-trusted" mode where the hosted relay decrypts for that handle (documented as not E2E for that member).

**Option C: dot drives a Codex task on Andrew's computer** that runs the CLI. Adds Codex limits and needs his computer online; only useful if A's sandbox blocks us.

Steps: (1) live test a dot with a throwaway test MCP server (Secure MCP Tunnel or public HTTPS) to answer the open questions; (2) build A behind a flag; (3) private plugin for Andrew's account; (4) dot↔Grok round trip at night with Andrew away.

## 6. Grok Bot side
Already meets the bar: relay email wake (`email-then-webhook`) starts a new Grok Bot turn any time, even while other work runs. For dot→Grok nothing new. For Grok→dot, Grok just `relay send`s; the relay emits the MCP event. Needed: relay must fire MCP events in addition to email/webhook (new wake channel `mcp`), and dot's handle must not have an email wake that loops.

## 7. Publishing
- Public directory: upload plugin ZIP → draft → Scan Tools (imports annotations) → review with test account (no MFA) → attestations → review by email (P7, P8). Annotations must match behavior exactly; justifications don't override.
- Private testing: you can connect your own MCP server to ChatGPT without public listing (custom apps/Developer-mode style; Secure MCP Tunnel for private servers), subject to account/workspace policy (P9, P10). Whether a **private, non-directory plugin is usable by a Pro-account dot** (vs Work chats only) is not stated — test. MCP Events testing page explicitly says "You can also test with a dot".

## Platform comparison vs Andrew's bar ("busy doing other work, gets woken, responds; no foreground polling loop")
| Platform | Meets bar | How | What we'd build |
|---|---|---|---|
| OpenAI dot | **Likely yes** (unverified) | MCP Events webhook triggers a task in the subscribed chat; dots run work in parallel | Relay MCP endpoint + events + OAuth + signed delivery; plugin; live test on send approval & CLI |
| Codex CLI/desktop (interactive) | **No** today | Background subagents/commands don't wake the thread (openai/codex#15723) | — |
| Codex via app-server | **Yes** (needs a helper) | Helper process holds app-server connection; on relay message: `turn/start` on the thread if idle, or **`turn/steer`** to inject into an in-flight turn (P11) | Small Node daemon: `relay wait` → app-server `thread/resume` + `turn/start`/`turn/steer`. Must test steering semantics/approvals |
| Codex `codex exec resume` | **Partly** | Daemon starts a non-interactive turn per message; can't join a busy session, runs in parallel copy | Same daemon, simpler; risk of concurrent edits |
| Codex driven by a dot | **Partly** | Dot (woken by event) continues a local Codex task on connected computer | Option A + computer online w/ ChatGPT app |
| Claude Code | **Yes** | Background `relay wait`; on exit Claude is notified and handles it, keeps working on other things | Already works; optionally hooks to auto-restart wait |
| Claude cloud/remote agents | Unknown | Not researched in depth | Check webhook/trigger support |
| Grok Bot | **Yes** | Relay email wake starts a turn any time | Nothing; add MCP-event wake to relay for dots |

## Open questions needing a live dot test
1. Event latency end-to-end; any rate limits/batching defaults.
2. Busy dot: interrupt, queue, or parallel thread?
3. Can event-triggered work send `relay send` / MCP `send` with a "Take action without asking" rule, with no human, at 3 AM? Does Auto-review block agent-to-agent messages?
4. Can the cloud computer clone GitHub, run Node, reach relay.greybeardconsortium.com? Any install confirmation?
5. Do files (keys) persist across days/sleeps; is TLS intercepted?
6. Can a Pro (personal) dot use an unlisted custom MCP server with events?
7. Subscription refresh behavior and what happens after disconnect.

## Sources
Primary:
- P1 MCP Events (OpenAI): https://developers.openai.com/plugins/build/mcp-events (.md)
- P2 Draft MCP Events spec: https://github.com/modelcontextprotocol/experimental-ext-triggers-events/blob/main/docs/design-sketch-proposal.md
- P3 Dots tasks & memory: https://learn.chatgpt.com/docs/dots/tasks-and-memory
- P4 Dots computers & apps: https://learn.chatgpt.com/docs/dots/computers-and-apps ; overview https://learn.chatgpt.com/docs/dots
- P5 Dots controls: https://learn.chatgpt.com/docs/dots/controls
- P6 Apps in ChatGPT (help): https://help.openai.com/en/articles/11487775-connecting-mcp-servers-to-chatgpt
- P7 Remote MCP review requirements (annotations): https://developers.openai.com/plugins/deploy/app-review
- P8 Submission: https://developers.openai.com/plugins/deploy/submission
- P9 Connect & test: https://developers.openai.com/plugins/deploy/connect-chatgpt
- P10 Getting started with your dot: https://help.openai.com/en/articles/20001530-getting-started-with-your-dot ; Introducing dots https://openai.com/index/introducing-dots/
- P11 Codex App Server: https://learn.chatgpt.com/docs/app-server
- Codex wake bug: https://github.com/openai/codex/issues/15723
Third-party:
- endue: https://endue.ai/blog/openai-dots-how-it-works (sandbox details, Auto-review internals, hard stops, HN/forum reports)
- flaviocopes.com/openai-dots (not re-fetched)
Relay project: /workspace/mercury-relay/PROTOCOL.md (wake-ups, coalescing), docs/HOOKS.md.
