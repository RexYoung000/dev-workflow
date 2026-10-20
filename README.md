# trae-Rex-workflow

面向 Trae 的项目级开发工作流：从需求、技术方案、Demo、Task/Issue，到实施与测试验收。每位开发者安装到自己的项目，使用自己的 GitHub 仓库。

项目名为 **trae-Rex-workflow**；为兼容既有安装，Skill ID 仍为 `dev-workflow`，项目安装目录与 CLI 路径不变。点名新名称或旧名称均可触发，升级仍安装到原目录，不会并存两份 Skill。

## 安装

需要 Python ≥3.9、Git ≥2.28，以及支持项目 Skill 的 Trae 桌面版。国内版与国际版共用同一安装包，不绑定地区账号和模型。v1.1.2 已修复 Windows 编码、BOM、长正文和更新恢复；平台测试和客户端实际验证范围分别见 [验收记录](docs/acceptance.md)，不将 CLI 测试当作客户端验收。

```bash
git clone https://github.com/RexYoung000/trae-Rex-workflow.git
cd trae-Rex-workflow
python3 scripts/workflow.py install --target "/你的/业务项目根目录" --init
```

已通过 Windows/macOS/Linux 上的 CLI 自动测试和 macOS Trae CN 3.4.4 新会话烟测。Windows 桌面 Trae 与国际版客户端尚未实测；安装后应在新会话复核技能加载和项目状态。

Windows PowerShell（建议较短的项目路径，不需要 Git Bash）：

```powershell
git clone https://github.com/RexYoung000/trae-Rex-workflow.git
cd trae-Rex-workflow
py -3 scripts/workflow.py install --target "C:\Projects\我的项目" --init
```

后续命令在 Windows 将 `python3` 换为 `py -3`；若未安装 Python Launcher，使用已安装的 `python`（先确认版本 ≥3.9）。路径始终加双引号。无需修改系统编码、全局 Trae 目录或注册表。

目标可以是空目录或已有项目。安装后在 **Trae 中打开目标业务项目**，在项目 Skills/技能设置中确认 `dev-workflow` 已启用（CN 3.4.4 入口为“设置 → 技能与命令”，其他版本菜单可能不同）；新开会话发送：

> 用 trae-Rex-workflow 开始新项目。先读取项目现有资料，逐题确认关键需求。

继续已有项目时发送“用 trae-Rex-workflow 继续当前项目”。规则入口在 `.trae/rules/dev-workflow.md`；不修改全局设置或要求安装 MCP。若需要自动导入已有 AGENTS，可在 Trae 规则设置中自行开启；Skill 本身也会明确读取它。

安装包自带脚本、模板和参考文件；安装完成后可移走源码 checkout。首次初始化不会复制本仓库的历史任务、状态或 PRD。已有 AGENTS、业务文档和自定义模板保留。

## 本地检查与 GitHub

在业务项目根目录运行：

```bash
python3 .trae/skills/dev-workflow/scripts/workflow.py status
python3 .trae/skills/dev-workflow/scripts/workflow.py task new --title '实现首个闭环' --module app
```

未加 --init 安装时，先使用同一入口运行 init。Task 创建后补充描述和验收标准；不要将未完成的模板检查点标为已验收。

Issue 同步另需 GitHub CLI、自己的登录账号及目标仓库写权限，并在 GitHub 开启 Issues。新项目请先自行建立远端仓库，然后在业务项目中配置：

```bash
git remote add origin https://github.com/你的账号/你的项目.git
gh auth login
python3 .trae/skills/dev-workflow/scripts/workflow.py task sync
```

已有 origin 不需要重复添加。同步会创建/关闭真实 Issue，应在确认 Task 内容后执行。工作流目前要求 Task 有 Issue 后进入执行阶段；不使用 GitHub 时可进行本地规划，但不能走完整六阶段。

## 更新与回退

Windows 更新/回退遇文件占用时，先解除对应文件占用后重试。若自动恢复失败，CLI 会打印保留的旧包与恢复目标；不要删除唯一备份。超长路径会提前拒绝，建议改用较短项目路径；详细处理见包内 [命令说明](skill/dev-workflow/references/commands.md)。

旧源码 checkout 可先更新仓库地址（**仅在本工作流的源码仓库执行，不要把业务项目的 origin 改成此地址**）：

```bash
git remote set-url origin https://github.com/RexYoung000/trae-Rex-workflow.git
git pull --ff-only
```


在源码 checkout 拉取新版后重新运行同一 install 命令。只替换 `.trae/skills/dev-workflow/`，不重置业务文档、Task 或阶段。内容相同则跳过；有变更时打印旧包在 `.trae/.dev-workflow-backups/` 下的备份位置。需要回退时，将该备份中的 dev-workflow 目录恢复到 `.trae/skills/dev-workflow/`，然后新开 Trae 会话。

请勿把整个源码仓库复制成业务项目模板：其中 tasks、docs 和 .workflow 属于工作流自身。也不要直接改 origin 后继续使用旧 Task 的 Issue 编号。仓库缓存冲突时 CLI 会停止同步，先核对业务项目的仓库与映射。

## 规则与限制

- 本地 Markdown 是事实源；GitHub Issue 仅单向创建/关闭，不持续刷新正文、不双向回写。
- CLI 检查任务结构、依赖和阶段条件；不能替代用户确认、实际运行、推送核对或体验验收。
- 并行预览不是自动调度器。仅在当前 Trae 内置 Agent 支持相关子智能体时采用并行，否则串行；不同模块仍需检查共享文件。
- 面向各自独立使用的开发者，不支持多人同时写同一个工作目录；不自动发布或部署。

开发者运行 `python3 -m unittest discover -s tests -v` 进行隔离测试。产品和技术契约见 [PRD](docs/prd.md)、[技术规范](docs/tech-spec.md)。

## 许可

[MIT](LICENSE)。此许可覆盖 trae-Rex-workflow，不改变安装目标业务项目的许可。
