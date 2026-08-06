# ret 因子示例

本示例直接读取 `market.swap_directory` 中的 1 分钟 K 线，不复制行情文件。
生成的 `ret_10m.parquet`、未来收益和回测结果都保存在本目录。

在项目根目录运行：

```powershell
uv run python .\examples\ret\generate_ret.py
uv run alphalab backtest --config .\examples\ret\backtest.yaml
```

如原始 K 线不在默认目录，生成因子时传入 `--input`，并同步修改
`backtest.yaml` 的 `market.swap_directory`。

`registry.copy_factor_file` 为 `false`，因此准入时不会在 `factor_store` 中
重复复制 `ret_10m.parquet`。

示例回测结果可直接打开：[report.html](report.html)。报告包含 10、30、60 和
180 分钟预测周期的指标、准入检查及图表。
