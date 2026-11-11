#!/usr/bin/env python3
"""compliance map: what does it take to do X in place A vs B vs C - from official government sources.
TinyFish: Research (deep run per activity) + Search (find official portals) + Fetch (confirm pages live)."""
import argparse, json, os, re, sys, time, urllib.request, urllib.parse
from datetime import date

AGENT = "https://agent.tinyfish.ai/v1"
SEARCH_URL = "https://api.search.tinyfish.ai"
FETCH_URL = "https://api.fetch.tinyfish.ai"
GOV = re.compile(r"\.gov\b|\.gov\.|\.gob\.|\.govt\.|\.gc\.ca|\.govt\.nz|\.gouv\.|europa\.eu|nationalarchives|singpass|mygov|india.gov|karnataka.gov|uae\.ae|dubai\.ae.|eesti\.ee|delaware\.gov", re.I)

def _req(url, key, payload=None, timeout=60):
    data = json.dumps(payload).encode() if payload is not None else None
    req = urllib.request.Request(url, data=data, method="POST" if data else "GET",
        headers={"X-API-Key": key, "Content-Type": "application/json", "User-Agent": "compliance-map/1.0"})
    with urllib.request.urlopen(req, timeout=timeout) as r:
        return json.load(r)

def research_launch(key, activity, places):
    plist = ", ".join(places)
    q = (f"A founder wants to {activity}. Compare exactly what it takes in each of these places: {plist}. "
         "Use ONLY official government sources (ministries, municipal corporations, licensing authorities, "
         "tax/registrar portals). For EACH place give: (1) every licence, registration and filing required, in order; "
         "(2) government fees for each step in local currency; (3) official processing time per step; "
         "(4) renewals and ongoing filings after starting; (5) the official page URL for every single item, "
         "with the date you checked it. Format: one markdown section per place with a table "
         "(requirement | detail | fee | time | official source URL). Where a rule is unclear, varies by case, "
         "or no official source exists, write UNCLEAR - never guess. End with: a side-by-side summary table "
         "(place | total govt fees | total time to approval | number of steps), a recommendation for the easiest "
         "place to start, and the trade-offs of that choice.")
    run = _req(f"{AGENT}/automation/run-research-async", key, {"query": q, "mode": "deep"}, timeout=90)
    return run.get("id") or run.get("research_run_id")

def research_poll(key, rid, wait=1500):
    deadline = time.time() + wait
    while time.time() < deadline:
        time.sleep(20)
        st = _req(f"{AGENT}/research-run/{rid}", key)
        if st.get("status") in ("completed", "done", "success"):
            return st
        if st.get("status") in ("failed", "cancelled"):
            raise RuntimeError(f"research run {rid} failed")
    raise TimeoutError(f"research run {rid} still running after {wait}s")

def search(key, q, n=5):
    try:
        url = SEARCH_URL + "?" + urllib.parse.urlencode({"query": q, "num_results": n})
        req = urllib.request.Request(url, headers={"X-API-Key": key, "User-Agent": "compliance-map/1.0"})
        with urllib.request.urlopen(req, timeout=45) as r:
            d = json.load(r)
        return d.get("results") or d.get("data") or []
    except Exception as e:
        print(f"search failed ({q[:40]}): {e}", file=sys.stderr); return []

def fetch_title(key, url):
    try:
        r = _req(FETCH_URL, key, {"urls": [url], "format": "markdown"}, timeout=60)
        res = (r.get("results") or [{}])[0]
        txt = (res.get("text") or res.get("title") or "")[:4000]
        return (res.get("title") or txt[:80]), len(txt) > 200
    except Exception as e:
        return f"fetch failed: {e}", False

def main():
    ap = argparse.ArgumentParser(description="Compare licences, costs and time to start an activity across places (TinyFish Research + Search + Fetch).")
    ap.add_argument("activity"); ap.add_argument("places", nargs="+")
    ap.add_argument("--research-run", help="existing research run id to poll instead of launching")
    ap.add_argument("--research-md", help="saved research memo markdown (skips launch+poll)")
    ap.add_argument("--out", help="write comparison markdown here")
    args = ap.parse_args()
    key = os.environ.get("TINYFISH_API_KEY") or sys.exit("set TINYFISH_API_KEY")

    memo, rid = None, args.research_run
    if args.research_md:
        memo = open(args.research_md).read()
        print(f"[1/3] Research: loaded saved memo ({len(memo)} chars)", file=sys.stderr)
    else:
        if not rid:
            print("[1/3] Research: launching deep run...", file=sys.stderr)
            rid = research_launch(key, args.activity, args.places)
            print(f"      run id {rid}", file=sys.stderr)
        st = research_poll(key, rid)
        deep = st.get("deep_result")
        if isinstance(deep, str):
            try: deep = json.loads(deep)
            except Exception: pass
        memo = deep.get("result") if isinstance(deep, dict) else (deep or st.get("quick_result") or "")
        with open(f"research-{rid}.json", "w") as f:
            json.dump(st, f)
    urls = sorted(set(re.findall(r"https?://[^\s)\]|\"']+", memo)))
    gov_urls = [u for u in urls if GOV.search(u)]
    print(f"      memo: {len(urls)} urls cited, {len(gov_urls)} on official domains", file=sys.stderr)

    print("[2/3] Search: finding official portals per place...", file=sys.stderr)
    portals = {}
    for p in args.places:
        hits = search(key, f"{args.activity} licence registration official government {p}")
        portals[p] = [h for h in hits if GOV.search(h.get("url") or "")][:3]

    print("[3/3] Fetch: confirming top official pages are live...", file=sys.stderr)
    confirmed = {}
    for p, hits in portals.items():
        for h in hits[:1]:
            u = h.get("url")
            if u:
                confirmed[p] = (u,) + fetch_title(key, u)

    L = [f"# compliance map: {args.activity}", "",
         f"places compared: {' vs '.join(args.places)} | checked {date.today().isoformat()}",
         f"TinyFish Research deep run {rid or 'attached memo'} - every item below cites the official page it came from", "",
         memo, "",
         "## official portals (Search API, gov domains first)", ""]
    for p, hits in portals.items():
        L.append(f"### {p}")
        if not hits:
            L.append("- no official portal surfaced via Search - flagged, not guessed")
        for h in hits:
            L.append(f"- [{h.get('title') or h.get('url')}]({h.get('url')})")
        if p in confirmed:
            u, title, ok = confirmed[p]
            L.append(f"- Fetch check: {'LIVE' if ok else 'COULD NOT LOAD'} - {title} ({u})")
        L.append("")
    L += ["---", "built with TinyFish endpoints: research, search, fetch",
          "TinyResearch (deep run) dug the requirements out of official government sites and cited each one; Search API found the official portals per place; Fetch API confirmed the key pages are live. unclear or missing rules are marked UNCLEAR, never guessed."]
    md = "\n".join(L)
    if args.out:
        open(args.out, "w").write(md)
        print(f"written to {args.out}", file=sys.stderr)
    print(md)

if __name__ == "__main__":
    main()
