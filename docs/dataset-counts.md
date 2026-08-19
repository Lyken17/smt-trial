# SMT-COMP 2025 每个 Track 的 benchmark 数量

本页回答完整竞赛各 Track 的数据量问题；`make check-all-selections` 会逐项核对这些
官方 selection 总数、映射、非空 SMT2 与 YAML 引用。

这里的“数据集数量”统一解释为 **benchmark instance 数量**。必须区分完整 SMT-LIB
2025 元数据和经过官方 seed/selection 最终选中的 Track 数据。

## 完整 2025 benchmark 库

| 发布物 | benchmark 数 | Logic 数 |
|---|---:|---:|
| Non-incremental（官方 metadata 条目） | 450,474 | 89 |
| Incremental | 44,708 | 41 |
| **合计** | **495,182** | — |

Zenodo 发布物自己的 README 将 89 个 archive 的文件数合计写为 **450,472**，而固定
官方 `benchmarks-2025.json.gz` 中有 **450,474** 个 non-incremental 条目。两者相差
2；本文 Track selection 数量由官方 metadata 和 selection 代码计算，不把这个上游
差异悄悄改成同一个数字。Zenodo README：
https://zenodo.org/records/16740866/files/README.md 。

## 各 Track 最终选择总数

| Track | benchmark 数 | Logic 数 | 说明 |
|---|---:|---:|---|
| SingleQuery | 129,361 | 88 | 官方普通 selection |
| Incremental | 22,942 | 39 | 按文件计数；一个文件可含多个 `check-sat` |
| ModelValidation | 59,762 | 36 | SAT/model 候选 |
| UnsatCore | 70,604 | 75 | UNSAT 且至少两个 assertion 的候选 |
| Parallel | 400 | 27 | 200 hard + 200 unsolved |
| Cloud | 0 | 0 | 2025 未举办 |
| ProofExhibition | 不适用 | 不适用 | 2025 selector/scorer 没有常规固定排名数据集 |
| UnsatCoreValidation | 动态生成 | 不适用 | 由 UnsatCore 输出生成验证任务 |

ModelValidation 和 UnsatCore 会使用 2025 SingleQuery 当前结果辅助确定候选，因此重现
这些数字时必须保留官方 2025 result metadata。

## SingleQuery：按 Division

| Division | 数量 | Division | 数量 |
|---|---:|---|---:|
| QF_Datatypes | 552 | QF_Equality | 3,821 |
| QF_Equality+LinearArith | 1,936 | QF_Equality+NonLinearArith | 631 |
| QF_Equality+Bitvec | 8,489 | QF_LinearIntArith | 6,040 |
| QF_LinearRealArith | 842 | QF_Bitvec | 10,703 |
| QF_FPArith | 1,600 | QF_NonLinearIntArith | 12,280 |
| QF_NonLinearRealArith | 3,104 | QF_Strings | 34,283 |
| Equality | 4,426 | Equality+LinearArith | 16,936 |
| Equality+MachineArith | 8,931 | Equality+NonLinearArith | 10,232 |
| Arith | 1,666 | Bitvec | 1,040 |
| FPArith | 1,849 | **合计** | **129,361** |

## Incremental：按 Division

| Division | 数量 | Division | 数量 |
|---|---:|---|---:|
| QF_Equality | 889 | QF_Equality+LinearArith | 2,031 |
| QF_Equality+NonLinearArith | 512 | QF_Equality+Bitvec | 1,832 |
| QF_Equality+Bitvec+Arith | 1,046 | QF_LinearIntArith | 69 |
| QF_LinearRealArith | 10 | QF_Bitvec | 1,305 |
| QF_FPArith | 9,752 | QF_NonLinearIntArith | 119 |
| Equality | 2,033 | Equality+LinearArith | 959 |
| Equality+MachineArith | 4 | Equality+NonLinearArith | 2,342 |
| Arith | 11 | Bitvec | 18 |
| FPArith | 10 | **合计** | **22,942** |

## ModelValidation：按 Division

| Division | 数量 | Division | 数量 |
|---|---:|---|---:|
| QF_Datatypes | 1,943 | QF_Equality | 1,571 |
| QF_Equality+LinearArith | 891 | QF_Equality+NonLinearArith | 475 |
| QF_Equality+Bitvec | 475 | QF_ADT+BitVec | 5,249 |
| QF_ADT+LinArith | 772 | QF_LinearIntArith | 4,903 |
| QF_LinearRealArith | 606 | QF_Bitvec | 8,211 |
| QF_FPArith | 24,369 | QF_NonLinearIntArith | 7,519 |
| QF_NonLinearRealArith | 2,778 | **合计** | **59,762** |

## UnsatCore：按 Division

| Division | 数量 | Division | 数量 |
|---|---:|---|---:|
| QF_Datatypes | 400 | QF_Equality | 2,263 |
| QF_Equality+LinearArith | 591 | QF_Equality+NonLinearArith | 266 |
| QF_Equality+Bitvec | 2,471 | QF_LinearIntArith | 1,069 |
| QF_LinearRealArith | 201 | QF_Bitvec | 2,949 |
| QF_FPArith | 13,643 | QF_NonLinearIntArith | 2,502 |
| QF_NonLinearRealArith | 300 | QF_Strings | 6,626 |
| Equality | 2,698 | Equality+LinearArith | 23,881 |
| Equality+MachineArith | 4,361 | Equality+NonLinearArith | 5,682 |
| Arith | 386 | Bitvec | 300 |
| FPArith | 15 | **合计** | **70,604** |

## Parallel：按 Division

| Division | 数量 | Division | 数量 |
|---|---:|---|---:|
| QF_Equality+LinearArith | 54 | QF_Equality+Bitvec | 38 |
| QF_LinearIntArith | 48 | QF_LinearRealArith | 36 |
| QF_Bitvec | 24 | QF_FPArith | 9 |
| QF_NonLinearIntArith | 23 | QF_NonLinearRealArith | 23 |
| Equality+MachineArith | 91 | Bitvec | 24 |
| FPArith | 30 | **合计** | **400** |

## 计算方法与来源网址

数量由固定提交中的官方对象直接计算：

```python
config = smtcomp.defs.Config(Path(".cache/official/data"))
smtcomp.selection.helper(config, track).filter(selected=True)
smtcomp.selection.helper_aws_selection(config).filter(selected=True)
```

- 官方 benchmark 元数据：
  https://github.com/SMT-COMP/smt-comp.github.io/blob/smtcomp25/data/benchmarks-2025.json.gz
- 官方 selection 实现：
  https://github.com/SMT-COMP/smt-comp.github.io/blob/smtcomp25/smtcomp/selection.py
- 官方 Track/Division/Logic 映射：
  https://github.com/SMT-COMP/smt-comp.github.io/blob/smtcomp25/smtcomp/defs.py
- 2025 submission seed 文件：
  https://github.com/SMT-COMP/smt-comp.github.io/tree/smtcomp25/submissions
- 2018–2025 result metadata：
  https://github.com/SMT-COMP/smt-comp.github.io/tree/smtcomp25/data
- non-incremental Zenodo：
  https://doi.org/10.5281/zenodo.16740866
- incremental Zenodo：
  https://doi.org/10.5281/zenodo.15493096
- Parallel/Cloud 官方说明：
  https://smt-comp.github.io/2025/parallel_track/
