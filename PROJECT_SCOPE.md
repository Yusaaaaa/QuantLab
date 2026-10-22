# 项目本体与独立研究的边界 / Project scope

版本：2026.10.22。此清单描述发布范围，不移动、不重命名原有研究和数据。

| 路径 | 归属 | 本次 GitHub 发布 |
|---|---|---|
| `src/quantlab/` | Python 数据、策略合同、引擎、账本、指标、报告、桌面桥接 | 是 |
| `desktop/` | Tauri / React 桌面源码、锁文件、构建所需图标 | 是，排除依赖/构建/自动生成 schema |
| `strategies/` | 惰性模板、买入持有、AAPL/TSLA 周等权、AAPL 周反转 | 是 |
| `factors/` | AAPL/基准日/周收益差纯计算与说明 | 是 |
| `configs/` | 核心和已有策略的运行配置 | 是；真实行情路径需要本地补齐 |
| `tests/`, `scripts/` | 离线测试、样例生成、数据/安装检查、指定规则独立审计 | 是 |
| `project_manual/cn`, `project_manual/en` | 本体中英文使用/维护手册 | 是，每版保留 TeX/PDF |
| `data/raw`, `data/cache`, `data/processed`, `data/metadata` | 用户行情、缓存和来源记录 | 仅空目录占位；不上传真实行情 |
| `tests/fixtures/known_prices.csv` | 小型人工测试数据 | 是，不是真实市场数据 |
| `runs/`, `run/`, `.quantlab-desktop/` | 回测档案和桌面任务工作文件 | 不上传运行内容 |
| `researchProject/01_aapl_tsla_rebalancing/` | 独立权重/再平衡频率研究 | 否 |
| `researchProject/02_threshold_partial_rebalancing/` | 独立阈值/部分再平衡研究 | 否 |
| `researchProject/03_time_and_asset_robustness/` | 独立入场时点/资产稳健性研究 | 否 |
| `researchProject/04_rebalancing_mechanisms/` | 独立恒等式/排列实验/GBM 机制研究 | 否 |
| `.venv`, `.wheelhouse`, 缓存、`build`, `dist` | 本机环境和可重建交付物 | 否 |

## 冻结代码不是项目本体的新实现

专题 01/02 的 `code/quantlab_reference/` 是当时 QuantLab 的冻结副本，用于历史一致性比较；不合并回 `src/quantlab/`。专题 02–04 的 `code/engine.py` 是两资产研究计算程序，不是本体引擎更新。专题 04 还单独实现无摩擦收盘恒等式和合成模型，它们的收益/回撤/换手口径不可直接替代本体指标。

本体 `src/quantlab`、`desktop` 和包配置不依赖 `researchProject`。独立研究引用的是自己的相对路径及冻结参考代码。移除独立研究后，本体离线测试与合成示例仍可运行。研究专题的计算/画图/TeX 生成脚本往往在顶层立即执行，会改写其本地结果；本次只在临时副本运行验证脚本。

## 数据分层

1. 人工测试/合成数据：用于安装和正确性验证，可用仓库脚本重建。
2. 本体真实行情：由配置显式引用，继续保留在本地 `data/`；档案再冻结一次。
3. 独立研究数据：各专题自带，连同结果、图表和协议在专题内管理。
4. 运行数据快照：是历史实验输入证据，不是默认行情源。

本次审查前，四个专题共登记 287 项哈希，全部一致。保留其目录可继续按各自 README 复算；本次应用版本不宣称完整重跑研究网格、蒙特卡洛模拟或重新验证全部统计结论。
