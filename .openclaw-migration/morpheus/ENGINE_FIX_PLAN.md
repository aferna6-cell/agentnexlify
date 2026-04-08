# ENGINE FIX PLAN — Morpheus Kalshi Bot

**Goal**: Get all engines actually executing profitable trades, not just "finding opportunities"

**Current State** (Feb 16):
| Engine | Signals | Executions | PnL | Status |
|--------|---------|------------|-----|--------|
| Index (LLM) | ✅ Working | 9 trades | +$107 | **KEEP** |
| Bracket Arb | 18+ "opps" | 0 trades | $0 | **BROKEN** |
| Weather NOAA | ✅ Signals | Many | -$4.27 | **SIZING BUG** |
| MM | Unknown | 0 fills | $0 | **BROKEN** |
| Bonding | Just started | 0 trades | $0 | **UNVALIDATED** |

---

## Engine 1: Bracket Arb (Priority: HIGH)

### The Problem
Engine finds 18+ opportunities per scan with margins up to 52%, but **zero trades ever executed**.

### Investigation Steps

```bash
# 1. Check if orders are being placed at all
ssh root@45.55.85.173 "journalctl -u morpheus.service --since '24 hours ago' | grep -i 'bracket_arb' | grep -i 'order'"

# 2. Check for rejection reasons
ssh root@45.55.85.173 "journalctl -u morpheus.service --since '24 hours ago' | grep -i 'bracket_arb' | grep -iE 'reject|fail|error|insufficient'"

# 3. Look at what "opportunities" actually look like
ssh root@45.55.85.173 "journalctl -u morpheus.service --since '1 hour ago' | grep -i 'bracket_arb_opportunity'"

# 4. Check the engine code for order placement
ssh root@45.55.85.173 "grep -n 'place_order\|submit_order\|create_order' /opt/morpheus/src/engines/kalshi_bracket_arb*.py"
```

### Likely Root Causes

1. **Signal only, no execution** — Engine logs opportunities but never calls order placement
2. **Stale prices** — By the time we check, arb is gone (need WebSocket, not polling)
3. **Minimum order size** — Kalshi may have $1 or $5 minimums we're not meeting
4. **Illiquid markets** — No counterparty at quoted price
5. **Order type wrong** — Placing market orders on empty books

### Fix Plan

```python
# A. Verify execution path exists
# In kalshi_bracket_arb_engine.py, find where opportunities are logged
# Trace: opportunity detected → risk check → order creation → order submission

# B. Add execution logging
# Before: silent failure
# After: log every step with success/failure reason

# C. Switch to limit orders at quoted price
# Market orders on thin books = bad fills or no fills

# D. Add staleness check
# If price is >5 seconds old, skip (assume arb is gone)

# E. Reduce minimum margin threshold
# Current: probably 5%+ 
# Try: 1-2% (smaller but real profits)
```

### Success Criteria
- [ ] See "bracket_arb order placed" in logs
- [ ] See "bracket_arb order filled" in logs  
- [ ] Positive PnL from bracket arb trades

---

## Engine 2: Weather/NOAA (Priority: HIGH)

### The Problem
55% win rate (good!) but **negative PnL** (-$4.27). Average loss > average win = sizing disaster.

### Investigation Steps

```bash
# 1. Get all weather trades with sizes and PnL
ssh root@45.55.85.173 "cat /opt/morpheus/state/trade_history.jsonl | jq -r 'select(.source==\"noaa\" or .source==\"weather\") | \"\(.ticker) \(.side) \(.size) \(.pnl)\"'"

# 2. Check position sizing logic
ssh root@45.55.85.173 "grep -n 'position_size\|size_usd\|contracts' /opt/morpheus/src/engines/kalshi_*weather*.py /opt/morpheus/src/engines/kalshi_bonding*.py"

# 3. Look at risk manager sizing
ssh root@45.55.85.173 "grep -n 'calculate_size\|kelly\|size' /opt/morpheus/src/risk*.py"
```

### Likely Root Causes

1. **Fixed sizing regardless of edge** — Betting same amount on 5% edge vs 30% edge
2. **No stop-loss / position cap** — Letting losers run
3. **Winners cut early** — Taking profit too soon on high-confidence trades
4. **Kelly fraction too aggressive** — Full Kelly is too volatile, need 1/4 Kelly

### Fix Plan

```python
# A. Edge-proportional sizing
# size = base_size * (edge / 0.10)  # Scale to edge strength
# 5% edge = 0.5x base, 20% edge = 2x base

# B. Maximum loss cap per trade
# max_loss_per_trade = 0.02 * bankroll  # 2% max loss
# Calculate position size backwards from max loss

# C. Minimum edge threshold
# Only trade if edge > 10% (not 5%)
# Fewer trades but higher quality

# D. Asymmetric exit
# Let winners run (exit at 80% of max profit)
# Cut losers fast (exit at 50% of entry if moving against)
```

### Config Changes

```yaml
# In config.yaml
weather:
  min_edge_pct: 0.10        # Only trade 10%+ edge (was 0.05)
  max_position_pct: 0.02    # 2% of bankroll max per trade
  kelly_fraction: 0.25      # Quarter Kelly (was probably 0.5 or 1.0)
  
bonding:
  min_edge_pct: 0.10
  max_position_pct: 0.03    # 3% for NOAA-verified (higher confidence)
```

### Success Criteria
- [ ] Average win > Average loss
- [ ] Positive PnL over 20+ trades
- [ ] Win rate stays >50%

---

## Engine 3: Market Making (Priority: MEDIUM)

### The Problem
Zero fills. Either not placing orders, or spread is wrong, or getting front-run.

### Investigation Steps

```bash
# 1. Check if MM orders are being placed
ssh root@45.55.85.173 "journalctl -u morpheus.service --since '24 hours ago' | grep -i 'mm\|market_mak' | grep -i 'order'"

# 2. Check for the spread bug (both sides at same price)
ssh root@45.55.85.173 "journalctl -u morpheus.service --since '24 hours ago' | grep -iE 'bid.*ask|spread'"

# 3. Look at MM engine logic
ssh root@45.55.85.173 "cat /opt/morpheus/src/engines/kalshi_mm*.py | head -200"
```

### Likely Root Causes

1. **Spread bug** — Placing YES and NO at same price (confirmed earlier)
2. **Spread too wide** — No one crosses our prices
3. **Spread too tight** — Getting picked off by informed traders
4. **No inventory management** — Accumulating one-sided risk
5. **Wrong markets** — MM on illiquid markets = no fills

### Fix Plan

```python
# A. Fix spread calculation
# WRONG: bid = mid, ask = mid
# RIGHT: bid = mid - spread/2, ask = mid + spread/2

# B. Dynamic spread based on volatility
# Calm market: tight spread (1-2%)
# Volatile market: wide spread (3-5%)

# C. Inventory skew
# If holding YES, lower ask price (want to sell)
# If holding NO, raise bid price (want to sell)

# D. Market selection
# Only MM on markets with >$1k daily volume
# Skip illiquid garbage
```

### Success Criteria
- [ ] Orders placed on both sides with different prices
- [ ] At least some fills (even if small)
- [ ] Net PnL positive after spread capture

---

## Engine 4: Bonding (Priority: MEDIUM-HIGH)

### The Problem
Just started generating NOAA-verified signals. Zero executions yet. Unknown if it works.

### Investigation Steps

```bash
# 1. Check bonding signal generation
ssh root@45.55.85.173 "journalctl -u morpheus.service --since '24 hours ago' | grep -i 'bonding'"

# 2. Check if signals are reaching order stage
ssh root@45.55.85.173 "journalctl -u morpheus.service --since '24 hours ago' | grep -i 'bonding' | grep -iE 'order|trade|submit'"

# 3. Look at bonding engine code
ssh root@45.55.85.173 "cat /opt/morpheus/src/engines/kalshi_bonding*.py | head -150"
```

### Likely Root Causes

1. **Signal → Order gap** — Generates signals but doesn't execute
2. **Edge threshold too high** — Rejecting valid opportunities
3. **Balance insufficient** — $0.06 means nothing can execute
4. **Risk manager blocking** — Daily loss limits, position limits

### Fix Plan

```python
# A. Verify execution path
# Signal → Risk check → Order creation → Submission → Fill

# B. Lower thresholds for NOAA-verified signals
# NOAA verified = high confidence, should trade more aggressively

# C. Priority queue
# When capital is limited, bonding signals should jump the queue
# (Higher win rate than other engines)
```

### Success Criteria
- [ ] Bonding signals reach order placement
- [ ] Orders fill
- [ ] Win rate matches NOAA accuracy (~70-90%)

---

## Engine 5: Index (LLM) — WORKING, OPTIMIZE

### Current State
Only profitable engine. 9 trades, 9 wins, +$107.67.

### Optimization Ideas

```python
# A. Faster detection
# Current: polling every X seconds
# Better: WebSocket to Yahoo Finance for real-time prices

# B. Larger position sizing
# This is the proven edge — allocate more capital here
# index_position_pct: 0.30  # 30% of bankroll per index trade

# C. Multiple data sources
# Yahoo Finance (current)
# Add: Google Finance, Bloomberg, TradingView
# Cross-reference for stronger signal
```

---

## Execution Order

### Day 1: Investigation
1. SSH in, run all investigation commands above
2. Document actual state of each engine
3. Identify which root cause applies to each

### Day 2-3: Bracket Arb Fix
- Highest potential (free money if it works)
- Trace signal → order path
- Add logging, fix execution

### Day 4-5: Weather/NOAA Sizing Fix
- Change config: min_edge 10%, kelly 0.25
- Add max loss cap per trade
- Test with small capital

### Day 6-7: MM Spread Fix
- Fix bid/ask calculation
- Add inventory skew
- Test on liquid markets only

### Week 2: Validation
- Run all engines with fixes
- Track PnL by engine
- Iterate on what's not working

---

## Quick Reference: SSH Commands

```bash
# Connect
ssh root@45.55.85.173

# View live logs
journalctl -u morpheus.service -f

# View recent logs
journalctl -u morpheus.service --since "1 hour ago"

# Restart bot
systemctl restart morpheus.service

# Edit config
nano /opt/morpheus/config.yaml

# Check state files
ls -la /opt/morpheus/state/
cat /opt/morpheus/state/risk_state.json

# Clear halt state
echo '{"halted": false}' > /opt/morpheus/state/client_halt_kalshi_primary.json
```

---

## Expected Outcomes After Fixes

| Engine | Current | Expected | Weekly Impact |
|--------|---------|----------|---------------|
| Index | +$107 (working) | +$10-15/week | +$10-15 |
| Bracket Arb | $0 (broken) | +$5-10/week | +$5-10 |
| Weather | -$4 (sizing bug) | +$2-5/week | +$6-9 |
| MM | $0 (broken) | +$1-3/week | +$1-3 |
| Bonding | $0 (new) | +$3-7/week | +$3-7 |

**Total potential**: +$25-44/week on $50-100 capital (50-90% weekly)

This is aggressive but achievable IF the engines actually execute.
