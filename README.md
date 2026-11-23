# Ringgit Radar

**Crypto in Ringgit, explained simply.** A free, mobile-first dashboard that shows live crypto prices in Malaysian Ringgit (RM) with plain-English and Bahasa Melayu notes for first-time buyers.

Track: **Data and Visualisation** · Built for the #BuildwithCMC API Hackathon (Round 2)

## Why

Most crypto sites show prices in US dollars and assume you already know what "BTC dominance" or "Fear & Greed" means. New Malaysian buyers think in RM, and many get pulled into scams on Telegram and WhatsApp. Ringgit Radar answers three beginner questions at a glance:

1. **How much is it in RM right now?** Every price, the total market and the calculator are in Ringgit.
2. **Is today a normal day or a crazy one?** Market mood gauge, biggest movers, and a one-line explanation for every coin.
3. **How do I stay safe?** A short guide on legality in Malaysia, how much to put in, stablecoins and scam red flags.

## Features

- Headline sentence: "1 Bitcoin is about RM… right now, up/down …% in 24 hours"
- Market mood gauge (CMC Fear & Greed) with a plain-language meaning
- Whole-market cap in RM and Bitcoin's share
- Today's 3 biggest gainers and 3 biggest losers (stablecoins excluded)
- "What does my RM buy?" calculator
- Top 25 coins in RM with 24h and 7d change; tap any coin for a simple explanation
- Watchlist saved on your device (no account, no tracking)
- English / Bahasa Melayu toggle
- Refreshes every hour automatically

## How it works

```
GitHub Actions (hourly) ──► build.py ──► CMC Pro API (convert=MYR)
                                  │
                                  └─► site/data.json ──► GitHub Pages (static site)
```

The API key lives only in a GitHub Actions secret (`CMC_API_KEY`). The browser never sees it, so there is no server to run and nothing to leak.

## CMC API endpoints used

| Endpoint | What it powers |
| --- | --- |
| `GET /v1/cryptocurrency/listings/latest` (`convert=MYR`, `limit=25`, `sort=market_cap`) | Coin table, movers, calculator, headline, per-coin tips |
| `GET /v1/global-metrics/quotes/latest` (`convert=MYR`) | Whole-market cap in RM, 24h change, BTC dominance |
| `GET /v3/fear-and-greed/latest` | Market mood gauge |

3 calls per refresh, 24 refreshes a day: about 72 calls a day, well inside the free Basic plan, so the site can keep running after the hackathon.

## Evidence of real API calls

Every build saves a trimmed copy of each live response in [`evidence/`](evidence/):
`listings_latest.json`, `global_metrics.json`, `fear_and_greed.json`. Each file contains the request (endpoint and params) and the response, including CMC's `status.timestamp` and `credit_count`.

## Run it yourself

```bash
pip install -r requirements.txt
export CMC_API_KEY=your_key_here   # never commit this
python build.py
cd site && python -m http.server 8000
# open http://localhost:8000
```

Deploy: fork, add `CMC_API_KEY` under *Settings → Secrets and variables → Actions*, enable *Settings → Pages → Source: GitHub Actions*, then run the workflow.

## What the API made possible, and where it got in the way

**Made possible:** `convert=MYR` on listings and global metrics meant every number could be shown natively in Ringgit without a separate FX API. The Fear & Greed endpoint turned a vague idea ("is the market scared?") into one number a beginner can read. Including `tags` in listings let me detect stablecoins and keep them out of the movers list.

**Got in the way:**
- The `tags` list is long and not standardised for beginners. A simple `is_stablecoin` flag would remove guesswork.
- `status.error_code` comes back as a string (`"1022"`) from some endpoints and an integer (`1022`) from others, so success checks need to handle both.
- The keyless public API hits its anonymous limit quickly from shared cloud IPs, so prototyping without a key was not reliable.

## Not financial advice

Ringgit Radar is an educational tool. Prices come from CoinMarketCap and can be delayed by up to an hour.

## License

MIT
