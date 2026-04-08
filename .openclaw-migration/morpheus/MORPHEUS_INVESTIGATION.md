# Morpheus Investigation Report — February 16, 2026

## Executive Summary

**The bot is bleeding money.** Despite 25 waves of "improvements," the core problem is simple: we're building complex machinery around strategies that don't have edge.

---

## The Numbers (Brutal Truth)

### Position Closes
- **Wins:** 125
- **Losses:** 232  
- **Win Rate:** 35%
- **That's worse than a coin flip.**

### Resolved Markets (LLM Predictions)
- **Wins:** 61
- **Losses:** 74
- **Win Rate:** 45%
- **Average CLV:** +0.017 (barely positive)

### The Real Problem
The raw CLV is slightly positive, but we're hemorrhaging money on **execution and position management bugs:**

1. **Same position exited 15+ times** — KXRT-WUT-60 keeps getting "closed" at -$0.30 per attempt
2. **Exponential position scaling** — KXTOPALBUMTHEFALLOFF went 24→48→96→192→384→768→1536→2048→4096 contracts, all exiting at 1¢
3. **476 order failures** — Many trying to trade on closed markets
4. **Market making placing BOTH sides at same price** — Not capturing spread, just churning

---

## What We're Doing vs What Actually Works

### Our Current Strategies

| Strategy | Status | Reality |
|----------|--------|---------|
| kalshi_llm | Running | LLMs have ~0 edge on Kalshi markets. KalshiBench shows ECE=0.40 for politics. |
| kalshi_contrarian | Running | Crowds are usually right. Contrarian = losing strategy. |
| kalshi_mm | Running | BROKEN. Placing YES+NO at same price isn't MM. Real MM captures spread. |
| kalshi_bonding | Running | Good idea, but verification logic is flawed (NOAA disagrees → reject) |
| kalshi_bracket_arb | Disabled | Never triggered once. The arb scanner doesn't find anything. |
| kalshi_theta | Enabled | Never produced a signal. |
| kalshi_crypto | Blocked by Kalshi | Dead code. |

**Net effect:** We're paying API costs to run 7 strategies, only 2 of which ever fire, and both lose money.

### What ACTUALLY Makes Money (Research)

From the $40M paper and Polymarket leaderboard analysis:

1. **Bracket Arbitrage** — Sum of YES prices in a bracket set should = $1. When it's $0.97, buy all brackets → free $0.03. Top trader extracted $1M+ this way.

2. **Copy Trading** — Follow proven profitable wallets. Simple. The top public bots are copy-traders, not predictors.

3. **Data-Backed Signals (NOAA/FRED)** — Weather and economic data have hard edge. This is the ONE thing we do that could work, but it's buried under LLM complexity.

4. **Speed** — Arb and copy require sub-second execution. We scan every 10 minutes.

---

## Critical Bugs Found

### 1. Position Monitor Death Loop (ROOT CAUSE FOUND)
```
position_closed KXRT-WUT-60 NO 3 @ -$0.30
position_closed KXRT-WUT-60 NO 3 @ -$0.30
position_closed KXRT-WUT-60 NO 3 @ -$0.30
... (15+ times)
```

**Root Cause:** Limit exit orders are being treated as fills!

The bug flow:
1. `place_order()` returns order_id (truthy) → treated as "success"
2. `_tracked.pop(key)` removes position from tracking
3. `log_position_closed()` logs the exit with calculated PnL
4. **BUT the limit order hasn't FILLED yet!**
5. Next cycle: `get_positions()` still shows the position (pending order)
6. Position isn't in `_tracked` (we popped it)
7. Position gets RE-TRACKED as new
8. Goto step 1...

**Fix:** Don't log `position_closed` until fill is CONFIRMED via fill_manager. Track pending exit orders separately.

### 2. Exponential Position Scaling Bug
```
KXTOPALBUMTHEFALLOFF: 24 → 48 → 96 → 192 → 384 → 768 → 1536 → 2048 → 4096
```
This looks like martingale/doubling-down logic that shouldn't exist. Positions are being added to exponentially, then all exiting at 1¢ for total loss.

### 3. Market Making Logic Broken
```
order_placed KXNYCMAYORDEBATEMENTION YES 2 @ 42¢
order_placed KXNYCMAYORDEBATEMENTION NO 2 @ 42¢
```
Real market making: bid 40¢, ask 44¢ → capture 4¢ spread.
Our market making: bid 42¢, ask 42¢ → capture nothing.

### 4. Trading on Closed Markets
476 `order_failed` events, many with `market_closed` error. We're wasting API calls trying to trade markets that already settled.

---

## The Honest Assessment

**We've been "painting rims on a car with no engine."**

25 waves of:
- Platt scaling
- 5-model ensembles  
- GraphCast weather integration
- Calibration overhauls
- Single-model penalties

None of this matters if the core strategy doesn't have edge.

### LLMs Don't Beat Prediction Markets

The research is clear:
- KalshiBench shows LLMs have ECE ~0.40 on politics (terrible)
- LLMs anchor on provided market prices
- Markets already incorporate public information

We've spent 25 waves calibrating LLM output when the fundamental problem is LLMs don't predict better than the crowd.

---

## The Plan: Strip to What Works

### Phase 1: Kill What Doesn't Work (Today)

Disable everything except:
1. **NOAA weather fast-path** — Data-backed, zero LLM cost
2. **FRED economic fast-path** — Data-backed, zero LLM cost

That's it. No LLM ensemble. No contrarian. No broken MM.

### Phase 2: Fix the Bugs (This Week)

1. **Fix position monitor death loop** — Add proper position state tracking
2. **Fix exponential scaling bug** — Find and kill whatever is doubling positions
3. **Add closed-market check** — Don't place orders on settled markets

### Phase 3: Build What Actually Works (Next Week)

#### Option A: Bracket Arbitrage (Free Money)

1. Fetch all bracket markets (KXHIGH*, KXGDP*, etc.)
2. Group by event (same date, same metric)
3. Calculate sum of YES prices
4. If sum < $0.97: buy all brackets → guaranteed $0.03+ profit

This is the strategy that extracted $40M from Polymarket.

#### Option B: Copy Trading (Proven Edge)

1. Identify 3-5 profitable Kalshi accounts (via leaderboard or API)
2. Monitor their trades via WebSocket
3. Mirror within seconds
4. Use their edge, pay no LLM costs

#### Option C: Real Market Making

1. Identify markets with 5c+ spread
2. Quote bid = mid - 2c, ask = mid + 2c
3. Manage inventory (skew quotes when one-sided)
4. Cancel and re-quote on fills

Not the broken "place both sides at same price" we have now.

### Phase 4: Speed (If Arb/Copy)

For arb and copy trading to work, we need:
- WebSocket connections (not polling every 10 min)
- Sub-second order execution
- Proper rate limit handling

---

## Recommended Config (Immediate)

```yaml
strategy:
  enabled_strategies: []  # Disable ALL strategies

# Enable ONLY data-backed fast-paths
llm:
  screening_enabled: true  # Keep for filtering
  ensemble_mode: "none"    # No LLM predictions

# NOAA-only weather trading
weather:
  enabled: true
  require_noaa_confirmation: true
  min_noaa_confidence: 0.8
  
# FRED-only economic trading  
economics:
  enabled: true
  require_fred_confirmation: true
```

---

## Success Metrics

Before adding ANY new strategy:

1. **Backtest on 500+ resolved markets**
2. **Require Brier < 0.20 AND positive CLV**
3. **Paper trade for 7 days**
4. **Only then go live**

We skipped all of this. That's why we're losing money.

---

## Bottom Line

Stop adding features. Fix the bugs. Kill the strategies that don't work.

The path to profitability is SUBTRACTION, not addition.

**Three things that could actually work:**
1. NOAA weather (already have, needs cleanup)
2. Bracket arbitrage (needs implementation)
3. Copy trading (needs implementation)

Everything else is noise.

---

## IMMEDIATE ACTION ITEMS

### Today (Critical Bug Fixes)

1. **Fix position monitor death loop**
   - In `_exit_position()`: Don't call `log_position_closed()` until fill confirmed
   - Add pending exit order tracking: `_pending_exits: Dict[str, order_id]`
   - In `_check_all_positions()`: Check if position has pending exit order, skip if yes
   - Only pop from `_tracked` when fill_manager confirms the fill

2. **Disable all strategies except NOAA/FRED fast-paths**
   ```yaml
   strategy:
     enabled_strategies: []  # DISABLE ALL
   ```
   Keep the engines loaded but don't generate signals. Let NOAA/FRED fast-paths run (they're zero-cost).

3. **Stop the bleeding on both accounts**
   ```bash
   ssh root@45.55.85.173 "systemctl stop morpheus.service morpheus2.service"
   ```
   Deploy bug fixes before restarting.

### This Week

4. **Fix MM quote logic** — Real market making captures spread:
   - `bid = mid - half_spread`
   - `ask = mid + half_spread`
   - NOT both at same price

5. **Add market-closed pre-check** — Before placing any order, check market status

6. **Clean up position tracking** — Single source of truth for all positions

### Next Week (New Strategy)

7. **Implement bracket arbitrage** — The proven $40M strategy:
   ```python
   async def find_bracket_arb():
       events = await fetch_bracket_events()  # KXHIGH*, KXGDP*, etc.
       for event in events:
           brackets = await fetch_brackets(event)
           total_yes = sum(b.yes_price for b in brackets)
           if total_yes < 0.97:  # 3% margin
               # BUY ALL BRACKETS → guaranteed profit
               return brackets
   ```

---

## Verification Checklist

Before going live again:

- [ ] Position monitor no longer logs duplicate closes
- [ ] No orders placed on closed markets (check logs for `market_closed`)
- [ ] Backtest NOAA-only strategy on 100 weather markets
- [ ] Paper trade for 48 hours with new config
- [ ] Verify bracket arb logic on historical data

---

## Files to Modify

| File | Change |
|------|--------|
| `src/position_monitor.py` | Fix death loop bug (pending exit tracking) |
| `src/kalshi_trading_client.py` | Add market-closed pre-check |
| `src/engines/kalshi_mm_engine.py` | Fix spread capture logic |
| `config.yaml` | `enabled_strategies: []` |

---

## Cost Analysis

Current state (last 7 days):
- LLM API spend: $3.11 / $25 budget
- Trading losses: Unknown (position_closed logging is broken)
- VPS cost: $0.33/day × 7 = $2.31

Estimated losses from bugs:
- KXRT-WUT-60 death loop: 15+ × -$0.30 = -$4.50 (fake PnL, but wasted API calls)
- KXTOPALBUMTHEFALLOFF exponential: up to -$10+ real losses

**First priority:** Stop the bleeding. Fix bugs. Then optimize.
