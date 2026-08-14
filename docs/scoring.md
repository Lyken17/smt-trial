# 官方 Division 评分与竞赛级 Recognition

当前已接通并验收的运行路径只有 SingleQuery；其他 Track 的评分语义保留为官方
规则参考和后续实现目标。

本仓库的 `smtcomp-score` 直接导入固定提交的：

```python
smtcomp.results.helper_get_results
smtcomp.scoring.add_disagreements_info
smtcomp.scoring.benchmark_scoring
smtcomp.scoring.filter_for
smtcomp.scoring.division_score
```

因此不会另写一套“看起来类似”的计分公式。

## 官方排序字段

评分是两层分开的：Track 之间不混排；每个 Track 内的每个 Division
独立排名和颁奖。Logic 结果汇总到其所属 Division，不另立官方奖项。

Division 内依次比较：

1. `error_score` 越少越好；
2. `correctly_solved_score` 越多越好；
3. `wallclock_time_score` 越少越好；
4. `cpu_time_score` 越少越好。

SingleQuery 与 Parallel 中，sound solver 的正确 SAT/UNSAT 各得 1；错误答案计
error。Incremental、UnsatCore 和 ModelValidation 使用各自 Track 的官方公式，见
[Track 文档](tracks-and-divisions.md)。发生 solver disagreement 时，官方代码先计算
sound solver 和 sound status，并排除 disagreement benchmark 后再计分。

具体公式：Incremental 累加 `nb_answers`；UnsatCore 对有效 UNSAT core
累加 `asserts - nb_answers`（`nb_answers` 是 core size）；ModelValidation 对每个
通过验证的 SAT model 加 1。

## `kind=24`

官方 `scoring.py` 定义：

```text
twentyfour := walltime_s <= 24
```

`filter_for(Kind.twentyfour, ...)` 只保留满足该条件的运行，再计算 Division 分数。
这不是把 solver timeout 改成 24 秒。正式执行仍按 1200 秒 wall limit；否则无法与
官方 24 视图一致，也会错误处理 24 秒后给出错误答案的运行。

## Parallel 与 virtual sequential

- `kind=par`：使用实际 wall/CPU 运行结果，所有常规 Track 都有；
- `kind=seq`：官方 `virtual_sequential_score` 仅保留总 CPU time 不超过 1200 秒的
  结果，只对 SingleQuery、UnsatCore 和 ModelValidation 计算；
- `kind=24`：SingleQuery 专有的 24 秒 wall-time score；
- `kind=sat/unsat`：SingleQuery 专有的 SAT/UNSAT 子集分数。

Incremental 和 Parallel Track 只有 `par`。本仓库会拒绝规则不允许的
Track/kind 组合。

## 竞赛级评比

2025 在 Division score 之上还有三种 competition-wide recognition：

- Best Overall：按 Division 规模归一化后汇总；
- Biggest Lead：比较各 Division 第一名相对第二名的领先幅度；
- Largest Contribution：比较移除该 solver 后 virtual best solver 的损失。

`make score` 计算官方 Division score。`make score-overall` 直接复用固定官方
`generate_website_page.py` 的归一化实现，计算 Rules PDF §7.3.1 的 Best Overall。
`NON-OFFICIAL all-division diagnostic sum` 仍只是正确题数/时间的调参辅助值，不是上述
任何官方 recognition。

## 单 Division 和诊断值

```bash
.venv/bin/smtcomp-score --data .cache/official/data \
  --track SingleQuery --kind 24 --division QF_LinearIntArith result.json.gz
```

`--track`、`--division` 和 `--kind/--performance` 都是必填项。命令同时输出一个
明确标注为非官方的诊断值；因为这里只选择了一个 Division，该值等于该 Division
行，不能作为跨 Division 官方奖项。运行 `make score-matrix` 可得到全部 195 个
合法 `(Track, Division, Performance)` 三元组。

Single Query 全量 Best Overall：

```bash
make score-overall TRACK=SingleQuery \
  RESULTS=.cache/official/data/results-sq-2025.json.gz
```

该入口不需要 `DIVISION` 或 `PERFORMANCE`，一次计算五种 performance；默认只显示
`cvc5`。官方结果页面：
https://smt-comp.github.io/2025/results/best-overall-single-query/ 。

对本地 BenchExec 结果，包装器会拒绝尚含
`ModelNotValidated` 的 ModelValidation 结果，也会拒绝没有
`validation_attempted` 证据的 UnsatCore 结果。官方 organizer JSON(.gz)
被视为已完成组委会验证的定稿数据。

## 本页来源网址

- https://github.com/SMT-COMP/smt-comp.github.io/blob/smtcomp25/smtcomp/scoring.py
- https://github.com/SMT-COMP/smt-comp.github.io/blob/smtcomp25/smtcomp/results.py
- https://github.com/SMT-COMP/smt-comp.github.io/blob/smtcomp25/smtcomp/main.py
- https://github.com/SMT-COMP/smt-comp.github.io/blob/smtcomp25/smtcomp/generate_website_page.py
- https://smt-comp.github.io/2025/rules.pdf
- https://smt-comp.github.io/2025/results/
