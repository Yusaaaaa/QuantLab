# Project rules

1. This is a research-grade US equity backtesting project.
2. Correctness, auditability, and no-look-ahead are higher priority than speed.
3. Strategies return target weights.
4. Strategies never manage cash, fills, commission, slippage, or metrics.
5. Strategies never download their own market data.
6. Strategies cannot access data after the decision timestamp.
7. Never change strategy definitions to improve backtest results unless explicitly asked.
8. Never silently change execution assumptions.
9. Never silently ignore missing or invalid data.
10. Every material engine change requires tests.
11. Every successful run must be reproducible.
12. Do not create research factors unless the user explicitly asks for and approves them.
13. The factors directory is reserved; do not populate it automatically.
14. V1 has one official example strategy: fixed 50% AAPL / 50% TSLA, buy once and hold.
15. Do not add SMA, momentum, RSI, value, quality, or other example strategies unless explicitly requested.
16. Do not implement V2 roadmap features during V1.
17. Run tests before declaring a phase complete.

The authoritative specification is `us_equity_quant_lab_codex_workdoc_v4.md`.
The user has authorized completion of Phases 1–7. Implement sequentially, passing
the phase acceptance tests before proceeding. Tests must remain offline.


User-approved research strategy added after V1: weekly_equal_weight_aapl_tsla.py,
50/50 AAPL/TSLA at each Monday open (holiday rolls to first session of the week),
2020-01-06 through 2025-12-31, $100,000 initial cash, default costs.
This explicit user authorization does not authorize additional research factors.


The user subsequently approved the AAPL-minus-market return-spread factor and a
weekly contrarian strategy: initially half AAPL/half cash; weekly spread < -1pp
spends half remaining cash, > +1pp sells half held shares, otherwise hold.
Approved factor: factors/return_spread.py (daily and weekly pure calculations).
Approved strategy: aapl_weekly_relative_reversal.py (weekly calculation used).
Factor dependencies must be explicitly bound, linted and archived with the strategy.
For this rule, decision_relative sizing preserves cash/share fractions across gaps;
standard target_weights execution remains unchanged. No other factors are authorized.


Release 2026.10.22: the user authorized publishing the current simple strategies
and factor with the application. Independent researchProject/ code/data/results
remain separate from application release content. This does not authorize new
research factors or silent changes to strategy semantics. See PROJECT_SCOPE.md.
