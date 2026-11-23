"""Slow-trend BTC bot for make.fun's "Race a BTC trading bot live for 24 hours".

Strategy (original design, built for a 24-hour race window with ~26 bps
round-trip costs):

- Trend signal: EMA(60) vs EMA(180) of the 1-minute closes. A wide spread
  filter means the bot only enters on a genuinely strong trend, so it
  trades a few times per day instead of chopping itself to death on
  1-minute noise.
- Patience decays: the entry spread threshold starts at 50 bps and
  relaxes to 30 bps after bar 720 and 10 bps after bar 1200, so the bot
  still takes a position on a quiet day instead of sitting out the race.
  Weaker (later) signals get half size and a tighter trailing stop.
- Exits: the spread falling below -50 bps, or a trailing stop off the
  highest close since entry (2% for full-size entries, 1% for half-size).
  After a stop-out the bot waits 30 bars before re-entering, so it does
  not buy straight back into the move that just stopped it out.
- Long only, at most one position, fully deterministic: every decision is
  a pure function of the bars seen and the account state. No clock, no
  randomness, no network, no files.

Protocol: agent-fun/bars-replay/v1 via the kit's Python shim (vendored
byte-for-byte under vendor/, as the rules allow).
"""

import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "vendor"))
import makefun_bars

# --- strategy parameters (fixed constants, no tuning at run time) ---
FAST_EMA = 60
SLOW_EMA = 180
MIN_BARS = 60            # bars of history before the first trade
EXIT_SPREAD_BPS = 50     # sell when fast EMA falls this far below slow EMA
STOP_COOLDOWN_BARS = 30  # no re-entry this long after a stop-out
MAX_SLIPPAGE_BPS = 100   # 1%: far above the ~9 bps of modelled cost
LAST_ENTRY_BAR = 1430    # never open a position on the final bars

# Entry ladder: (bars_seen < upper, spread threshold bps, size fraction,
# trailing stop pct). Early in the window only a strong trend qualifies
# and it gets full size; later, weaker trends qualify at half size.
ENTRY_LADDER = (
    (720, 50, 1.0, 2.0),
    (1200, 30, 0.5, 1.0),
    (1 << 30, 10, 0.5, 1.0),
)


class Bot:
    def __init__(self):
        self.symbol = None
        self.bars_seen = 0
        self.ema_fast = None
        self.ema_slow = None
        self.k_fast = 2.0 / (FAST_EMA + 1)
        self.k_slow = 2.0 / (SLOW_EMA + 1)
        self.pending_buy = False   # a buy was sent, fill not yet seen
        self.peak = 0.0            # highest close since entry
        self.trail_pct = 2.0       # trailing stop of the open position
        self.cool_until = -1       # bars_seen before which no re-entry

    def on_hello(self, state):
        self.symbol = state.hello["symbols"][0]["symbol"]

    def on_batch(self, state, batch):
        # A rejected buy means we are not entering after all.
        for fill in batch.get("fills", []):
            if fill.get("side") == "buy" and fill.get("status") == "rejected":
                self.pending_buy = False

        bar = state.latest.get(self.symbol)
        if bar is None:
            return []
        close = int(bar["c"]) / 10 ** state.symbols[self.symbol]["price_scale"]
        self.bars_seen += 1
        if self.ema_fast is None:
            self.ema_fast = close
            self.ema_slow = close
        else:
            self.ema_fast = close * self.k_fast + self.ema_fast * (1.0 - self.k_fast)
            self.ema_slow = close * self.k_slow + self.ema_slow * (1.0 - self.k_slow)

        if state.warming_up:
            return []

        holding = state.positions.get(self.symbol)
        have_position = holding is not None and holding.qty > 0
        if have_position:
            self.pending_buy = False
            self.peak = max(self.peak, close)

        if have_position or self.pending_buy:
            # Manage the open position: trend break or trailing stop.
            if not have_position:
                return []
            spread_bps = (self.ema_fast - self.ema_slow) / self.ema_slow * 10000.0
            stopped = close < self.peak * (1.0 - self.trail_pct / 100.0)
            if spread_bps < -EXIT_SPREAD_BPS or stopped:
                if stopped:
                    self.cool_until = self.bars_seen + STOP_COOLDOWN_BARS
                self.peak = 0.0
                return [{
                    "side": "sell",
                    "symbol": self.symbol,
                    "qty": holding.qty,
                    "max_slippage_bps": MAX_SLIPPAGE_BPS,
                }]
            return []

        # Flat: look for an entry.
        if self.bars_seen < MIN_BARS or self.bars_seen >= LAST_ENTRY_BAR:
            return []
        if self.bars_seen < self.cool_until:
            return []
        spread_bps = (self.ema_fast - self.ema_slow) / self.ema_slow * 10000.0
        for upper, threshold_bps, size_frac, trail_pct in ENTRY_LADDER:
            if self.bars_seen < upper:
                break
        if spread_bps <= threshold_bps:
            return []
        cash = state.cash
        room = state.weight_room(self.symbol)
        notional = int(min(cash, room) * size_frac)
        min_notional = int(state.hello["fees"]["min_notional_quote_units"])
        if notional < min_notional:
            return []
        self.pending_buy = True
        self.peak = close
        self.trail_pct = trail_pct
        return [{
            "side": "buy",
            "symbol": self.symbol,
            "notional_quote_units": notional,
            "max_slippage_bps": MAX_SLIPPAGE_BPS,
        }]


def main():
    bot = Bot()
    makefun_bars.run(bot.on_batch, on_hello=bot.on_hello)


if __name__ == "__main__":
    main()
