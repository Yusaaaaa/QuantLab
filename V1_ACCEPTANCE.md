# V1 实施与验收记录

日期：2026-09-18。工作目录：`/Users/yusa/ChatGPTWorkSpace/QuantLab`。
用户授权继续完成全部阶段；未改动原始工作文档。

## 阶段验收

| 阶段 | 完成内容 | 阶段门禁结果 |
| --- | --- | --- |
| Phase 0 | src layout、依赖、CLI 骨架、项目约定 | 11 tests passed（此前已验收） |
| Phase 1 | 严格配置、CSV/Parquet、NYSE 日历、数据校验、离线样本 | 31 tests passed；样本生成与读取通过 |
| Phase 2 | 截断历史视图、只读 Context、策略合同、validator、唯一官方示例 | 51 tests passed；CLI validator 成功 |
| Phase 3 | Position/Portfolio、Order/Fill、费用、滑点、现金约束 | 65 tests passed；手算费用/滑点/账本通过 |
| Phase 4 | 显式 open/close 事件循环、策略与成交解耦 | 73 tests passed；零费用/佣金/滑点 E2E 通过 |
| Phase 5 | 20 项标准指标、回撤、基准、rolling | 81 tests passed；手算及未定义指标边界通过 |
| Phase 6 | HTML、10 张图、完整快照、日志、归档、复现命令 | 83 tests passed；生成五年示例报告 |
| Phase 7 | 文档、错误信息、离线限制、源码缓存/归档失败/配置歧义修复、锁定依赖、干净安装 | **113 tests passed**，无 warnings |

Phase 6 的 HTML 自动渲染视觉检查未完成：内置浏览器安全策略拒绝本地 file:// URL。
未尝试通过其他浏览器或本地代理绕过。报告文件、10 张内嵌 PNG、关键指标、审计文字和复现命令已做自动检查；
图表由本地 matplotlib 生成。此限制不影响 CLI 回测或浏览器手动打开报告，但不能声称已完成页面视觉验收。

## 最终工程验证

- 开发环境：Python 3.12.14；editable install 成功；quantlab --help 成功。
- pytest：113 passed；autouse fixture 禁止 socket connect / connect_ex / create_connection。
- pip check：No broken requirements found。
- Ruff：Python 文件格式化完成，F 类检查全部通过。格式化工具置于临时目录，没有增加运行依赖。
- 构建 wheel 成功，包含 Jinja HTML 模板。
- 用全新临时虚拟环境、`--no-index` 和本地 wheelhouse 安装固定依赖与 wheel，确认导入来自 site-packages。
- 干净环境中同样 113 tests passed，CLI help / strategy validator 成功，五年离线示例生成 HTML。
- 清洁安装执行记录在本地 `validation/clean-install.log`（不纳入 Git）。复核脚本为 `scripts/check_clean_install.py`。

## 关键验收证据

| 要求 | 实现 / 验证 |
| --- | --- |
| 无未知配置字段、无重复 YAML 键 | config.py；test_config.py / test_hardening.py |
| 8 个符号、约 5 年 deterministic synthetic 数据 | data/sample.py；test_data.py；无真实行情含义 |
| CSV / Parquet 标准 long panel | 两个 local provider；相同精度读写比较 |
| NYSE 日期、节假日与提前收盘 | exchange_calendars XNYS；7 月 4 日休市和 7 月 3 日提前收盘测试 |
| 不静默修复异常数据 | validator；重复/无效值/缺失股票/非交易日均明确失败或按政策告警 |
| 策略不能拿到未来行 | MarketDataView 物理截断副本；未来跳价不改变过去观察、输出或成交 |
| 策略上下文只读 | frozen dataclass + MappingProxyType；变更原始持仓 dict 不影响 Context |
| 不在策略下载或触碰引擎 | 加载前 AST 合同检查；网络/provider/engine 导入被拒绝；不是恶意代码沙箱 |
| 仅唯一官方 50/50 买入持有策略 | strategies 中只有官方示例与无动作模板；factors 中只有 README |
| t close → next session open | 显式 Clock/open/close；UTC 时间戳；信号与成交日期错开测试 |
| 整数股、手续费、滑点、残余现金 | test_execution.py / test_engine.py 的四组独立手算 |
| 先卖后买、持仓省略即清仓 | Broker；卖出后才分配买入现金 |
| 无负现金、账本身份 | Portfolio 持续检查；买入费用进入成本，卖出实现损益 |
| 不可成交、持仓缺失估值 | 取消并记原因；已持有证券 missing bar 用 last mark 并告警；不自动重试 |
| 基准对齐 | 严格完整 NYSE session，缺失 benchmark 不允许静默补齐 |
| 20 个稳定指标键名 | performance.py；core hand-calculated tests；N/A 不冒充有效比率 |
| 报告审计假设与 10 图 | builder + plots + HTML template；嵌入图片和必需内容测试 |
| 不覆盖历史运行 | 原子 mkdir + collision suffix；重复运行得到不同目录 |
| 冻结全部输入和实现 | config / strategy / raw panel / code snapshot / package versions / fingerprints |
| 保存元数据与错误 | Git 状态、Python、依赖、seed、数据/策略/引擎 hash；失败日志与 failure.json |
| 相同输入可复现 | equity / orders / fills / positions / metrics 比较；删除原 CSV 后仍可由快照复现 |
| 防止归档失败误标成功 | manifest 写入后原子发布 metadata.json；注入写入失败测试 |
| 完整中文 README 和策略指引 | 安装、离线 quick start、合同、指标、政策、限制、复现、V2 roadmap |

## 独立手算锚点

初始现金 $100,000；下一 open：AAPL=$100、TSLA=$200。

| 模式 | AAPL 实际买入 | TSLA 实际买入 | 现金余额 | 总手续费 | 总滑点成本 |
| --- | ---: | ---: | ---: | ---: | ---: |
| zero cost | 500 | 250 | 0 | 0 | 0 |
| 每股 $0.005，最低 $1 | 500 | 249 | 196.255 | 3.745 | 0 |
| 10 bps 滑点 | 499 | 249 | 200.30 | 0 | 99.70 |
| 手续费 + 10 bps 滑点 | 499 | 249 | 196.56 | 3.74 | 99.70 |

已用 AAPL close=$110、TSLA close=$210 等固定后续价格验证日终权益。
手续费模式中 TSLA 请求 250 股，但现金约束缩为 249；按字母顺序分配是显式政策。

## 已知边界与保留项

- 所有示例为 synthetic 数据，不能拿示例结果评价 AAPL/TSLA 的历史表现。
- 复权研究单位不等于历史 raw share 数量；公司行动不重复入账，raw 公司行动不支持。
- 日终 volume 仅作零成交量的执行代理，非真实开盘时已知流动性；报告明确披露。
- 固定 universe 仍有选择/存活偏差；未实现 point-in-time 成分库。
- Validator 不是 OS 沙箱，仅运行经过审阅的可信策略 Python。
- Yahoo adapter 可选，未联网验收；核心功能与测试无网络依赖。
- 页面自动视觉验收受浏览器安全策略限制，已如实保留；没有未披露的报告检查结论。
- 未实施 V2 的策略/因子、优化、walk-forward、broker、web dashboard、数据库等功能。
