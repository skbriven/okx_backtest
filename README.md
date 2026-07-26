# AlphaLab Backtest 使用指南

AlphaLab Backtest 是一个通过 YAML 配置运行的永续合约因子回测库。它接收一个
Parquet 因子文件，在指定时间范围内同时回测多个预测周期，为每个周期生成独立结果，
并按照配置的门槛决定是否将因子写入本地因子库。

当前包版本：`0.3.0`

## 1. 功能概览

- 输入一个时间戳索引、单个数值列的因子 Parquet 文件。
- 一次配置多个以分钟为单位的预测周期，例如 `[5, 15, 30, 60]`。
- 只对 YAML 指定的一段完整时间区间回测，不划分样本内、样本外、训练集或测试集。
- 回测对象必须是以 `-SWAP` 结尾的永续合约，例如 `BTC-USDT-SWAP`。
- 缺少某个周期的未来收益率文件时，从该合约的 1 分钟 `close` 自动生成。
- 每个预测周期单独计算指标并执行入库检查。
- 只要至少一个预测周期通过检查，因子就会进入本地因子库。
- 生成一个可离线打开的自包含 HTML 报告，可在页面中切换预测周期。
- 可选保存每个周期的 JSON 指标、策略明细 Parquet 和 PNG 报告。

完整流程如下：

```text
读取 YAML
  -> 校验配置
  -> 读取并校验因子 Parquet
  -> 检查各周期未来收益率文件
  -> 对缺失周期读取 SWAP close 并生成收益率
  -> 因子与收益率按时间戳对齐
  -> 计算滚动因子方向和历史分组阈值
  -> 按预测周期的时间网格生成多空持仓
  -> 扣除手续费和滑点
  -> 计算指标及逐周期入库检查
  -> 写入结果目录和 HTML 报告
  -> 至少一个周期通过时写入本地因子库
```

## 2. 运行环境

### 2.1 系统要求

- Windows、Linux 或 macOS。
- Python `3.10` 及以上；建议使用 Python `3.12`。
- 安装时若需要自动下载 Python 和依赖，电脑必须能够联网。
- 运行回测本身不需要联网，所有输入和输出均为本地文件。

项目运行依赖：

- matplotlib
- numpy
- pandas
- pyarrow
- PyYAML

这些依赖会在联网安装 wheel 时自动解析和安装，但不包含在
`alphalab_backtest-0.3.0-py3-none-any.whl` 文件内部。

### 2.2 建议的交付目录

将 wheel、YAML 和数据整理到同一个工作目录，路径可以自行调整：

```text
alphalab-run/
├─ alphalab_backtest-0.3.0-py3-none-any.whl
├─ backtest.yaml
├─ factors/
│  └─ ret_10m.parquet
├─ swap/
│  └─ BTC-USDT-SWAP.parquet
├─ returns/                 # 可以预先为空
├─ results/                 # 程序自动创建
└─ factor_store/            # 因子通过门槛后自动创建
```

YAML 中的相对路径都以 YAML 文件所在目录为基准，因此推荐使用上面的结构和相对路径，
方便整套目录移动到另一台电脑。

## 3. 在联网的空白 Windows 电脑上安装

项目推荐使用 `uv` 管理 Python 和项目内虚拟环境，不会修改全局 Python 包。

### 3.1 安装 uv

任选一种方式。

使用 Windows 包管理器：

```powershell
winget install --id=astral-sh.uv -e
```

或使用 uv 官方安装脚本：

```powershell
powershell -ExecutionPolicy ByPass -c "irm https://astral.sh/uv/install.ps1 | iex"
```

安装后重新打开 PowerShell，并确认：

```powershell
uv --version
```

uv 的其它安装方式见
[uv 官方安装文档](https://docs.astral.sh/uv/getting-started/installation/)。

### 3.2 创建项目内虚拟环境

进入交付目录：

```powershell
cd D:\path\to\alphalab-run
uv venv --python 3.12 .venv
```

如果本机没有 Python 3.12，uv 默认会自动下载。虚拟环境只创建在当前目录的
`.venv` 中。

### 3.3 安装 wheel

```powershell
uv pip install --python .\.venv\Scripts\python.exe .\alphalab_backtest-0.3.0-py3-none-any.whl
```

该命令会同时安装 wheel 声明的第三方依赖。验证安装：

```powershell
.\.venv\Scripts\alphalab.exe --version
```

预期输出：

```text
0.3.0
```

不需要激活虚拟环境；后续直接调用 `.venv` 内的命令即可。

## 4. 完全离线电脑的安装说明

单独一个项目 wheel 不能完成完全离线安装。离线交付时还必须准备：

1. 适用于目标系统和 CPU 架构的 Python 3.10+；
2. `uv` 的离线安装程序或可执行文件；
3. 本项目 wheel；
4. numpy、pandas、pyarrow、matplotlib、PyYAML 及其传递依赖的兼容 wheel。

建议在一台与目标电脑操作系统、CPU 架构和 Python 版本相同的联网电脑上建立
`wheelhouse`。可在联网电脑的交付目录中执行：

```powershell
uv venv --python 3.12 --seed .download-env
.\.download-env\Scripts\python.exe -m pip download --dest .\wheelhouse .\alphalab_backtest-0.3.0-py3-none-any.whl
```

把 `wheelhouse`、适用的 Python 安装包和 uv 离线程序一起复制到目标电脑。确认目标机
已经安装 Python 和 uv 后执行：

```powershell
uv venv --python 3.12 .venv
uv pip install --offline --find-links .\wheelhouse --python .\.venv\Scripts\python.exe .\wheelhouse\alphalab_backtest-0.3.0-py3-none-any.whl
```

如果交付内容只有 `alphalab_backtest-0.3.0-py3-none-any.whl`，则目标电脑仍需要联网
下载第三方依赖。

## 5. 准备输入数据

### 5.1 因子 Parquet

因子文件必须满足以下要求：

- Parquet 的 index 是时间戳；
- 时间戳不能重复；
- 只有一个数据列；
- 该列必须是数值类型；
- 列名不限，读入后会统一命名为 `factor`；
- 时间戳会统一转换为 UTC；
- 因子时间戳应与收益率时间戳精确对齐。

示例：

```python
import numpy as np
import pandas as pd

index = pd.date_range(
    "2024-01-01",
    periods=10_000,
    freq="1min",
    tz="UTC",
    name="timestamp",
)
factor = pd.DataFrame(
    {"ret_10m": np.random.standard_normal(len(index))},
    index=index,
)
factor.to_parquet("factors/ret_10m.parquet")
```

不允许下面这些输入形式：

- 默认整数 index；
- 两列或更多因子值；
- 字符串类型因子；
- 重复时间戳。

框架一次只回测一个因子文件。如果要回测多个因子，应为每个因子分别准备 YAML 并
分别执行。

### 5.2 永续合约 close Parquet

当任一预测周期的未来收益率文件不存在时，框架会读取：

```text
<market.swap_directory>/<market.instrument>.parquet
```

例如：

```text
D:/crypto/okx/data/swap/BTC-USDT-SWAP.parquet
```

close 文件支持两种格式。

格式一，`timestamp` 和 `close` 都是普通列：

```python
pd.DataFrame(
    {
        "timestamp": timestamp_values,
        "close": close_values,
    }
).to_parquet("swap/BTC-USDT-SWAP.parquet", index=False)
```

格式二，时间戳是 index，数据中有一个 `close` 列：

```python
pd.DataFrame(
    {"close": close_values},
    index=timestamp_index,
).to_parquet("swap/BTC-USDT-SWAP.parquet")
```

要求：

- 文件名必须与 YAML 中的 `market.instrument` 完全一致；
- 必须包含 `close`；
- `close` 必须是数值，所有非空值必须有限且大于 0；
- 时间戳不能重复；
- 建议使用连续的 1 分钟行情。

空的 close 值不会阻止文件读取，但会使依赖该值的未来收益率变成 `NaN`。

如果所有未来收益率文件都已经存在，回测不会读取 close 文件。

### 5.3 未来收益率 Parquet

每个预测周期对应一个独立文件。默认路径为：

```text
<returns.directory>/<instrument>/<horizon>min.parquet
```

例如：

```text
returns/BTC-USDT-SWAP/5min.parquet
returns/BTC-USDT-SWAP/15min.parquet
```

缺失文件会自动生成，公式严格为：

```text
future_return[t] = close[t + n + 1分钟] / close[t + 1分钟] - 1
```

其中 `n` 是预测周期的分钟数。例如 5 分钟周期使用：

```text
close[t + 6分钟] / close[t + 1分钟] - 1
```

计算基于真实时间戳查找，不是简单的行位移。因此：

- close 数据缺少 `t+1` 或 `t+n+1` 时，该时刻收益率为 `NaN`；
- 数据尾部无法取得未来 close 的记录为 `NaN`；
- 原始行情不是连续 1 分钟数据时，可能产生大量 `NaN`。

自动生成的文件：

- index 名为 `timestamp`；
- 只有一个 `return` 列；
- 不会覆盖已经存在的收益率文件。

如果文件已经存在，框架直接使用它，不会重新计算或核对其计算公式。已有收益率文件
支持：

- 时间戳 index 加一个数值列；或
- 普通 `timestamp` 列加数值 `return` 列。

## 6. 编写 YAML

可以复制 [示例配置](examples/backtest.yaml)，再修改其中的路径和参数。

推荐的可移植配置如下：

```yaml
version: 2

factor:
  name: ret_10m
  path: ./factors/ret_10m.parquet

market:
  instrument: BTC-USDT-SWAP
  swap_directory: ./swap

returns:
  directory: ./returns
  file_pattern: "{instrument}/{horizon}min.parquet"

time_range:
  start: "2024-01-01T00:00:00Z"
  end: "2025-01-01T00:00:00Z"

backtest:
  prediction_horizons: [5, 15, 30, 60]
  direction:
    method: rolling_ic
    window: 30D
    min_observations: 43200
  grouping:
    quantiles: 10
    long_groups: [10]
    short_groups: [1]
  costs:
    fee_bps: 0
    slippage_bps: 0

admission:
  mode: per_horizon
  rules:
    min_valid_samples: 100000
    min_coverage: 0.95
    min_ic: 0.005
    min_icir: 1.0
    min_sharpe: 0.8
    max_absolute_drawdown: 0.40

registry:
  directory: ./factor_store
  copy_factor_file: true
  overwrite: false

output:
  directory: ./results
  save_metrics_json: true
  save_strategy_parquet: true
  save_report_png: true
  save_report_html: true
  save_config_snapshot: true
```

### 6.1 顶层字段

| 字段 | 是否必填 | 说明 |
| --- | --- | --- |
| `version` | 是 | 当前只能是 `2` |
| `factor` | 是 | 候选因子名称和路径 |
| `market` | 是 | 永续合约名称和 close 目录 |
| `returns` | 是 | 未来收益率目录及文件名模板 |
| `time_range` | 是 | 本次完整回测区间 |
| `backtest` | 是 | 预测周期、方向、分组和成本 |
| `admission` | 否 | 因子入库规则 |
| `registry` | 是 | 本地因子库位置和写入行为 |
| `output` | 是 | 回测结果位置和保存开关 |

配置中出现未支持的字段会直接报错，不会被静默忽略。

### 6.2 `factor`

| 字段 | 默认值 | 说明 |
| --- | --- | --- |
| `name` | 因子文件名，不含扩展名 | 只能包含字母、数字、点、下划线和连字符 |
| `path` | 无，必填 | 因子 Parquet 路径 |

`name` 同时用于结果目录和因子库目录，建议保证同一个合约下名称唯一。

### 6.3 `market`

| 字段 | 默认值 | 说明 |
| --- | --- | --- |
| `instrument` | 无，必填 | 大写永续合约名，必须以 `-SWAP` 结尾 |
| `swap_directory` | 无，必填 | 永续合约 close 文件所在目录 |

例如 `BTC-USDT-SWAP`、`ETH-USDT-SWAP`。

### 6.4 `returns`

| 字段 | 默认值 | 说明 |
| --- | --- | --- |
| `directory` | 无，必填 | 所有未来收益率的根目录 |
| `file_pattern` | `"{instrument}/{horizon}min.parquet"` | 相对于根目录的文件模板 |

`file_pattern` 必须同时包含 `{instrument}` 和 `{horizon}`，只能生成相对路径，不能包含
`..`。按合约分目录可以避免不同币种的未来收益率互相覆盖。

### 6.5 `time_range`

| 字段 | 默认值 | 说明 |
| --- | --- | --- |
| `start` | 无，必填 | 回测开始时间，包含该时刻 |
| `end` | 无，必填 | 回测结束时间，不包含该时刻 |

实际区间为 `[start, end)`。没有时区的信息按 UTC 处理，有时区的信息转换成 UTC。
`start` 必须早于 `end`。这一整段时间会作为一个完整回测区间。

### 6.6 `backtest.prediction_horizons`

必须是一个非空的正整数列表，值的单位是分钟：

```yaml
prediction_horizons: [5, 15, 30, 60]
```

不能重复。框架会按从小到大的顺序运行，并为每个值创建独立的 `<horizon>min`
结果目录。

### 6.7 `backtest.direction`

| 字段 | 默认值 | 说明 |
| --- | --- | --- |
| `method` | `rolling_ic` | 当前只支持 `rolling_ic` |
| `window` | `30D` | pandas 时间窗口字符串，例如 `60min`、`24h`、`30D` |
| `min_observations` | `43200` | 开始计算方向和分组前至少需要的历史样本数 |

每个时刻使用滚动历史 IC 判断因子方向：

- 历史 IC 小于 0，方向为 `-1`；
- 其它情况方向为 `1`；
- `signal_factor = factor × factor_direction`。

计算方向时，代码会把每条因子与未来收益率观测的时间戳向后移动当前预测周期，再将其
纳入滚动历史。这是当前实现采用的时点约定。滚动窗口会产生预热期，预热期记录不参与
最终回测。

### 6.8 `backtest.grouping`

| 字段 | 默认值 | 说明 |
| --- | --- | --- |
| `quantiles` | `10` | 分组数量，至少为 2 |
| `long_groups` | `[quantiles]` | 做多的组，可指定多个 |
| `short_groups` | `[1]` | 做空的组，可指定多个 |

组号范围为 `1` 到 `quantiles`，多空组不能重叠。分组阈值只使用当前时刻以前的因子历史
计算。若历史 IC 为负，组号会反转，使高组始终代表经过方向修正后的高信号。

策略只选择 UTC 时间戳落在预测周期网格上的记录调仓。例如 15 分钟周期通常在
`00:00`、`00:15`、`00:30`、`00:45` 等时刻调仓。

### 6.9 `backtest.costs`

| 字段 | 默认值 | 说明 |
| --- | --- | --- |
| `fee_bps` | `0` | 单位换仓手续费，单位 bp |
| `slippage_bps` | `0` | 单位换仓滑点，单位 bp |

```text
cost_rate = (fee_bps + slippage_bps) / 10000
cost[t] = abs(position[t] - position[t-1]) × cost_rate
net_return[t] = position[t] × future_return[t] - cost[t]
```

仓位取值为 `-1`、`0` 或 `1`。从 `-1` 直接翻转到 `1` 时换手为 `2`，会扣除两倍成本。

### 6.10 `admission`

`mode` 当前只支持 `per_horizon`，即每个预测周期独立判断。

| 规则 | 通过条件 |
| --- | --- |
| `min_valid_samples` | `valid_samples >= 配置值` |
| `min_coverage` | `coverage >= 配置值`，配置范围为 0 到 1 |
| `min_ic` | `ic >= 配置值` |
| `min_icir` | `icir >= 配置值` |
| `min_sharpe` | `sharpe >= 配置值` |
| `max_absolute_drawdown` | `abs(max_drawdown) <= 配置值` |

规则值可以设为 `null` 或直接省略，表示不检查该项。一个周期必须通过所有已配置规则
才算通过。只要至少一个周期通过，因子整体就会入库；未通过周期的拒绝原因仍会写入
结果和 HTML 报告。

### 6.11 `registry`

| 字段 | 默认值 | 说明 |
| --- | --- | --- |
| `directory` | 无，必填 | 本地因子库根目录 |
| `copy_factor_file` | `true` | 入库时是否复制原始因子文件 |
| `overwrite` | `false` | 已存在同名因子时是否替换整个条目 |

实际条目路径为：

```text
<registry.directory>/<instrument>/<factor.name>/
```

建议默认保留 `overwrite: false`，防止误覆盖已有因子。使用 `overwrite: true` 时，
同合约同因子名称的原条目会被整体替换。

### 6.12 `output`

| 字段 | 默认值 | 说明 |
| --- | --- | --- |
| `directory` | 无，必填 | 回测结果根目录 |
| `save_metrics_json` | `true` | 保存逐周期 `metrics.json` |
| `save_strategy_parquet` | `true` | 保存逐周期 `strategy.parquet` |
| `save_report_png` | `true` | 保存逐周期 `report.png` |
| `save_report_html` | `true` | 保存可切换周期的总 HTML 报告 |
| `save_config_snapshot` | `true` | 保存本次 YAML 快照 |

实际结果路径为：

```text
<output.directory>/<instrument>/<factor.name>/
```

结果目录和因子库目录不能相同，也不能互相包含。

## 7. 运行回测

### 7.1 命令行运行

Windows：

```powershell
.\.venv\Scripts\alphalab.exe backtest --config .\backtest.yaml
```

Linux 或 macOS：

```bash
./.venv/bin/alphalab backtest --config ./backtest.yaml
```

成功时会打印类似：

```text
Factor: ret_10m
Accepted horizons: [5, 15]
Rejected horizons: [30, 60]
Generated return files:
- D:\alphalab-run\returns\BTC-USDT-SWAP\15min.parquet
Results: D:\alphalab-run\results\BTC-USDT-SWAP\ret_10m
HTML report: D:\alphalab-run\results\BTC-USDT-SWAP\ret_10m\report.html
Registry: D:\alphalab-run\factor_store\BTC-USDT-SWAP\ret_10m
```

若没有周期通过，最后一行是：

```text
Registry: not admitted
```

出现配置、数据或文件错误时，命令返回退出码 `1` 并在标准错误中打印 `error: ...`。

### 7.2 Python 调用

```python
from alphalab_backtest import run_backtest

result = run_backtest("backtest.yaml")

print(result.summary)
print(result.output_directory)
print(result.html_report_path)
print(result.generated_return_files)
print(result.registry_directory)
```

返回对象 `BacktestRunResult` 包含：

| 属性 | 说明 |
| --- | --- |
| `summary` | 整体结果和各周期核心指标字典 |
| `output_directory` | 本次结果目录 |
| `html_report_path` | HTML 报告路径；关闭 HTML 时为 `None` |
| `generated_return_files` | 本次自动生成的收益率文件路径元组 |
| `registry_directory` | 入库目录；没有周期通过时为 `None` |

也可以先加载并检查配置：

```python
from alphalab_backtest import load_config, run_backtest

config = load_config("backtest.yaml")
print(config.market.instrument)
print(config.backtest.prediction_horizons)

result = run_backtest(config)
```

## 8. 输出文件

假设输出目录是 `./results`、因子库是 `./factor_store`，最终结构如下：

```text
returns/
└─ BTC-USDT-SWAP/
   ├─ 5min.parquet
   ├─ 15min.parquet
   ├─ 30min.parquet
   └─ 60min.parquet

results/
└─ BTC-USDT-SWAP/
   └─ ret_10m/
      ├─ config.snapshot.yaml
      ├─ summary.json
      ├─ report.html
      ├─ 5min/
      │  ├─ metrics.json
      │  ├─ strategy.parquet
      │  └─ report.png
      ├─ 15min/
      │  ├─ metrics.json
      │  ├─ strategy.parquet
      │  └─ report.png
      └─ ...

factor_store/
└─ BTC-USDT-SWAP/
   └─ ret_10m/
      ├─ factor.parquet
      ├─ config.snapshot.yaml
      ├─ metadata.json
      └─ horizons/
         ├─ 5min/
         │  └─ metrics.json
         └─ 15min/
            └─ metrics.json
```

因子库的 `horizons` 中只保存通过门槛的周期。

### 8.1 `report.html`

直接双击即可用浏览器打开，不需要启动服务，也不需要联网。报告内嵌所有图片，并提供
预测周期下拉框。切换周期时会同时更新：

- 通过或拒绝状态；
- 核心指标；
- 入库规则检查；
- 拒绝原因；
- 各分组平均未来收益；
- 净值、回撤、日 IC 等图表；
- 收益率文件路径及本次是否自动生成。

### 8.2 `summary.json`

包含：

- 库版本、因子、合约和文件 SHA256；
- 回测时间范围；
- 自动生成的收益率文件；
- 通过和拒绝的预测周期；
- 每个周期的核心指标及拒绝原因。

无穷值和非数值结果在 JSON 中保存为 `null`。

### 8.3 `metrics.json`

保存单个预测周期的完整指标、分组收益和逐项入库检查，同时记录使用的收益率文件及
该文件是否为本次自动生成。

### 8.4 `strategy.parquet`

主要字段：

| 字段 | 说明 |
| --- | --- |
| `timestamp` | 调仓时间 |
| `factor` | 原始因子值 |
| `signal_factor` | 方向修正后的因子 |
| `history_ic` | 用于决定方向的滚动历史 IC |
| `factor_direction` | 因子方向，`1` 或 `-1` |
| `group` | 当前分组 |
| `forward_return` | 对应预测周期未来收益率 |
| `long_position` | 做多仓位，`0` 或 `1` |
| `short_position` | 做空仓位，`0` 或 `-1` |
| `position` | 合并仓位，`-1`、`0` 或 `1` |
| `turnover` | 本次仓位变化绝对值 |
| `gross_return` | 扣费前策略收益 |
| `cost` | 手续费与滑点 |
| `net_return` | 扣费后策略收益 |
| `nav` | 累计净值 |

### 8.5 因子库元数据

`metadata.json` 记录：

- 库版本；
- 因子名称与合约；
- 原始因子路径和 SHA256；
- close 数据来源；
- 是否复制因子文件；
- 回测时间范围；
- 通过和拒绝的预测周期。

## 9. 指标说明

| 指标 | 含义 |
| --- | --- |
| `factor_samples` | 时间范围内的因子样本数 |
| `aligned_non_null_samples` | 因子与收益率时间戳对齐后，双方均非空的样本数 |
| `valid_samples` | 完成滚动历史预热后实际用于 IC 和分组统计的样本数 |
| `trade_samples` | 落在该预测周期调仓网格上的样本数 |
| `coverage` | `aligned_non_null_samples / factor_samples` |
| `ic` | 方向修正后因子与未来收益率的相关系数 |
| `icir` | 日 IC 均值除以日 IC 标准差，再乘 `sqrt(365)` |
| `long_count` | 做多记录数 |
| `short_count` | 做空记录数 |
| `open_count` | 做多与做空记录数之和 |
| `open_frequency` | `open_count / trade_samples` |
| `annual_return` | 合并策略扣费后净值按实际时间跨度年化 |
| `sharpe` | 调仓收益均值除以标准差，再按实际观测频率年化；无风险利率为 0 |
| `max_drawdown` | 合并策略净值的最大回撤，通常为负数 |
| `calmar` | 年化收益除以最大回撤绝对值 |
| `final_nav` | 合并策略最终净值 |

`long_*` 和 `short_*` 字段分别表示纯多头和纯空头策略的绩效。

回测时间很短时，年化收益、Sharpe 和 Calmar 可能非常大，不应只依赖年化指标判断
因子质量。建议同时检查样本数、覆盖率、IC、ICIR、最大回撤和实际净值曲线。

## 10. 重复运行和文件覆盖

- 已存在的未来收益率文件不会被覆盖。
- 结果目录中的同名文件会被本次运行更新，但未启用的输出项不会主动删除旧文件。
- 若因子通过且因子库条目已存在，`registry.overwrite: false` 会报错。
- `registry.overwrite: true` 会替换整个同合约同因子条目，应谨慎使用。
- 修改了 close 数据但希望重新生成收益率时，需要先自行备份并移除目标收益率文件；
  框架不会自动判断已有收益率是否过期。
- 为保留多次实验，推荐使用不同的 `factor.name` 或不同的 `output.directory`。

## 11. 常见错误

### `Factor parquet must contain exactly one value column`

因子文件包含多个普通列。只保留一个数值因子列，时间应放在 index。

### `Parquet index must contain timestamps`

因子或 index 格式收益率文件使用了整数 index。保存前将时间设置为
`DatetimeIndex`。

### `Swap parquet not found`

某个收益率周期缺失，框架尝试生成它，但没有找到：

```text
<swap_directory>/<instrument>.parquet
```

检查 YAML 路径、合约名和文件名大小写。

### `requires at least ... aligned non-null rows`

因子与收益率精确对齐后的非空样本少于 `direction.min_observations`。检查：

- 因子与行情时间戳是否使用同一时区；
- 两者是否有共同时间范围；
- close 是否为连续 1 分钟；
- `min_observations` 是否高于实际数据量。

### `has no rows after the rolling-history warm-up`

滚动窗口完成预热后没有可用样本。增加数据长度，或合理降低
`direction.min_observations`。

### `Factor registry entry already exists`

同合约、同因子名已存在于因子库。若不是明确要替换，不要直接开启覆盖；可以修改
`factor.name` 或 `registry.directory`。

### HTML 没有生成

确认：

```yaml
output:
  save_report_html: true
```

HTML 使用内嵌 PNG，因此即使 `save_report_png: false`，生成 HTML 时仍会在内存中
绘制图表，但不会单独保存 PNG 文件。

## 12. wheel 分发与源码可见性

wheel 是 Python 安装包，不是源码加密格式。接收者可以将 `.whl` 当作 ZIP 解压，并
查看其中的 Python 文件和包结构。因此：

- wheel 适合安装、版本化和分发；
- wheel 不能保证算法或源码保密；
- 不应把密码、密钥、私有连接信息写入代码或 YAML；
- 若有强保密要求，需要另行评估编译扩展、服务端执行或商业授权方案，但这些方案也
  不等于绝对不可逆。

## 13. 开发、测试和重新构建 wheel

以下操作仅供项目维护者使用。

### 13.1 创建开发环境

```powershell
uv venv --python 3.12 .venv
uv pip install --python .\.venv\Scripts\python.exe -e . pytest
```

### 13.2 运行测试

```powershell
.\.venv\Scripts\python.exe -m pytest -p no:cacheprovider
```

### 13.3 构建 wheel

```powershell
uv build --wheel
```

构建结果位于 `dist/`。发布新版本前，需要同步更新：

- `pyproject.toml` 中的版本号；
- `src/alphalab_backtest/_version.py` 中的版本号；
- 本指南中的 wheel 文件名和当前版本。

可以用下面的命令计算交付文件 SHA256，并将结果通过独立渠道提供给接收者：

```powershell
Get-FileHash .\dist\alphalab_backtest-0.3.0-py3-none-any.whl -Algorithm SHA256
```
