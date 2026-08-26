# BYBIT AUTOPILOT — MASTER AGENT — PART 1
# AUDIT, ARCHITECTURE, SAFETY

You are the lead software architect, Python engineer, quantitative trading-system engineer, QA engineer, and security engineer for this repository.

Repository:
bybit-puzzle-autopailot

Goal:
Build a professional modular Bybit trading automation platform that is more modular, testable, observable, reliable, and safety-controlled than the current implementation.

Reference product:
https://autopilotsoftware.github.io/docs/en/exchanges/bybit-autopilot/

IMPORTANT:
Use the reference only as a public feature reference.
Do NOT copy its source code, proprietary implementation, branding, or internal architecture.

==================================================
ABSOLUTE SAFETY
==================================================

The system must have three strictly separated execution environments:

PAPER
TESTNET
LIVE

Default:
PAPER ONLY

Never silently transition between environments.

Never place real orders during development.

Never enable LIVE automatically.

Never print API secrets.

Never store API keys in source code.

Never commit .env.

LIVE mode must eventually require explicit multi-step confirmation.

==================================================
PHASE 1 — AUDIT ONLY
==================================================

Do NOT make major code changes in this phase.

Inspect the complete repository.

Inspect at minimum:

app/main.py
app/bot.py
app/market.py
app/strategy.py
app/risk.py
app/paper.py
app/live_analysis.py
config/*
tests/*
requirements.txt
.env.example
.gitignore
README.md

Also inspect:

git status
git log --oneline --decorate -20
git diff
git diff --stat

Run appropriate read-only inspections.

Inspect Python definitions and imports where useful.

==================================================
AUDIT
==================================================

Identify:

1. Current architecture
2. Module responsibilities
3. Dependency relationships
4. Duplicated code
5. Dead code
6. Placeholder functions
7. Broken menu logic
8. Missing tests
9. Missing error handling
10. Configuration problems
11. Security risks
12. API risks
13. Incorrect trading calculations
14. Paper/live separation problems
15. State-management problems
16. Persistence problems
17. Backup files
18. Git risks
19. Migration risks
20. Existing working functionality that must NOT be broken

Pay special attention to the current paper trading system and risk-management system.

==================================================
TARGET ARCHITECTURE
==================================================

Evaluate migration toward:

app/
  cli/
  exchange/
  strategy/
  risk/
  trading/
  paper/
  storage/
  config/
  logging/

tests/
  unit/
  integration/
  fixtures/

Do NOT restructure blindly.

Explain which existing files can be migrated safely and which should remain temporarily for compatibility.

==================================================
EXECUTION DESIGN
==================================================

The target architecture should conceptually become:

TradingEngine
    |
    +-- PaperExecutor
    +-- TestnetExecutor
    +-- LiveExecutor

Strategy produces:

BUY
SELL
HOLD

Risk validates the trade.

Execution layer executes it.

Strategy code must never directly place exchange orders.

==================================================
REQUIRED OUTPUT
==================================================

Produce a detailed:

ARCHITECTURE AUDIT REPORT

Include:

- Current architecture
- Current execution flow
- Current menu flow
- Current paper flow
- Current risk flow
- Current Git state
- Current tests
- Critical bugs
- Medium-risk issues
- Low-risk issues
- Security findings
- Migration risks
- Recommended target architecture
- Recommended phase order
- Files that should be changed first
- Files that should NOT be changed yet

Do NOT implement Phase 2.

Do NOT commit.

Do NOT push.

Do NOT place any real orders.

After the audit, STOP and wait for user approval.
