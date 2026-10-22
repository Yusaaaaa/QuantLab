# 用户明确批准的研究因子

此目录最初在 V1 中预留为空。用户现已明确批准“个股收益率减标普收益率”这一研究因子，
并要求按周频进行 AAPL 加减仓回测，因此新增 `return_spread.py`。

- `daily_return_spread(data, symbol, benchmark)`：两日收盘之间的个股收益率减基准收益率。
- `weekly_return_spread(data, symbol, benchmark)`：两个相邻日历周最后交易日收盘之间的个股收益率减基准收益率。
- 周度版本必须在该周最后交易日收盘调用，由策略通过已知下一交易日日历保证。
- 返回起止日期、个股收益、基准收益和差值。两端日期必须同步；不足历史返回 None，日期错位报错。
- 不计算阈值、不决定买卖、不分配仓位、不下载数据、不修改账户。
- 使用 MarketDataView 提供的历史数据；真实回测采用 SPY 的复权收益作为标普 500 的可交易基金代理。

此次策略调用周度版本。单日与周度共用同一纯数学模块，没有自动切换频率。

配置必须显式绑定因子源码，例如：

```yaml
strategy:
  factor_paths:
    factors.return_spread: ../factors/return_spread.py
```

策略中使用 `from factors.return_spread import weekly_return_spread`。
加载器只绑定配置列出的文件，对因子同样执行导入/I/O 合同检查；不扫描目录，不修改 sys.path。
每次回测将实际因子源码保存到 `factors.snapshot/`，记录 SHA-256，并将冻结配置指向快照。
因此，之后修改研究因子不会改变旧实验的复现输入。

这不是大型 Factor API 或因子平台。其他因子仍必须由用户明确提出、理解、验证并批准，
不得自动添加 momentum、RSI、value、quality 等研究内容。普通数学工具仍放在 utils 中。
