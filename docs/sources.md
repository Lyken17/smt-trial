# 官方来源与版本

## 一手来源清单

| 内容 | 官方地址 | 本仓库使用方式 |
|---|---|---|
| SMT-COMP 2025 首页 | https://smt-comp.github.io/2025/ | 年份、公告、结果入口 |
| 2025 Rules PDF | https://smt-comp.github.io/2025/rules.pdf | 竞赛规范 |
| Parallel Track | https://smt-comp.github.io/2025/parallel_track/ | 机器描述、20 分钟、400 个实例、Cloud 未举办 |
| Model Validation | https://smt-comp.github.io/2025/model/ | 模型输出及验证约束 |
| Solver submission | https://smt-comp.github.io/2025/solver_submission/ | Ubuntu 24.04、JSON、Zenodo final archive |
| Results | https://smt-comp.github.io/2025/results/ | 官方结果及 Division 页面 |
| 组织与评分代码 | https://github.com/SMT-COMP/smt-comp.github.io | 官方 `smtcomp25` tag，提交 `b0faba0...` |
| 官方 scrambler | https://github.com/SMT-COMP/scrambler | 固定提交 `2f2dbcd...` |
| benchmark 提交流程 | https://github.com/SMT-LIB/benchmark-submission | SMT-LIB 数据进入上游的流程 |
| 2025 non-incremental | https://doi.org/10.5281/zenodo.16740866 | 完整逻辑归档和 Zenodo 校验和 |
| 2025 incremental | https://doi.org/10.5281/zenodo.15493096 | 完整逻辑归档和 Zenodo 校验和 |
| cvc5 2025 archive | https://zenodo.org/records/15760304 | 官方提交包与系统描述 |
| BenchExec | https://github.com/sosy-lab/benchexec | 官方生成的 XML 所使用的资源执行器 |
| Incremental trace executor | https://github.com/SMT-COMP/trace-executor/releases/tag/smtcomp2024-rc1 | 官方 2025 代码指定的发布包，本仓库额外验证 SHA-256 |
| Model validator | https://github.com/SMT-COMP/dolmen/tree/871b9de26643052dfcfa5b47ee23785f0b983219 | `defs.py` 固定的 Dolmen commit |

## 精确文件依据

### 官方 2025 版本

本仓库使用 SMT-COMP 官方发布的 `smtcomp25` Git tag：

- 官方 tags 列表：https://github.com/SMT-COMP/smt-comp.github.io/tags
- `smtcomp25` tag 源码：https://github.com/SMT-COMP/smt-comp.github.io/tree/smtcomp25
- tag 指向的完整 commit：
  https://github.com/SMT-COMP/smt-comp.github.io/commit/b0faba09100a297a32544ac29a54feb4d5d174b4

`smtcomp25` 直接指向
`b0faba09100a297a32544ac29a54feb4d5d174b4`（2025-08-14）。代码中固定
完整 SHA，文档中同时保留 tag URL：前者确保字节级可重现，后者说明
这个 SHA 的官方身份。

所有以下路径均指官方仓库提交
`b0faba09100a297a32544ac29a54feb4d5d174b4`（官方 tag `smtcomp25`）：

- https://github.com/SMT-COMP/smt-comp.github.io/blob/smtcomp25/smtcomp/defs.py
  ：Track、Division、Logic、2025 年份参数、时间、内存、核心、
  selection seed、移除的非法 benchmark；
- https://github.com/SMT-COMP/smt-comp.github.io/blob/smtcomp25/smtcomp/selection.py
  ：普通 Track 与 Parallel/AWS 的选择算法；
- https://github.com/SMT-COMP/smt-comp.github.io/blob/smtcomp25/smtcomp/scramble_benchmarks.py
  ：scramble ID、参数、文件布局与映射 CSV；
- https://github.com/SMT-COMP/smt-comp.github.io/blob/smtcomp25/smtcomp/benchexec.py
  ：BenchExec XML 的 wall/CPU/memory/core 限制；
- https://github.com/SMT-COMP/smt-comp.github.io/blob/smtcomp25/smtcomp/scoring.py
  ：正确数、错误数、时间、24 秒过滤、虚拟 sequential 分数；
- https://github.com/SMT-COMP/smt-comp.github.io/blob/smtcomp25/smtcomp/results.py
  ：结果读取和 benchmark/Division 连接；
- https://github.com/SMT-COMP/smt-comp.github.io/blob/smtcomp25/smtcomp/main.py
  ：`create-cache`、`select-and-scramble`、`scramble-aws`、
  `show-scores` 等官方命令；
- https://github.com/SMT-COMP/smt-comp.github.io/blob/smtcomp25/data/benchmarks-2025.json.gz
  ：完整 benchmark 身份、逻辑、状态、assert 数、
  incremental check-sat 数；
- https://github.com/SMT-COMP/smt-comp.github.io/tree/smtcomp25/data
  ：选择算法需要的历史结果及 2025 官方结果；
- https://github.com/SMT-COMP/smt-comp.github.io/tree/smtcomp25/submissions
  ：参赛 solver、Track/Logic 参与范围和 seed；
- https://github.com/SMT-COMP/smt-comp.github.io/blob/smtcomp25/submissions/cvc5.json
  ：cvc5 2025 提交包、SHA-256、命令和参与范围。

`versions.env` 是所有外部版本的单一入口。`scripts/fetch_official.py` 从固定提交
下载元数据和 submission 文件；Zenodo 文件则逐个使用 API 返回的 checksum 验证。

## cvc5 官方提交

SingleQuery/UnsatCore/ModelValidation 使用 `cvc5-default.zip`，SHA-256 为
`627082d4c9b70d74787fbb8f78214fd4bc20924de1be294f658df4ea2e20c63f`。
Incremental 使用 `cvc5-inc.zip`，SHA-256 为
`e5c29e6ae5a6193e06812f62c7eeb574f64939dd3ff61f08ae2ac87e6296fc48`。
cvc5 2025 官方 submission 没有报名 Parallel；本项目的 Parallel cvc5 是研究性
调参项，评分与数据仍严格使用 2025 Parallel 规则，不能称为官方参赛结果。
