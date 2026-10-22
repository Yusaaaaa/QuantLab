# QuantLab 2026.10.22 审查与验证记录

核对日期：2026-10-22。发布标签：`v2026.10.22`。完整发布边界见 [PROJECT_SCOPE.md](PROJECT_SCOPE.md)。

## 结论

当前项目可以作为独立的本地日线回测应用发布。发布内容包含 Python 本体、Tauri 工作台、当前简单策略/因子、配置、测试、辅助脚本和中英文手册。四个独立研究专题及其冻结引擎、行情、结果和图表不并入本体，也不上传。现有策略数学规则、成交时点、费用及滑点没有改变。

已修复桌面历史列表受单个损坏档案影响、失败/成功状态优先级和目录链接边界问题；更新了有已知漏洞的前端构建依赖。测试和历史成交比较未发现本次改动引入的交易结果回归。

## 审查范围

- 逐模块检查配置、输入校验/复权、交易日历、物理截断历史、策略加载/合同、普通与 decision_relative 转换、卖出先行/现金约束、账本恒等式、基准/绩效、HTML 报告与归档快照。
- 检查全部 CLI、桌面 JSON 桥接、Rust 子进程管理/取消、开发服务器访问限制、React 编辑/保存/配置/结果流及版本元数据。
- 检查现有策略、因子、辅助脚本和测试合同；发布前解析全部本体和独立研究 Python 文件（本体 48、测试 19、策略 4、因子 1、脚本 4、研究及冻结副本 120）。这些数量是审查时的 Python 文件计数，不含生成字节码。
- 核对四个专题的目录、参考引擎、计算/绘图/报告脚本与数据依赖。专题 01/02 的 quantlab_reference 是冻结参考，不是新的本体源码；02–04 的研究引擎仅用于专题。
- 验证发布候选文件不含真实行情、运行档案、研究内容、虚拟环境、依赖/构建缓存。对常见 GitHub token、AWS access-key 和私钥签名扫描未发现命中；这不是完整安全认证。

## 修复与文档调整

| 项目 | 审查前 | 处理 |
|---|---|---|
| 历史读取 | 单个 summary/metadata JSON 损坏会中断整页；仅文件存在即可判成功 | 逐条隔离错误，失败标记优先，要求 complete 元数据 |
| 目录边界 | catalog 可枚举被整个目录符号链接带到工作区外的文件；history 可跟随外部运行链接 | 在枚举/读取前检查解析路径，拒绝外部目录；新增回归测试 |
| 大成交表 | 先读完整 CSV，再截前 2,000 笔 | 通过 islice 限制实际读取行数 |
| npm 依赖 | 审计返回 2 high + 1 moderate（Vite / source-map-js / esbuild） | Vite 6.4.5 修复线与 source-map-js 1.2.2；复审 0 项 |
| 旧导出范围 | 所有策略/因子被排除，配置/测试引用缺失实现 | 按用户新授权包含现有实现，清楚标记真实数据另备 |
| 版本与说明 | Python/npm/Tauri/Rust 为 0.1.0，UI 硬编码 0.1；README 有较早阶段措辞 | 统一 2026.10.22，界面从 package.json 读版本；更新 README、范围、发布说明与中英文手册 |

新增 4 个针对历史损坏、状态及符号链接边界的测试；包版本测试改为与 pyproject 和 VERSION 交叉核对。原有规则和因子定义保持不变。

## 实际验证结果

| 检查 | 结果 | 证据 |
|---|---|---|
| 发布源码完整 Python 套件 | 136 passed | [pytest](docs/validation/2026.10.22/pytest.txt) |
| 构建 wheel 并安装到独立验证环境后测试 | 136 passed；从 site-packages 导入版本 2026.10.22 | [installed wheel tests](docs/validation/2026.10.22/installed-wheel-pytest.txt) |
| Python 依赖一致性 | No broken requirements found | [pip check](docs/validation/2026.10.22/pip-check.txt) |
| 空行情发布副本生成合成 sample、校验与完整回测/HTML 报告 | 成功；期末资产 $109,083.15，价格为人工模拟 | [sample run](docs/validation/2026.10.22/sample-backtest.txt) |
| 原 AAPL 周反转真实历史的逐日/逐笔回归 | 1,507 sessions、198 fills；数量/方向/日期/费用一致，最大权益误差 $2.91e-11 | [parity](docs/validation/2026.10.22/historical-parity.json) |
| TypeScript / Vite 6 生产构建 | 通过；大 bundle 体积提示仍存在 | [frontend build](docs/validation/2026.10.22/frontend-build.txt) |
| Cargo check --locked | 通过 | 同一本地 Rust 编译环境；release 构建进一步通过 |
| Tauri macOS release App | 构建通过 | [native build](docs/validation/2026.10.22/native-build.txt) |
| npm audit | 初始 3 项，修复后 0 项已知漏洞 | [before](docs/validation/2026.10.22/npm-audit-before.json) / [after](docs/validation/2026.10.22/npm-audit-after.json) |
| 四个研究专题清单完整性 | 287/287 哈希匹配，无缺失/改变 | [integrity](docs/validation/2026.10.22/research-integrity.json) |
| 专题 02–04 验证脚本 | 临时副本重新运行通过；包含未来价格扰动、窗口切片、排序不变性、恒等式/排列/GBM 单元检验 | [02](docs/validation/2026.10.22/research-02-validation.json) / [03](docs/validation/2026.10.22/research-03-validation.json) / [04](docs/validation/2026.10.22/research-04-validation.json) |
| 中英文手册 | 已更新、XeLaTeX 编译并检查排版；中文 20 页，英文 19 页 | project_manual/ 中 TeX/PDF |

验证环境使用 macOS arm64、Python 3.12.14 与项目固定 Python 依赖。独立 wheel 安装验证环境从本机 runtime 继承可用包，再安装锁定依赖和新 wheel，未执行全新操作系统上的无缓存安装。当前原生版本完成编译，本次未重新执行原生窗口逐控件交互回归；2026-09-21 的原生运行记录在 desktop/README.md 中明确作为历史验收保留。

## 保留的限制与后续维护事项

- 可信代码合同不是恶意 Python 沙箱；固定股票池、复权研究单位、零量可交易代理、stale mark 等已知模型限制仍应披露。
- App 依赖工作区 Python 环境；此版本不是内置 Python 的通用安装包。发布源码与文档，不上传本机二进制、数据或结果。
- 前端初始 bundle 约 1 MB（gzip 约 328 KB），有构建提示；大日志轮询和长日线历史的性能仍有优化空间，不影响此次正确性验证。
- 研究脚本在模块顶层写入结果、部分报告解释为固定文字。它们可以复算指定专题，但不是通用策略 API，也不能直接吸收为运行时；改变假设后要同步审核文字与清单。
- 本次没有重跑专题 01 的完整网格、专题 04 的全量蒙特卡洛，也不重新认证其所有统计结论。已检查其源码/完整性，并重跑现有指定验证。
- 没有变更 GitHub 仓库可见性。发布前核对为 PUBLIC，现有历史通过正常追加提交保留。
