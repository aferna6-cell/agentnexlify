# Deep Dive: What Profitable Polymarket Bots Do That Ours Doesn't

## The Core Question

What makes money in prediction markets?

| Strategy | Profitable? | Why |
|----------|-------------|-----|
| **Copy Trading** | ✅ Yes | Proven edge (someone else's skill) |
| **Market Making** | ✅ Yes | Capture spread mechanically |
| **Bracket Arbitrage** | ✅ Yes | Mathematical guarantee |
| **LLM Predictions** | ❌ No | No edge vs efficient markets |
| **Contrarian Betting** | ❌ No | Crowds are usually right |

---

## Detailed Analysis: What They Do vs What We Do

### 1. SPEED

| Bot | Polling Interval | Quote Refresh | Cancel/Replace |
|-----|-----------------|---------------|----------------|
| **Polymarket MM (lorine93s)** | WebSocket (real-time) | 1,000ms | 500ms |
| **Polymarket Copy (RandyTas)** | 1,000ms (1 sec) | Instant on detection | N/A |
| **Our Bot** | 600,000ms (10 min) | 60,000ms (1 min) | Never |

**Why This Matters:**

In prediction markets, opportunities disappear in seconds:
- Arbitrage: Someone else takes it
- Copy trading: Miss the entry price
- MM: Spread captured by faster bots

**Gap: We are 600x slower than competitive bots.**

---

### 2. MARKET MAKING LOGIC

#### Polymarket MM Bot (lorine93s) — CORRECT

```python
def calculate_bid_price(self, mid_price: float, spread_bps: int) -> float:
    return mid_price * (1 - spread_bps / 10000)  # BELOW mid

def calculate_ask_price(self, mid_price: float, spread_bps: int) -> float:
    return mid_price * (1 + spread_bps / 10000)  # ABOVE mid

# Example: mid = 50¢, spread = 100 bps (1%)
# bid = 49.5¢ (we BUY here)
# ask = 50.5¢ (we SELL here)
# When both fill: capture 1¢ profit
```

#### Our MM Bot — THE BUG

Looking at trade history:
```
order_placed KXNYCMAYORDEBATEMENTION YES 2 @ 42¢
order_placed KXNYCMAYORDEBATEMENTION NO 2 @ 42¢
```

Both sides at 42¢! The A-S math produces bid ≈ ask when market spread = 0.

**Root Cause:** We check spread at SCAN time (every 5 min), but quote at different time. By quote time, spread has collapsed.

**Fix Required:**
```python
async def _generate_quotes(self, state: MMMarketState) -> None:
    # Get fresh orderbook
    ob = await self.kalshi_client.get_orderbook(state.ticker)
    
    # RECALCULATE spread from fresh data
    spread_cents = best_yes_ask - best_yes_bid
    
    # SKIP if spread too tight (no room to capture)
    if spread_cents < self._min_spread_cents:
        self.logger.debug("mm_skip_tight_spread", ticker=state.ticker, spread=spread_cents)
        return  # Don't quote, wait for spread to widen
```

---

### 3. INVENTORY MANAGEMENT

#### Polymarket MM Bot — SOPHISTICATED

```python
@dataclass
class Inventory:
    yes_position: float = 0.0
    no_position: float = 0.0
    net_exposure_usd: float = 0.0
    
    def get_skew(self) -> float:
        total = abs(self.yes_position) + abs(self.no_position)
        return abs(self.net_exposure_usd) / self.total_value_usd
    
    def is_balanced(self, max_skew: float = 0.3) -> bool:
        return self.get_skew() <= max_skew

class InventoryManager:
    def can_quote_yes(self, size_usd: float) -> bool:
        # Don't add to YES if already max exposed
        potential_exposure = self.inventory.net_exposure_usd + size_usd
        return potential_exposure <= self.max_exposure_usd
    
    def get_quote_size_yes(self, base_size: float, price: float) -> float:
        # Reduce size when skewed toward YES
        if self.inventory.net_exposure_usd > self.target_balance:
            return base_size * 0.5  # Quote smaller on heavy side
        return base_size
```

#### Our Bot — BASIC

We have `state.inventory` but:
- No per-market USD exposure tracking
- No skew-based size adjustment
- No cross-market total exposure limit
- Inventory only updates on fills, not from position API

**Gap: We don't actively manage inventory to stay balanced.**

---

### 4. COPY TRADING (THE BIG ONE)

#### Why Copy Trading Works

1. **Edge Source:** The trader you copy has real skill/information
2. **Zero LLM Cost:** No API calls, just monitor positions
3. **Proven Results:** Can verify trader's historical P&L before copying
4. **Speed:** 1-second detection means you get similar entry price

#### Polymarket Copy Trading Flow

```
┌─────────────────┐       ┌─────────────────┐       ┌─────────────────┐
│  Top Trader     │       │   Your Bot      │       │   Your Wallet   │
│  Opens Position │──1s──>│  Detects Trade  │──1s──>│  Mirrors Trade  │
│  $1000 @ 45¢    │       │  Scales to $100 │       │  $100 @ 45.5¢   │
└─────────────────┘       └─────────────────┘       └─────────────────┘
```

Key features:
- **Proportional sizing:** `my_size = trader_size * (my_balance / trader_balance) * multiplier`
- **Trade aggregation:** Combine multiple small trades into one (saves gas)
- **Multi-trader:** Copy 3-5 traders with independent strategies
- **Exit mirroring:** When trader exits, you exit

#### Kalshi Limitation

**Problem:** Kalshi API doesn't expose individual user trades publicly.

**What Kalshi Provides:**
- `/markets/{ticker}/trades` — Public trade feed (no user IDs)
- `/portfolio/positions` — Only YOUR positions

**What Kalshi Doesn't Provide:**
- Other users' positions
- Other users' trade history
- Leaderboard API

**Workaround Options:**
1. **Whale Watching:** Monitor public trade feed for large orders (>$500), follow momentum
2. **Scrape Leaderboard:** Browser automation to get top usernames, but can't map to trade activity
3. **Manual Networks:** Find profitable traders through community, get their trades manually

---

### 5. BRACKET ARBITRAGE

#### The Math

For a bracket event (e.g., NYC high temp):
- `< 45°F` = YES @ 5¢
- `45-50°F` = YES @ 15¢  
- `50-55°F` = YES @ 40¢
- `> 55°F` = YES @ 35¢

Sum = 95¢. Exactly ONE will settle to $1.

**Arb:** Buy all 4 for 95¢ → Guaranteed $1 back → 5.3% profit

#### Why Markets Misprice

1. **Low-volume brackets:** Illiquid brackets stay stale
2. **Recency bias:** Last bracket traded at old price
3. **Complexity:** Traders don't check sum across all brackets
4. **Time decay:** As close time approaches, mispricing increases

#### Implementation

```python
async def find_bracket_arbs(self):
    # 1. Get all weather/GDP/jobs events
    events = await self.kalshi_client.get_events()
    
    for event in events:
        # 2. Get all brackets (markets with same event_ticker)
        markets = await self.get_markets_by_event(event.ticker)
        
        if len(markets) < 2:
            continue  # Not a bracket event
        
        # 3. Sum YES ask prices
        total_cost = sum(m.yes_ask for m in markets)
        
        # 4. Check for arb
        if total_cost < 0.97:  # 3% margin for fees/slippage
            yield ArbOpportunity(
                event=event.ticker,
                markets=markets,
                cost=total_cost,
                profit_pct=(1.0 - total_cost) / total_cost,
            )
```

**Why We're Not Finding Arbs:**

Current `bracket_arb_engine.py` scans but finds nothing. Likely issues:
1. **Wrong event grouping:** Using `series_ticker` but markets use different field
2. **Stale prices:** REST polling misses opportunities
3. **Too strict filters:** Requiring volume/spread that eliminates candidates

---

## The Honest Comparison

| Feature | Polymarket Bots | Our Bot |
|---------|-----------------|---------|
| **Primary Strategy** | Copy Trading | LLM Predictions |
| **Has Edge?** | ✅ Yes (others' skill) | ❌ No (LLMs don't beat markets) |
| **Polling Speed** | 1 second | 600 seconds |
| **Real-time Data** | WebSocket | REST polling |
| **MM Spread Logic** | Correct (bid < mid < ask) | Buggy (same price) |
| **Inventory Tracking** | Per-market USD, skew adjustment | Basic count only |
| **Position Sizing** | Proportional, tiered | Kelly (but based on fake edge) |
| **API Cost** | Zero (no LLM) | $3+/month |
| **Win Rate** | 55%+ (following winners) | 35% (guessing) |

---

## Implementation Plan for Claude Code

### Priority 1: Fix MM Spread Bug (Day 1)

**File:** `src/engines/kalshi_mm_engine.py`

**Change:** In `_generate_quotes()`, add spread check BEFORE generating quotes:

```python
async def _generate_quotes(self, state: MMMarketState) -> None:
    # Get fresh orderbook
    ob = await self.kalshi_client.get_orderbook(state.ticker)
    
    # Calculate CURRENT spread (not from scan time)
    best_yes_bid = yes_bids[0][0] if yes_bids else 0
    best_yes_ask = 100 - (no_bids[0][0] if no_bids else 100)
    current_spread = best_yes_ask - best_yes_bid
    
    # CRITICAL: Skip if spread too tight to capture
    if current_spread < self._min_spread_cents:
        self.logger.debug(
            "mm_skip_tight_spread",
            ticker=state.ticker,
            spread=current_spread,
            min_required=self._min_spread_cents,
        )
        return  # No signal, wait for spread to widen
    
    # Also ensure our quotes maintain minimum spread
    if our_yes_ask - our_yes_bid < self._min_spread_cents:
        # Widen our quotes instead of collapsing
        our_yes_bid = int(mid_cents) - self._min_spread_cents // 2
        our_yes_ask = int(mid_cents) + self._min_spread_cents // 2
```

### Priority 2: Implement Bracket Arbitrage (Days 2-3)

**File:** `src/engines/kalshi_bracket_arb_engine.py` (rewrite)

```python
class KalshiBracketArbEngine(BaseEngine):
    name = "kalshi_bracket_arb"
    
    async def _find_bracket_events(self) -> Dict[str, List[KalshiMarket]]:
        """Group markets by event (same resolution criteria)."""
        all_markets = await self.kalshi_client.fetch_markets_by_close_date(max_days=3)
        
        events: Dict[str, List[KalshiMarket]] = {}
        
        for m in all_markets:
            # Weather brackets: KXHIGH-NYC-26FEB20-T45, KXHIGH-NYC-26FEB20-B45-T50, etc.
            # Extract event key: "KXHIGH-NYC-26FEB20"
            parts = m.ticker.rsplit("-", 1)  # Split on last dash
            if len(parts) == 2:
                event_key = parts[0]
                if event_key not in events:
                    events[event_key] = []
                events[event_key].append(m)
        
        # Filter to events with 3+ brackets (true bracket events)
        return {k: v for k, v in events.items() if len(v) >= 3}
    
    async def _scan_for_arb(self):
        events = await self._find_bracket_events()
        
        for event_key, markets in events.items():
            # Sum all YES ask prices
            total_cost = sum(m.yes_ask for m in markets)
            
            if total_cost < 0.97:  # 3% arb margin
                # BUY ALL BRACKETS
                for market in markets:
                    yield TradeSignal(
                        engine=self.name,
                        market_id=market.ticker,
                        side="buy_yes",
                        confidence=0.99,
                        edge=(1.0 - total_cost),
                        metadata={
                            "strategy": "bracket_arb",
                            "event": event_key,
                            "total_cost": total_cost,
                            "profit_pct": (1.0 - total_cost) / total_cost,
                            "_force_size_usd": 5.0,  # $5 per bracket
                        }
                    )
```

### Priority 3: Speed Up Polling (Day 4)

**File:** `config.yaml`

```yaml
kalshi:
  scan_interval_seconds: 60      # Was 600 (10x faster)

market_making:
  quote_refresh_seconds: 5       # Was 60 (12x faster)
  scan_interval_seconds: 60      # Was 300 (5x faster)

bracket_arb:
  scan_interval_seconds: 30      # Fast arb detection
```

### Priority 4: Whale Watching (Days 5-7)

Since Kalshi doesn't expose user trades, implement momentum detection:

**File:** `src/engines/kalshi_whale_engine.py` (new)

```python
class KalshiWhaleEngine(BaseEngine):
    """Detect and follow large trades on Kalshi."""
    
    async def _scan_for_whales(self):
        for ticker in self._watched_markets:
            trades = await self.kalshi_client.get_recent_trades(ticker, limit=50)
            
            for trade in trades:
                # Large trade detection
                if trade.size_usd >= 500:  # $500+ = whale
                    # Follow the momentum
                    yield TradeSignal(
                        engine=self.name,
                        market_id=ticker,
                        side=trade.side,
                        confidence=0.65,
                        edge=0.05,  # Assume 5% edge from whale info
                        metadata={
                            "strategy": "whale_following",
                            "whale_size": trade.size_usd,
                            "_force_size_usd": min(50, trade.size_usd * 0.1),
                        }
                    )
```

### Priority 5: Kill What Doesn't Work (Day 1, immediate)

**File:** `config.yaml`

```yaml
strategy:
  enabled_strategies: []  # Disable ALL strategy-based signals

llm:
  ensemble_mode: "none"   # No LLM calls

contrarian:
  enabled: false          # Crowds are usually right

# Keep ONLY:
# - NOAA/FRED fast-paths (data edge)
# - Fixed MM engine (after bug fix)
# - Bracket arb (once implemented)
```

---

## Success Metrics

### Before Going Live

| Strategy | Backtest Requirement | Paper Trade Requirement |
|----------|---------------------|------------------------|
| MM (fixed) | Positive spread capture in 100 quotes | 48h paper trade |
| Bracket Arb | Find 10+ arb opportunities in history | 24h paper trade |
| Whale Following | Positive CLV on detected whales | 7d paper trade |
| NOAA/FRED | Brier < 0.20 | Already running |

### Live Metrics to Track

1. **Fill Rate:** % of quotes that fill (target: >30%)
2. **Spread Captured:** Actual spread vs quoted spread
3. **Inventory Skew:** Max skew reached (target: <0.4)
4. **Arb Opportunities:** Found vs executed
5. **Win Rate by Strategy:** Track each strategy separately

---

## Bottom Line

**The profitable bots make money by:**
1. Following people who have edge (copy trading)
2. Capturing mechanical spread (market making)
3. Exploiting mathematical mispricing (arbitrage)

**We've been:**
1. Guessing with LLMs (no edge)
2. Placing broken MM quotes (same price both sides)
3. Not finding arbs (wrong grouping logic)

**The fix is:**
1. Kill LLM predictions
2. Fix MM spread logic
3. Implement proper bracket arb
4. Speed up 10-100x
5. Add whale detection as alternative to copy trading
