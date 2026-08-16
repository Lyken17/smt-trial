# cvc5 官方参数文档速查指南

本文档的目标不是提供参数清单，而是**指导如何使用官方文档和工具来查找和验证参数**。

## 📖 本地官方文档

本仓库已将 **cvc5 1.3.4** 官方文档本地化至 [`docs/cvc5-official-docs/`](./cvc5-official-docs)。
在调参时，**优先查阅本地文档**而非外网链接：

- **本地选项总表**：[`docs/cvc5-official-docs/options.html`](./cvc5-official-docs/options.html)
- **本地 Theory 参考**：[`docs/cvc5-official-docs/theories/theories.html`](./cvc5-official-docs/theories/)
- **本地 Resource Limits**：[`docs/cvc5-official-docs/resource-limits.html`](./cvc5-official-docs/resource-limits.html)
- **本地 Binary 文档**：[`docs/cvc5-official-docs/binary/binary.html`](./cvc5-official-docs/binary/binary.html)

**外网官方入口**（用于验证或查看最新版本）：

- cvc5 文档首页：https://cvc5.github.io/docs-ci/docs-main/
- cvc5 选项总表：https://cvc5.github.io/docs-ci/docs-main/options.html

## 调参前必读

本项目的参数调优要遵循以下原则：

- **不凭记忆填参数**：每个 option 都必须有官方文档证据
- **不缩减官方内容**：本地文档不会删除或简化官方参数列表
- **必须有完整链条**：官方 docs → 当前 `cvc5 --help` → TOML 配置

本仓库当前使用的官方 cvc5 发行包由 `versions.env` 固定。调参时应以**本地官方文档为准**，并在每次实际调参时再核对 `cvc5 --help` 或 `--show-config`。

---

## 1. 这个仓库里"什么才算参数"

本项目要求调参只发生在：

```text
configs/cvc5/<Track>/<Performance>.toml
```

参数配置采用三层覆盖结构：

```toml
[default]
args = ["--option1", "--option2=value"]

[division.DIVISION_NAME]
args = ["--option3"]

[division.DIVISION_NAME.logic.LOGIC_NAME]
args = ["--option4"]
```

覆盖顺序：`default → division → division.logic`

**调参限制**：
- 允许按 Track、Division、Logic 调参
- 禁止按 benchmark 名称、路径、checksum、预期答案、运行顺序或已观察结果分派参数
- 不得修改官方 metadata、selection、scramble、expected status

---

## 2. cvc5 官方参数查询的基本命令

不在本文档中寻找参数名，而是使用 cvc5 本身提供的命令：

```bash
# 查看所有可用选项
cvc5 --help

# 查看仅标准选项（不含实验性）
cvc5 --help-regular

# 按类别查看选项
cvc5 --help-option-categories

# 查看当前配置
cvc5 --show-config

# 查看版本和编译信息
cvc5 --version
```

这些命令会告诉你：

- 选项的确切名称和别名
- 是否为 Boolean 选项（`--foo` 或 `--no-foo`）
- 非 Boolean 选项的参数形式（`--foo=value` 或 `--foo value`）
- 该版本中实际可用的选项

---

## 3. 官方文档中的参数分类

打开官方 `Options` 页面（本地：[`docs/cvc5-official-docs/options.html`](./cvc5-official-docs/options.html)），
你会看到这些模块名：

- Most Commonly-Used cvc5 Options
- Additional cvc5 Options
- Arithmetic Theory Module
- Arrays Theory Module
- Bags Theory Module
- Base Module
- Bitvector Theory Module
- Datatypes Theory Module
- Decision Heuristics Module
- Expression Module
- Finite Field Theory Module
- Floating-Point Module
- Driver Module
- Parallel Module
- Parser Module
- Printing Module
- Proof Module
- SAT Layer Module
- Quantifiers Module
- Separation Logic Theory Module
- Sets Theory Module
- SMT Layer Module
- Strings Theory Module
- Theory Layer Module
- Uninterpreted Functions Theory Module

**调参时的关键步骤**：

1. 确定当前 Division / Logic 对应哪个 Theory（例如 `QF_LinearIntArith` → Arithmetic）
2. 打开官方 docs 中对应 Theory 模块
3. 阅读该模块中的参数描述
4. 用 `cvc5 --help` 验证参数在当前版本中确实存在
5. 写入 TOML 配置

---

## 4. 推荐的调参工作流

### 第一步：理解当前 Division 和 Logic

查看 `configs/cvc5/<Track>/` 中已有的 TOML 文件，找到目标 Division 和 Logic。

### 第二步：查询官方文档

打开本地官方 HTML 文档（或官方网站），在对应 Theory 模块中查找相关参数。

例如：
- 如果处理 `QF_LinearIntArith` → 查阅 **Arithmetic Theory Module**
- 如果处理 `QF_BV` → 查阅 **Bitvector Theory Module**
- 如果处理 quantified logic → 查阅 **Quantifiers Module**
- 如果处理 `QF_S` 或 `SLIA` → 查阅 **Strings Theory Module**

### 第三步：验证参数存在

用当前本地 cvc5 binary 确认参数确实存在：

```bash
cvc5 --help | grep -i "<option-name>"
cvc5 --show-config | grep "<option-name>"
```

### 第四步：写入配置

在正确的 TOML 层级写入参数：

```toml
[division.YOUR_DIVISION.logic.YOUR_LOGIC]
args = ["--verified-option"]
```

### 第五步：查询配置

使用项目提供的工具查看最终合并后的参数：

```bash
.venv/bin/smtcomp-cvc5-config configs/cvc5/<Track>/<Performance>.toml \
  --track <Track> --division <Division> --logic <Logic>
```

---

## 5. 一条核心规则：证据链完整性

任何一个参数配置都应该能回答这些问题：

1. **这个参数在官方文档中吗？** → 查阅 `docs/cvc5-official-docs/options.html`
2. **这个参数在当前 cvc5 版本中有效吗？** → 运行 `cvc5 --help`
3. **这个参数属于哪个 Theory/Module？** → 查看官方 docs 的模块分类
4. **这个参数与当前 Division/Logic 是否匹配？** → 确认 Theory 与问题域相关

如果无法清晰地回答上述问题，就不应该将该参数写入配置。

---

## 6. 常见问题排查

**Q: 参数名在官方 docs 中没看到？**
A: 
1. 确认查看的是当前项目使用的 cvc5 版本（1.3.4）的文档
2. 用 `cvc5 --help` 搜索参数名确认是否存在
3. 检查是否需要拼写调整或使用别名

**Q: 参数在 `cvc5 --help` 中出现但不在官方 docs 中？**
A:
1. 可能是实验性选项或内部调试选项
2. 查看官方 docs 是否有 "undocumented" 或 "experimental" 标记
3. 在 AGENTS.md 中标注为什么选择该参数

**Q: 某个参数属于多个 Module？**
A:
1. 通常参数只归属于一个主模块
2. 在官方 docs 的模块列表中找到主分类
3. 理解该参数在该模块中的作用后再使用

---

## 7. 总结

**本文档不提供参数清单。** 它的目标是教你如何：

- ✅ 使用本地官方 HTML 文档查找参数
- ✅ 用 `cvc5 --help` 命令验证参数有效性
- ✅ 按 Theory 分类理解参数的适用范围
- ✅ 建立"官方 docs → 当前版本 → TOML 配置"的完整证据链

**永远不要**：

- ❌ 凭记忆拼凑参数
- ❌ 使用本文档作为参数白名单
- ❌ 跳过官方文档的查阅步骤
- ❌ 根据 benchmark 名称或路径来选择参数

---

**相关资源**：

- AGENTS.md：项目调参规则
- README.md：调参边界说明
- `versions.env`：当前 cvc5 版本
- `cvc5 --help`：当前 binary 的权威参考
