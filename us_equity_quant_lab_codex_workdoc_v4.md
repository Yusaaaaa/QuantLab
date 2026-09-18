# US Equity Quant Lab

## Codex 项目总工作文档 · V4

**用途：** 交给 Codex 作为本地美股量化研究与回测项目的实施规格。\
**项目定位：** 本地、可审计、可复现的美股日频研究回测系统。\
**V1 核心：** 把"策略 → 数据 → 成交 → 记账 → 指标 → 报告"做正确。\
**重要约定：** 可以预留 `factors/`，但 V1
不放任何用户尚未确认、尚未理解的研究因子。V1
唯一官方策略示例是最简单的固定权重买入并持有。

------------------------------------------------------------------------

# 0. 给 Codex 的最高优先级指令

请完整阅读本文件后再开始编码。

开发原则按优先级排序：

1.  **正确性 \> 可审计性 \> 可复现性 \> 易用性 \> 性能 \> 功能数量。**
2.  先做一个"窄而硬"的日频回测研究台，不要一开始造大型交易平台。
3.  策略逻辑和回测引擎彻底解耦。
4.  策略输出 **target
    weights**；引擎负责订单、成交、现金、持仓、手续费、滑点和绩效。
5.  默认禁止任何 look-ahead。
6.  默认信号在 `t` 日收盘后形成，交易在 `t+1 open` 执行。
7.  每个影响结果的假设必须显式配置或写进报告。
8.  每次成功运行必须可复现，并冻结配置与策略源码。
9.  AI 写策略时不得自己下载数据、不得直接修改
    portfolio、不得访问未来数据、不得偷偷改研究定义以改善结果。
10. V1 **不要实现任何用户尚未确认的 momentum、SMA、RSI、value、quality
    等示例策略或示例因子**。
11. V1 官方示例只做一件事：第一次可交易时目标仓位
    `AAPL=50%`、`TSLA=50%`，之后持有不动。
12. 每阶段验收和 pytest 未通过，不进入下一阶段。
13. 不要擅自扩展本规格范围。

------------------------------------------------------------------------

# 1. 用户最终希望得到什么

长期工作流：

``` text
用户提出策略想法
        ↓
用户自己写 / AI 按统一合同生成 Strategy
        ↓
strategies/
        ↓
Strategy Validator
        ↓
Backtest Engine
        ↓
Data → Orders → Execution → Portfolio
        ↓
Commission + Slippage
        ↓
Equity / Positions / Orders / Fills
        ↓
Performance & Risk Analytics
        ↓
Automatic HTML Report
        ↓
runs/<run_id>/ 完整实验快照
```

用户以后可以只描述策略思想，让 AI 写策略代码；但 AI
只能在策略合同允许的范围内工作，不能修改回测器来"配合"某个策略。

------------------------------------------------------------------------

# 2. V1 产品边界

## 2.1 V1 要做

-   US equities
-   Daily OHLCV
-   多股票组合
-   long-only
-   cash
-   integer shares
-   target-weight strategy
-   可配置 start/end
-   initial cash
-   benchmark
-   rebalance schedule
-   commission
-   slippage
-   execution timing
-   max position weight
-   max gross exposure
-   adjusted/raw price policy
-   local CSV / Parquet data
-   optional online data provider
-   offline synthetic sample data
-   benchmark comparison
-   standard performance/risk metrics
-   automatic HTML report
-   run archive
-   strategy validation
-   no-look-ahead tests
-   reproducibility tests

## 2.2 V1 明确不做

以下只写入 roadmap，不实现：

``` text
live trading
paper trading
broker connection
web dashboard / Streamlit
database service
minute/tick backtesting
options / futures / crypto
short selling
margin / leverage
sector-neutral / beta-neutral portfolio construction
AutoML
automatic alpha discovery
automatic parameter search
grid-search platform
Optuna
walk-forward framework
Docker / Kubernetes
full point-in-time constituent database
large factor platform
```

原因：先确认回测器本身可信，再做研究优化。

------------------------------------------------------------------------

# 3. 关于 Strategy 和 Factor 的定稿

## 3.1 Strategy

Strategy 是**完整决策规则**。

例如未来用户自己确认一个策略后，Strategy 可以包含：

-   计算什么信息；
-   如何选股票；
-   如何确定仓位；
-   何时再平衡。

Strategy 输出：

``` python
{
    "AAPL": 0.50,
    "TSLA": 0.50,
}
```

Strategy 不负责成交。

## 3.2 Factor

Factor 是可复用的研究特征。

架构可以预留：

``` text
factors/
    __init__.py
    README.md
```

但 V1 **不要为了演示而创建 momentum、volatility、RSI、value 等
factor**。

`factors/README.md` 只写：

> 此目录预留给用户未来已经理解、验证并明确批准的可复用研究因子。Codex
> 不得自行填充研究因子。

未来是否建立 Factor API、放哪些 factor，由用户研究后决定。

## 3.3 Utils 不等于 Factor

确定性的数学工具可以进入：

``` text
src/quantlab/utils/
```

例如：

``` python
def simple_return(price, periods=1):
    return price / price.shift(periods) - 1
```

但不要把普通数学函数包装成"alpha"。

------------------------------------------------------------------------

# 4. V1 唯一官方策略示例

文件：

``` text
strategies/fixed_weight_buy_and_hold.py
```

目的不是展示 alpha，而是验证整个回测系统。

## 4.1 策略定义

配置：

``` yaml
strategy:
  path: "strategies/fixed_weight_buy_and_hold.py"
  params:
    weights:
      AAPL: 0.50
      TSLA: 0.50
```

行为：

``` text
第一次满足可交易条件的 decision date：
    target AAPL = 50%
    target TSLA = 50%

默认在下一交易日 open 执行。

之后：
    不再主动 rebalance。
    一直持有到回测结束。
```

注意："50%/50%"指目标资金权重。由于 integer
shares、commission、slippage，会自然留下少量 cash。

## 4.2 为什么只用这个示例

它没有：

-   alpha
-   factor
-   technical indicator
-   ranking
-   optimization
-   parameter fitting

因此如果结果不对，问题几乎一定来自：

``` text
data
execution timing
target-weight conversion
rounding
commission
slippage
cash accounting
position accounting
mark-to-market
metrics
reporting
```

这正适合作为 V1 integration test。

------------------------------------------------------------------------

# 5. 推荐仓库结构

采用标准 `src` layout：

``` text
us-equity-quant-lab/
│
├── AGENTS.md
├── README.md
├── pyproject.toml
├── .gitignore
├── .env.example
│
├── configs/
│   ├── default.yaml
│   └── examples/
│       └── fixed_weight_buy_and_hold.yaml
│
├── data/
│   ├── raw/
│   ├── processed/
│   ├── cache/
│   └── metadata/
│
├── src/
│   └── quantlab/
│       ├── __init__.py
│       ├── cli.py
│       ├── config.py
│       ├── types.py
│       │
│       ├── data/
│       │   ├── base.py
│       │   ├── csv_local.py
│       │   ├── parquet_local.py
│       │   ├── yahoo.py
│       │   ├── schema.py
│       │   ├── validator.py
│       │   ├── calendar.py
│       │   └── market_view.py
│       │
│       ├── strategy/
│       │   ├── base.py
│       │   ├── context.py
│       │   ├── loader.py
│       │   └── validator.py
│       │
│       ├── engine/
│       │   ├── backtest.py
│       │   ├── clock.py
│       │   ├── portfolio.py
│       │   ├── position.py
│       │   ├── order.py
│       │   ├── fill.py
│       │   ├── broker.py
│       │   └── execution.py
│       │
│       ├── costs/
│       │   ├── commission.py
│       │   └── slippage.py
│       │
│       ├── metrics/
│       │   ├── performance.py
│       │   ├── drawdown.py
│       │   ├── benchmark.py
│       │   └── rolling.py
│       │
│       ├── report/
│       │   ├── builder.py
│       │   ├── plots.py
│       │   ├── tables.py
│       │   └── templates/
│       │       └── report.html.j2
│       │
│       └── utils/
│           ├── logging.py
│           ├── paths.py
│           ├── serialization.py
│           └── statistics.py
│
├── strategies/
│   ├── README.md
│   ├── _template.py
│   └── fixed_weight_buy_and_hold.py
│
├── factors/
│   ├── __init__.py
│   └── README.md
│
├── scripts/
│   ├── make_sample_data.py
│   └── validate_data.py
│
├── tests/
│   ├── fixtures/
│   ├── test_config.py
│   ├── test_data.py
│   ├── test_market_view.py
│   ├── test_strategy_validator.py
│   ├── test_commission.py
│   ├── test_slippage.py
│   ├── test_portfolio.py
│   ├── test_execution.py
│   ├── test_engine.py
│   ├── test_metrics.py
│   ├── test_drawdown.py
│   ├── test_no_lookahead.py
│   └── test_reproducibility.py
│
└── runs/
```

`data/raw/`、`data/cache/`、`runs/`、`.env` 默认 gitignore。

------------------------------------------------------------------------

# 6. 技术栈

V1 保持简单：

``` text
Python 3.12+
pandas
numpy
pydantic >= 2
PyYAML
typer
pyarrow
matplotlib
jinja2
pytest
```

可选在线数据：

``` text
yfinance
```

原则：

-   核心 Backtest Engine 自己实现；
-   不使用 Backtrader / Zipline / vectorbt 作为核心引擎；
-   不要未经 profiling 就上 Polars / Numba / multiprocessing；
-   pytest 不依赖互联网。

------------------------------------------------------------------------

# 7. CLI

统一入口：

``` bash
quantlab
```

最低命令：

``` bash
quantlab --help
quantlab backtest run --strategy <path> --config <path>
quantlab strategies validate <path>
quantlab report open <run_id>
```

示例：

``` bash
quantlab strategies validate strategies/fixed_weight_buy_and_hold.py

quantlab backtest run \
    --strategy strategies/fixed_weight_buy_and_hold.py \
    --config configs/examples/fixed_weight_buy_and_hold.yaml
```

正式接口不要依赖把策略复制到引擎目录。

------------------------------------------------------------------------

# 8. Configuration

使用 Pydantic v2。

必须：

``` python
extra = "forbid"
```

未知字段直接报错，防止 YAML 拼错后静默使用默认值。

示例：

``` yaml
backtest:
  start_date: "2018-01-01"
  end_date: "2025-12-31"
  initial_cash: 100000
  base_currency: "USD"

data:
  provider: "csv_local"
  frequency: "1d"
  price_mode: "adjusted"
  benchmark: "SPY"

universe:
  symbols:
    - AAPL
    - TSLA

strategy:
  params:
    weights:
      AAPL: 0.50
      TSLA: 0.50

execution:
  decision_time: "close"
  timing: "next_open"
  allow_fractional_shares: false

commission:
  model: "per_share"
  per_share: 0.005
  minimum: 1.00

slippage:
  model: "bps"
  bps: 5.0

portfolio:
  allow_short: false
  allow_negative_cash: false
  max_position_weight: 1.0
  max_gross_exposure: 1.0

analytics:
  trading_days: 252
  risk_free_rate: 0.0

report:
  enabled: true
  open_after_run: false

reproducibility:
  random_seed: 42
```

优先级：

``` text
CLI override > YAML > defaults
```

resolved config 必须保存到 run directory。

------------------------------------------------------------------------

# 9. DataProvider

引擎不得依赖某个具体网站。

定义协议：

``` python
class DataProvider(Protocol):
    def load_prices(
        self,
        symbols: list[str],
        start_date,
        end_date,
    ) -> pd.DataFrame:
        ...
```

V1：

``` text
CSVLocalDataProvider
ParquetLocalDataProvider
YahooDataProvider   # optional convenience only
```

网络源不是"唯一真实来源"。

------------------------------------------------------------------------

# 10. 标准数据 Schema

最低：

``` text
date
symbol
open
high
low
close
volume
```

可选：

``` text
adj_close
dividend
split_factor
```

内部推荐 long format：

``` text
date | symbol | open | high | low | close | volume | adj_close
```

必须检查：

-   duplicate date-symbol
-   missing symbol
-   invalid dates
-   non-positive prices
-   negative volume
-   NaN execution price
-   timezone/calendar issues
-   suspicious extreme returns

不要静默修复所有异常。

------------------------------------------------------------------------

# 11. Offline Sample Data

创建：

``` text
scripts/make_sample_data.py
```

生成至少：

``` text
AAPL
TSLA
SPY
+ 5 个 synthetic symbols
```

约 5 年 daily OHLCV。

数据必须 deterministic，由 random seed 固定。

应包含可测试的特殊情况：

-   正常上涨/下跌段；
-   缺失 bar；
-   `volume=0`；
-   某些不可交易日；
-   已知价格序列供手算。

**所有核心测试和官方 example 必须无网可运行。**

------------------------------------------------------------------------

# 12. Trading Calendar / Time

日频 V1 使用 NYSE calendar。

必须区分：

``` text
decision timestamp
execution timestamp
valuation timestamp
```

默认：

``` text
t close:
    data through t becomes observable
    strategy generates target weights

t+1 open:
    broker executes orders
```

不能把"代码循环到哪一行"当作时间模型。

------------------------------------------------------------------------

# 13. No-Look-Ahead

这是系统最高优先级测试之一。

`MarketDataView` 在 `dt` 时只能提供截至 `dt` 允许看到的数据。

策略不得获得完整 DataFrame 后自己切片。

必须测试：

``` text
未来某天制造巨大价格跳变
→ 当前日期的 strategy output 不得受它影响
```

禁止默认：

``` text
read t close
→ calculate signal
→ fill at same t close
```

未来如果支持 `same_close`，必须显式配置，并在报告中高亮 warning。

------------------------------------------------------------------------

# 14. Strategy Contract

每个策略文件提供：

``` python
STRATEGY_META = {
    "name": "...",
    "version": "...",
    "description": "...",
}
```

并实现：

``` python
class Strategy(BaseStrategy):

    def warmup_bars(self) -> int:
        return 0

    def generate_target_weights(
        self,
        dt,
        data,
        ctx,
    ) -> dict[str, float] | None:
        ...

def build_strategy(params: dict) -> Strategy:
    return Strategy(params)
```

`None` 表示本时点不产生新的 rebalance instruction。

Target weights 第一版：

``` text
0 <= each weight <= 1
sum(weights) <= 1
```

不允许：

``` text
NaN
inf
negative weights
unknown symbol
gross exposure > configured maximum
```

------------------------------------------------------------------------

# 15. AI 生成 Strategy 的安全边界

AI/Codex 新建策略时：

允许：

-   使用 `data` 提供的历史数据；
-   使用只读 `ctx`；
-   读取 params；
-   返回 target weights。

禁止：

-   requests / HTTP / yfinance 等自行拉数；
-   直接写 portfolio.cash；
-   直接改 positions；
-   自己创建 fills；
-   自己扣 commission；
-   自己模拟 slippage；
-   访问 `dt` 之后数据；
-   import engine 私有实现；
-   修改回测配置来让结果变好。

以后每个真实研究策略的文件头必须说明：

``` text
Strategy Name
Idea
Exact Mathematical Rule
Universe
Selection Rule
Portfolio Construction
Decision Time
Execution Time
Required Data
Parameters
Look-ahead Protection
Known Limitations
```

但 V1 的固定权重 example 不需要制造额外研究逻辑。

------------------------------------------------------------------------

# 16. Strategy Validator

命令：

``` bash
quantlab strategies validate strategies/<name>.py
```

至少检查：

-   import 成功；
-   `STRATEGY_META` 存在；
-   `build_strategy` 存在；
-   能实例化；
-   符合 BaseStrategy；
-   `warmup_bars()` 合法；
-   `generate_target_weights()` 存在；
-   禁止的网络/data-provider import；
-   禁止 engine-private import；
-   基本 target-weight validation。

验证通过后才建议运行正式回测。

------------------------------------------------------------------------

# 17. Target Weight → Order

假设：

``` text
equity = $100,000
AAPL target = 50%
TSLA target = 50%
```

先得到：

``` text
target_notional = target_weight × current_equity
```

在 execution price 已知后计算整数目标股数。

若不允许 fractional shares：

``` text
target_qty = floor(target_notional / estimated_execution_price)
```

然后：

``` text
order_qty = target_qty - current_qty
```

必须考虑：

-   slippage；
-   commission；
-   residual cash；
-   integer rounding；
-   sell-before-buy（未来 rebalance 时）；
-   cash constraint。

由于费用，不能简单把 100% notional 全部买完后再让现金变负。

------------------------------------------------------------------------

# 18. Order / Fill

Order：

``` text
order_id
created_at
execution_date
symbol
side
quantity
order_type
reference_price
status
reject_reason
```

Fill：

``` text
fill_id
order_id
timestamp
symbol
quantity
fill_price
commission
slippage_cost
```

状态至少：

``` text
pending
filled
cancelled
rejected
```

------------------------------------------------------------------------

# 19. Commission

统一接口：

``` python
class CommissionModel:
    def calculate(self, quantity, price) -> float:
        ...
```

V1：

## ZeroCommission

``` text
0
```

## PerShareCommission

``` text
max(minimum_fee, abs(quantity) * per_share_fee)
```

## BpsCommission

``` text
abs(quantity * price) * bps / 10000
```

全部单元测试。

------------------------------------------------------------------------

# 20. Slippage

统一接口：

``` python
class SlippageModel:
    def execution_price(
        self,
        side,
        reference_price,
        quantity,
        market_data,
    ) -> float:
        ...
```

V1：

## ZeroSlippage

``` text
fill = reference
```

## FixedBpsSlippage

Buy：

``` text
fill = reference * (1 + bps / 10000)
```

Sell：

``` text
fill = reference * (1 - bps / 10000)
```

------------------------------------------------------------------------

# 21. 不可成交情况

默认规则：

-   execution bar 不存在 → 不成交；
-   `volume <= 0` → 默认取消并记录；
-   execution price NaN / inf / `<=0` → 不成交；
-   不允许用未来价格补成交；
-   资金不足 → 按确定性规则缩量或 reject；
-   所有 cancelled/rejected order 写入日志与报告。

这些行为必须有测试。

------------------------------------------------------------------------

# 22. Portfolio

Portfolio 保存：

``` text
cash
positions
market_value
equity
weights
realized_pnl
unrealized_pnl
```

Position：

``` text
symbol
quantity
average_cost
last_price
market_value
unrealized_pnl
```

每日保存 snapshot。

核心恒等式：

``` text
equity = cash + sum(position market values)
```

必须持续验证。

------------------------------------------------------------------------

# 23. Corporate Actions / Adjusted Prices

V1 优先使用可靠的 adjusted research data。

必须明确：

-   signal 用 raw 还是 adjusted；
-   valuation 用 raw 还是 adjusted；
-   dividend 如何处理；
-   split 如何处理。

禁止 double counting：

``` text
adjusted price 已包含 dividend effect
+
再次手工加 dividend
```

如果数据源不能可靠处理 corporate actions，报告必须说明限制。

------------------------------------------------------------------------

# 24. Universe / Survivorship Bias

V1 可以使用固定 symbol list。

例如：

``` yaml
universe:
  symbols: [AAPL, TSLA]
```

这是诚实的"小池研究"。

未来做历史指数成分或全市场选股时，需要 point-in-time universe。

如果用户使用"今天的指数成分股"回测过去，报告必须警告：

``` text
Potential survivorship bias:
current constituent list is being used historically.
```

------------------------------------------------------------------------

# 25. Benchmark

默认可设：

``` text
SPY
```

Benchmark：

-   同一日期范围；
-   同一 calendar；
-   对齐 returns；
-   单独构造 benchmark curve；
-   用于 alpha / beta / information ratio。

------------------------------------------------------------------------

# 26. Backtest Engine 事件顺序

每日逻辑必须显式：

``` text
1. Advance clock
2. Make permitted market data observable
3. Update valuation
4. If decision event:
       call strategy
       validate target weights
       create pending target
5. If execution event:
       convert target to orders
       apply execution model
       apply slippage
       apply commission
       update cash / positions
6. Mark portfolio
7. Record daily snapshot
```

不要让事件顺序散落在代码中。

------------------------------------------------------------------------

# 27. BacktestResult

统一返回：

``` python
BacktestResult(
    equity_curve=...,
    returns=...,
    positions=...,
    orders=...,
    fills=...,
    benchmark=...,
    metrics=...,
    warnings=...,
    metadata=...,
)
```

Analytics / Report 只消费结果，不重新运行 Strategy。

------------------------------------------------------------------------

# 28. V1 Metrics

指标键名固定，避免后续报告和实验脚本反复改接口。

至少：

``` text
total_return
cagr
ann_vol
sharpe
sortino
max_drawdown
max_dd_duration_days
calmar
turnover_ann
avg_gross_exposure
avg_cash_weight
beta
alpha_ann
tracking_error
information_ratio
n_orders
n_fills
total_commission
total_slippage_cost
total_transaction_cost
```

## 28.1 Total Return

``` text
V_T / V_0 - 1
```

## 28.2 CAGR

``` text
(V_T / V_0)^(1 / years) - 1
```

## 28.3 Annualized Volatility

``` text
std(daily returns) * sqrt(252)
```

## 28.4 Sharpe

``` text
mean(daily excess return) / std(daily excess return) * sqrt(252)
```

## 28.5 Max Drawdown

``` text
running_max_t = max(V_0 ... V_t)
drawdown_t = V_t / running_max_t - 1
MDD = min(drawdown_t)
```

还要记录：

``` text
peak_date
trough_date
recovery_date
duration
```

不要为了指标数量而牺牲定义准确性。

------------------------------------------------------------------------

# 29. 不强制虚假的 Trade Win Rate

V1 的固定权重 buy-and-hold 不适合强行定义大量 round-trip trade
statistics。

因此：

-   orders / fills / turnover / costs 必须准确；
-   round-trip `win_rate`、profit factor、average holding period
    可以等以后定义清楚交易配对规则后再加入。

不要为了报告好看而输出语义不可靠的数字。

------------------------------------------------------------------------

# 30. Automatic Report

每次成功回测自动生成：

``` text
report.html
```

## 30.1 Summary

``` text
Run ID
Strategy
Start / End
Initial Cash
Final Equity
Benchmark
Data Provider
Price Policy
Decision Timing
Execution Timing
Commission
Slippage
Universe
Git Commit
```

## 30.2 Headline Metrics

显示 V1 metrics。

## 30.3 Charts

至少：

1.  Strategy equity curve
2.  Strategy vs benchmark
3.  Drawdown
4.  Underwater
5.  Rolling volatility
6.  Rolling Sharpe
7.  Monthly return heatmap
8.  Yearly returns
9.  Cash weight / invested exposure
10. Transaction costs over time

图表标题默认英文，降低服务器字体问题。

## 30.4 Audit Section

必须写：

``` text
decision timing
execution timing
price adjustment policy
commission assumption
slippage assumption
fractional-share policy
missing-data policy
universe source
survivorship warning
look-ahead protection
```

## 30.5 Reproduction Command

报告必须给出可复制命令：

``` bash
quantlab backtest run \
    --strategy ... \
    --config ...
```

------------------------------------------------------------------------

# 31. Run Archive

每次运行建立：

``` text
runs/<YYYYMMDD_HHMMSS>_<strategy>_<hash6>/
```

至少保存：

``` text
config.snapshot.yaml
strategy.snapshot.py
summary.json
metrics.json
equity.csv
returns.csv
positions.parquet
orders.csv
fills.csv
benchmark.csv
warnings.json
report.html
logs.txt
metadata.json
```

历史 run 不覆盖。

------------------------------------------------------------------------

# 32. Reproducibility

相同：

``` text
code
data
config
seed
```

必须产生相同结果。

metadata 至少保存：

``` text
run_id
timestamp
strategy name/version
git commit
python version
package versions
data fingerprint
random seed
```

------------------------------------------------------------------------

# 33. Logging / Errors

日志写 console + run `logs.txt`。

重要事件：

``` text
run start/end
resolved config
data warnings
strategy validation
decision events
orders
rejections/cancellations
report generation
elapsed time
```

异常建议：

``` text
InvalidConfigError
DataUnavailableError
InvalidStrategyOutputError
InsufficientHistoryError
InsufficientCashError
ExecutionError
```

禁止静默吞异常。

------------------------------------------------------------------------

# 34. Testing Philosophy

测试必须和模块一起写。

## 34.1 Commission

``` text
100 shares * $0.005 = $0.50
minimum = $1
expected = $1
```

## 34.2 Slippage

``` text
reference = 100
slippage = 10 bps

buy = 100.10
sell = 99.90
```

## 34.3 Drawdown

``` text
100 → 120 → 90 → 110 → 130
MDD = 90 / 120 - 1 = -25%
```

## 34.4 Portfolio Accounting

每个日期验证：

``` text
equity == cash + market_value
```

## 34.5 No Look-Ahead

未来价格变化不得改变过去的 strategy decision。

## 34.6 Reproducibility

同一输入运行两次：

``` text
equity equal
orders equal
fills equal
metrics equal
```

------------------------------------------------------------------------

# 35. 对 50/50 AAPL/TSLA Example 的专门验收

使用一小段完全手工构造的 synthetic data，例如：

``` text
Initial cash = 100,000

Decision date:
AAPL close = known
TSLA close = known

Next open:
AAPL open = 100
TSLA open = 200
```

在 zero-cost 模式下，人工计算应该买多少整数股、剩多少 cash。

然后分别打开：

``` text
commission
slippage
```

重新手算 expected result。

测试必须验证：

``` text
order quantities
fill prices
commission
slippage cost
cash after fills
position quantities
end-of-day market value
equity
```

这条测试是 V1 最重要的 end-to-end accounting test。

------------------------------------------------------------------------

# 36. AGENTS.md

根目录必须创建，并至少包含：

``` text
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
```

------------------------------------------------------------------------

# 37. strategies/README.md

必须告诉未来 AI：

1.  从 `_template.py` 开始；
2.  先写清楚策略定义；
3.  只能使用允许的 `data` 和 `ctx`；
4.  返回 target weights；
5.  不碰 engine；
6.  不自己拉数据；
7.  不看未来；
8.  创建策略后先运行：

``` bash
quantlab strategies validate <strategy.py>
```

9.  用户没有要求时，不替用户"改进"策略；
10. 回测差不代表可以自动改规则。

------------------------------------------------------------------------

# 38. factors/README.md

只写类似：

``` text
This directory is intentionally empty in V1.

It is reserved for reusable research factors that the user has explicitly
defined, understood, validated, and approved.

Codex must not populate this directory with momentum, volatility, RSI,
value, quality, technical, or other research factors unless explicitly
requested by the user.

Generic deterministic mathematical utilities belong in src/quantlab/utils/.
```

V1 不再添加其他文件。

------------------------------------------------------------------------

# 39. README

README 中文为主，代码/字段英文。

至少包含：

-   项目定位；
-   安装；
-   30 秒离线 quick start；
-   sample data；
-   config；
-   strategy contract；
-   如何运行 50/50 example；
-   commission/slippage；
-   execution timing；
-   report；
-   reproducibility；
-   known limitations；
-   survivorship bias；
-   如何让 AI 新建策略；
-   V2 roadmap；
-   research disclaimer。

------------------------------------------------------------------------

# 40. 分阶段 Codex 实施计划

## Phase 0 --- Skeleton / CLI

实现：

``` text
repo
pyproject
src layout
AGENTS.md
README skeleton
CLI
pytest
```

验收：

``` bash
pip install -e .
quantlab --help
pytest
```

全部成功。

不要实现完整引擎。

## Phase 1 --- Config + Offline Data

实现：

``` text
Pydantic config
CSV provider
Parquet provider
schema
validator
calendar
sample-data generator
```

Yahoo provider 可以做简单 adapter，但测试不得依赖网络。

验收：

-   sample data 可生成；
-   可读成标准 panel；
-   unknown config field 报错；
-   invalid price/volume 有 warning/error。

## Phase 2 --- MarketDataView + Strategy Contract

实现：

``` text
MarketDataView
BaseStrategy
Context
loader
validator
_template.py
fixed_weight_buy_and_hold.py
```

验收：

``` bash
quantlab strategies validate strategies/fixed_weight_buy_and_hold.py
```

成功。

并通过 no-look-ahead test。

## Phase 3 --- Ledger + Costs + Execution

实现：

``` text
Position
Portfolio
Order
Fill
Broker
Commission
Slippage
TargetWeight -> Orders
```

使用手工 synthetic prices 做精确测试。

## Phase 4 --- Backtest Engine

连接：

``` text
Clock
Data
Strategy
Execution
Portfolio
```

只跑唯一官方策略：

``` text
50% AAPL
50% TSLA
buy once
hold
```

验收：

-   zero-cost 手算完全对齐；
-   commission 模式对齐；
-   slippage 模式对齐；
-   signal date / fill date 正确错开；
-   不产生意外负现金。

## Phase 5 --- Metrics

实现 V1 指标。

每个核心指标有 hand-calculated tests。

## Phase 6 --- Automatic Report + Run Archive

生成：

``` text
report.html
run snapshots
metrics
orders/fills
warnings
reproduction command
```

验收：

-   HTML 可打开；
-   关键指标存在；
-   execution assumptions 明确；
-   策略源码和 config 已冻结。

## Phase 7 --- V1 Hardening

完成：

-   README；
-   strategies README；
-   factors README；
-   error messages；
-   offline quick start；
-   reproducibility；
-   full pytest；
-   clean installation test。

**到此 V1 完成。**

------------------------------------------------------------------------

# 41. V2 Roadmap（现在不实现）

V1 稳定后再讨论：

## Research strategies

只有用户明确提出并确认策略定义后才新增。

## Factor library

只有用户已经理解、验证并希望复用某些 factor 后才设计正式 Factor API。

## Robustness / Optimization

优先顺序：

``` text
out-of-sample
walk-forward
transaction-cost sensitivity
parameter sensitivity
start-date sensitivity
subperiod analysis
universe sensitivity
```

之后才考虑 grid search / Optuna。

禁止：

``` text
在完整历史上搜最佳参数
→ 再把同一段历史当作最终成绩
```

## Point-in-time universe

做历史指数/全市场研究前再正式加入。

## Advanced execution

之后再考虑：

``` text
short
borrow cost
leverage
volume participation
limit orders
intraday
paper trading
live adapters
```

------------------------------------------------------------------------

# 42. V1 最终验收清单

-   [ ] `pip install -e .` 成功
-   [ ] `quantlab --help` 成功
-   [ ] `pytest` 全部通过
-   [ ] 无网可以生成 sample data
-   [ ] CSV / Parquet 可以加载
-   [ ] Pydantic unknown fields 报错
-   [ ] MarketDataView 防未来数据
-   [ ] Strategy validator 可运行
-   [ ] Strategy 不能自行下载数据
-   [ ] Strategy 不能直接修改 portfolio
-   [ ] 唯一官方 example 是 50% AAPL / 50% TSLA buy-and-hold
-   [ ] 没有未经用户要求的 SMA/momentum/RSI 等 example
-   [ ] `factors/` 没有未经用户批准的研究因子
-   [ ] target weights 校验正确
-   [ ] `t close -> t+1 open` 默认时序正确
-   [ ] integer-share conversion 正确
-   [ ] commission 正确
-   [ ] slippage 正确
-   [ ] cash accounting 正确
-   [ ] position accounting 正确
-   [ ] zero-volume / missing execution bar 有明确处理
-   [ ] benchmark 对齐正确
-   [ ] CAGR / Sharpe / Sortino / MDD / Calmar 等有测试
-   [ ] turnover / exposure / costs 有输出
-   [ ] 自动生成 HTML report
-   [ ] 报告含 audit assumptions
-   [ ] 报告含 reproduction command
-   [ ] 每次 run 不覆盖历史结果
-   [ ] 保存 strategy snapshot
-   [ ] 保存 resolved config
-   [ ] 保存 git commit / versions / data fingerprint / seed
-   [ ] 同一输入可复现
-   [ ] README 可以让新环境从零跑通

------------------------------------------------------------------------

# 43. 第一次直接交给 Codex 的 Prompt

把本文件放在 repo 根目录，然后给 Codex：

``` text
Read this project specification in full before changing any files.

Implement Phase 0 only.

Create:
- the repository skeleton;
- src/quantlab package layout;
- pyproject.toml;
- dependency configuration;
- .gitignore and .env.example;
- AGENTS.md;
- README skeleton;
- Typer CLI skeleton;
- pytest setup.

Important constraints:
- Do not implement the full backtest engine yet.
- Do not create SMA, momentum, RSI, value, quality, or any other research
  strategy examples.
- The only future V1 example strategy will be a fixed-weight buy-and-hold:
  50% AAPL and 50% TSLA, bought once and then held.
- You may create the empty factors/ directory and its README, but do not
  populate it with research factors.
- Do not add a third-party backtesting framework.
- Do not implement optimization, walk-forward, live trading, dashboards,
  databases, Docker, or intraday features.
- Keep tests offline.

When Phase 0 is finished:
1. run the tests;
2. show exactly what files were created;
3. report test results;
4. list assumptions and unresolved issues;
5. state what Phase 1 will contain.

Do not proceed to Phase 1 until explicitly instructed.
```

Phase 0 人工检查通过后，再说：

``` text
Implement Phase 1 only.
```

依次推进。

------------------------------------------------------------------------

# 44. 研究纪律

这个系统的目的不是制造漂亮的历史收益曲线，而是建立一个以后能信任的实验环境。

以后任何真实策略都必须能回答：

``` text
What exactly is the rule?
What information was available at decision time?
When was the trade executed?
What universe was used?
How were missing/untradable securities handled?
What commission and slippage were assumed?
What benchmark was used?
Was the result in-sample or out-of-sample?
How sensitive is it to costs and parameters?
Can the exact run be reproduced?
```

AI 的职责是**忠实实现用户的研究定义**，不是自动把策略改到历史表现最好。

最终原则：

``` text
先把规则写清楚
→ 再防止未来数据
→ 再把成交和账本算对
→ 再算指标
→ 再自动报告
→ 再谈策略研究
→ 最后才谈优化
```
