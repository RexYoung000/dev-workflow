# trae-Rex-workflow 技术规范

| 项 | 值 |
|---|---|
| 版本 | v1.1.2，Trae 项目级分发 |
| 日期 | 2026-10-20 |
| 依据 | 当前 PRD 与用户本轮实施授权 |

项目与仓库名称为 `trae-Rex-workflow`，兼容 Skill ID 仍为 `dev-workflow`；不迁移消费项目的 `.trae/skills/dev-workflow/`、规则路径或已有 Task。源码仓库 origin 与自身 repo 缓存同时更新，GitHub Issue 编号不变。

## 1. 来源与目标环境

Python ≥3.9，仅标准库；Git 初始化需要支持 `git init -b main`（Git ≥2.28）。GitHub 操作调用本机 gh CLI，不读取或分发凭据。安装和本地命令不需要 gh 或网络；同步需要已登录 gh、GitHub origin、Issues 开启和写权限。

Trae 项目 Skill 路径以官方文档为准：`.trae/skills/<name>/SKILL.md`，支持 name/description、相邻脚本、模板与参考资源。原生规则位于 `.trae/rules/`；使用 alwaysApply 的薄入口指向包内手册。AGENTS 的自动导入是用户设置，不修改该设置，也不把该开关作为唯一启动方式。

参考：[技能](https://docs.trae.cn/ide_skills)、[规则](https://docs.trae.cn/ide_rules)、[子智能体](https://docs.trae.cn/ide_subagents)。真实客户端是否识别及触发须单独验证；文件布局正确不等同于 UI 验收。

本版只支持 github.com 仓库。gh 子进程固定使用 github.com，登录检查也限定该主机，不让本机用于企业 GitHub 的 GH_HOST 将同步写入转向其他服务。

国际版遵循相同项目目录：[Skills](https://docs.trae.ai/ide/skills)、[Rules](https://docs.trae.ai/ide/rules)。国内版与国际版的用户全局目录差异不影响本包；不新增地区开关，不分发模型或账号配置。

## 2. 单一维护来源与目录

```text
源码仓库/
  README.md, LICENSE, AGENTS.md
  docs/prd.md, tech-spec.md, acceptance.md  # 工作流自身资料，不分发
  scripts/workflow.py                     # 兼容薄入口
  skill/dev-workflow/
    SKILL.md
    scripts/workflow.py                   # 唯一 CLI 实现
    references/{phases,questioning,commands}.md
    assets/project-agents.md, trae-rule.md
    assets/templates/{prd,tech-spec,task}-template.md
  tests/test_workflow.py                  # 标准库 unittest，隔离测试
  tasks/, .workflow/                      # 工作流自身运行状态，不分发
```

```text
消费项目/
  .trae/skills/dev-workflow/               # 完整运行包 + LICENSE
  .trae/rules/dev-workflow.md              # 短引用；已有文件不覆盖
  AGENTS.md                               # 仅缺失时生成
  docs/templates/                         # 仅缺失时从包内模板生成
  docs/prd.md, docs/tech-spec.md           # 由项目需求产生，不复制源码资料
  tasks/                                 # 首次初始化为空
  .workflow/state.json                    # 首次阶段 1
```

消费项目统一命令：`python3 .trae/skills/dev-workflow/scripts/workflow.py ...`。CLI 定位项目根：优先从 cwd 向上找 `.workflow/state.json`；已安装脚本不允许误操作其安装项目之外的其他 workflow 根。init 默认 cwd，显式安装目标通过 install 的 --target 传入。

## 3. CLI 契约

| 命令 | 行为 |
|---|---|
| install [--target PATH] [--init] | 目标默认 cwd；复制完整 Skill 包及许可；可同时初始化 |
| init | 缺失文件才生成；不覆盖已有业务资料、规则、任务和状态 |
| task new --title TEXT --module TEXT [--deps T-001,T-002] | 分配最大 ID +1；验证依赖及输入；从本项目 task 模板生成 |
| task sync | 先校验 origin/缓存/登录/权限，再按 Task ID 查重、创建/回填及关闭 |
| status | 只读：阶段、配置、有效/异常 Task、待同步、blocked、执行候选和等待原因 |
| phase next / phase set N | 前进累积校验；回退免门槛但仍须状态文件有效；不篡改 Task |

错误中文输出，非零退出；文件/JSON/命令异常不泄露凭据。status 不写状态或任务。模板为轻量 front-matter 子集，不支持完整 YAML；输入限单行文本、deps 为逗号分隔 ID。

### 3.1 安装与升级

- 安装资源来自当前包自身，不依赖 cwd 或硬编码路径；源码 checkout 自身目标明确跳过，避免重复维护安装副本。
- 源码根 LICENSE 在打包时带入；已安装包可作为后续安装源。排除 pycache 等运行缓存。
- 覆盖前暂存完整新包，旧包移到 `.trae/.dev-workflow-backups/<唯一时间目录>/dev-workflow/`，完成后打印新包文件清单与备份路径。失败尽可能恢复旧包。
- 同内容重复安装不替换、不制造备份。安装器托管路径不跟随符号链接，不通过目标目录外的链接覆盖其他项目。
- 已有 AGENTS、同名规则、自定义模板逐字保留；已存在状态通过验证后保留。源 Skill 缺失/资源不齐、跨仓库状态或非法目标在写入前报错。
- `--init` 从目标自己的 origin 识别 repo；无 origin 时 repo 为空；不复制源 repo、phase、Task 或 docs 正文。
- 只做项目级安装，不修改用户全局配置，不创建仓库远端、不登录账号、不自动 sync。

### 3.2 项目状态与仓库隔离

```json
{
  "phase": 1,
  "repo": "",
  "config": {"max_parallel": 3},
  "updated_at": "本机时区 ISO 时间"
}
```

phase 必须为 1..6 整数，max_parallel 为正整数，repo 为空或 owner/name。origin 存在且与缓存不同：明确拒绝 sync 和初始化，不自动把旧 issue 编号迁到新仓库。status 只读显示冲突；无 origin 可做本地规划，sync 必须拒绝。缺失缓存但已确定 origin 时，sync 可补写该缓存。Issue 同步前通过 `gh auth status` 与 `gh repo view --json nameWithOwner,hasIssuesEnabled,viewerPermission` 只读检查；无写权限或 Issues 未启用时拒绝写入。

### 3.3 Task 与依赖校验

必填 id/title/module/status；id 为 T-数字，status 限定五种，issue 为空或正整数；禁止重复 ID。deps 必须是有效已存在的 ID，不能自依赖或形成环；依赖异常的 Task 也不能作为有效执行候选。保留合法 front-matter 的额外字段和正文。done 必须在验收标准节包含至少一条 checkbox 且全部勾选；正文别处的 checkbox 不作为验收依据。

异常 Task：status 必须报告；phase 前进一律阻止；sync 跳过并最终以非零码提示，不关闭该 Task 的 Issue。task new 遇现存异常时先要求修正，防止重复编号或错误依赖。

### 3.4 阶段机器门槛

| 目标 | 累积条件 |
|---|---|
| 任意前进 | 状态、全部 Task 和依赖结构合法 |
| ≥2 | docs/prd.md 存在且非空 |
| ≥3 | docs/tech-spec.md 存在且非空 |
| ≥4 | 至少一个有效 Task |
| ≥5 | 全部 Task 有合法 Issue 编号 |
| ≥6 | 全部 Task done 且验收 checkbox 全勾选 |

不以“排除异常后剩下的任务全完成”判通过。用户确认、Demo 运行与 git push 为 Agent 的独立验收责任，CLI 不冒称已检查。

### 3.5 调度预览

先判断 deps 全为 done，再将 todo/in-progress 按模块分组；每模块最多选一个，优先既有 in-progress；有同模块并行冲突时明确报告。全局最多 max_parallel，其余列为排队。未完成依赖、blocked/review 与异常 Task 不标为可执行。仅为候选建议，不自动启动子智能体或提供文件锁；Agent 核对跨模块共享文件，运行时能力不可用则串行。

## 4. 验证与验收

### Windows 兼容契约（v1.1.2，实施前）

- CLI 标准输出/错误在本进程明确为 UTF-8，不改全局环境；Git/gh 的正常结构化输出严格按 UTF-8 解码。失败诊断可按本机编码回退，不能用字符替换让损坏 JSON 继续同步。
- 子进程使用参数列表、绝对可执行文件路径且不用 shell。Issue 创建使用 `gh issue create --body-file -`，正文以 UTF-8 字节送入 stdin，保留换行且不受 Windows 命令行正文长度影响。
- Task、状态、模板与门槛文档读取支持 UTF-8 BOM、LF/CRLF；所有写入无 BOM UTF-8/LF。Task 文件名的标题片段限定 UTF-8 字节数，完整标题仍保存于 front-matter。
- 原子文件替换与包目录移动只对 PermissionError 有限重试。更新交换失败尝试恢复旧包；恢复也失败时保留备份并明确输出旧包位置与目标路径，清理失败不能掩盖原始错误。
- Windows 安装/初始化预检包含暂存与备份的最长托管路径，超过传统路径限制时在写入前拒绝并建议短项目路径；不修改注册表或 Git 全局配置。超长路径支持不作承诺。
- 托管路径同时拒绝 Windows junction（目录联接），避免其绕过符号链接保护写到其他项目；CI 通过原生 junction 验证。
- GitHub Actions 在 Windows/macOS/Linux、Python 3.9/3.13 执行测试，仅授予 contents:read。测试替身不依赖 Unix shebang/chmod/PATH 覆盖或真实 gh，不访问真实业务仓库。

依据：[Python subprocess](https://docs.python.org/3.13/library/subprocess.html)、[Windows 命令行上限](https://learn.microsoft.com/en-us/windows/win32/api/processthreadsapi/nf-processthreadsapi-createprocessw)、[gh Issue 正文输入](https://cli.github.com/manual/gh_issue_create)。

### 验证范围

- Python 标准库 unittest，CLI 在 TemporaryDirectory 中运行；需要 gh 时用记录调用的假后端，不对真实仓库制造测试 Issue。
- 端到端：source clone → install --init → 删除/移开分发源 → 新建 Task/status/phase；安装包可独立运行。
- 保留：已有 AGENTS、业务 PRD、tech-spec、规则、自定义模板、Task、phase/config 不被覆盖。
- 升级：同版本幂等、旧包备份可恢复、缺资源/链接路径/错误目标非零退出。
- 隔离：不同项目使用不同 origin；缓存冲突、无 origin、gh 未登录、权限不足、Issues 关闭在写入前停止。
- 任务：缺字段、重复 ID、缺依赖、环、非法 issue、done 未验收均不能越过门槛；有依赖任务不得误提示并行。
- 同步：创建/回填/关闭的完整生命周期与中断重跑幂等；异常 Task 不关闭 Issue。
- Skill：front-matter、相对资源和引用完整，默认入口与总资源大小分别统计。真实 Trae 新会话点名触发、规则读取和体验单独记录，未运行就标待验证。
- 本轮允许普通 commit/push；不创建 release、不合并 PR、不部署。
