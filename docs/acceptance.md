# trae-Rex-workflow 验证与验收记录

## v1.1.2 Windows 与地区版本兼容修复（2026-10-20）

状态：实现已推送、六组跨平台 CI 与公开安装复核通过；用户完整体验待验收。跟踪 T-009 / Issue #9，先文档提交 `279ca6d`，实现提交 `68388d9`。

### 已实现与测试边界

- CLI 自行配置 UTF-8 输出；Git/gh 正常输出严格 UTF-8，错误诊断允许本机编码回退；损坏 JSON 不会被替换字符后继续同步。测试强制 cp1252 输出环境与 cp936 诊断场景。
- 状态、Task、模板及门槛文档接受 UTF-8 BOM/CRLF；status 不改文件，写回统一无 BOM UTF-8/LF。UTF-16 与任意 ANSI 业务文件不在支持范围。
- Issue 正文改用 `--body-file -` + UTF-8 stdin；长正文（超过 32767 UTF-16 单元，含中文、emoji、引号、换行）完整传到隔离后端，命令参数保持短小。
- Task 文件名的标题片段限定 72 个 UTF-8 字节，内容保留完整标题；Windows 超长托管路径在写入前拒绝，提示短项目路径，不改注册表或全局编码。
- 更新/原子保存对短暂 PermissionError 最多尝试 4 次；模拟换包失败可自动恢复旧包，连恢复也失败时保留旧包备份并显示恢复路径。原生 Windows 文件共享锁和 junction 测试已在 Windows CI 执行通过。
- 测试入口不依赖 shebang/chmod 或 PATH 覆盖，所有 gh 调用转至测试目录中的 Python 假后端；不需要真实 gh 或登录，不创建测试 Issue。
- 国内版与国际版共用 `.trae/skills/dev-workflow/` 与 `.trae/rules/dev-workflow.md`，保持新旧名称触发和原安装路径；新增 PowerShell 文档、UTF-8 文件保存与占用恢复说明。

### 真实执行结果

最终 [跨平台 CI 39438525126](https://github.com/RexYoung000/trae-Rex-workflow/actions/runs/39438525126) 在提交 `be46441` 上六组全部成功：

| 执行环境 | Python | 结果 |
|---|---|---|
| windows-latest（Windows Server 2025 x64） | 3.9 / 3.13 | 每组 46 项通过；包括真实 Win32 文件共享锁与 junction |
| macos-15-intel / macos-latest | 分别 3.9 / 3.13 | 每组 44 项通过、2 项 Windows 专用测试跳过 |
| ubuntu-latest | 3.9 / 3.13 | 每组 44 项通过、2 项 Windows 专用测试跳过 |

Skill 结构与相对资源检查通过，运行依赖仍仅 Python 标准库。CI 的 Actions 固定到已核实的官方提交，只授予 contents:read，不保存 checkout 凭据，不执行发布部署。

本地 macOS Python 3.13.3：46 项中 44 项通过、2 项 Windows 专用检查按平台跳过；另补可执行文件为显式相对路径、执行时切换项目目录的跨盘符回归。首次 Windows CI 发现两项直接调用内部函数的测试输出依赖系统编码，已于 `e311418` 用内存捕获修复，CLI 的旧编码测试保持不变；首次 macOS/Python 3.9 在 ARM 镜像安装 Intel 解释器时缺少 libintl，已于 `6e9d8af` 调整最低版本测试机架构，没有跳过产品测试。

公开分发：从 GitHub 匿名重新 clone `be46441`，安装到中文/空格路径的独立项目，包内版本为 1.1.2、阶段 1、零 Task。移走源码 checkout 后，包内 CLI 能离线创建 T-001 并显示有效 1 / 异常 0，无源项目历史数据。

真实客户端：macOS Trae CN 3.4.4、GLM-5.3-Flash，使用 `68388d9` 分发包升级先前独立验证项目后新建会话（后续仅补工具绝对路径处理与测试环境）。UI 展开实际显示“调用技能：dev-workflow”，子任务记录读取 1 个文件、执行 2 条命令；`--version` 为 1.1.2，`status` 为阶段 1、零 Task，并读取新版 Windows/地区版本说明。本轮只读，无 Issue/提交/推送操作。

加载量：发现元数据 377 B；SKILL.md 调用入口 2554 B；完整安装包 11 文件 / 49352 B（含 CLI、参考、模板与 MIT LICENSE）。默认入口未增加；资源总量增加来自实际兼容处理和恢复文档，按需资源不算删除。

### 尚未覆盖与手工验收

- 当前电脑仅安装 Trae CN；国际版目录协议已按官方 [Skills](https://docs.trae.ai/ide/skills) / [Rules](https://docs.trae.ai/ide/rules) 核对，**国际版真实客户端触发仍未验证**。
- Windows CI 验证 Python CLI、文件系统与隔离同步；**没有 Windows 桌面 Trae UI 验收**，不能等同于 Windows 版所有客户端/模型均可用。
- 用户可按 README 在自己的项目安装，Trae 打开该根目录、启用项目 Skill `dev-workflow`，新会话发送“用 trae-Rex-workflow 继续当前项目”，核对包内版本 1.1.2、项目自己的阶段/Task/origin。国际版同样操作，界面菜单名称可能不同；最终完整六阶段体验仍待用户验收。

## v1.1.1 项目更名（2026-10-20）

- 用户确认项目名及仓库名为 `trae-Rex-workflow`，修正输入时 workflow 的拼写。先文档提交 `4840b12`，再实施。
- GitHub 仓库 ID 仍为 1423105107，历史和 Issue 保留；本地 origin 与本仓库 repo 缓存同步为 `RexYoung000/trae-Rex-workflow`。
- 稳定 Skill ID 与 `.trae/skills/dev-workflow/` 安装路径保留，新旧名称均可点名，不要求已有消费项目迁移；旧 AGENTS、规则和 CLI 路径仍有效。
- 34 项回归测试与 Skill 结构检查通过。独立项目 `trae-rename-verification` 的 Trae CN 3.4.4 新会话只点名 trae-Rex-workflow，实际加载 Skill dev-workflow，并运行包内 --version（1.1.1）与 status（阶段 1、零 Task）。
- 本轮加载量：发现元数据 377 B，SKILL.md 入口 2554 B，完整安装包 11 文件 / 43939 B。按需资源总量包含模板与 CLI，没有把移动当作删除。
- 新仓库地址匿名公开 clone（630efee）与全新项目安装复核通过，包内 CLI 为 1.1.1、阶段 1、零 Task；改名实现已推送；用户完整体验验收仍待确认。

## Windows 与国际版兼容性评估（2026-10-20）

以下保留修复前评估，已修复项以本页 v1.1.2 记录为准。本节是代码检查、官方文档核对与本机模拟结果，**不是 Windows 或国际版客户端实测**；本轮更名不包含这些兼容缺口的修复。

| 观察 | 证据与处理建议 |
|---|---|
| 非 UTF-8 标准输出 | 以 cp1252 模拟 Trae 捕获输出，CLI --help 返回 UnicodeEncodeError。明确本进程输出编码，不依赖系统默认；Windows 命令可临时用 -X utf8 缓解，不改系统全局设置 |
| 子进程解码 | 模拟 cp936 默认解码后，包含中文的 UTF-8 JSON 触发 UnicodeDecodeError。对子进程按工具明确指定解码方式，结构化 JSON 不用错误替换掩盖损坏 |
| BOM 与换行 | CRLF Task 正常；UTF-8 BOM Task 的字段未识别，BOM state.json 被拒绝。读取接受 utf-8-sig，继续写无 BOM UTF-8 |
| 长 Issue 正文 | 当前 --body 直接放进命令行，模拟参数为 35067 UTF-16 单元，超过 Windows CreateProcessW 的 32767 上限。改为 gh --body-file 或标准输入 |
| Windows 测试入口 | 当前假 gh 使用 Unix shebang/chmod，多处测试文本读写和子进程捕获依赖默认编码；不能直接将 34 项本机通过当作 Windows 通过。先改跨平台测试替身、显式 UTF-8，再加真实 Windows 测试执行 |
| 文件占用与长路径 | 本轮未复现 Windows 文件锁与路径上限；属于待真机验证风险。检查中文/空格/长路径、文件占用下更新失败与备份恢复，必要时补有限重试和明确恢复提示 |

国际版官方文档确认项目技能 `.trae/skills/`、项目规则 `.trae/rules/` 及 AGENTS 导入约定与当前设计一致。全局目录使用 `~/.trae/`，CN 使用 `~/.trae-cn/`，本包不写全局目录，因此无需按地区维护两套安装包。当前不绑定 CN 模型或子智能体配置，能力不可用时串行；真实国际版新会话加载与运行仍待验证。

参考：[国际版 Skills](https://docs.trae.ai/ide/skills)、[国际版 Rules](https://docs.trae.ai/ide/rules)、[Python Windows UTF-8](https://docs.python.org/3.13/using/windows.html#utf-8-mode)、[Windows 命令行上限](https://learn.microsoft.com/en-us/windows/win32/api/processthreadsapi/nf-processthreadsapi-createprocessw)、[gh body-file](https://cli.github.com/manual/gh_issue_create)。

## v1.1 Trae 项目级分发（2026-10-20）

状态：实现与代理验证通过；真实 Trae 新会话点名烟测通过；实现提交 `4eaae15` 已推送，匿名公开 clone 安装复核通过。用户完整体验验收待确认，不归档本轮迭代。

### 先文档后实施

本轮范围由用户明确授权，许可证由用户选择 MIT。PRD、技术规范、维护入口、README 与 LICENSE 先独立提交于 `bab7d2c`，然后迁移并实现自包含分发包。跟踪任务 T-007 / Issue #7。

### 实现与代理验证

| 项目 | 结果与实际覆盖 |
|---|---|
| 完整分发 | Skill 内含 CLI、模板、参考文件；安装带 LICENSE 和薄规则；根 CLI 为兼容入口，唯一实现位于 Skill |
| 空项目 | install --init → 阶段 1、空 Task、无业务 PRD；无源账号和历史状态 |
| 自包含 | 测试复制完整分发源、安装后删除源 checkout，包内 new/status 仍可用；可再次安装到另一个空项目 |
| 已有项目 | AGENTS、业务文档、同名规则、自定义模板、Task、phase/config 逐字保留 |
| 更新与回退 | 内容相同不备份；变更先备份；模拟包替换失败时恢复旧包；链接/缺资源/错误目标在写入前拒绝 |
| 项目隔离 | 目标 origin 自动识别；缓存冲突、无 origin、伪 GitHub 主机、GH_HOST 指向其他主机、跨项目使用已安装 CLI 均拒绝危险路径 |
| 同步 | 假 gh 后端验证登录、权限、Issues 前置；创建/回填/关闭、重复同步、创建后响应丢失恢复；异常 done 与错误 Issue 映射不关闭 |
| 门槛与依赖 | 缺字段、重复 ID、缺依赖、依赖环、非法 Issue、done 未验收无法前进；候选尊重依赖、模块及上限 |
| 自动测试 | `python3 -m unittest discover -s tests -v`：34 项通过（Python 3.13.3） |
| Skill 检查 | skill-creator quick_validate 通过；相对资源引用与 Python 3.9 语法检查通过 |

测试所需 PyYAML 仅安装于仓库外的隔离验证目录；产品运行仍仅依赖 Python 标准库。GitHub 模拟测试没有访问或写入真实业务仓库。真实远端操作仅用于本仓库正式跟踪任务。

### 真实 Trae 客户端烟测

- 环境：macOS，Trae CN **3.4.4**，本地 Agent 会话，GLM-5.3-Flash；Python 3.13.3、Git 2.54.0、gh 2.73.0。
- 独立项目：`trae-client-verification`，通过 install --init 安装；不使用原有开发项目或会话。
- 新会话请求：点名 dev-workflow，只读加载技能、读取 AGENTS、运行 status，禁止写文件、联网和 Issue/提交/推送操作。
- UI 工具记录实际显示“调用技能：dev-workflow”，描述与新版包一致；随后读取 1 个文件并执行 1 条命令。
- 结果：项目内 `.trae/skills/dev-workflow/scripts/workflow.py status` 返回阶段 1、并发上限 3、有效/异常 Task 都为 0、origin 与仓库缓存未配置。
- 再由外部 CLI 检查同一项目，状态与 Task 数量一致，无新增 Task 或业务文档。
- 结论：**项目 Skill 被真实 Trae 发现，点名加载与包内 CLI 运行通过**。该结论仅覆盖本机版本与只读入口。

### 公开分发复核

从 GitHub 匿名重新 clone `4eaae15`（禁用 credential helper 与交互登录），按 README 安装到含中文和空格路径的另一个独立项目。目标预先配置自己的示例 origin；安装后得到阶段 1、空 Task、目标自己的 repo 缓存，未带入 dev-workflow 的阶段与历史任务。移走刚 clone 的源码目录后，包内 CLI 仍能创建 T-001 并读取正确状态。此复核未对示例远端进行网络读写。

### 加载量与分发资源

- 默认发现的 name/description 元数据：309 字节。
- 调用时 SKILL.md 入口全文：2370 字节（约 2.37 KB）。
- 完整安装包：11 个文件，43503 字节（约 43.50 KB，含脚本、模板、参考文件及许可，不含运行缓存）。
- 参考与资产是按需资源，迁移进包不算删除或减少总资源；不会在 Skill 被调用时自动把全部 CLI/模板源码注入上下文。

### 尚未覆盖与用户验收

- Windows、Linux、Trae 国际版及其他客户端版本未做真实运行；Python 3.9 仅语法核对，实际测试为 3.13.3。
- 不点名的语义自动匹配、规则独立自动注入、子智能体并发和完整六阶段业务体验未逐项 UI 验证。
- GitHub 测试使用假后端覆盖生命周期；未为测试创建新的真实业务仓库或制造测试 Issue。
- 用户可在自己的项目安装，Trae 新开会话发送“用 dev-workflow 继续当前项目”，核对仅出现该项目的阶段、仓库与 Task。最终使用体验由用户验收。

---

下列内容为 v1.0 历史原文，旧章节编号与完成状态只指当时版本，不代表 v1.1 已获用户验收。

## v1.0 历史验收（2026-10-18）

| 项 | 值 |
|---|---|
| 验收日期 | 2026-10-18 |
| 验收人 | Rex（项目所有者，PRD §2） |
| 结论 | **验收通过，项目归档** |

## 交付物

| 交付物 | 位置 |
|---|---|
| PRD v1.0 | docs/prd.md |
| 技术规范 v1.0 | docs/tech-spec.md |
| AGENTS.md 操作手册 | AGENTS.md |
| CLI（Python 标准库单文件） | scripts/workflow.py |
| Trae 项目级 Skill（已安装可触发） | skill/dev-workflow/ → .trae/skills/dev-workflow/ |
| GitHub 镜像 | github.com/RexYoung000/dev-workflow（Issue #1-#6 全部关闭） |

## Agent 测试复查结论（2026-10-18）

sync 幂等复测 0 新建 / 0 关闭；init 内嵌 AGENTS 模板与定稿逐字一致；安装副本与仓库源 diff 无差异；远端 Issue 全部 CLOSED；本地与 origin/main 同步且工作区干净。

## 用户验收

- Skill 新会话触发实测通过（T-006，2026-10-18）。
- 2026-10-18 用户确认整体验收通过。

## 迭代回流记录

- 缺陷：无。
- 新需求：无。后续迭代候选见 PRD §10 非目标（Web 面板、Issue 双向同步等）。
