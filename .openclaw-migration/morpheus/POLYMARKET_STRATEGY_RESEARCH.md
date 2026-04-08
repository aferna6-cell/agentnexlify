# Polymarket Bot Strategy Research — Converting to Kalshi

## Executive Summary

Analyzed the top GitHub repos for Polymarket trading bots. The most successful strategies are:

1. **Copy Trading** (825+ stars) — Mirror proven profitable wallets
2. **Market Making** (247 stars) — Proper spread capture with inventory management
3. **Arbitrage** — Cross-platform or intra-bracket

Our current approach (LLM predictions) is NOT used by any successful public bot.

---

## Strategy #1: Copy Trading (HIGHEST ROI)

### How It Works

1. Identify top traders from leaderboard (Polymarket or Kalshi)
2. Monitor their positions via API (1-second polling)
3. Mirror trades with proportional sizing
4. Exit when they exit

### Key Implementation Details

From `RandyTas/polymarket-copytrading-bot` (825 stars):

```javascript
// 1-second polling interval
const FETCH_INTERVAL = 1;

// Proportional sizing
const tradeSize = (myBalance / traderBalance) * traderTradeSize * TRADE_MULTIPLIER;

// Trade aggregation (combine small trades)
TRADE_AGGREGATION_WINDOW_SECONDS = 30
```

### Converting to Kalshi

**Challenge:** Kalshi doesn't have a public leaderboard API like Polymarket.

**Solutions:**
1. **Manual wallet identification** — Find profitable accounts via:
   - Kalshi leaderboard (web scrape)
   - Track accounts with consistent wins
   - Monitor high-volume accounts
   
2. **Activity monitoring** — Kalshi REST API provides:
   - `/portfolio/positions` — but only YOUR positions
   - `/markets/{ticker}/trades` — public trade feed (no user IDs)
   
**Reality Check:** Kalshi doesn't expose individual user trades publicly. Copy trading on Kalshi requires either:
- Insider knowledge of profitable accounts
- Building relationships with good traders
- Using the public trade feed for "whale watching" (large orders)

### Verdict: LIMITED on Kalshi (need alternative approach)

---

## Strategy #2: Market Making (PROVEN PROFITABLE)

### How It Works (Proper MM)

From `lorine93s/polymarket-market-maker-bot`:

```python
def calculate_bid_price(self, mid_price: float, spread_bps: int) -> float:
    return mid_price * (1 - spread_bps / 10000)

def calculate_ask_price(self, mid_price: float, spread_bps: int) -> float:
    return mid_price * (1 + spread_bps / 10000)

# Example: mid = 50¢, spread = 100 bps (1%)
# bid = 49.5¢, ask = 50.5¢
# Capture 1¢ when both sides fill
```

### Key Features

| Feature | What It Does | Our Bot Has It? |
|---------|--------------|-----------------|
| **Inventory Management** | Track YES/NO exposure separately | ❌ No |
| **Inventory Skew** | Reduce quotes when one-sided | ❌ No |
| **Cancel/Replace** | 500ms refresh cycles | ❌ We do 60s |
| **WebSocket Orderbook** | Real-time price updates | ❌ We poll REST |
| **Spread Capture** | bid < mid < ask | ❌ BROKEN (same price) |

### Converting to Kalshi

Kalshi supports market making with **zero maker fees**. This is our biggest opportunity.

**Required Changes:**

1. **Fix spread logic:**
```python
# Current (BROKEN):
yes_bid = mid
yes_ask = mid  # Same price!

# Correct:
half_spread = 2  # cents
yes_bid = mid - half_spread  # BUY YES at 48¢
no_bid = 100 - mid - half_spread  # BUY NO at 48¢ (= SELL YES at 52¢)
```

2. **Add inventory tracking:**
```python
class InventoryManager:
    yes_contracts: int = 0
    no_contracts: int = 0
    max_exposure: float = 50.0  # $50 max one-sided
    
    def get_skew(self) -> float:
        total = self.yes_contracts + self.no_contracts
        return abs(self.yes_contracts - self.no_contracts) / total if total > 0 else 0
    
    def should_reduce_quotes(self, side: str) -> bool:
        # Don't add to already-heavy side
        if self.get_skew() > 0.3:
            return True
        return False
```

3. **Add WebSocket for real-time orderbook:**
```python
# Kalshi WebSocket endpoint
wss://api.elections.kalshi.com/trade-api/ws/v2

# Subscribe to orderbook
{"type": "subscribe", "channels": [{"name": "orderbook", "markets": ["KXHIGHNYC-26FEB20-T45"]}]}
```

4. **Faster refresh cycle:**
```python
QUOTE_REFRESH_MS = 1000  # 1 second, not 60 seconds
CANCEL_REPLACE_INTERVAL_MS = 500  # Half second
```

### Verdict: HIGH POTENTIAL on Kalshi (zero fees = pure profit)

---

## Strategy #3: Bracket Arbitrage

### How It Works

Weather markets on Kalshi have bracket structures:
- KXHIGHNYC-26FEB20-T45 (High < 45°F) = YES at 5¢
- KXHIGHNYC-26FEB20-B45-T50 (45-50°F) = YES at 15¢
- KXHIGHNYC-26FEB20-B50-T55 (50-55°F) = YES at 40¢
- KXHIGHNYC-26FEB20-B55 (High > 55°F) = YES at 35¢

Sum: 5 + 15 + 40 + 35 = 95¢

**If sum < 100¢, buy all brackets → guaranteed $1 payout.**

Profit = $1 - cost = $1 - $0.95 = $0.05 (5.3% risk-free)

### Why This Works

Markets aren't perfectly efficient. Especially for:
- Low-volume brackets
- Complex multi-outcome events
- Markets near close time

### Converting to Kalshi

Kalshi has MANY bracket markets:
- Weather highs/lows (KXHIGH*, KXLOW*)
- GDP ranges (KXGDP-*)
- Jobs numbers (KXJOBLESS-*)
- Price targets (KXTRUTHSOCIAL-*)

**Implementation:**

```python
async def find_bracket_arbs():
    # 1. Find all bracket events (same date, same metric)
    events = await kalshi.get_events()
    
    for event in events:
        markets = await kalshi.get_markets_by_event(event.ticker)
        
        # 2. Sum all YES ask prices
        total_cost = sum(m.yes_ask for m in markets)
        
        # 3. Check for arb (need 3%+ margin for fees/slippage)
        if total_cost < 0.97:
            profit_pct = (1.0 - total_cost) / total_cost
            
            # 4. Size based on min liquidity across brackets
            min_liquidity = min(m.yes_ask_size for m in markets)
            
            # 5. Execute all legs simultaneously
            for market in markets:
                await kalshi.place_order(
                    ticker=market.ticker,
                    side="yes",
                    count=min_liquidity,
                    price_cents=int(market.yes_ask * 100),
                )
```

### Verdict: BEST OPPORTUNITY (risk-free when executed properly)

---

## What's Wrong With Our Current Approach

### LLM Predictions

| Problem | Evidence |
|---------|----------|
| No edge | 45% win rate on resolved markets |
| Calibration doesn't help | Negative CLV despite Platt scaling |
| High cost | $3.11 LLM spend, negative returns |
| Slow | 10-minute scans miss opportunities |

### Comparison to Successful Bots

| Aspect | Successful Bots | Our Bot |
|--------|-----------------|---------|
| **Strategy** | Copy/MM/Arb (proven edge) | LLM predictions (no edge) |
| **Speed** | 1-second polling, WebSocket | 10-minute polling |
| **MM Logic** | Proper spread capture | Broken (same price both sides) |
| **Inventory** | Balanced YES/NO | No tracking |
| **Data Source** | Price action, orderbook | LLM guessing |

---

## Recommended Priority

### Phase 1: Bracket Arbitrage (Week 1)

1. Build event grouping logic
2. Sum bracket prices
3. Execute when sum < 97¢
4. Log and track arb opportunities

**Why first:** Risk-free profit, works with current REST API, no ML required.

### Phase 2: Fix Market Making (Week 2)

1. Implement proper spread logic (bid < mid < ask)
2. Add inventory tracking per market
3. Add WebSocket orderbook feed
4. Reduce quote refresh to 1 second

**Why second:** Zero maker fees on Kalshi = pure profit if done right.

### Phase 3: Whale Watching (Week 3)

Since Kalshi doesn't expose user trades, build "whale detection":

1. Monitor `/markets/{ticker}/trades` for large orders
2. Detect unusual volume spikes
3. Follow the momentum

### Phase 4: Keep NOAA/FRED Fast-Paths

Our one actual edge:
- NOAA weather data has 12-24 hour lead on market pricing
- FRED economic data gives hard numbers before markets adjust

Keep these, kill everything else.

---

## Code Changes Required

### 1. New: `src/engines/kalshi_bracket_arb_engine.py`

```python
"""Bracket arbitrage scanner — risk-free profit from mispriced bracket sets."""

class KalshiBracketArbEngine(BaseEngine):
    name = "kalshi_bracket_arb"
    
    async def _scan_for_arb(self):
        # Group markets by event (same date, same metric)
        events = await self._group_by_event()
        
        for event_ticker, markets in events.items():
            # Sum YES ask prices
            total_cost = sum(m.yes_ask for m in markets)
            
            if total_cost < 0.97:  # 3% margin
                # Signal: buy all brackets
                for market in markets:
                    yield TradeSignal(
                        engine=self.name,
                        market_id=market.ticker,
                        side="buy_yes",
                        confidence=0.99,  # Near-certain
                        edge=(1.0 - total_cost),
                        metadata={
                            "strategy": "bracket_arb",
                            "event": event_ticker,
                            "total_cost": total_cost,
                            "profit_pct": (1.0 - total_cost) / total_cost,
                        }
                    )
```

### 2. Fix: `src/engines/kalshi_mm_engine.py`

```python
# Replace quote generation with proper spread logic:
def generate_quotes(self, market: KalshiMarket) -> tuple[Quote, Quote]:
    mid = (market.yes_bid + market.yes_ask) / 2
    
    spread_cents = max(self._min_spread_cents, 2)
    
    # BID: below mid (we BUY)
    bid_price = int(mid * 100) - spread_cents
    
    # ASK: above mid (we SELL)  
    ask_price = int(mid * 100) + spread_cents
    
    return (
        Quote(side="buy_yes", price=bid_price, size=self._quote_size),
        Quote(side="buy_no", price=100 - ask_price, size=self._quote_size),
    )
```

### 3. New: `src/feeds/kalshi_ws.py`

```python
"""WebSocket feed for real-time Kalshi orderbook updates."""

import websockets

async def subscribe_orderbook(ticker: str):
    uri = "wss://api.elections.kalshi.com/trade-api/ws/v2"
    
    async with websockets.connect(uri) as ws:
        await ws.send(json.dumps({
            "type": "subscribe",
            "channels": [{"name": "orderbook", "markets": [ticker]}]
        }))
        
        async for message in ws:
            data = json.loads(message)
            yield data  # Real-time orderbook updates
```

### 4. Config Changes

```yaml
# Disable LLM predictions (no edge)
llm:
  ensemble_mode: "none"
  
# Enable bracket arb
bracket_arb:
  enabled: true
  min_margin_pct: 3.0
  scan_interval_seconds: 60  # Every minute
  
# Fix MM
market_making:
  enabled: true
  min_spread_cents: 2
  max_spread_cents: 10
  quote_refresh_ms: 1000  # 1 second
  inventory_skew_limit: 0.3
```

---

## Success Metrics

Before going live with new strategies:

| Strategy | Backtest Requirement | Paper Trade Requirement |
|----------|---------------------|------------------------|
| Bracket Arb | Find 10+ arb opportunities in historical data | 48h paper trade |
| MM | Positive spread capture in simulation | 7 days paper trade |
| NOAA/FRED | Brier < 0.20, positive CLV | Keep current |

---

## Bottom Line

**Stop predicting. Start arbitraging.**

1. **Bracket Arb** = Free money (risk-free)
2. **MM** = Free money (zero fees)
3. **NOAA/FRED** = Actual data edge

Kill LLM ensemble. Kill contrarian. Kill everything without proven edge.
