# Single Query 操作手册

当前只承诺 SMT-COMP 2025 Single Query 可完整构建、运行和评分。

## 构建

```bash
make setup-single-query
```

等价的可恢复分步命令：

```bash
make system-deps
make storage-single-query
make setup
make benchmarks-single-query
make solver-single-query
make cache
make select-single-query
```

`make system-deps` 读取 `configs/setup-single-query.env`。Debian/Ubuntu 使用该机器
现有的 APT 软件源；交互终端允许 sudo 提示当前用户输入密码。其他发行版只要已经
提供配置中的等价命令和 Python venv 即可通过，否则应使用其本机包管理器安装。
仓库不固定区域镜像、发行版代号、CPU 架构、用户名或 sudo 密码。APT 包说明：
https://packages.ubuntu.com/ 。

`make storage-single-query` 根据发布物 README 的约 78 GB 解压体积预检磁盘。普通
Linux 默认把所有内容放在仓库 `.cache`。当 `CACHE_PLACEMENT=auto` 且检测到仓库位于
WSL 的 Windows 挂载盘时，才使用当前用户的 `${XDG_CACHE_HOME:-$HOME/.cache}` 并在
工作区建立符号链接；已有有效链接会复用。任何主机都可通过绝对路径
`EXTERNAL_CACHE_ROOT` 显式选择其他大容量 filesystem。路径只影响存储位置，不能改
归档内容、selection 输入或输出；删除缓存后只需重跑对应 make 目标。来源：
https://zenodo.org/records/16740866/files/README.md ；WSL 存储建议：
https://learn.microsoft.com/windows/wsl/filesystems 。

`make setup` 固定官方工具和 scrambler revision，建立 `.venv` 并编译 scrambler。
官方工具：https://github.com/SMT-COMP/smt-comp.github.io 。官方 scrambler：
https://github.com/SMT-COMP/scrambler 。固定值见 `versions.env`。

`make benchmarks-single-query` 只处理 Zenodo non-incremental record：
https://zenodo.org/records/16740866 。每个压缩包下载完成后先验证 Zenodo checksum，
再检查 tar member 不含绝对路径或 `..`，最后展开。不会下载 incremental record。
默认并行展开 4 个 archive；通过 `EXTRACT_JOBS=N` 可覆盖。它只控制本地解压并发，
不参与 benchmark 选择或评分。worker-pool 文档：
https://docs.python.org/3/library/concurrent.futures.html 。

`make solver-single-query` 只处理官方 cvc5 default archive：
https://zenodo.org/records/15760304/files/cvc5-default.zip 。不会下载 `cvc5-inc.zip`。

`make cache` 直接运行官方 `create-cache`。`make select-single-query` 通过可恢复包装器
直接调用固定版本的官方 `selection.helper`、`create_scramble_id` 和 `scramble_file`；
只有 yml 与 scrambled SMT2 都存在的任务才跳过。选择代码来源：
https://github.com/SMT-COMP/smt-comp.github.io/blob/smtcomp25/smtcomp/selection.py 。
本地 scramble 并发默认由 `SELECTION_JOBS=auto` 按 CPU 数确定并限制到最多 16；可用
正整数覆盖，只影响构建时间。

若选择被中断，直接重跑 `make select-single-query`；包装器会重写完整官方映射并只
补缺 yml/SMT2。官方选中的
`QF_ABV/2019-Mann/ridecore-qf_abv-bug.smt2` 原文件约 1.1 GB，在内存受限的 WSL
上可能使 scrambler 被系统终止。此时 selection 仍不完整，不能把 129,360 个 yml
报告为 129,361；应提高 WSL memory/swap 后重跑。WSL 配置说明：
https://learn.microsoft.com/windows/wsl/wsl-config#wslconfig 。

## 调参、运行、评分

只修改 `configs/cvc5/single-query.toml` 中目标 Division/Logic 的 `args`。例如：

```bash
make run TRACK=SingleQuery DIVISION=QF_LinearIntArith \
  CONFIG=configs/cvc5/single-query.toml \
  CVC5=.cache/solver/default/bin/cvc5 RUN_ID=lia-v1

make score TRACK=SingleQuery DIVISION=QF_LinearIntArith \
  PERFORMANCE=24 RUN_ID=lia-v1

make score TRACK=SingleQuery DIVISION=QF_LinearIntArith \
  PERFORMANCE=par RUN_ID=lia-v1
```

Single Query 的合法 performance 是 `24`、`par`、`seq`、`sat`、`unsat`。
`24` 只筛选 `walltime_s <= 24`，正式运行仍使用 PDF 规定的 1200 秒、4 cores、
30 GiB。规则：https://smt-comp.github.io/2025/rules.pdf 。评分代码：
https://github.com/SMT-COMP/smt-comp.github.io/blob/smtcomp25/smtcomp/scoring.py 。

官方排名单位是 Division。每次 `make score` 必须指定一个 Division；输出中的
`NON-OFFICIAL ... diagnostic sum` 不是官方排名。错误 SAT/UNSAT 由官方 scorer
计入 error，不得过滤。

参数可以依赖 Track、Division、Logic，不得依赖 benchmark 名称、路径、checksum、
预期答案、运行次序或已观察答案。Division/Logic 映射来源：
https://github.com/SMT-COMP/smt-comp.github.io/blob/smtcomp25/smtcomp/defs.py 。

## 验收

```bash
test "$(git -C .cache/smtcomp-tool rev-parse HEAD)" = \
  b0faba09100a297a32544ac29a54feb4d5d174b4
test "$(git -C .cache/scrambler rev-parse HEAD)" = \
  2f2dbcd69d98894031c6359add0a898cd071bd98
test -x .cache/scrambler/scrambler
test -x .cache/solver/default/bin/cvc5
# Zenodo README 的 archive 文件总计为 450472；metadata 条目数为 450474。
test "$(find -L .cache/benchmarks/non-incremental -name '*.smt2' | wc -l)" -eq 450472
test "$(find -L .cache/execution/benchmarks/files -name '*.yml' | wc -l)" -eq 129361
.venv/bin/python -m unittest discover -s tests -v
```

数量计算依据和逐 Division 结果见 `docs/dataset-counts.md`。benchmark metadata：
https://github.com/SMT-COMP/smt-comp.github.io/blob/smtcomp25/data/benchmarks-2025.json.gz 。
