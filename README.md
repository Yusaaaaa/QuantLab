# QuantLab 2026.10.22

本版本包含 Python 日线回测引擎、Tauri 桌面工作台、现有简单策略/因子、离线测试及中英文手册。

- 版本：`2026.10.22`；Git 标签：`v2026.10.22`。
- [项目本体与独立研究的边界](PROJECT_SCOPE.md)
- [本次审查与验证记录](AUDIT_2026.10.22.md)
- [版本说明](RELEASE_NOTES.md)
- [中文手册](project_manual/cn/quantlab_manual_cn.pdf) / [English manual](project_manual/en/quantlab_manual_en.pdf)

GitHub 版本包含 `strategies/` 和 `factors/`。`researchProject/` 独立研究、真实行情、运行档案、环境和构建产物留在本地；克隆后先生成合成 sample，再运行基础示例。指向真实历史 Parquet 的 2020–2025 配置需要自行准备对应数据，不能直接在空数据目录运行。桌面 App 也需本地构建或使用现有构建副本，并依赖工作区 Python 环境。

本地、可审计、可复现的美股日频研究回测系统。V1 已实现数据 → 策略 → 成交 →
账本 → 指标 → HTML 报告 → 实验归档。规格见 [工作文档 V4](us_equity_quant_lab_codex_workdoc_v4.md)。
正确性 > 可审计性 > 可复现性 > 易用性 > 性能 > 功能数量。

## 安装

Python 3.12+，建议新建虚拟环境。已验证环境为 Python 3.12.14 / macOS arm64。
Python 3.9 不适用；克隆后需创建自己的 `.venv`。

```bash
cd /path/to/QuantLab
python3.12 -m venv .venv
source .venv/bin/activate
python -m pip install -r requirements.lock
python -m pip install -e '.[dev]'
quantlab --help
pytest
```

首次安装依赖需网络或预先准备的 wheel 缓存；安装后的核心运行与测试完全离线。
`requirements.lock` 固定本次验收的依赖版本；跨系统需有对应平台的可用安装包。
NumPy 限制为 `<2.4`，避开 pandas 2.x 与 NumPy 2.5 的 timedelta 弃用兼容问题。
本机虚拟环境使用 Codex 提供的 Python runtime；若移动或删除该 runtime，需用独立 Python 3.12+ 重建环境。

## 30 秒离线 quick start（已完成安装后）

```bash
cd /path/to/QuantLab
source .venv/bin/activate
python scripts/make_sample_data.py
quantlab strategies validate strategies/fixed_weight_buy_and_hold.py --config configs/examples/fixed_weight_buy_and_hold.yaml
quantlab backtest run --strategy strategies/fixed_weight_buy_and_hold.py --config configs/examples/fixed_weight_buy_and_hold.yaml
```

命令会打印本次 `runs/<run_id>/` 和 `report.html` 路径。

```bash
quantlab report open <run_id>
```

也可直接用浏览器打开报告文件。HTML 内嵌全部图片，无外部脚本、字体或 CDN。
`report open` 默认从当前目录的 `runs/` 查找，可使用 `--runs-dir /absolute/path`。

## 离线 sample data

生成 2020–2024 年 NYSE 交易日数据，共 AAPL、TSLA、SPY、SYN1–SYN5 八个名称。
**所有价格都是人工模拟，绝非上述股票的真实行情，示例收益没有投资含义。**
固定 seed=42 包含上涨/下跌区段；SYN1 缺失 bar、SYN2 零成交量、SYN3 缺失开盘价。
`data/raw/sample.csv` 与 `sample.parquet` 使用同一精度；生成器还保存手算用的 `known_prices.csv`。

```bash
python scripts/make_sample_data.py --seed 42 --output-dir data/raw
python scripts/validate_data.py configs/default.yaml
```

NYSE 日历使用 [exchange_calendars 官方项目](https://github.com/gerrymanoim/exchange_calendars)，
包含节假日、提前收盘和 UTC 开收盘时间。每日 `date` 是不带时区的交易日标签；
决策/成交/估值 timestamp 则带 UTC 时区。

## Configuration

参考 `configs/default.yaml` 和唯一官方示例配置。Pydantic v2 的 `extra=forbid`
适用于所有配置段，未知字段、无效日期范围、非有限费用参数会报错。
优先级：CLI `--strategy` > YAML > 默认值。数据/策略/输出相对路径均相对于 YAML 文件所在目录；
CLI 显式策略路径相对于当前工作目录。程序接口为 `load_config()`、`run_backtest()` 和 `archive_run()`。

支持 `csv_local`、`parquet_local`；输入是 long-format：

```text
date,symbol,open,high,low,close,volume,adj_close
```

`adjusted` 模式必须有 `adj_close`；用 `adj_close / raw_close` 同步缩放 OHLC，不再额外入账分红/拆股。
成交量保留源数据值，整数股代表复权研究单位，不是当年的原始持股数量。
`raw` 模式是未处理公司行动的价格研究；若输入声明非零 dividend 或 split_factor 非 0/1，直接拒绝。
原始数据源漏报公司行动仍可能导致偏差。

可选联网 adapter：安装 `pip install -e '.[online]'`，显式设置 `data.provider: yahoo`
及真实的 `data.source` 描述。Yahoo 非权威唯一来源，未进行联网验收；回测会冻结下载的实际输入。
策略本身不得下载数据。

## 唯一官方策略与合同

`strategies/fixed_weight_buy_and_hold.py` 首次满足当前已知可交易条件时返回
`AAPL=0.5, TSLA=0.5`，之后始终返回 `None`，不主动再平衡、不自动重试取消订单。
因整数股、费用和滑点，实际仓位有误差并可能留有现金。

```python
STRATEGY_META = {"name": "...", "version": "...", "description": "..."}

class Strategy(BaseStrategy):
    def warmup_bars(self) -> int:
        return 0

    def generate_target_weights(self, dt, data, ctx) -> dict[str, float] | None:
        ...

def build_strategy(params: dict) -> Strategy:
    return Strategy(params)
```

`None` 不产生指令；空 dict 表示清仓；未包含的持仓目标为零。
权重必须有限、非负、在 universe 内，且不超过单股/总敞口限制。
这些限制约束目标权重；价格变动后的权重漂移不会触发强制交易。
`rebalance_schedule` 为 daily / weekly / monthly，指每交易日/每周首个交易日/每月首个交易日的决策资格；
策略输出 `None` 仍不成交。warmup 只累计所选回测区间内的可观测 bar，全部不足时报错。

`data.history(symbol, bars=None, end=None)` 返回截止决策时点的副本；`data.current(symbol)`
返回当前 bar 或 None。数据视图不保留未来行，日内请求完整当日日线会被拒绝。
`ctx` 提供只读 cash、equity、positions、universe、seed；修改返回的历史副本不会改变引擎。

Validator 在导入前检查网络、数据源、引擎私有导入及常见文件 I/O，验证元信息、实例类型、warmup 和基础输出。
**它是可信 Python 策略的合同检查，不是运行恶意代码的系统沙箱。**
完整参数下的权重每次决策仍会运行时校验；自定义参数可经 `--config` 传给 validator。

## 时间、订单与账本

1. 当日 open：执行上一交易日 close 产生的 pending target。
2. 按当日 open 标记已有持仓，冻结用于转换目标金额的 equity。
3. 按滑点价格计算整数目标股数；先卖出，再按股票代码字母顺序买入。
4. 买入数量以现金及手续费确定性缩量；未成交余量取消，不允许负现金。
5. 当日 close：估值、生成只读历史视图、调用策略、保存日终 snapshot。

开盘价、当日收盘价和策略可用历史严格分离。V1 不支持 same_close。
订单保留请求数量、实际数量、状态和原因；成交保存 reference 关联、价格、费用与滑点成本。
买入手续费进入 average_cost，卖出净收入计算 realized_pnl；持续校验
`equity = cash + market_value = initial_cash + realized_pnl + unrealized_pnl`。

- commission：zero、per_share（最低费）、bps；零成交数量不扣最低费。
- slippage：zero、bps；买入加价、卖出减价。已体现在成交价，绝不重复扣现金。
- 缺失 execution bar、无效 open、volume=0：取消，不借未来价格补成交。
- 缺失持仓当日 bar：最后已知价格估值并逐日告警；缺失 benchmark bar：失败。
- 非法价格、负成交量、重复 date-symbol、非交易日、缺少股票：明确失败。
- 末日 pending target 取消；期末持仓不强制卖出。

每日最终 volume 仅作为零成交量的可成交标记，这是工作文档规定的日线模型假设；
它在真实开盘时尚未知，不能理解成盘中流动性仿真，也不用于成交量比例下单。

## 指标与报告

输出 total_return、CAGR、波动率、Sharpe、Sortino、MDD、回撤时长、Calmar、换手、
平均敞口/现金、beta、alpha、tracking error、information ratio、订单/成交数和成本。
首个交易日 close 是现金基线，日收益统计不包含其占位零收益；CAGR 用首末估值日期相差天数 / 365.25。
波动率用样本标准差，Sortino 用所有观测的负超额收益平方均值，回撤持续时间用日历日。
换手采用双边成交额 / 前收盘 equity，并按 252 / 收益区间数年化，不除以二。
无法定义的比率为 `null` / N/A；不会伪造 buy-and-hold 的 round-trip 胜率。
完整公式在报告的 Metric definitions 和 `src/quantlab/metrics/performance.py`。

基准是首个 session close 起的无费用、可分数股买入持有曲线；与策略同日期、同复权政策。
报告包含 10 张图、汇总、全部标准指标、回撤区间、订单审计、警告、运行假设和复现命令。
默认自动生成；`report.enabled: false` 可明确禁用，`open_after_run` 控制是否打开浏览器。

## 实验归档与复现

每个独立目录的名称包含 UTC 时间、策略名称与配置/源码 hash，冲突加后缀，绝不覆盖旧目录。
主要文件：

```text
config.snapshot.yaml      # resolved config；重定向至本次冻结的数据/策略
config.original.json      # 初始解析后的配置
strategy.snapshot.py
data.snapshot.parquet     # 调整前的实际输入 panel，复现无需网络
code.snapshot/            # 当时的 quantlab 源码和可安装项目描述
requirements.snapshot.txt
summary.json / metrics.json / metadata.json / warnings.json
manifest.json             # 文件 SHA-256（不含仍在写入的日志和 manifest 自身）
equity.csv / returns.csv / benchmark.csv / decisions.csv
positions.parquet / orders.csv / fills.csv
report.html / logs.txt / reproduce.sh
```

metadata 保存 Git commit/工作区状态、Python/依赖版本、seed、策略/引擎/数据指纹。
无提交的仓库会诚实记录 `git_commit: null`，代码快照和指纹仍可审计。
`failure.json` 标识失败运行，成功结果只在全部保存完成后记录；失败目录保留错误日志。

同一环境直接 `sh runs/<run_id>/reproduce.sh`；结果会保存到新的 run 目录。
跨环境复现需先在新虚拟环境安装该 run 的 `requirements.snapshot.txt`，再安装
`code.snapshot/`，执行原报告中的命令。快照中的绝对路径针对本机；移动 archive 后需更新
config 的数据/策略/输出路径，保留原快照并另存修改后的配置。

## 测试与验收

```bash
pytest
python -m pip check
```

测试套件禁用 socket 连接，覆盖手算账本/成交/费用/指标、未来价格扰动、只读上下文、
缺失与不可交易数据、配置错误、策略校验、报告归档、原始数据删除后的快照复现。
阶段记录、最终结果及自动视觉检查限制见 `V1_ACCEPTANCE.md`。

## 如何让 AI 新建策略

先提供明确的 Idea、Exact Mathematical Rule、Universe、Selection Rule、Portfolio Construction、
Decision/Execution Time、Required Data、Parameters、Look-ahead Protection、Known Limitations。
要求从 `_template.py` 开始，只使用 data/ctx，返回目标权重，不改引擎，不拉数据。
先运行 validator 再回测；表现差不得自动改规则。详见 `strategies/README.md`。

## Known limitations / 研究纪律

- 仅 long-only、USD、整数股、日线、固定 universe；没有杠杆/做空/真实券商。
- 复权序列可能因后续公司行动修订，不代表 point-in-time 原始行情；整数复权研究单位存在舍入近似。
- 固定股票池有选择与存活偏差，当前指数成分回看历史会明确警告；未实现历史成分数据库。
- 缺失持仓价格采用 stale mark，会影响风险估计；报告逐项披露。
- 不模拟盘口、成交容量、限价单、借券或退市清算；只读视图不是恶意 Python 沙箱。
- 同版本数据和代码可复现；不同平台/依赖的浮点运算不保证逐字节相同。
- 因子目录仅包含用户明确批准的研究特征；不自动添加策略或优化逻辑。

## 后续扩展与当前边界

当前已有用户批准的简单策略/因子、桌面界面；后续独立研究位于本地 `researchProject/`，不属于本次发布的运行时。通用样本外验证、walk-forward、point-in-time universe、高级成交模型、实盘/模拟券商、数据库、分钟数据和自动参数搜索尚未作为本体功能实现。

本项目用于研究与工程验证，不构成投资建议；历史或合成数据结果不保证未来表现。


## 用户追加策略：AAPL / TSLA 每周一等权再平衡

策略：`strategies/weekly_equal_weight_aapl_tsla.py`；配置：`configs/weekly_equal_weight_aapl_tsla_2020_2025.yaml`。
本金 $100,000；2020-01-06 首次建仓；每周一开盘恢复各 50% 的目标，周一休市顺延；结束于 2025-12-31 收盘。
原本地实验使用 Yahoo Finance 真实历史复权数据；该 Parquet 不随仓库分发。准备好配置指定的本地文件后，回测无需联网。
费用沿用每股 $0.005 / 最低 $1，滑点 5 bps。2020-01-03 是准备信号用的纯现金基线，
标准 CAGR 也以此为起点；股数仍是整数复权研究单位，具体限制见前文。

```bash
quantlab strategies validate strategies/weekly_equal_weight_aapl_tsla.py --config configs/weekly_equal_weight_aapl_tsla_2020_2025.yaml
quantlab backtest run --config configs/weekly_equal_weight_aapl_tsla_2020_2025.yaml
```

策略层新增只读 `ctx.next_session_date`，仅暴露已知交易日历，未来行情仍不可见。
此策略的 `rebalance_schedule: daily` 表示每天检查是否需要为下一 session 发出目标；真正目标频率为每周一次。
这是一条用户明确批准的组合再平衡规则，本身不需要 Factor。因子扩展见下一节。


## 用户追加因子与策略：AAPL 周度相对收益反转

因子 `factors/return_spread.py` 独立计算单日/整周的个股收益率减基准收益率；
策略 `strategies/aapl_weekly_relative_reversal.py` **调用周度函数**，并决定买卖。
配置为 `configs/aapl_weekly_relative_reversal_2020_2025.yaml`。

规则：2020-01-06 首次用一半现金买苹果，此后每周一（休市顺延）查看上一完整交易周：
AAPL 复权收益 − SPY 复权收益 < -1 个百分点时，用剩余现金的 50% 买入（预算含手续费）；
> +1 个百分点时卖出 floor(持股数 / 2)；恰好等于阈值或在区间内不交易。
首次建仓优先，不同时根据首周因子加减仓；现金不计利息。终止于 2025-12-31 收盘。
日常检查仍是 daily，但真正决策只有每周一次。

本策略要求显式 `execution.sizing: decision_relative`：把收盘目标权重变化冻结为现金/股数比例，
下一开盘时按该比例计算成交量。这样遇到周末跳空，仍然买半数现金或卖半数股数。
默认 `target_weights` 模式维持原有行为，不变更其他策略的成交定义。
该新增模式目前仅支持一只可交易股票；基准仅供历史观察，不能由本策略买入。

```bash
quantlab strategies validate strategies/aapl_weekly_relative_reversal.py --config configs/aapl_weekly_relative_reversal_2020_2025.yaml
quantlab backtest run --config configs/aapl_weekly_relative_reversal_2020_2025.yaml
quantlab backtest run --config configs/aapl_half_cash_buy_and_hold_2020_2025.yaml
```

配置中的 `strategy.factor_paths` 明确绑定因子源码，loader 校验后加载；不自动扫描因子库。
回测保存 `factors.snapshot/`、`metadata.factor_fingerprints`；`decisions.csv` 的 details 保存
每周因子起止日期、双方收益率、收益差和操作原因。策略只返回权重，不管理账户。
MarketDataView 现在可观察配置股票池加基准的历史，target weights 仍只能包含可交易 universe。
`scripts/audit_weekly_relative_reversal.py <run_dir>` 可独立重算本次规则的全部信号、成交和权益。

## 桌面工作台

Tauri 桌面 App 支持双主题、策略与因子编辑、配置、回测与报告。打开 `dist/QuantLab.app`；操作和构建见 [桌面使用说明](desktop/README.md)。
