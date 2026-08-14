# cvc5 配置、硬件和不可修改项

## 唯一调参面

当前受支持的调参面是 `configs/cvc5/SingleQuery/<Performance>.toml`。每个文件包含
SingleQuery 全部 19 个 Division，Division/Logic 参数在文件内部覆盖。其他 Track 当前
没有可用 TOML，不得把其代码骨架声明为已经完成复现。

配置目录先按 Track 分层，再按 Performance 分文件。SingleQuery 当前包含 5 个配置。
`24` 仍是结果的评分视图，不是 24 秒运行限制；文件名中的 `24`
表示该次完整重跑以 24 score 为优化目标。

参数合并顺序是 `default` → `division` → `division.logic`。后层增加的 cvc5 参数
由 cvc5 自己按命令行规则解释。配置验证器拒绝时间/资源/输入语言等 harness-owned
选项；运行前还应以对应官方 cvc5 的 `--help` 验证每个参数。

`smtcomp-cvc5-dispatch` 唯一读取的 benchmark 内容是标准 `set-logic` 声明；它不会
读取 `:status`，也不会把文件身份传给配置层。

配置文件在 `[meta]` 中固定 `performance`。`make prepare/run` 会核对命令行
Performance 与该字段；不匹配就停止。Division 只选择文件内部的一个 Division，省略
Division 则运行全部 19 个。Performance 不会进入 solver dispatch。默认调用示例：

```bash
make run TRACK=SingleQuery DIVISION=QF_LinearIntArith PERFORMANCE=24
make score TRACK=SingleQuery DIVISION=QF_LinearIntArith PERFORMANCE=24
```

它们默认共用自动生成的 `RUN_ID=SingleQuery-QF_LinearIntArith-24`。切换到 `par` 会
选择 `configs/cvc5/SingleQuery/par.toml` 和另一结果目录。省略 `DIVISION` 可对该
Track/Performance 做全量运行。不同 performance 文件代表不同候选 submission；不得把
五个文件各自的最好分数拼接成一份 submission。

允许：启发式、decision mode、theory-specific option、随机 seed 的固定 portfolio、
Parallel Track 的线程/portfolio 策略，以及按 Division/Logic 分流。

禁止：

- benchmark 名、family、路径、hash、scramble ID、顺序、期望状态驱动的参数；
- 修改官方 benchmark、metadata、历史结果、selected set 或 status；
- 修改 wall/CPU/memory/core 上限；
- 修改或包裹结果以隐藏错误 SAT/UNSAT；
- 修改官方 scoring、soundness、model/core validation；
- 用 24 秒 timeout 代替官方 24 score filter；
- 把本项目的 cvc5 Parallel 研究结果称为 cvc5 的 SMT-COMP 2025 官方提交结果。

## 普通 Track 执行限制

官方 `defs.py` 和 `benchexec.py` 生成：

- wall time：1200 秒；
- CPU limit：`1200 * 4 = 4800` CPU 秒；
- cores：4；
- memory：30 GiB；
- 正式节点要求：`Intel Xeon E3-1230 v5 @ 3.40 GHz`；
- solver submission 页面说明基础容器为 Ubuntu 24.04。

因此“sequential”不是只能占一个 core；2025 官方普通 Track 的 BenchExec envelope
是 4 cores。若要做严格可比的 wall time，CPU 型号、频率、NUMA、内核、容器和系统
负载也必须一致。

## Parallel 机器与执行器限制

官方网页和代码描述的是两个层次：

- Parallel 页面：一台机器 **256 virtual cores、2 TB memory**；
- 固定提交 `defs.py`/BenchExec：`cpuCores_parallel=128`、
  `memlimit_M_parallel=1000 GiB`、wall 1200 秒、CPU limit `1200*128` 秒。

本仓库的 canonical config 使用实际官方执行器数值 128/1000 GiB；文档同时保留
机器规格，不能偷偷把其中一个当成另一个。没有相同硬件时可以做功能测试，但耗时
不能与官方结果直接横向比较。

## 配置变更记录

每次结果至少记录：Git commit、config SHA-256、cvc5 archive SHA-256、Track、Kind、
Division、host CPU、物理/逻辑 core、RAM、OS、kernel、wall/CPU score、correct、error。

## 本页来源网址

- https://github.com/SMT-COMP/smt-comp.github.io/blob/smtcomp25/smtcomp/defs.py
- https://github.com/SMT-COMP/smt-comp.github.io/blob/smtcomp25/smtcomp/benchexec.py
- https://smt-comp.github.io/2025/parallel_track/
- https://smt-comp.github.io/2025/solver_submission/
- https://github.com/SMT-COMP/smt-comp.github.io/blob/smtcomp25/submissions/cvc5.json
- https://zenodo.org/records/15760304
