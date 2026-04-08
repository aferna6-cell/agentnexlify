# Morpheus Fix Plan — Step by Step

## Phase 0: Stop the Bleeding (Do First)

```bash
# SSH into droplet
ssh root@45.55.85.173

# Stop both bots immediately
systemctl stop morpheus.service morpheus2.service

# Verify they're stopped
systemctl status morpheus.service morpheus2.service
```

---

## Phase 1: Fix Position Monitor Death Loop

**File:** `src/position_monitor.py`

### The Bug

When `_exit_position()` places a limit order, it treats the order_id response as "position closed." But limit orders can sit unfilled. Next cycle, `get_positions()` still shows the position, it gets re-tracked, and the exit loop repeats forever.

### The Fix

**Step 1:** Add pending exit order tracking (around line 50, after other instance variables):

```python
# In __init__, add:
self._pending_exits: Dict[str, str] = {}  # key -> order_id (exit orders awaiting fill)
```

**Step 2:** In `_exit_position()`, DON'T log position_closed or pop from _tracked. Instead, record the pending exit:

Find this block (around line 700-730):
```python
if result:
    # Calculate P&L from actual sell price
    entry_cost = tracked.entry_price_cents * tracked.count / 100.0
    ...
    self._tracked.pop(key, None)
    ...
    get_trade_logger().log_position_closed(...)
```

Replace with:
```python
if result:
    # Record pending exit — don't log close until fill confirmed
    order_id = result.get("order_id") if isinstance(result, dict) else str(result)
    self._pending_exits[key] = order_id
    self.logger.info(
        "exit_order_placed",
        ticker=pos.ticker,
        side=side,
        count=count,
        order_id=order_id,
        account=client.label,
    )
    # DON'T pop from _tracked yet
    # DON'T log position_closed yet
    # fill_manager will handle confirmation
```

**Step 3:** In `_check_position()`, skip positions with pending exits:

Find the start of `_check_position()` and add this early return:
```python
async def _check_position(
    self,
    client: KalshiTradingClient,
    pos: KalshiPosition,
) -> None:
    key = f"{client.label}:{pos.ticker}"
    
    # NEW: Skip if we have a pending exit order for this position
    if key in self._pending_exits:
        self.logger.debug("position_has_pending_exit", ticker=pos.ticker, account=client.label)
        return
    
    # ... rest of existing code
```

**Step 4:** Add a method to confirm exits (call this from fill_manager or a new check loop):

```python
async def _check_pending_exits(self, client: KalshiTradingClient) -> None:
    """Check if pending exit orders have filled."""
    keys_to_remove = []
    
    for key, order_id in list(self._pending_exits.items()):
        if not key.startswith(f"{client.label}:"):
            continue
            
        ticker = key.split(":", 1)[1]
        
        try:
            # Check order status via Kalshi API
            order = await client.get_order(order_id)
            if order is None:
                # Order not found — might have been filled and cleared
                keys_to_remove.append(key)
                continue
                
            status = order.get("status", "").lower()
            
            if status in ("filled", "executed"):
                # Exit confirmed — now we can log and clean up
                tracked = self._tracked.get(key)
                if tracked:
                    fill_price = order.get("avg_fill_price", order.get("price", 1))
                    entry_cost = tracked.entry_price_cents * tracked.count / 100.0
                    exit_proceeds = fill_price * tracked.count / 100.0
                    pnl = exit_proceeds - entry_cost
                    
                    get_trade_logger().log_position_closed(
                        platform="kalshi",
                        ticker=ticker,
                        side=tracked.side,
                        count=tracked.count,
                        entry_price_cents=tracked.entry_price_cents,
                        exit_price_cents=int(fill_price * 100),
                        pnl_usd=pnl,
                        account_label=client.label,
                    )
                    self._tracked.pop(key, None)
                    
                keys_to_remove.append(key)
                
            elif status in ("canceled", "cancelled", "expired"):
                # Exit failed — remove from pending, will retry next cycle
                keys_to_remove.append(key)
                self.logger.warning("exit_order_canceled", ticker=ticker, order_id=order_id)
                
            # If still "open" or "pending", leave it alone
            
        except Exception as e:
            self.logger.error("check_pending_exit_error", ticker=ticker, error=str(e))
    
    for key in keys_to_remove:
        self._pending_exits.pop(key, None)
```

**Step 5:** Call `_check_pending_exits` in the main monitor loop:

In `_check_all_positions()`, add before the position loop:
```python
# Check pending exits first
for client in self.trading_clients:
    await self._check_pending_exits(client)
```

---

## Phase 2: Fix Market Making Logic

**File:** `src/engines/kalshi_mm_engine.py`

### The Bug

The MM engine places YES and NO orders at the same price (both at 42¢). Real market making quotes a spread: bid lower, ask higher.

### The Fix

Find the quote generation logic (look for where bid/ask prices are calculated). The Avellaneda-Stoikov math looks correct in the comments, but check the actual implementation.

**Look for something like:**
```python
yes_bid = ...
yes_ask = ...
```

**Should be:**
```python
mid = km.yes_price  # e.g., 0.42
half_spread = 0.02  # 2 cents each side

yes_bid = int((mid - half_spread) * 100)  # 40
yes_ask = int((mid + half_spread) * 100)  # 44

# Then place:
# - Buy YES limit at 40¢ (this is our bid)
# - Sell YES limit at 44¢ (this is our ask) — or equivalently, buy NO at 56¢
```

**Key insight:** A market maker places ONE side at a time, not both. You:
1. Place a bid (buy YES at 40¢)
2. Place an ask (sell YES at 44¢ — which is same as buy NO at 56¢)
3. When BOTH fill, you captured the spread

If the current code is placing both YES and NO at the same price (42¢ each), that's not MM — that's just washing. Fix it to quote a proper spread.

---

## Phase 3: Add Closed-Market Pre-Check

**File:** `src/kalshi_trading_client.py`

### The Bug

476 order failures because we're trying to trade on markets that already closed.

### The Fix

In `place_order()`, add a pre-check:

```python
async def place_order(
    self,
    ticker: str,
    side: str,
    count: int,
    price_cents: int,
    order_type: str = "limit",
    is_exit: bool = False,
) -> Optional[Dict]:
    # NEW: Check market status before placing order
    try:
        market = await self._get_market_status(ticker)
        if market is None:
            self.logger.warning("market_not_found", ticker=ticker)
            return None
        if market.get("status", "").lower() in ("closed", "settled", "finalized"):
            self.logger.info("skip_closed_market", ticker=ticker, status=market.get("status"))
            return None
    except Exception as e:
        self.logger.warning("market_status_check_failed", ticker=ticker, error=str(e))
        # Continue anyway — order will fail if market is closed
    
    # ... rest of existing place_order code
```

Add the helper method:
```python
async def _get_market_status(self, ticker: str) -> Optional[Dict]:
    """Fetch market status from Kalshi API."""
    # Use caching to avoid rate limits
    cache_key = f"market_status:{ticker}"
    cached = self._market_cache.get(cache_key)
    if cached and (time.monotonic() - cached[0]) < 60:  # 1 min cache
        return cached[1]
    
    try:
        response = await self._client.get(f"/markets/{ticker}")
        market = response.json().get("market", {})
        self._market_cache[cache_key] = (time.monotonic(), market)
        return market
    except Exception:
        return None
```

---

## Phase 4: Disable Losing Strategies

**File:** `config.yaml`

### The Change

```yaml
strategy:
  enabled_strategies: []  # DISABLE ALL ENGINE-BASED STRATEGIES
  
# Disable LLM predictions (keep screening for filtering)
llm:
  ensemble_mode: "none"  # or remove ensemble config entirely
  screening_enabled: true
  
# Disable market making (it's broken)
market_making:
  enabled: false
  
# Disable contrarian (crowds are usually right)
contrarian:
  enabled: false
  
# Keep bonding but make it stricter
bonding:
  enabled: true
  min_price_cents: 95  # only near-certain (was 90)
  verify_with_data: true
```

The NOAA/FRED fast-paths run inside the LLM engine but bypass LLM calls when data is available. They should still work with `ensemble_mode: "none"`.

---

## Phase 5: Fix Exponential Position Bug

### Investigation

The 24→48→96→... pattern suggests something is doubling positions. Check:

1. **Search for position accumulation logic:**
```bash
grep -r "count \*\|count +" src/
grep -r "double\|multiply\|scale" src/
```

2. **Check if signals are being duplicated:**
   - Is the same signal being processed by both accounts?
   - Is the orchestrator adding to existing positions instead of skipping?

3. **Check fill_manager:**
   - Is it re-filling the same order multiple times?

Most likely cause: The bot sees an "opportunity" (KXTOPALBUMTHEFALLOFF NO), places an order, order fills, next scan sees the same opportunity, places another order, etc. Each scan doubles down.

### The Fix

Add a position-size gate in the orchestrator or risk manager:

```python
# In risk.py or orchestrator.py
def check_existing_position(self, ticker: str, side: str) -> bool:
    """Return True if we already have a position in this market."""
    for pos in self.get_all_positions():
        if pos.ticker == ticker:
            return True
    return False

# Then in signal processing:
if self.check_existing_position(signal.ticker, signal.side):
    self.logger.debug("skip_existing_position", ticker=signal.ticker)
    continue
```

---

## Phase 6: Verification Before Restarting

### Checklist

1. **Run the bot in dry_run mode first:**
```yaml
dev:
  dry_run: true
```

2. **Watch logs for 30 minutes:**
```bash
journalctl -u morpheus.service -f
```

3. **Check for:**
   - [ ] No `position_closed` spam (death loop fixed)
   - [ ] No `market_closed` errors (pre-check working)
   - [ ] No exponential position sizes in logs
   - [ ] MM placing bid/ask at DIFFERENT prices

4. **Once clean, disable dry_run and restart with one account only:**
```bash
systemctl start morpheus.service
# Keep morpheus2 stopped until verified
```

---

## Phase 7: Future — Bracket Arbitrage

Once bugs are fixed, implement actual edge:

### The Strategy

Kalshi has bracket markets like:
- KXHIGHNYC-26FEB20-T45 (High temp in NYC above 45°F)
- KXHIGHNYC-26FEB20-B45-T50 (High temp between 45-50°F)
- KXHIGHNYC-26FEB20-B50 (High temp below 50°F)

These are mutually exclusive and exhaustive. The YES prices should sum to $1.00.

If they sum to $0.97, you can buy all brackets for $0.97 and guaranteed get $1.00 back = 3% risk-free profit.

### Implementation Sketch

```python
class BracketArbEngine:
    async def scan_for_arb(self):
        # 1. Find all bracket events
        events = await self.find_bracket_events()
        
        for event in events:
            # 2. Get all brackets in the event
            brackets = await self.get_brackets(event.event_ticker)
            
            # 3. Calculate sum of YES ask prices
            total_cost = sum(b.yes_ask for b in brackets)
            
            # 4. Check for arb
            if total_cost < 0.97:  # 3% margin for fees/slippage
                profit_pct = (1.0 - total_cost) / total_cost
                
                # 5. Execute: buy YES on ALL brackets
                for bracket in brackets:
                    await self.place_order(
                        ticker=bracket.ticker,
                        side="yes",
                        price=bracket.yes_ask,
                        count=self.calculate_size(profit_pct),
                    )
```

---

## Summary: Order of Operations

1. **Stop bots** — `systemctl stop morpheus.service morpheus2.service`
2. **Fix position monitor** — Death loop bug (most critical)
3. **Fix config** — Disable broken strategies
4. **Fix market-closed check** — Reduce wasted API calls
5. **Fix MM spread logic** — Or just disable MM for now
6. **Test in dry_run** — Watch logs for 30 min
7. **Deploy to one account** — Verify clean operation
8. **Deploy to second account** — Once first is stable
9. **Build bracket arb** — Real edge, not LLM hopium

---

## Files Changed Summary

| File | Changes |
|------|---------|
| `src/position_monitor.py` | Add `_pending_exits`, fix `_exit_position`, add `_check_pending_exits` |
| `src/kalshi_trading_client.py` | Add `_get_market_status`, pre-check in `place_order` |
| `src/engines/kalshi_mm_engine.py` | Fix bid/ask spread calculation |
| `config.yaml` | Disable broken strategies |
| `src/orchestrator.py` or `src/risk.py` | Add existing-position check to prevent doubling |

---

## Questions?

If you hit anything unclear while implementing, ping me and I'll dig into the specific code section.
