# SMT-COMP 2025 cvc5 分 Track/Division 调优框架

本仓库为 SMT-COMP 2025 的五个实际举办 Track 提供独立的
`Track / Performance / Division / Logic` cvc5 调参、官方选择、执行和评分入口。
Cloud 2025 未举办，因此不伪造 Cloud 排名。构建完成必须通过 `make check-all-selections`；
任何少一道题、空 SMT2 或损坏 YAML 都会直接失败。

UnsatCore 有一个必须公开的官方资料缺口：规则只说由 sound Single Query solvers 的
“a selection”验证 core，但组织者没有发布最终 validator 身份列表。本仓库因此构建
所有公开资料能确定的 sound-solver 最大池，并在 manifest 中标记
`exact_organizer_pool=false`；它是可审计的实验证明，不冒充未知的最终私有选择。
因此 `make run TRACK=UnsatCore ...` 默认使用 `UC_VALIDATION_MODE=public-pool`；只有拿到
额外的组织者 validator 结果时才改为 `external`。

## Track 接口总览

| Track | 当前状态 | 参数配置 | 官方选择目录 | 结果目录 | 合法 performance |
|---|---|---|---|---|---|
| SingleQuery | 官方数据/执行/评分 | `configs/cvc5/SingleQuery/<performance>.toml` | `files` | `results_singlequery` | `24`, `par`, `seq`, `sat`, `unsat` |
| Incremental | 官方 trace executor/评分 | `configs/cvc5/Incremental/par.toml` | `files_inc` | `results_inc` | `par` |
| UnsatCore | 官方 core 生成/最大公开验证池/评分 | `configs/cvc5/UnsatCore/<performance>.toml` | `files_unsatcore` | `results_unsatcore` | `par`, `seq` |
| ModelValidation | 官方 Dolmen/评分 | `configs/cvc5/ModelValidation/<performance>.toml` | `files_model` | `results_model` | `par`, `seq` |
| Parallel | 官方 400 题选择/资源/评分 | `configs/cvc5/Parallel/par.toml` | `files_parallel` | `results_parallel` | `par` |

五个 Track 共用同一接口：

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

## 硬件与系统环境要求

### SMT-COMP 2025 官方比赛机器

普通四个 Track 不是在任意“4 核机器”上运行。官方 Machine Specifications 明确写明：
SingleQuery、Incremental、UnsatCore、ModelValidation 使用 SoSy-Lab BenchCloud 的
**168 台 apollon 节点**；每台节点配置为：

| 官方普通 Track 节点 | 规格 |
|---|---|
| CPU | Intel Xeon E3-1230 v5 @ 3.40 GHz |
| 物理核 | 4 cores，全部提供给 solver |
| 主机内存 | 33 GB RAM |
| 单次运行内存上限 | 30 GiB |
| 单次 wall-time 上限 | 1200 秒 |
| 单次 CPU-time 上限 | 4800 秒（1200 × 4） |
| 执行基础设施 | SoSy-Lab BenchExec/BenchCloud |

官方机器规格页：https://smt-comp.github.io/2025/specs/ 。规则 PDF 说明比赛在这 168 台
apollon 节点上通过 BenchExec 执行，并将每个 processor 的 4 cores 提供给 solver：
https://smt-comp.github.io/2025/rules.pdf 。

Parallel 使用另一台官方大机器：

| 官方 Parallel 环境 | 规格 |
|---|---|
| 整机 | 256 virtual cores、2 TB RAM |
| 每个正式 solver run | 128 cores、1000 GiB |
| 时间 | wall 1200 秒、CPU 153600 秒（1200 × 128） |
| 执行基础设施 | 与其他 Track 相同的 BenchExec-based infrastructure |

“256 virtual cores、2 TB”来自官方 Parallel 页面；“每个 run 分配 128 cores、1000 GiB”
来自固定 2025 `defs.py` 和其生成的 BenchExec XML。这是整机规格和单任务配额两个层次，
不能混为一谈。来源：https://smt-comp.github.io/2025/parallel_track/ 和
https://github.com/SMT-COMP/smt-comp.github.io/blob/smtcomp25/smtcomp/defs.py 。

### 官方软件执行环境

规则规定 solver 在与以下 competition image 相同安装环境的机器上运行：

```text
registry.gitlab.com/sosy-lab/benchmarking/competition-scripts/user:latest
```

2025 Solver Submission 页面说明该镜像基于 Ubuntu 24.04；提交 CI 也会在该镜像中下载
并运行 solver。正式复现应使用 Linux、BenchExec 容器模式和可用的 cgroups，而不是只
比较裸跑命令的时间。来源：https://smt-comp.github.io/2025/solver_submission/ 和
https://gitlab.com/sosy-lab/benchmarking/competition-scripts/#computing-environment-on-competition-machines 。

`seq` 不表示把执行限制改成单核；它是正式结果上的 virtual-sequential 评分视图。
`24` 也不是 24 秒 timeout，而是在正式 1200 秒运行之后应用 `walltime_s <= 24` 的评分
视图。若 CPU 型号、频率、内核、容器、cgroups、NUMA 或系统负载不同，正确性结果仍可
用于测试，但 wall/CPU time 不能声称与官方机器严格可比。

### 本地构建要求（非官方比赛机器规格）

以下仅是运行本仓库构建脚本的本地条件，不能替代上述官方环境：

- 官方 cvc5 和 trace executor 是 GNU/Linux x86-64 ELF，需 x86-64 Linux；Windows
  应通过 WSL2 使用；
- `make setup-all` 检查至少 100 GiB 可用磁盘，正式运行产生的结果空间另计；
- 两套 benchmark 压缩包约 8 GB；建议使用本地 Linux SSD；
- 需要 Bash、GNU Make、Python >= 3.11；ModelValidation 构建需要 Docker + buildx；
- `make smoke-all` 可在较小机器上检查功能，但不能产生官方硬件可比成绩。

WSL 文件系统建议：https://learn.microsoft.com/windows/wsl/filesystems 。

## 全 Track 一键构建

完整构建（包括两套 benchmark、两套 cvc5、trace executor、官方 Dolmen、公开可重建的
UnsatCore validator pool 和五个官方 selection）：

```bash
make setup-all
```

该目标读取 `configs/setup-all.env`，至少预留 100 GiB；ModelValidation 的官方构建需要
Docker + buildx，Debian/Ubuntu 会从当前机器配置的 APT 源安装。构建顺序和每一步都可
单独重跑：`system-deps → storage → setup → benchmarks → solver → cache →
execution-tools → validator pool → Dolmen → select-all → check-all-selections`。
来源分别见 `docs/sources.md` 与 https://smt-comp.github.io/2025/rules.pdf 。

开发机不必先生成几十万道题即可做真实小规模验收：

```bash
make smoke-all
```

它会实际运行两套官方 cvc5、官方 Incremental trace executor、官方 core 提取器、
可公开重建的多 solver validator manifest、官方 Dolmen，以及 Parallel dispatcher。
Parallel 此处只做功能测试；官方可比全量仍要求 128 cores/1000 GiB，并由
`make setup-all && make check-all-selections` 在资源充足机器完成。

## 固定的官方资产

| 资产 | 本仓库使用值 | 官方来源 |
|---|---|---|
| SMT-COMP 工具 | `b0faba09100a297a32544ac29a54feb4d5d174b4` | https://github.com/SMT-COMP/smt-comp.github.io/tree/b0faba09100a297a32544ac29a54feb4d5d174b4 |
| scrambler | `2f2dbcd69d98894031c6359add0a898cd071bd98` | https://github.com/SMT-COMP/scrambler/tree/2f2dbcd69d98894031c6359add0a898cd071bd98 |
| benchmark metadata | `benchmarks-2025.json.gz` | https://github.com/SMT-COMP/smt-comp.github.io/blob/smtcomp25/data/benchmarks-2025.json.gz |
| non-incremental 数据 | Zenodo `16740866` | https://zenodo.org/records/16740866 |
| incremental 数据 | Zenodo `15493096` | https://zenodo.org/records/15493096 |
| 官方 cvc5 包 | `cvc5-default.zip`，SHA-256 写在 `versions.env` | https://zenodo.org/records/15760304/files/cvc5-default.zip |
| 官方 cvc5 incremental 包 | `cvc5-inc.zip`，SHA-256 写在 `versions.env` | https://zenodo.org/records/15760304/files/cvc5-inc.zip |
| Incremental trace executor | 固定 release + SHA-256 | https://github.com/SMT-COMP/trace-executor/releases/tag/smtcomp2024-rc1 |
| ModelValidation validator | Dolmen commit `871b9de26643052dfcfa5b47ee23785f0b983219` | https://github.com/SMT-COMP/dolmen/tree/871b9de26643052dfcfa5b47ee23785f0b983219 |
| 规则 | SMT-COMP 2025 rules PDF | https://smt-comp.github.io/2025/rules.pdf |

官方 metadata 有 450,474 个 non-incremental 条目、89 个 Logic；Zenodo README 的
89 个 archive 表尾写 450,472 个文件，这两个官方数字相差 2，仓库分别记录而不篡改。
竞赛官方 selection 最终
得到 129,361 个 Single Query instance、88 个 Logic、19 个 Division。各 Division
数量见 `docs/dataset-counts.md`。这里的“完整 benchmark”指完整原始库加官方选中集，
不是仓库自选样本。

## 调参入口与边界

调参配置使用 `Track / Performance` 层级，Division 位于文件内部：

```text
configs/cvc5/
  SingleQuery/
    par.toml
    seq.toml
    24.toml
    sat.toml
    unsat.toml
  Incremental/par.toml
  UnsatCore/{par,seq}.toml
  ModelValidation/{par,seq}.toml
  Parallel/par.toml
```

全部 11 个合法 Track/Performance 配置均已生成；每个文件必须包含该 Track 的全部
Division，所以既能运行一个 Division，也能运行一个 Track/Performance 全量。
初始化缺失文件可执行 `make init-configs TRACK=<Track>`；已有调参配置不会被覆盖。实现入口是
`scripts/init_track_configs.py`。

参数合并顺序为 `default → division → division.logic`：

```toml
[default]
args = ["--fp-exp", "--use-portfolio"]

[division.QF_LinearIntArith]
args = ["--example-option=value"]

[division.QF_LinearIntArith.logic.QF_LIA]
args = ["--another-option"]
```

查询最终参数：

```bash
.venv/bin/smtcomp-cvc5-config configs/cvc5/SingleQuery/24.toml \
  --track SingleQuery --division QF_LinearIntArith --logic QF_LIA
```

允许按 Track、Division、Logic 调参；禁止按 benchmark 名称、路径、checksum、预期
答案、运行顺序或已观察结果分派参数。不得修改官方 metadata、selection、scramble、
expected status、结果解析和评分公式。

调参时必须以官方 cvc5 文档和当前本地 binary help 为证据，而不是靠记忆或杜撰参数名。
相关入口：

- **本地官方文档**：[`docs/cvc5-official-docs/options.html`](./docs/cvc5-official-docs/options.html)（cvc5 1.3.4 完整文档）
- 官方文档首页：https://cvc5.github.io/docs-ci/docs-main/
- 官方 options：https://cvc5.github.io/docs-ci/docs-main/options.html
- 本地速查指南：[`docs/cvc5-options-reference.md`](./docs/cvc5-options-reference.md)

本地速查文档总结了官方 cvc5 的 option 模块、theory 模块、变量命名、Boolean/非 Boolean 参数规则，以及对 `Track / Division / Logic` 的调参边界要求。
**调参前必须阅读本地官方文档中的参数定义，确保每个 option 在当前 cvc5 版本中存在且适用于目标 Track/Division/Logic。**

普通四个 Track 的资源限制直接采用 2025 PDF 和固定 `defs.py`：wall time 1200 秒、
4 cores、30 GiB memory。Parallel 是官方 128 cores、1000 GiB 的 BenchExec 限制；
虚拟核仍由操作系统映射到真实 CPU，不能把一台 14-thread 机器的功能冒烟测试称作
官方可比 Parallel 成绩。`24` 不是运行超时；它是对同一次正式结果筛选
`walltime_s <= 24` 的官方评分视图。代码来源：

- https://github.com/SMT-COMP/smt-comp.github.io/blob/smtcomp25/smtcomp/defs.py ；
- https://github.com/SMT-COMP/smt-comp.github.io/blob/smtcomp25/smtcomp/scoring.py 。

## 分 Division 运行

例如只调优并运行 `QF_LinearIntArith`：

```bash
make run TRACK=SingleQuery DIVISION=QF_LinearIntArith \
  PERFORMANCE=24 \
  CVC5=.cache/solver/default/bin/cvc5 \
  RUN_ID=lia-v1
```

省略 `CONFIG` 时，上述命令自动选择 `configs/cvc5/SingleQuery/24.toml`。
`PERFORMANCE=par` 会改选同目录的 `par.toml`。默认 `RUN_ID` 和 XML 文件名也包含
`Track/Division/Performance`，避免不同实验互相覆盖；仍可显式指定 `RUN_ID`。

Performance 只在启动运行前选择一套完整候选配置，并在之后选择评分视图；不会传给
cvc5，也不能根据单个 benchmark 的答案切换配置。每套配置必须重新运行整个 Division，
不同配置的最佳分数不能拼成同一份官方 submission。

省略 `DIVISION=...` 会使用同一 performance 文件中的全部官方 Division，运行整个
Track/Performance。`make prepare` 只生成 BenchExec
XML；`make run` 会先生成 XML、由 BenchExec 执行，再用官方
`convert-benchexec-results` 生成评分输入。特殊路径为：Incremental 通过官方 trace
executor 统计多个答案；ModelValidation 在转换前调用官方 Dolmen；UnsatCore 先生成
core 验证任务并要求验证证据；Parallel 使用官方 128-core/1000-GiB XML 限制。

其他 Track 的真实命令示例：

```bash
make run TRACK=Incremental DIVISION=QF_LinearIntArith PERFORMANCE=par RUN_ID=inc-lia-v1
make run TRACK=ModelValidation DIVISION=QF_LinearIntArith PERFORMANCE=seq RUN_ID=mv-lia-v1
make run TRACK=UnsatCore DIVISION=QF_LinearIntArith PERFORMANCE=par \
  UC_VALIDATION_MODE=public-pool RUN_ID=uc-lia-v1
make run TRACK=Parallel DIVISION=QF_LinearIntArith PERFORMANCE=par RUN_ID=parallel-lia-v1
```

官方选择和执行入口来源：

- selection：https://github.com/SMT-COMP/smt-comp.github.io/blob/smtcomp25/smtcomp/selection.py ；
- BenchExec 集成：https://github.com/SMT-COMP/smt-comp.github.io/blob/smtcomp25/smtcomp/benchexec.py ；
- BenchExec 项目：https://github.com/sosy-lab/benchexec 。

## 分 Division 评分

正式 Division 排名坐标是 `(Track, Division, performance)`；合法组合共 195 个，
由 `make score-matrix` 直接从固定官方 `defs.tracks` 生成。此外，官方还有
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
`normalized_correctness_score`，并只输出所选 Track 合法的 performance。官方页面：
https://smt-comp.github.io/2025/results/best-overall-single-query/ 。

Single Query 支持五个官方视图：

- `par`：原始并行结果；
- `seq`：官方 virtual sequential CPU-time 过滤；
- `sat`：只保留最终 sound status 为 SAT 的 benchmark；
- `unsat`：只保留最终 sound status 为 UNSAT 的 benchmark；
- `24`：只保留 wall time 不超过 24 秒的结果。

Incremental 与 Parallel 只有 `par`；UnsatCore 与 ModelValidation 有 `par` 和 `seq`。
评分器会拒绝不存在的组合，也会拒绝尚未验证的本地 ModelValidation/UnsatCore 结果。

排序字段由官方代码定义：先最少 `error_score`，再最多
`correctly_solved_score`，再最少 wallclock/cpu time。错误 SAT/UNSAT 会计入 error，
不得隐藏。包装器直接 import 固定 checkout 中的 `smtcomp.scoring`，没有重写公式。
评分实现与定义来源：

- https://github.com/SMT-COMP/smt-comp.github.io/blob/smtcomp25/smtcomp/scoring.py ；
- https://github.com/SMT-COMP/smt-comp.github.io/blob/smtcomp25/smtcomp/results.py ；
- https://github.com/SMT-COMP/smt-comp.github.io/blob/smtcomp25/smtcomp/defs.py 。

## 完整性检查

构建完成后应满足：

```bash
git -C .cache/smtcomp-tool rev-parse HEAD
git -C .cache/scrambler rev-parse HEAD
.cache/solver/default/bin/cvc5 --version
find -L .cache/benchmarks/non-incremental -name '*.smt2' | wc -l
find -L .cache/execution/benchmarks/files -name '*.yml' | wc -l
make check-all-selections
make smoke-all
.venv/bin/python -m unittest discover -s tests -v
```

预期 revision、cvc5 SHA-256 和下载记录都在 `versions.env`。更详细的来源、选择依据、
评分和运行说明见 `docs/sources.md`、`docs/benchmark-selection.md`、
`docs/scoring.md` 和 `docs/operations.md`；这些文档均列出对应网址。
