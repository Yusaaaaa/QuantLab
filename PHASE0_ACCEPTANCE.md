# Phase 0 验收记录

工作目录：`/Users/yusa/ChatGPTWorkSpace/QuantLab`。
原始工作文档未修改。按第 43 节仅实现 Phase 0。

## 验证结果

- Python 3.12.14，项目独立 `.venv`。
- `.venv/bin/python -m pip install -e '.[dev]'`：成功。
- `.venv/bin/quantlab --help`：退出码 0。
- `.venv/bin/pytest`：11 passed in 0.07s；测试不使用网络。
- `.venv/bin/python -m pip check`：No broken requirements found。
- Git 仓库已初始化，分支 `codex/phase-0`，尚未创建提交。

## 本阶段创建的项目文件（完整清单）

- `.env.example`
- `.gitignore`
- `AGENTS.md`
- `PHASE0_ACCEPTANCE.md`
- `README.md`
- `configs/examples/.gitkeep`
- `data/cache/.gitkeep`
- `data/metadata/.gitkeep`
- `data/processed/.gitkeep`
- `data/raw/.gitkeep`
- `factors/README.md`
- `pyproject.toml`
- `runs/.gitkeep`
- `scripts/.gitkeep`
- `src/quantlab/__init__.py`
- `src/quantlab/cli.py`
- `src/quantlab/costs/__init__.py`
- `src/quantlab/data/__init__.py`
- `src/quantlab/engine/__init__.py`
- `src/quantlab/metrics/__init__.py`
- `src/quantlab/report/__init__.py`
- `src/quantlab/report/templates/.gitkeep`
- `src/quantlab/strategy/__init__.py`
- `src/quantlab/utils/__init__.py`
- `strategies/README.md`
- `tests/fixtures/.gitkeep`
- `tests/test_cli.py`

另有工具自动生成的 `.git/`、`.venv/`、`.pytest_cache/`、`__pycache__/`
及 `src/us_equity_quant_lab.egg-info/`；环境与构建缓存不作为源码交付。

## 假设与未决项

- 以第 43 节的首次实施指令为阶段边界，不提前实现完整引擎。
- 空包预留架构；CLI 业务命令显式退出 1，不声称已执行验证或回测。
- factors/ 仅 README；未创建策略、因子、行情或结果文件。
- Python 来自本机 Codex runtime，移动/删除该 runtime 后应使用独立 Python 3.12+ 重建虚拟环境。
- 当前依赖采用版本范围，精确环境锁定和运行版本快照在后续复现工作中处理。
- NYSE calendar 库选择、数据异常处理细则在 Phase 1 实现时确定；本阶段无阻塞项。

## 下一阶段

Phase 1：Pydantic v2 严格配置（extra=forbid）、CSV/Parquet provider、
标准 OHLCV schema、数据校验、NYSE calendar、固定 seed 的离线样本生成。
必须验证未知字段失败、异常价格/成交量告警或报错、样本可标准化加载。

工作文档第 43 节明确规定：“Do not proceed to Phase 1 until explicitly instructed.”
本阶段结束，等待用户人工检查及 Phase 1 指令。
