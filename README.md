# compliance map

Where should I set up? Give it one activity and at least three places. It pulls every licence, filing, cost and time to approval from official government sites and lines them up side by side, then recommends the easiest place to start and explains the trade-offs.

Built on three TinyFish endpoints:

1. **Research (TinyResearch deep run)** digs the requirements out of official government sources - every item cited with its official page URL and check date. Unclear or missing rules are marked UNCLEAR, never guessed.
2. **Search** finds the official government portals for each place.
3. **Fetch** confirms the key official pages are live.

## usage

```bash
export TINYFISH_API_KEY=...   # https://agent.tinyfish.ai/api-keys
python3 compliance_map.py "open a small cafe" "Bengaluru India" Singapore "Dubai UAE" --out report.md
```

options:
- `--research-run <id>` - poll an existing TinyResearch run instead of launching a new one
- `--research-md <file>` - attach a saved research memo (skips launch and poll)

## demos

- [open a small cafe: Bengaluru vs Singapore vs Dubai](demos/demo-cafe.md)
- [register a private limited company: India vs Estonia vs Delaware](demos/demo-company-registration.md)

Each demo links the official source for every requirement, flags places where no official portal surfaced, and ends with a recommendation plus trade-offs - the comparison a founder would use to decide where to start, then hand to a lawyer to confirm.

Built for the TinyBounties Compliance Map bounty by [@somdipto](https://github.com/somdipto).
