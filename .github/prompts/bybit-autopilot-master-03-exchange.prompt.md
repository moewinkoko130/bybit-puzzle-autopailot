# BYBIT AUTOPILOT — MASTER AGENT — PART 3
# EXCHANGE, TESTNET, LIVE SAFETY

Only begin this phase after the previous phases are stable and tests pass.

Do NOT jump directly to LIVE trading.

Required order:

PAPER
↓
TESTNET
↓
LIVE

==================================================
EXCHANGE ARCHITECTURE
==================================================

Create a dedicated Bybit adapter.

Only the exchange layer may interact with Bybit order endpoints.

Strategy, risk, paper engine, and CLI must not directly call order endpoints.

Conceptual interfaces:

create_order()
cancel_order()
amend_order()
get_order()
get_open_orders()
get_order_history()

Position interfaces:

get_positions()
get_position()
close_position()
set_stop_loss()
set_take_profit()

Support:

Market
Limit

Use unique internal order IDs.

Where supported, use exchange orderLinkId to correlate application trades and exchange orders.

Official Bybit API references:

https://bybit-exchange.github.io/docs/v5/order/create-order

https://bybit-exchange.github.io/docs/v5/position/trading-stop

==================================================
MARKET DATA
==================================================

Support:

ticker
candles
latest price
symbol information
tick size
quantity step
minimum quantity
minimum order value

Handle:

timeout
network failure
rate limit
malformed response
empty response
API errors

Use bounded retry with exponential backoff.

Never hammer the API.

==================================================
TESTNET
==================================================

Implement complete TESTNET execution before LIVE.

Display clearly:

Environment: TESTNET
Execution: REAL TESTNET ORDERS

PAPER:

Environment: PAPER
Execution: SIMULATED

LIVE:

Environment: MAINNET
Execution: REAL

Never infer the environment only from a hidden variable.

Always display it prominently.

==================================================
LIVE SAFETY GATE
==================================================

LIVE mode must require multiple explicit confirmations.

Example:

WARNING

You are about to enable REAL BYBIT TRADING.

Real funds may be lost.

Type exactly:

ENABLE LIVE TRADING

Then require a second confirmation.

LIVE must refuse activation if:

API key missing
API secret missing
risk settings invalid
symbol invalid
quantity invalid
test connection failed
account information unavailable

Never bypass the safety gate.

==================================================
API SECURITY
==================================================

Use .env for secrets.

Never print:

API key
API secret

Use masking:

API Key: abcd********wxyz

Ensure:

.env

is in .gitignore.

Never commit .env.

==================================================
TRADING MODES
==================================================

Support:

SIGNAL ONLY
PAPER ONLY
TESTNET
LIVE

Default:

PAPER ONLY

==================================================
ORDER / POSITION RECONCILIATION
==================================================

Before enabling LIVE:

Implement reconciliation between local state and exchange state.

Handle:

unknown orders
missing orders
partial fills
closed positions
restart recovery
network interruption

Never assume local state is correct when exchange state can be queried.

==================================================
DAILY RISK CONTROLS
==================================================

Implement:

Daily PnL
Daily loss limit
Consecutive losses
Trading pause
Reset behavior

If daily loss reaches the configured limit:

TRADING PAUSED

No new trade may be opened until the configured reset condition is satisfied.

==================================================
LOGGING
==================================================

Structured logs:

INFO  MARKET
INFO  SIGNAL
INFO  RISK
INFO  PAPER
INFO  ORDER
WARN  RISK_LIMIT
ERROR API

Never log secrets.

==================================================
FINAL ADVANCED ROADMAP
==================================================

Only after core PAPER and TESTNET systems are stable, design support for:

multiple symbols
multiple strategies
strategy enable/disable
strategy parameters
trailing stop
break-even
partial take profit
cooldown
session filters
volatility filter
spread/slippage filter
maximum exposure
portfolio risk
backtesting
walk-forward testing
optimization
performance reports
CSV export
JSON export

Do not implement advanced features before core execution is stable.

==================================================
BACKTESTING
==================================================

Backtesting must reuse the same strategy and risk modules.

Do not create a separate strategy implementation for backtesting.

Clearly label all results as simulated.

Never imply profitability or future performance.

Performance metrics:

Total Return
Total PnL
Win Rate
Profit Factor
Average Trade
Largest Win
Largest Loss
Max Drawdown
Sharpe-like metric
Number of Trades
Average Holding Time

==================================================
QUALITY RULE
==================================================

Prioritize:

1. Correctness
2. Safety
3. Testability
4. Maintainability
5. Observability
6. Reliability
7. Performance
8. User experience

A smaller stable system is better than a large broken system.

==================================================
GIT RULE
==================================================

Never automatically:

git push

Never:

git reset --hard

Never delete existing backups.

Before destructive changes:

create a backup or use a dedicated branch.

At the end of every phase report:

PHASE
FILES CHANGED
FEATURES ADDED
TESTS PASSED
TESTS FAILED
SECURITY NOTES
NEXT STEP

Do not claim a feature is complete until it is implemented and tested.

Never place real orders during development.
