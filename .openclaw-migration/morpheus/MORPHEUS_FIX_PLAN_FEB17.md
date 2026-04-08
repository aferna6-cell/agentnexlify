# Morpheus Fix Plan — February 17, 2026

## Executive Summary

**Current state:** $0 liquid, -$3.84 daily P&L, all capital locked in losing positions  
**Historical P&L:** +$1,382.54 total (bot WAS profitable)  
**Recent 24h:** -$4.50 approximate losses  
**Root cause:** Strategy drift from proven winners to experimental losers

---

## The Brutal Truth: P&L by Ticker

### Big Winners (Historical)
| Ticker | Trades | P&L | What Worked |
|--------|--------|-----|-------------|
| KXCPICORE | 29 | **+$1,040.81** | CPI predictions — economic data edge |
| KXBTCD | 83 | **+$293.58** | Bitcoin daily — momentum/trend following |
| KXBTC | 29 | **+$49.20** | Bitcoin — same |
| KXLOWTNYC | 9 | **+$19.25** | Weather NYC low temp — NOAA data |
| KXRT | 30 | **+$15.10** | Rotten Tomatoes — LLM cultural knowledge |
| KXHIGHCHI | 8 | **+$4.41** | Chicago high temp — weather |

### Big Losers (Historical)
| Ticker | Trades | P&L | What Failed |
|--------|--------|-----|-------------|
| KXTOPMODEL | 63 | **-$17.52** | Top Model predictions — LLM terrible at reality TV |
| KXLOWTCHI | 5 | **-$11.06** | Chicago LOW temp — harder to predict than high |
| KXHIGHNY | 26 | **-$7.62** | NYC high temp — more volatility |
| KXHIGHTATL | 20 | **-$4.99** | Atlanta high temp — coastal weather variance |
| KXINXU | 3 | **-$1.05** | S&P 500 index — LLM can't beat efficient markets |

---

## Today's Losses Breakdown (Feb 17)

### 1. Index LLM Trading: -$1.05 (3 trades, 0% win rate)
```
KXINXU-26FEB17H1600-T6749.9999 NO @ 9c → closed @ 2c = -$0.40
KXINXU-26FEB17H1600-T6774.9999 NO @ 13c → closed @ 3c = -$0.30  
KXINXU-26FEB17H1600-T6749.9999 NO @ 9c → closed @ 2c = -$0.35
```
**Problem:** LLM predicts S&P direction for 1-hour windows. Financial markets are efficient — no edge vs. millions of traders. The 6-10% "edge" estimates are hallucinated.

### 2. Bonding at 95-97c: -$0.52 (net loss after wins)
```
KXHIGHCHI-26FEB17-T53 NO @ 92c → closed @ 86c = -$0.40
KXHIGHTDC-26FEB17-B59.5 NO @ 96c → closed @ 92c = -$0.12
KXHIGHTDC-26FEB17-T53 NO @ 31c → closed @ 14c = -$0.17
```
**Problem:** At 97c, you risk $0.97 to make $0.03 (32:1 against). Weather has ~5% surprise rate. Math:
- 95 wins × $0.03 = $2.85
- 5 losses × $0.97 = $4.85
- **Net: -$2.00 per 100 trades**

### 3. Bracket Arb Early Exits: -$0.35
```
XRP brackets bought at $0.08-$0.18 each
Total cost: ~$0.97 for 8 brackets
Expected: $1.00 payout (ONE bracket wins) = $0.03 profit
Actual: Positions closed at MTM before settlement = LOST the arb
```
**Problem:** Position monitor is exiting bracket arb positions early instead of holding to settlement. The "55% edge" signal is correct — total bracket cost < $1 — but early exit destroys the guaranteed profit.

### 4. MM on Volatile Politics: -$0.95
```
KXTARIFFDECISIONRELEASE-26FEB21 YES @ 41c → closed @ 15c = -$0.95
```
**Problem:** Politics markets move 20c+ on single news events. Market making requires stable prices.

---

## Root Causes

### 1. Strategy Drift
Bot was profitable (+$1,382) on:
- **CPI/Economic data** (+$1,040) — FRED data edge, actual information advantage
- **Bitcoin** (+$343) — trend following, momentum
- **Weather buy_NO** (+$24) — NOAA forecasts are accurate

Bot started losing when it expanded to:
- Index LLM (gambling on S&P)
- Bonding at 95c+ (negative EV math)
- Reality TV predictions (no data edge)
- MM on politics (news-driven moves)

### 2. Bracket Arb Implementation Bug
The bracket arb engine correctly identifies arbitrage (total bracket cost < $1), but:
- Position monitor closes positions at market value
- Market value fluctuates before settlement
- Guaranteed profit becomes realized loss

### 3. Bonding Price Threshold Too High
Config says `min_price_cents: 90` but trades are filling at 92-97c.
At 90c: risk $0.90 to make $0.10 (9:1) — requires 91% success
At 97c: risk $0.97 to make $0.03 (32:1) — requires 97% success
Weather achieves ~95% accuracy. Only 90c or lower is +EV.

### 4. Capital Death Spiral
$0 liquid → can't take new signals → bot halts → positions resolve → capital freed → immediately loses on bad signals → repeat

---

## The Fix

### Phase 1: Immediate Config Changes

```yaml
# 1. DISABLE index LLM entirely
kalshi_llm:
  blocked_tickers:
    - "KXINXU"      # S&P 500 hourly
    - "KXNASDAQ"    # NASDAQ hourly
    - "KXSPX"       # S&P index

# 2. Fix bonding price threshold
bonding:
  max_price_cents: 90    # Was 97, now 90 (requires 91% success rate)
  min_profit_pct: 0.10   # Was 0.03, now 10% (risk $0.90 for $0.10)

# 3. Bracket arb: hold to settlement
bracket_arb:
  hold_to_settlement: true    # NEW: never exit early
  position_monitor_skip: true # NEW: PM ignores bracket positions

# 4. Disable index/crypto entirely in LLM
llm:
  blocked_categories:
    - "Financials"  # All index markets
    - "Crypto"      # All crypto markets (until proven)
```

### Phase 2: Strategy Prioritization

**KEEP (Proven Winners):**
1. **Economic data (CPI/jobs)** — +$1,040 historical. Data advantage is real.
2. **Weather buy_NO** — NOAA forecasts accurate, buy_YES already blocked
3. **Bitcoin trend following** (if re-enabled) — momentum signals work

**DISABLE (Proven Losers):**
1. **Index LLM** — efficient markets, no edge
2. **Bonding above 90c** — negative EV math
3. **Reality TV/entertainment** — no data edge
4. **MM on politics** — news-driven volatility

**FIX (Broken Implementation):**
1. **Bracket arb** — hold to settlement, don't MTM exit

### Phase 3: Capital Injection

Bot needs $50-100 fresh capital to escape death spiral:
- Current: $0 liquid
- Minimum viable: $20 (can take small signals)
- Recommended: $100 (proper position sizing)

Without capital, bot will:
1. Hit insufficient_balance on every signal
2. Never recover from halt state
3. Positions resolve but immediately depleted

---

## Implementation Checklist

- [ ] SSH to server, update config.yaml with fixes
- [ ] Add `hold_to_settlement: true` to bracket_arb engine
- [ ] Add blocked_tickers to LLM config
- [ ] Lower bonding max_price_cents to 90
- [ ] Clear halt state: `echo '{"trading_halted":false}' > state/client_halt_*.json`
- [ ] Restart morpheus service
- [ ] Deposit $50-100 to Kalshi account
- [ ] Monitor for 24h, verify no index trades

---

## Expected Outcome

With fixes:
- **Index losses eliminated:** $0/day instead of -$1/day
- **Bonding breakeven→profitable:** 90c threshold is +EV
- **Bracket arb realized:** ~$0.03 guaranteed per arb set
- **Focus on CPI/weather:** proven edge continues

**Projected daily P&L:** +$2-5/day (based on historical CPI/weather performance)
**Break-even timeline:** 2-3 weeks to recover recent losses

---

## Code Changes Required

### 1. Bracket Arb Engine (`src/engines/kalshi_bracket_arb_engine.py`)

Add flag to mark positions as "hold to settlement":

```python
# In signal generation
signal = TradingSignal(
    ...
    metadata={
        "hold_to_settlement": True,
        "arb_set_id": f"{event_ticker}_{timestamp}",
    }
)
```

### 2. Position Monitor (`src/position_monitor.py`)

Skip bracket arb positions:

```python
def check_position(self, position):
    if position.metadata.get("hold_to_settlement"):
        return  # Don't reprice or exit bracket arb
```

### 3. LLM Engine (`src/engines/kalshi_llm_engine.py`)

Add ticker blocklist:

```python
BLOCKED_TICKERS = ["KXINXU", "KXNASDAQ", "KXSPX", "KXBTC15M"]

def generate_signal(self, market):
    if any(market.ticker.startswith(t) for t in BLOCKED_TICKERS):
        return None  # Skip index/crypto
```

---

## Lessons Learned

1. **Play to your edge.** CPI data edge is real (+$1,040). Index prediction is gambling (-$1.05).
2. **Math beats intuition.** Bonding at 97c LOOKS safe but is -EV. Calculate the Kelly.
3. **Hold your arbs.** Arbitrage only works if you complete both legs to settlement.
4. **Capital is oxygen.** $0 liquid = death spiral. Always maintain reserve.
5. **Measure everything.** Per-ticker P&L analysis revealed the winners/losers instantly.

---

*Generated by MyAgent — Feb 17, 2026*
