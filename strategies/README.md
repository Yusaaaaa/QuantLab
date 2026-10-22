# 给用户与未来 AI 的策略合同

1. 从 `_template.py` 开始，先写清楚 Strategy Name、Idea、Exact Mathematical Rule、Universe、Selection Rule、Portfolio Construction、Decision Time、Execution Time、Required Data、Parameters、Look-ahead Protection、Known Limitations。
2. 规则必须由用户明确提出并确认，不得为提高回测收益改变定义。
3. 只使用 params、截至决策 close 的 `data` 和只读 `ctx`。
4. 返回 `dict[str, float]` target weights，或 `None`（不产生新指令）。空 dict 表示清仓；省略现有持仓代表其目标为零。
5. 不触碰 engine，不管理现金、持仓、订单、成交、手续费、滑点或绩效。
6. 不自行下载/读取外部数据，不使用网络、data provider、engine 私有导入，不访问未来。
7. `data.history(symbol, bars=None, end=None)` 返回副本；`data.current(symbol)` 返回当日 bar 或 None。数据视图不含未来行。
8. `ctx` 包含 cash、equity、positions（股票→整数股数）、universe、seed、next_session_date（下一交易日的已知日历日期，不含未来行情），全为只读。可以维护策略自身状态。
9. `warmup_bars()` 是非负整数；历史只在回测日期范围内累计。
10. 创建后先运行 `quantlab strategies validate strategies/<name>.py --config configs/<config>.yaml`。
11. Validator 是可信代码合同检查与基本 smoke test，不是恶意 Python 沙箱，也不保证覆盖所有动态路径；正式回测仍逐次校验输出。
12. 无用户要求时不得改进策略；回测差不代表可以自动改规则。

V1 唯一官方示例：`fixed_weight_buy_and_hold.py`。默认 AAPL/TSLA 各 50%，第一次满足当日已知可交易条件后发出一次目标，下一 NYSE session open 尝试成交，随后一直持有。下一个 open 是否缺失不能提前知道，因此执行失败不会自动重试。

允许导入数学/数据计算模块 math、numpy、pandas、statistics、typing、collections、datetime 和 quantlab.strategy.base；常见外部读取、反射、私有属性与危险操作会被拒绝。遇到合同限制应明确讨论需要的接口，不得绕过校验。


用户已明确批准的研究策略：`weekly_equal_weight_aapl_tsla.py`。从 2020-01-06 开盘开始，
每周一（休市顺延到当周首个交易日）以 AAPL/TSLA 各 50% 为目标调仓，持有至 2025-12-31 收盘。
该策略按交易日历定时，不依赖研究因子。通过每日 close 检查 next_session_date，在前一交易日发出指令，
从而保证实际执行发生在周一开盘。`rebalance_schedule: daily` 是检查频率，不是每天调仓。


用户明确批准的因子策略：`aapl_weekly_relative_reversal.py`，配合 `factors.return_spread` 周度函数。
需通过配置 factor_paths 显式绑定，并使用 execution.sizing=decision_relative，以保留半数现金/股数语义。
可以实现 `decision_metadata()` 返回审计说明，框架会将它记录进 decisions.csv，不影响成交。
ctx.execution_sizing 为只读政策标识。data 可观察 universe 与 benchmark 的历史，但不能为 benchmark
创建仓位，除非用户在 universe 中明确将其列为可交易证券。
