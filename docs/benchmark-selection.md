# Benchmark 下载、选择和 scramble

## 1. 完整数据集

`make benchmarks` 查询 non-incremental 与 incremental Zenodo record。归档均按
Zenodo 给出的算法和 digest 校验，然后检查
tar 路径安全性并解压到：

```text
.cache/benchmarks/
  non-incremental/<LOGIC>/...
```

数据规模很大且解压比例高，因此不提交到 Git。当前所谓“完整 benchmark”指官方
2025 non-incremental 发布物的全部逻辑归档，再由官方 Single Query selector 产生
正式选中集，而不是仓库自选小样本。权威身份清单是官方
`data/benchmarks-2025.json.gz`。Incremental 的官方发布物是
https://zenodo.org/records/15493096 。

## 2. Single Query 官方选择算法

实现依据为官方 `smtcomp/selection.py::track_selection`：

1. 只保留 Single Query 的官方 Logic；
2. 去掉 trivial benchmark；
3. 每个 Logic 的样本数是
   `min(总数, max(300, floor(总数 * 0.5)))`；
4. 先取新 benchmark，再从旧 benchmark 补足；2025 代码将 family 以 `2024`
   开头者视为 new；
5. 使用官方 seed 对排序后的集合进行 Polars sampling；
6. 通过官方 scrambler 重命名符号并生成 scramble ID 和 `original_id.csv`。

trivial 判定来自官方历史 competitive results：同一 benchmark 的竞争性运行均在
1 秒内给出已知答案。冲突结果会按官方代码排除/处理，不能读取本地期望答案来挑题。

2025 seed 是所有 competitive submission seed 求和后模 `2^30`，再加
`Config.nyse_seed=2033841`。该数、日期 `2025-06-30` 和 submission seed 均直接
来自官方固定提交，不能自行换随机种子来制造更有利的数据集。

## 3. Parallel 官方选择

实现依据为 `smtcomp/selection.py::aws_selection`：

- 总数 400；
- 只考虑 Parallel 中 competitive 的 Logic；
- 使用历史 SingleQuery 结果；任何 solver 在 180 CPU 秒内解决的实例被排除；
- 剩余实例分为 hard（有人解决过但超过 180 秒）与 unsolved（没人解决）；
- 两组各选 200；先在各 Logic 内按相同 seed 随机抽样，再 round-robin 保证 Logic
  覆盖；
- `scramble-aws` 同时生成 Cloud/Parallel 数据，但 Cloud 2025 不执行。

Parallel 页面所说的 400 个实例与这里的 `aws_num_selected=400` 一致。

## 4. 可复现命令

```bash
make metadata
make cache
make benchmarks
make select-all
make check-all-selections
```

不能修改 `data/*.json.gz`、selection cache、scrambler、seed、历史结果或生成后的
benchmark。任何 selection 变更都会变成另一个实验，不再是 SMT-COMP 2025 复现。

`configs/setup-all.env` 中的 `SELECTION_JOBS` 只控制官方 scrambler 的本地
worker 数；`CACHE_PLACEMENT` 和 `EXTERNAL_CACHE_ROOT` 只决定生成文件存在哪个
filesystem。这些设置都不得改变官方 metadata、历史结果、seed、selected IDs 或
scramble 输出。

`scripts/select_official_track.py` 是普通 Track 的中断恢复包装器，不实现另一套 selection：它直接
调用固定 checkout 的 `selection.helper`、`create_scramble_id` 与 `scramble_file`，并
始终重写完整官方 `original_id.csv`。只有官方 yml 和非空 scrambled SMT2 同时存在时
才跳过该任务；缺任一文件或空文件都会用同一官方 seed 重新生成。Parallel 直接调用
官方 `scramble-aws`。
进度包装使用 Python `as_completed`，只改变终端进度显示顺序，不改变任务输入、
官方 scrambler 调用、seed 或输出文件名。实现文档：
https://docs.python.org/3/library/concurrent.futures.html#concurrent.futures.as_completed 。

## 本页来源网址

- https://github.com/SMT-COMP/smt-comp.github.io/blob/smtcomp25/smtcomp/selection.py
- https://github.com/SMT-COMP/smt-comp.github.io/blob/smtcomp25/smtcomp/scramble_benchmarks.py
- https://github.com/SMT-COMP/smt-comp.github.io/blob/smtcomp25/data/benchmarks-2025.json.gz
- https://smt-comp.github.io/2025/parallel_track/
- https://doi.org/10.5281/zenodo.16740866
- https://doi.org/10.5281/zenodo.15493096
- https://learn.microsoft.com/windows/wsl/filesystems
