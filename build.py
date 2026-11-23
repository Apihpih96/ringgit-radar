"""Ringgit Radar - build script.

Pulls live market data from the CoinMarketCap Pro API, priced in Malaysian
Ringgit (MYR), adds plain-English notes for beginners, and writes
site/data.json for the static dashboard in site/index.html.

Usage:
    CMC_API_KEY=xxxx python build.py

Endpoints used (CMC Pro API):
    GET /v1/cryptocurrency/listings/latest   top coins, convert=MYR
    GET /v1/global-metrics/quotes/latest      total market cap / BTC dominance, convert=MYR
    GET /v3/fear-and-greed/latest             CMC Fear & Greed index
"""
from __future__ import annotations

import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path

import requests

BASE = "https://pro-api.coinmarketcap.com"
CURRENCY = "MYR"
TOP_N = int(os.environ.get("TOP_N", "25"))
ROOT = Path(__file__).parent
SITE = ROOT / "site"
EVIDENCE = ROOT / "evidence"


def cmc_get(path: str, params: dict | None = None) -> dict:
    key = os.environ.get("CMC_API_KEY")
    headers = {"Accept": "application/json"}
    if key:  # in CI the key comes from a GitHub secret; never commit it
        headers["X-CMC_PRO_API_KEY"] = key
    for attempt in range(3):
        r = requests.get(BASE + path, params=params or {}, headers=headers, timeout=30)
        if r.status_code == 429 and attempt < 2:
            time.sleep(2 ** attempt * 5)
            continue
        r.raise_for_status()
        body = r.json()
        status = body.get("status", {})
        if status.get("error_code") not in (0, "0", None):
            raise RuntimeError(f"CMC error on {path}: {status}")
        return body
    raise RuntimeError(f"CMC rate limit on {path}")


def save_evidence(name: str, path: str, params: dict, body: dict) -> None:
    """Keep a trimmed copy of a real response as proof of a live API call."""
    EVIDENCE.mkdir(exist_ok=True)
    trimmed = dict(body)
    if isinstance(trimmed.get("data"), list):
        trimmed["data"] = trimmed["data"][:2]
    (EVIDENCE / f"{name}.json").write_text(
        json.dumps({"request": {"endpoint": path, "params": params}, "response": trimmed}, indent=2)
    )


def tip_for_coin(c: dict) -> str:
    """One plain-English line a beginner can understand."""
    d1, d7 = c["change_24h"], c["change_7d"]
    sym = c["symbol"]
    if c.get("stable"):
        return f"{sym} is a stablecoin: it tries to stay at about US$1, so it barely moves."
    if d1 <= -10:
        return f"{sym} dropped hard today. Sharp falls happen often; don't panic-sell or buy just because it's 'cheap'."
    if d1 >= 10:
        return f"{sym} jumped today. Big pumps often cool off; chasing them is risky."
    if d7 <= -15:
        return f"{sym} has had a rough week, down {abs(d7):.0f}%."
    if d7 >= 15:
        return f"{sym} is up {d7:.0f}% this week. Strong run, but past moves don't promise future ones."
    if abs(d1) < 1.5:
        return f"{sym} is calm today, moving less than 1.5%."
    return f"{sym} is {'up' if d1 > 0 else 'down'} {abs(d1):.1f}% today, a normal day for crypto."


def tip_for_coin_ms(c: dict) -> str:
    """Bahasa Melayu version of tip_for_coin."""
    d1, d7 = c["change_24h"], c["change_7d"]
    sym = c["symbol"]
    if c.get("stable"):
        return f"{sym} ialah stablecoin: ia cuba kekal sekitar US$1, jadi hampir tidak bergerak."
    if d1 <= -10:
        return f"{sym} jatuh teruk hari ini. Kejatuhan mendadak selalu berlaku; jangan panik jual atau beli hanya kerana ia 'murah'."
    if d1 >= 10:
        return f"{sym} melonjak hari ini. Lonjakan besar selalunya reda; mengejarnya berisiko."
    if d7 <= -15:
        return f"{sym} mengalami minggu yang sukar, turun {abs(d7):.0f}%."
    if d7 >= 15:
        return f"{sym} naik {d7:.0f}% minggu ini. Prestasi kukuh, tetapi pergerakan lalu tidak menjanjikan masa depan."
    if abs(d1) < 1.5:
        return f"{sym} tenang hari ini, bergerak kurang daripada 1.5%."
    return f"{sym} {'naik' if d1 > 0 else 'turun'} {abs(d1):.1f}% hari ini, hari biasa untuk kripto."


MOOD_MS = [
    (24, "Ketakutan melampau", "Ketakutan melampau: ramai orang menjual kerana panik. Harga boleh berayun dengan liar."),
    (44, "Takut", "Takut: pasaran gelisah. Ambil masa dan elakkan keputusan tergesa-gesa."),
    (55, "Neutral", "Neutral: tiada mood yang kuat buat masa ini."),
    (75, "Tamak", "Tamak: orang teruja dan membeli. Berhati-hati dengan gembar-gembur."),
    (100, "Tamak melampau", "Tamak melampau: banyak gembar-gembur. Inilah masa pemula selalu membeli di puncak."),
]


def mood_ms(value: int) -> tuple[str, str]:
    for top, label, text in MOOD_MS:
        if value <= top:
            return label, text
    return MOOD_MS[-1][1], MOOD_MS[-1][2]


def mood_text(value: int) -> str:
    if value <= 24:
        return "Extreme fear: many people are selling in panic. Prices can swing wildly."
    if value <= 44:
        return "Fear: the market is nervous. Take your time and avoid rushed decisions."
    if value <= 55:
        return "Neutral: no strong mood either way right now."
    if value <= 75:
        return "Greed: people are excited and buying. Be careful of hype."
    return "Extreme greed: lots of hype. This is often when beginners buy at the top."


STABLE_TAGS = {"stablecoin"}


def build() -> dict:
    # 1. Top coins priced in MYR
    p1 = {"start": 1, "limit": TOP_N, "convert": CURRENCY, "sort": "market_cap"}
    listings = cmc_get("/v1/cryptocurrency/listings/latest", p1)
    save_evidence("listings_latest", "/v1/cryptocurrency/listings/latest", p1, listings)

    coins = []
    for item in listings["data"]:
        q = item["quote"][CURRENCY]
        c = {
            "id": item["id"],
            "rank": item["cmc_rank"],
            "name": item["name"],
            "symbol": item["symbol"],
            "slug": item["slug"],
            "price": q["price"],
            "change_1h": q.get("percent_change_1h") or 0.0,
            "change_24h": q.get("percent_change_24h") or 0.0,
            "change_7d": q.get("percent_change_7d") or 0.0,
            "market_cap": q.get("market_cap") or 0.0,
            "volume_24h": q.get("volume_24h") or 0.0,
            "stable": bool(STABLE_TAGS & set(item.get("tags") or [])),
            "logo": f"https://s2.coinmarketcap.com/static/img/coins/64x64/{item['id']}.png",
        }
        c["tip"] = tip_for_coin(c)
        c["tip_ms"] = tip_for_coin_ms(c)
        coins.append(c)

    # 2. Global market in MYR
    p2 = {"convert": CURRENCY}
    glob = cmc_get("/v1/global-metrics/quotes/latest", p2)
    save_evidence("global_metrics", "/v1/global-metrics/quotes/latest", p2, glob)
    g = glob["data"]
    gq = g["quote"][CURRENCY]

    # 3. Fear & Greed (optional: keep building if the plan lacks it)
    fg = None
    try:
        fgb = cmc_get("/v3/fear-and-greed/latest")
        save_evidence("fear_and_greed", "/v3/fear-and-greed/latest", {}, fgb)
        d = fgb["data"]
        v = int(d["value"])
        lab_ms, txt_ms = mood_ms(v)
        fg = {"value": v, "label": d["value_classification"], "text": mood_text(v), "label_ms": lab_ms, "text_ms": txt_ms}
    except Exception as e:  # noqa: BLE001
        print(f"fear & greed unavailable: {e}", file=sys.stderr)

    movers = [c for c in coins if not c["stable"]]
    gainers = sorted((c for c in movers if c["change_24h"] > 0), key=lambda c: c["change_24h"], reverse=True)[:3]
    losers = sorted((c for c in movers if c["change_24h"] < 0), key=lambda c: c["change_24h"])[:3]

    btc = next((c for c in coins if c["symbol"] == "BTC"), None)
    headline = headline_ms = None
    if btc:
        arah = "naik" if btc["change_24h"] >= 0 else "turun"
        headline_ms = (
            f"1 Bitcoin kini bernilai kira-kira RM{btc['price']:,.0f}, {arah} "
            f"{abs(btc['change_24h']):.1f}% dalam 24 jam lepas."
        )
        direction = "up" if btc["change_24h"] >= 0 else "down"
        headline = (
            f"1 Bitcoin is about RM{btc['price']:,.0f} right now, {direction} "
            f"{abs(btc['change_24h']):.1f}% in the last 24 hours."
        )

    data = {
        "updated_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "currency": CURRENCY,
        "headline": headline,
        "headline_ms": headline_ms,
        "global": {
            "market_cap": gq.get("total_market_cap"),
            "volume_24h": gq.get("total_volume_24h"),
            "market_cap_change_24h": gq.get("total_market_cap_yesterday_percentage_change"),
            "btc_dominance": g.get("btc_dominance"),
            "eth_dominance": g.get("eth_dominance"),
            "active_coins": g.get("active_cryptocurrencies"),
        },
        "fear_greed": fg,
        "gainers": [c["id"] for c in gainers],
        "losers": [c["id"] for c in losers],
        "coins": coins,
    }
    SITE.mkdir(exist_ok=True)
    (SITE / "data.json").write_text(json.dumps(data, indent=1))
    return data


if __name__ == "__main__":
    d = build()
    print(f"Built {len(d['coins'])} coins at {d['updated_utc']}")
    print(d["headline"])
