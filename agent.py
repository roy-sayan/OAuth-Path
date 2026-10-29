#!/usr/bin/env python3
"""OAuth Path agent: investigate an app and emit a source-backed OAuth setup guide.

Hosted demo: https://roy-sayan.github.io/OAuth-Path/ (same schema, same rules).
This script is the two-step CLI version: research, then structure, then audit.

Usage:
    export ANTHROPIC_API_KEY=...           # never commit this
    python agent.py "Notion" > guides/notion.json
    python agent.py "https://linear.app" --md > guides/linear.md

Output schema matches the web page (name, verdict, summary, time, effort, facts,
steps, blockers, ev, src). Every source URL must have been returned by search;
anything else is dropped, and claims left without support are downgraded.
"""
import argparse, json, os, re, sys
import anthropic

MODEL = os.environ.get("OAUTH_PATH_MODEL", "claude-sonnet-5-5")
client = anthropic.Anthropic()

RESEARCH_SYSTEM = """You are an integrations analyst helping developers who build AI agents.
Goal: work out what it takes to get an OAuth app registered, approved and usable for
end users of ONE provider. Use web search. Prefer, in order: the provider's own developer
docs and policy pages, official changelogs, then reputable third parties.
Find and note, with the URL for each:
 1. Does the provider support OAuth 2.0 for third-party apps? Which flows/grant types?
 2. How to register an app (portal URL, required fields, redirect URI rules).
 3. Review or approval gates: which scopes/products need review, who reviews, what
    they ask for (privacy policy, domain verification, demo video, security assessment).
 4. Stated or reported timelines and costs. Record exact figures and who said them.
 5. Limits before approval (user caps, test-user lists, rate limits, token lifetimes).
 6. Common rejection reasons and what happens after rejection.
 7. Which steps need a human (account creation, legal forms, identity checks, payment).
Never guess. If something is not found, say it was not found."""

STRUCTURE_SYSTEM = """Turn the research notes into ONE JSON object, nothing else:
{"name":str,"verdict":"Easy|Moderate|Hard","summary":str,"time":str,"effort":"Low|Medium|High",
 "facts":[[label,value],[label,value],[label,value]],
 "steps":[["agent"|"you",str], ...5-8],
 "blockers":[[symptom,fix], ...3-5],
 "ev":[["Primary|Secondary|Unverified",str], ...],
 "src":[[label,url], ...]}
Rules:
- Primary = stated on the provider's own docs/changelog. Secondary = only third parties.
  Unverified = not found, inferred, or likely stale. Do not upgrade labels.
- Times and costs are ranges with their source; if no source gives one, write "not published".
- "agent" steps are things software can do with API/browser tools (draft manifests, scope
  minimisation, test calls, draft submission text). Account creation, legal acceptance,
  identity/payment, recording screencasts and review submissions are "you".
- Use only URLs that appear in the notes. Never invent URLs."""

def text_of(msg):
    return "".join(b.text for b in msg.content if b.type == "text")

def seen_urls(msg):
    urls = set()
    for b in msg.content:
        if b.type == "web_search_tool_result" and isinstance(b.content, list):
            urls.update(r.url for r in b.content if getattr(r, "url", None))
    return urls

def research(target):
    urls, notes = set(), []
    messages = [{"role": "user", "content": f"Investigate OAuth app setup and approval for: {target}"}]
    for _ in range(4):  # allow pause_turn continuations
        msg = client.messages.create(
            model=MODEL, max_tokens=6000, system=RESEARCH_SYSTEM, messages=messages,
            tools=[{"type": "web_search_20250305", "name": "web_search", "max_uses": 12}])
        urls |= seen_urls(msg)
        notes.append(text_of(msg))
        if msg.stop_reason != "pause_turn":
            break
        messages.append({"role": "assistant", "content": msg.content})
    return "\n".join(notes), urls

def structure(target, notes, urls):
    msg = client.messages.create(
        model=MODEL, max_tokens=4000, system=STRUCTURE_SYSTEM,
        messages=[{"role": "user", "content":
                   f"App: {target}\n\nAllowed URLs:\n" + "\n".join(sorted(urls)) +
                   f"\n\nResearch notes:\n{notes}"}])
    raw = text_of(msg)
    m = re.search(r"\{.*\}", raw, re.S)
    if not m:
        raise ValueError("Model returned no JSON")
    return json.loads(m.group(0))

def audit(guide, urls):
    """Drop sources the search never returned; flag if nothing cited."""
    guide["src"] = [s for s in guide.get("src", []) if len(s) == 2 and s[1] in urls]
    if not guide["src"]:
        guide["ev"] = [["Unverified", e[1]] for e in guide.get("ev", [])]
        guide["ev"].append(["Unverified", "No cited source survived the URL check; treat as a draft."])
    guide["generated_with"] = {"model": MODEL, "web_search": True, "setup_attempted": False}
    return guide

def to_markdown(g):
    out = [f"# {g['name']} OAuth path ({g['verdict']})", g["summary"], "",
           f"Time: {g['time']}", f"Effort: {g['effort']}", "", "## Path"]
    out += [f"{i}. [{'Agent' if s[0]=='agent' else 'You'}] {s[1]}" for i, s in enumerate(g["steps"], 1)]
    out += ["", "## Blockers"] + [f"- {b[0]}: {b[1]}" for b in g["blockers"]]
    out += ["", "## Evidence"] + [f"- [{e[0]}] {e[1]}" for e in g["ev"]]
    out += ["", "## Sources"] + [f"- {s[0]}: {s[1]}" for s in g["src"]]
    return "\n".join(out)

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("target", help="App name or website")
    ap.add_argument("--md", action="store_true", help="Emit Markdown instead of JSON")
    ap.add_argument("--out", help="Write to this file instead of stdout")
    a = ap.parse_args()
    notes, urls = research(a.target)
    guide = audit(structure(a.target, notes, urls), urls)
    text = to_markdown(guide) if a.md else json.dumps(guide, indent=2, ensure_ascii=False)
    if a.out:
        os.makedirs(os.path.dirname(a.out) or ".", exist_ok=True)
        open(a.out, "w", encoding="utf-8").write(text)
    else:
        print(text)

if __name__ == "__main__":
    sys.exit(main())
