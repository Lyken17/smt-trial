# SMT-COMP 2025 合法评分三元组

本页保留完整竞赛矩阵作为后续路线图；当前实际支持范围只有表中的 SingleQuery
95 个三元组，其他 Track 尚未纳入当前可用性承诺。

事实来源：

- 官方 Track/Division 定义：https://github.com/SMT-COMP/smt-comp.github.io/blob/smtcomp25/smtcomp/defs.py
- 官方 performance 规则：https://smt-comp.github.io/2025/rules.pdf
- 官方评分实现：https://github.com/SMT-COMP/smt-comp.github.io/blob/smtcomp25/smtcomp/scoring.py

下面每一行表示该行的每个 Division 与每个 Performance 两两组合；不同 Track
之间不能交叉组合。完整展开结果由 `make score-matrix` 输出，共 195 个三元组。

| Track | Division 集合 | Performance 集合 | 三元组数 |
|---|---|---|---:|
| SingleQuery | `Arith`, `Bitvec`, `Equality`, `Equality_LinearArith`, `Equality_MachineArith`, `Equality_NonLinearArith`, `FPArith`, `QF_Bitvec`, `QF_Datatypes`, `QF_Equality`, `QF_Equality_Bitvec`, `QF_Equality_LinearArith`, `QF_Equality_NonLinearArith`, `QF_FPArith`, `QF_LinearIntArith`, `QF_LinearRealArith`, `QF_NonLinearIntArith`, `QF_NonLinearRealArith`, `QF_Strings` | `par`, `seq`, `24`, `sat`, `unsat` | 95 |
| Incremental | `Arith`, `Bitvec`, `Equality`, `Equality_LinearArith`, `Equality_MachineArith`, `Equality_NonLinearArith`, `FPArith`, `QF_Bitvec`, `QF_Equality`, `QF_Equality_Bitvec`, `QF_Equality_Bitvec_Arith`, `QF_Equality_LinearArith`, `QF_Equality_NonLinearArith`, `QF_FPArith`, `QF_LinearIntArith`, `QF_LinearRealArith`, `QF_NonLinearIntArith` | `par` | 17 |
| UnsatCore | `Arith`, `Bitvec`, `Equality`, `Equality_LinearArith`, `Equality_MachineArith`, `Equality_NonLinearArith`, `FPArith`, `QF_Bitvec`, `QF_Datatypes`, `QF_Equality`, `QF_Equality_Bitvec`, `QF_Equality_LinearArith`, `QF_Equality_NonLinearArith`, `QF_FPArith`, `QF_LinearIntArith`, `QF_LinearRealArith`, `QF_NonLinearIntArith`, `QF_NonLinearRealArith`, `QF_Strings` | `par`, `seq` | 38 |
| ModelValidation | `QF_ADT_BitVec`, `QF_ADT_LinArith`, `QF_Bitvec`, `QF_Datatypes`, `QF_Equality`, `QF_Equality_Bitvec`, `QF_Equality_LinearArith`, `QF_Equality_NonLinearArith`, `QF_FPArith`, `QF_LinearIntArith`, `QF_LinearRealArith`, `QF_NonLinearIntArith`, `QF_NonLinearRealArith` | `par`, `seq` | 26 |
| Parallel | `Arith`, `Bitvec`, `Equality`, `Equality_LinearArith`, `Equality_MachineArith`, `Equality_NonLinearArith`, `FPArith`, `QF_Bitvec`, `QF_Datatypes`, `QF_Equality`, `QF_Equality_Bitvec`, `QF_Equality_LinearArith`, `QF_Equality_NonLinearArith`, `QF_FPArith`, `QF_LinearIntArith`, `QF_LinearRealArith`, `QF_NonLinearIntArith`, `QF_NonLinearRealArith`, `QF_Strings` | `par` | 19 |

调用格式：

```bash
make score \
  TRACK=UnsatCore \
  DIVISION=QF_LinearIntArith \
  PERFORMANCE=seq \
  RESULTS=results/uc-v1/results_unsatcore
```

`KIND` 是 `PERFORMANCE` 的兼容旧名。实现会在读取结果前验证整个三元组；合法
矩阵由 `src/smtcomp_harness/matrix.py` 从固定 `smtcomp25` 官方定义动态生成。
