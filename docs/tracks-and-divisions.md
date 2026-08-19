# Track、Division 与数据边界

下表描述官方 2025 竞赛本身；本仓库支持其中五个实际举办且具有常规评分的 Track。

Division/Logic 映射不在本仓库复制维护，而是在运行时直接读取官方
`smtcomp.defs.tracks`，避免表格与官方代码漂移。可用
`.venv/bin/smtcomp export-division-tracks FILE` 导出机器可读映射。

| Track | 输入/目标 | 选择和评分差异 | 2025 状态 |
|---|---|---|---|
| SingleQuery | 非增量公式，一次 SAT/UNSAT 查询 | 正确解数优先，错误使 solver 在相应 Division 不 sound | 正式 |
| Incremental | 多个 `check-sat` | 按正确回答总数计分；任一 incremental error 计错误 | 正式 |
| UnsatCore | 候选 UNSAT、至少两个 assertion | 验证 core；分数为 assertion 数减 core 大小 | 正式 |
| ModelValidation | 候选 SAT | solver 模型由官方验证器验证 | 实验性 |
| ProofExhibition | proof 输出 | 2025 官方 `scoring.py` 明确没有常规 score 实现 | 展示/实验性 |
| Parallel | 非增量困难实例，一台大机器单实例运行 | 400 个实例；允许 portfolio；parallel score | 实验性、已举办 |
| Cloud | 分布式云 | 与 Parallel 共用 AWS 选择代码，但执行不同 | **2025 未举办** |
| UnsatCoreValidation | UnsatCore 的验证辅助 Track | 内部验证流程，不是独立 solver 排名 | 辅助 |

普通 Track 中包含诸如 `QF_LinearIntArith`、`QF_NonLinearIntArith`、
`QF_Bitvec`、`Equality+MachineArith`、`Arith` 等 Division；每个 Division 又由
若干 SMT-LIB Logic 组成。例如 LIA 属于 `Arith`，QF_LIA 属于
`QF_LinearIntArith`。不要把 Logic（如 LIA）误称为 Division。

本项目允许按 Division 配置，也允许在 Division 内按 Logic 进一步配置：

```toml
[division.QF_LinearIntArith]
args = ["--some-division-option"]

[division.QF_LinearIntArith.logic.QF_LIA]
args = ["--some-logic-option"]
```

禁止出现 benchmark 文件名、family、hash、期望状态或 scramble ID。

各 Track 和 Division 的实际数量见 [dataset-counts.md](dataset-counts.md)。

## 本页来源网址

- https://github.com/SMT-COMP/smt-comp.github.io/blob/smtcomp25/smtcomp/defs.py
- https://smt-comp.github.io/2025/
- https://smt-comp.github.io/2025/parallel_track/
- https://smt-comp.github.io/2025/model/
- https://smt-comp.github.io/2025/results/
