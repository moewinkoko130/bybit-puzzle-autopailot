# BYBIT AUTOPILOT — MASTER AGENT — PART 2
# CORE PAPER / STRATEGY / RISK ARCHITECTURE

You are continuing work on:

bybit-puzzle-autopailot

Only begin this phase after the user explicitly approves the Phase 1 audit.

Do NOT implement LIVE trading in this phase.

Default execution remains:

PAPER ONLY

==================================================
DEVELOPMENT ORDER
==================================================

Implement in this order:

1. Paper engine stabilization
2. Persistent database/history
3. Strategy engine
4. Risk engine
5. Paper performance
6. Trading engine/state management

After each logical step:

python -m py_compile ...
pytest -q
git diff --check
git status

If a test fails:
STOP.
Fix the failure before continuing.

==================================================
PAPER ENGINE
==================================================

Build a proper paper simulator.

Support:

BUY
SELL

Each trade should track:

trade_id
symbol
timeframe
strategy
side
entry_price
quantity
stop_loss
take_profit
opened_at
closed_at
exit_price
exit_reason
fees
slippage
realized_pnl
status

Statuses:

OPEN
CLOSED

Exit reasons:

STOP_LOSS
TAKE_PROFIT
MANUAL_CLOSE

Simulate:

fees
slippage
position state
PnL

History must survive process restart.

Use SQLite unless the existing project provides a strong reason not to.

==================================================
PAPER PERFORMANCE
==================================================

Main menu must eventually become:

11. Run Bot
12. Paper Performance
13. Exit

Paper Performance must use the same persistent trade-history source as the paper engine.

Display:

Total Trades
Wins
Losses
Breakeven
Win Rate
Total PnL
Average PnL
Profit Factor
Largest Win
Largest Loss
Average Win
Average Loss
Max Drawdown
Current Equity
Open Positions
Closed Positions

No placeholder output.

==================================================
STRATEGY ENGINE
==================================================

Create a strategy interface.

Initially support:

EMA Crossover
RSI

EMA parameters:

fast period
slow period

RSI parameters:

period
overbought
oversold

Signals must contain:

signal
strategy
symbol
timeframe
timestamp
price
indicators

==================================================
EMA CROSSOVER
==================================================

Do NOT use:

EMA9 > EMA21 = BUY
EMA9 < EMA21 = SELL

as a crossover event.

Use actual crossover detection:

BUY:

previous_fast <= previous_slow
current_fast > current_slow

SELL:

previous_fast >= previous_slow
current_fast < current_slow

Prevent duplicate entries from the same signal.

==================================================
RISK ENGINE
==================================================

Maintain:

MAX_RISK_PERCENT
STOP_LOSS_PERCENT
TAKE_PROFIT_PERCENT
REWARD_RATIO
POSITION_SIZE

Basic formula:

risk_amount =
equity * risk_percent / 100

price_risk =
abs(entry_price - stop_loss)

position_size =
risk_amount / price_risk

Validate:

minimum quantity
quantity step
price tick size
minimum order value

Add limits:

maximum risk per trade
maximum open positions
maximum daily loss
maximum consecutive losses
maximum position size
maximum leverage

If rejected:

TRADE REJECTED

and clearly explain the reason.

Never silently execute.

==================================================
TRADING ENGINE
==================================================

Flow:

Market Data
    ↓
Indicators
    ↓
Signal
    ↓
Signal Validation
    ↓
Risk Validation
    ↓
Position Validation
    ↓
Execution
    ↓
Position Monitoring
    ↓
History
    ↓
Statistics

Never:

signal → order

without risk validation.

==================================================
DUPLICATE PROTECTION
==================================================

Prevent:

duplicate entries
duplicate signals
duplicate orders
restart-induced duplicate trades

Use deterministic state.

==================================================
TESTING
==================================================

Create tests for:

EMA calculation
EMA crossover
HOLD
BUY
SELL
insufficient candles

Risk amount
position size
SL
TP
invalid risk
maximum risk

Paper open
paper close
BUY PnL
SELL PnL
SL
TP
trade history
statistics
drawdown
fees
slippage

Use mocks where required.

==================================================
GIT
==================================================

Do not automatically push.

Do not reset --hard.

Do not delete backups.

At the end report:

PHASE
FILES CHANGED
FEATURES ADDED
TESTS PASSED
TESTS FAILED
SECURITY NOTES
NEXT STEP

Do not claim unfinished features are complete.
