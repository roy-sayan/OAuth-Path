# OAuth Path

Look up an app, get a shareable guide to its OAuth setup and approval, and know what an
agent can do versus what you must do yourself.

**Live demo:** https://roy-sayan.github.io/OAuth-Path/

## The problem

A developer building an AI agent needs their users to connect an app. If Composio has a
managed OAuth app for that toolkit, they register nothing. If not, or if they want their own
branding, custom scopes or their own rate-limit quota, they must register an OAuth app with
the provider and sometimes get it approved. Today they piece this together from docs and
emails. They cannot tell whether it is an hour of work or weeks of waiting.

## What is in this repo

| File | Purpose |
|---|---|
| `index.html` | The hosted product (GitHub Pages): guide library plus live "generate a guide" box |
| `agent.py` | CLI research agent: web search, structured guide, source audit |
| `worker.js` | Optional Cloudflare Worker proxy so visitors can generate guides without an API key |

Library guides: **GitHub** (easy), **Slack** (moderate), **Google/Gmail** (hard), **LinkedIn** (hard).
These were picked because their friction differs in kind: no review, a rate-limit trap,
a scope-driven security assessment, and manual per-product review.

## How live generation works

Type an app name or website that is not in the library. The agent searches the web, drafts a
guide in the same schema as the library, drops any source URL that search did not return, and
labels each claim Primary, Secondary or Unverified.

The site is static, so the API key must live somewhere. Two modes:

1. **Proxy (recommended for demos).** Deploy `worker.js`, then set `PROXY_URL` in `index.html`.
   The key stays server-side as a Worker secret. Visitors need nothing.
2. **Bring your own key (default, no backend).** If `PROXY_URL` is empty, the page asks for an
   Anthropic API key, keeps it in tab memory only, and calls the API directly from the browser.
   No key is stored, logged or committed.

```bash
# Proxy deploy
npm i -g wrangler
wrangler secret put ANTHROPIC_API_KEY
wrangler deploy worker.js --name oauth-path
# then set PROXY_URL in index.html and redeploy Pages
```

## CLI agent setup

```bash
pip install -r requirements.txt
export ANTHROPIC_API_KEY=...        # keep out of git
python agent.py "Notion" --out guides/notion.json
python agent.py "https://linear.app" --md
```

Optional: `OAUTH_PATH_MODEL` overrides the model. The browser and Worker paths use one combined
search-and-answer call; the CLI uses separate research and structuring steps. Keep the prompts
in sync.

## Key decisions

1. **Answer "how hard is this?" first.** Every guide opens with a verdict, time, effort and
   the review gate, before any steps. Developers decide whether to build at all from this.
2. **Every step is tagged Agent or You.** This is the honest answer to "what can an agent do
   for me." Agents draft manifests, minimise scopes, write submission text and run test calls.
   Humans create accounts, accept legal terms, record screencasts and pass identity checks.
3. **Evidence labels instead of confidence theatre.** Each claim is Primary (provider docs),
   Secondary (third parties) or Unverified. Times and costs are ranges with their source.
4. **The agent cannot cite what it did not retrieve.** `agent.py` drops any source URL that
   search never returned, and downgrades claims when nothing survives.
5. **Start from Composio's managed-auth check.** The first thing a developer should learn is
   whether they need to register an app at all (`composio_managed_auth_schemes`).
6. **Four deep guides over one hundred shallow ones.** Quality and evidence matter more than
   coverage for a take-home. The schema is fixed so coverage scales by running the agent.

## What I tested and what I did not

- Guides were built from provider docs, changelogs and third-party write-ups, researched
  on 29 Oct 2026.
- **No provider accounts were created and no OAuth approval was attempted.** All times are
  estimates from documentation and reports, not measurements.
- `agent.py`, `worker.js` and the browser live-generation path were syntax-checked but **not run
  end to end**; I had no network or API key in my build environment. Test live generation on
  the hosted page with an unfamiliar app before relying on it.
- Not verified: whether Composio's managed apps for Slack, Google or LinkedIn avoid the
  limits described; whether a GitHub App's credentials work with a Composio custom auth
  config; real review durations for Slack Marketplace and LinkedIn.

## Limitations

- Live guides are research drafts: web-searched and source-filtered, but setup was not attempted
  and the model can still misread a source. Bring-your-own-key mode costs the visitor API usage.
- A public Worker needs spend and rate limits before wider sharing; the included one only checks origin.
- Provider policy changes often (Slack rate limits, Google verification tiers). Guides carry a
  research date and should be re-run periodically.
- Third-party sources for Google costs and LinkedIn tier limits disagree or are vendor-biased.
- The agent does not yet attempt setup. Next step: drive provider consoles for the
  no-payment, no-review portions (create app, set redirect URI, request minimal scopes)
  and record what actually breaks.
- No user accounts, saved guides, or change monitoring.

## Next steps

1. Run the agent on 20 apps; manually audit 5 against provider docs; track the correction rate.
2. Attempt real setup for GitHub, Slack and Google up to the review gate; log blockers.
3. Cross-reference with Composio's managed-auth directory so the guide opens with
   "Composio provides this" where true.
4. Re-run guides on a schedule and surface diffs when policies change.
