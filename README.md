# SMT-COMP 2025 cvc5 分 Track/Division 调优框架

当前唯一支持并接受正式调优结果的是 **Single Query Track**。其他 Track 的配置名、
代码骨架和官方规则说明仅为后续补充保留，尚未构建对应数据、validator 或端到端
验收，不能把它们当前产生的输出称为 SMT-COMP 2025 可复现成绩。

## Track 接口总览

| Track | 当前状态 | 参数配置 | 官方选择目录 | 结果目录 | 合法 performance |
|---|---|---|---|---|---|
| SingleQuery | **已支持** | `configs/cvc5/single-query.toml` | `files` | `results_singlequery` | `24`, `par`, `seq`, `sat`, `unsat` |
| Incremental | 预留，未验收 | `configs/cvc5/incremental.toml` | `files_inc` | `results_inc` | `par` |
| UnsatCore | 预留，未验收 | `configs/cvc5/unsat-core.toml` | `files_unsatcore` | `results_unsatcore` | `par`, `seq` |
| ModelValidation | 预留，未验收 | `configs/cvc5/model-validation.toml` | `files_model` | `results_model` | `par`, `seq` |
| Parallel | 预留，未验收 | `configs/cvc5/parallel.toml` | `files_parallel` | `results_parallel` | `par` |

下面是预留的通用接口；当前正式使用时 `TRACK` 必须是 `SingleQuery`：

```bash
make prepare TRACK=<Track> DIVISION=<Division>
make run TRACK=<Track> DIVISION=<Division> RUN_ID=<run-id>
make score TRACK=<Track> DIVISION=<Division> PERFORMANCE=<kind> RUN_ID=<run-id>
make score-matrix
```

完整的合法 `(Track, Division, performance)` 组合见
`docs/scoring-matrix.md`；数据集和选择规则见 `docs/dataset-counts.md` 与
`docs/benchmark-selection.md`；各 Track 的特殊验证流程见 `docs/operations.md`、
`docs/scoring.md` 和 `docs/tuning-rules.md`。规则总入口：
https://smt-comp.github.io/2025/rules.pdf 。

## Single Query 一键构建

Debian/Ubuntu、WSL 或已安装等价依赖的其他 Linux 发行版上执行：

```bash
make setup-single-query
```

启动该命令前只需具备 Bash、GNU Make、网络访问和管理员权限（或预先安装好依赖）；
Python 最低版本是 3.11。完整 non-incremental 数据及生成物至少预留 85 GiB 可用空间。
若尚未安装 Make，可先直接执行 `bash scripts/install_system_deps.sh`，再运行上面的命令。

该目标严格按以下顺序执行：

1. `make system-deps`：读取 `configs/setup-single-query.env`。Debian/Ubuntu 使用机器
   已配置的 APT 软件源；交互终端中 sudo 可正常提示当前用户输入密码。其他发行版在
   已安装等价工具时通过检查，否则提示使用本机包管理器安装，不绑定某个镜像、
   Ubuntu 版本或 CPU 架构。
2. `make storage-single-query`：按官方 README 标注的约 78 GB 解压体积预检磁盘。
   普通 Linux 默认使用仓库 `.cache`；只有检测到仓库位于 WSL 的 Windows 挂载盘时，
   才自动把大逻辑和 selection 放到当前用户的 XDG/`~/.cache` Linux filesystem，
   再建立符号链接。`EXTERNAL_CACHE_ROOT` 可显式覆盖，既不包含用户名也不固定盘符。
3. `make setup`：固定并安装官方 SMT-COMP 工具，固定并编译官方 scrambler。
4. `make benchmarks-single-query`：只下载 Zenodo 2025 non-incremental 发布物；
   不下载 incremental 数据。89 个 `.tar.zst` 分别按 Zenodo checksum 校验后解包。
5. `make solver-single-query`：只下载并校验官方 cvc5 default/SQ 提交包；不下载
   incremental cvc5 包。
6. `make cache`：运行官方 `smtcomp create-cache`。
7. `make select-single-query`：调用固定官方 `selection.helper`、
   `create_scramble_id` 与 `scramble_file` 生成 Single Query；完整任务会跳过，因此中断后
   可恢复，成员、seed、ID、scrambler 参数和输出格式仍全部来自官方代码。

也可以逐条执行上面七个目标。大包会复用已完整下载的 byte-range 分段；已通过
checksum 的整包不会重下。
解压默认使用 4 个 worker；可按机器的 CPU 与存储吞吐临时覆盖，例如
`make benchmarks-single-query EXTRACT_JOBS=8`。该参数只影响构建速度，不改变
archive 内容、官方 selection 或评分。worker-pool 实现依据：
https://docs.python.org/3/library/concurrent.futures.html 。
官方 scramble 默认由 `SELECTION_JOBS=auto` 按主机 CPU 数选择并发（上限 16），也可
显式覆盖；同样只影响构建速度。缓存布局由 `CACHE_PLACEMENT` 与可选的
`EXTERNAL_CACHE_ROOT` 控制；这些目录
均是可由官方输入重建的缓存。WSL 文件系统建议见
https://learn.microsoft.com/windows/wsl/filesystems 。

例如强制使用指定缓存盘和 8 个 scramble worker：

```bash
EXTERNAL_CACHE_ROOT=/data/smtcomp-cache SELECTION_JOBS=8 \
  make setup-single-query
```
该入口不会安装 Docker、Dolmen、trace executor，也不会下载 incremental 数据。

依赖配置及来源：

- `configs/setup-single-query.env`；
- Ubuntu 包目录：https://packages.ubuntu.com/ ；
- Python venv：https://docs.python.org/3/library/venv.html ；
- 官方 scrambler：https://github.com/SMT-COMP/scrambler 。

## 固定的官方资产

| 资产 | 本仓库使用值 | 官方来源 |
|---|---|---|
| SMT-COMP 工具 | `b0faba09100a297a32544ac29a54feb4d5d174b4` | https://github.com/SMT-COMP/smt-comp.github.io/tree/b0faba09100a297a32544ac29a54feb4d5d174b4 |
| scrambler | `2f2dbcd69d98894031c6359add0a898cd071bd98` | https://github.com/SMT-COMP/scrambler/tree/2f2dbcd69d98894031c6359add0a898cd071bd98 |
| benchmark metadata | `benchmarks-2025.json.gz` | https://github.com/SMT-COMP/smt-comp.github.io/blob/smtcomp25/data/benchmarks-2025.json.gz |
| non-incremental 数据 | Zenodo `16740866` | https://zenodo.org/records/16740866 |
| 官方 cvc5 包 | `cvc5-default.zip`，SHA-256 写在 `versions.env` | https://zenodo.org/records/15760304/files/cvc5-default.zip |
| 规则 | SMT-COMP 2025 rules PDF | https://smt-comp.github.io/2025/rules.pdf |

官方 metadata 有 450,474 个 non-incremental 条目、89 个 Logic；Zenodo README 的
89 个 archive 表尾写 450,472 个文件，这两个官方数字相差 2，仓库分别记录而不篡改。
竞赛官方 selection 最终
得到 129,361 个 Single Query instance、88 个 Logic、19 个 Division。各 Division
数量见 `docs/dataset-counts.md`。这里的“完整 benchmark”指完整原始库加官方选中集，
不是仓库自选样本。

## 调参入口与边界

Single Query 参数入口是：

```text
configs/cvc5/single-query.toml
```

参数合并顺序为 `default → division → division.logic`：

```toml
[default]
args = ["--quiet", "--fp-exp", "--use-portfolio"]

[division.QF_LinearIntArith]
args = ["--example-option=value"]

[division.QF_LinearIntArith.logic.QF_LIA]
args = ["--another-option"]
```

查询最终参数：

```bash
.venv/bin/smtcomp-cvc5-config configs/cvc5/single-query.toml \
  --track SingleQuery --division QF_LinearIntArith --logic QF_LIA
```

允许按 Track、Division、Logic 调参；禁止按 benchmark 名称、路径、checksum、预期
答案、运行顺序或已观察结果分派参数。不得修改官方 metadata、selection、scramble、
expected status、结果解析和评分公式。

资源限制直接采用 2025 PDF 和固定 `defs.py`：wall time 1200 秒、4 cores、
30 GiB memory。`24` 不是运行超时；它是对同一次正式结果筛选
`walltime_s <= 24` 的官方评分视图。代码来源：

- https://github.com/SMT-COMP/smt-comp.github.io/blob/smtcomp25/smtcomp/defs.py ；
- https://github.com/SMT-COMP/smt-comp.github.io/blob/smtcomp25/smtcomp/scoring.py 。

## 分 Division 运行

例如只调优并运行 `QF_LinearIntArith`：

```bash
make run TRACK=SingleQuery DIVISION=QF_LinearIntArith \
  CONFIG=configs/cvc5/single-query.toml \
  CVC5=.cache/solver/default/bin/cvc5 \
  RUN_ID=lia-v1
```

省略 `DIVISION=...` 会运行整个 Single Query Track。`make prepare` 只生成 BenchExec
XML；`make run` 会先生成 XML、由 BenchExec 执行，再用官方
`convert-benchexec-results` 生成评分输入。

官方选择和执行入口来源：

- selection：https://github.com/SMT-COMP/smt-comp.github.io/blob/smtcomp25/smtcomp/selection.py ；
- BenchExec 集成：https://github.com/SMT-COMP/smt-comp.github.io/blob/smtcomp25/smtcomp/benchexec.py ；
- BenchExec 项目：https://github.com/sosy-lab/benchexec 。

## 分 Division 评分

正式 Division 排名坐标是 `(SingleQuery, Division, performance)`。此外，官方还有
Rules PDF §7.3.1 定义的 Best Overall recognition：先在每个 Division 计算归一化正确率，
再按 `log10(N_D)` 加权汇总；它不是把正确题数直接相加。本仓库输出的 diagnostic sum
仍明确标为非官方，只用于调参观察。

```bash
make score TRACK=SingleQuery DIVISION=QF_LinearIntArith \
  PERFORMANCE=24 RUN_ID=lia-v1

make score TRACK=SingleQuery DIVISION=QF_LinearIntArith \
  PERFORMANCE=par RUN_ID=lia-v1

make score-overall TRACK=SingleQuery \
  RESULTS=.cache/official/data/results-sq-2025.json.gz
```

`make score-overall` 直接调用固定官方 `generate_website_page.py` 的
`normalized_correctness_score`，一次输出 cvc5 的 `par`、`seq`、`sat`、`unsat` 和 `24`
五项官方 Best Overall 分数与排名。官方页面：
https://smt-comp.github.io/2025/results/best-overall-single-query/ 。

Single Query 支持五个官方视图：

- `par`：原始并行结果；
- `seq`：官方 virtual sequential CPU-time 过滤；
- `sat`：只保留最终 sound status 为 SAT 的 benchmark；
- `unsat`：只保留最终 sound status 为 UNSAT 的 benchmark；
- `24`：只保留 wall time 不超过 24 秒的结果。

排序字段由官方代码定义：先最少 `error_score`，再最多
`correctly_solved_score`，再最少 wallclock/cpu time。错误 SAT/UNSAT 会计入 error，
不得隐藏。包装器直接 import 固定 checkout 中的 `smtcomp.scoring`，没有重写公式。
评分实现与定义来源：

- https://github.com/SMT-COMP/smt-comp.github.io/blob/smtcomp25/smtcomp/scoring.py ；
- https://github.com/SMT-COMP/smt-comp.github.io/blob/smtcomp25/smtcomp/results.py ；
- https://github.com/SMT-COMP/smt-comp.github.io/blob/smtcomp25/smtcomp/defs.py 。

### 已实跑的官方归档示例

以下不是虚构样例，也不是本地调参新成绩；输入是组织者发布的
`results-sq-2025.json.gz`，再由本仓库固定的官方 scorer 重新计算。来源：
https://github.com/SMT-COMP/smt-comp.github.io/blob/smtcomp25/data/results-sq-2025.json.gz 。

| Division | performance | solver | error | correctly solved |
|---|---|---|---:|---:|
| `QF_LinearIntArith` | `24` | cvc5 | 0 | 3,782 |
| `QF_LinearIntArith` | `par` | cvc5 | 0 | 5,370 |
| `QF_Bitvec` | `24` | cvc5 | 0 | 8,498 |

复现其中一项：

```bash
make score TRACK=SingleQuery DIVISION=QF_LinearIntArith PERFORMANCE=24 \
  RESULTS=.cache/official/data/results-sq-2025.json.gz
```

## 完整性检查

构建完成后应满足：

```bash
git -C .cache/smtcomp-tool rev-parse HEAD
git -C .cache/scrambler rev-parse HEAD
.cache/solver/default/bin/cvc5 --version
find -L .cache/benchmarks/non-incremental -name '*.smt2' | wc -l
find -L .cache/execution/benchmarks/files -name '*.yml' | wc -l
.venv/bin/python -m unittest discover -s tests -v
```

预期 revision、cvc5 SHA-256 和下载记录都在 `versions.env`。更详细的来源、选择依据、
评分和运行说明见 `docs/sources.md`、`docs/benchmark-selection.md`、
`docs/scoring.md` 和 `docs/operations.md`；这些文档均列出对应网址。
