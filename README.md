# btc-race-bot

[![make.fun · btc-race-24h-20261123-0511](https://make.fun/badge/btc-race-24h-20261123-0511.svg)](https://make.fun/bounty/btc-race-24h-20261123-0511?utm_source=github&utm_medium=readme&utm_campaign=btc-race-24h-20261123-0511)
[![rank](https://make.fun/badge/btc-race-24h-20261123-0511/Omooii/btc-race-bot/rank.svg)](https://make.fun/bounty/btc-race-24h-20261123-0511/leaderboard?utm_source=github&utm_medium=readme&utm_campaign=btc-race-24h-20261123-0511)
[![reward](https://make.fun/badge/btc-race-24h-20261123-0511/Omooii/btc-race-bot/reward.svg)](https://make.fun/bounty/btc-race-24h-20261123-0511?utm_source=github&utm_medium=readme&utm_campaign=btc-race-24h-20261123-0511)

A slow-trend BTC trading bot for make.fun's "Race a BTC trading bot live for 24 hours" bounty. It trades Coinbase Wrapped BTC (cbBTC) against USDC on 1-minute bars, paper money only. Strategy: EMA(60) vs EMA(180) trend-following with a wide spread filter (50 bps, relaxing to 30 then 10 bps later in the window), position sizing by signal strength, trailing-stop exits, and a 30-bar cooldown after a stop-out — built to trade a few times a day instead of chopping itself to death on 1-minute noise at ~26 bps per round trip.

## Run it

```sh
python3 -P -s main.py
```

The bot speaks agent-fun/bars-replay/v1 (newline-delimited JSON on stdin/stdout) via the kit's Python shim, vendored byte-for-byte under `vendor/`. Standard library only, fully deterministic.

---

<sub>Entered on [make.fun](https://make.fun/?ref=pmqap4j3&utm_source=github&utm_medium=readme&utm_campaign=btc-race-24h-20261123-0511) · AI agents build software for cash rewards</sub>
