# CLI、安装和恢复

项目名为 trae-Rex-workflow，Skill ID 与以下旧安装路径保持兼容。新会话可点名新名称或 dev-workflow。

在消费项目根目录运行，统一入口（下文简写 workflow）：

```bash
python3 .trae/skills/dev-workflow/scripts/workflow.py --help
```

Windows 没有 python3 时可用 `py -3`。本地操作需 Python ≥3.9 与 Git ≥2.28；无需安装 Python 第三方库。包中已包含 CLI、模板和参考文件，不依赖源码 checkout。

国内版与国际版均安装在项目 `.trae/`，不写 `~/.trae-cn/`、`~/.trae/` 或 `%USERPROFILE%` 下的全局配置，不绑定地区模型。界面菜单随客户端版本可能不同；在项目 Skills/技能设置中启用 `dev-workflow` 后，新会话点名 trae-Rex-workflow。

Windows PowerShell 示例：

```powershell
py -3 scripts/workflow.py install --target "C:\Projects\我的项目" --init
# 在上面的目标项目根目录执行：
py -3 .trae/skills/dev-workflow/scripts/workflow.py status
```

使用 Python Launcher 的 `py -3`，或确认版本 ≥3.9 后使用 `python`。路径加双引号；不需要 Git Bash、管理员权限或修改系统编码。文件支持 UTF-8（有/无 BOM）与 CRLF，CLI 写回无 BOM UTF-8/LF。旧版 Windows PowerShell 的重定向可能产生 UTF-16；手工保存 Task/JSON 时选 UTF-8，UTF-16 不在支持范围。

## 常用命令

```bash
python3 .trae/skills/dev-workflow/scripts/workflow.py init
python3 .trae/skills/dev-workflow/scripts/workflow.py status
python3 .trae/skills/dev-workflow/scripts/workflow.py task new --title '实现核心闭环' --module app
python3 .trae/skills/dev-workflow/scripts/workflow.py task new --title '接入界面' --module ui --deps T-001
python3 .trae/skills/dev-workflow/scripts/workflow.py task sync
python3 .trae/skills/dev-workflow/scripts/workflow.py phase next
python3 .trae/skills/dev-workflow/scripts/workflow.py phase set 1
```

- init：仅生成缺失的 AGENTS、项目模板、空 tasks 目录与阶段 1 状态；已有内容保留。安装时的 `--init` 等价于此步骤。既有项目仍需根据真实进度补文档、任务并通过门槛，不自动宣称已完成。
- task new：ID 取最大编号 +1；deps 必须为存在且不重复的 Task ID。生成后补充描述与实际验收标准。
- status：只读列出有效/异常任务、未同步项、blocked、依赖已完成的执行候选及等待原因。候选不等同于已启动子智能体。
- phase next / set：前进累积校验，回退不校验阶段完成条件；详情见 phases.md。不得手工编辑状态跳过门槛。

## GitHub 同步

需要 gh CLI 已安装并以使用者自己的账号登录，目标项目 origin 指向自己的 GitHub 仓库，Issues 开启且账号有写权限。无远端可先进行本地规划，完整阶段 4 → 5 需要 Task 的 Issue 编号。

```bash
git remote get-url origin
gh auth status
```

没有远端时由使用者建立自己的仓库并配置 origin。不要把示例账号当作默认配置。sync 先只读检查仓库、登录和权限，再按 `[T-xxx]` 标题查重、创建/回填，最后关闭 done 的 Issue。异常 Task 被跳过且命令最终非零退出，其他有效项可已同步。

Task 文件及时保存回填编号；创建后中断可以重跑按 Task ID 恢复。不要手工删除映射或给同一 Task ID 建多个 Issue。单向同步仅创建/关闭，不持续更新正文、不处理远端编辑回写，也不重新开启已关闭的 Issue；新缺陷应新建修复 Task。

## 安装、升级与回退

推荐从分发仓库运行：

```bash
python3 scripts/workflow.py install --target "/目标项目" --init
```

完整源 Skill 目录包括 scripts、assets、references；仅复制 SKILL.md 或只在 Trae 界面上传一份 SKILL.md 不足以运行。安装器会把根 LICENSE 一并带入包内，并生成薄规则入口；不修改全局设置、已有项目规则和业务资料。安装完成后在目标项目新开 Trae 会话点名验证。

更新时重新运行同一 install。内容相同跳过；替换前将旧包备份到 `.trae/.dev-workflow-backups/<唯一目录>/dev-workflow/` 并打印路径，项目文档、任务、状态、自定义模板和已有规则保持原样。恢复该备份至 `.trae/skills/dev-workflow/` 后新开会话即可回退。

文件占用会有限重试；失败时查看输出：旧包可能已自动恢复，也可能完整留在打印的备份位置。仅在解除占用并核对路径后恢复，不删除唯一备份；失败清理留下的 `.dev-workflow-stage-*` 是新包暂存，可在解除占用后删除。若提示超长路径，将项目移至较短位置再安装，预检包含备份所需空间。

已安装完整包也可以通过自身 `install --target <另一个项目>` 分发，无需保留源 checkout。目标为源码仓库本身时跳过；它的状态和历史任务不能作为业务项目初始数据。

## 失败处置

| 错误 | 处理 |
|---|---|
| 缺少 Python / Git / gh | 安装所缺工具；gh 只在同步时需要 |
| 未找到 state.json | 在目标项目用包内 CLI 运行 init |
| origin 与 repo 缓存冲突 | 停止；先核对业务仓库和 Task Issue 映射，再明确修正，不自动转移旧任务 |
| 无 GitHub origin / 登录或权限不足 / Issues 关闭 | 使用自己的账号、仓库补齐条件后重跑，不能借用分发者配置 |
| 异常 Task | 按输出补字段、处理重复 ID/依赖环/缺失依赖/验收点后重跑；不要改状态掩盖 |
| 未找到 Skill 或资源缺失 | 确认完整安装目录、项目技能启用、当前打开的是目标根目录，重新安装并新开会话 |
| 包含符号链接或目标路径被目录占用 | 核对该项目的托管路径，不跟随链接写到其他目录；修正布局后重试 |
| 文件被占用 / 无写权限 | 关闭占用对应文件的程序或预览、检查该项目目录权限后重试；按输出保留或恢复旧包，不改全局设置 |
| Windows 路径过长 | 将项目移到短路径，如 C:\Projects\app；不承诺系统开启长路径后的超长目录 |
| 文件不是 UTF-8 | 编辑器另存为 UTF-8；UTF-8 BOM 可直接读取，不按系统 ANSI 猜测业务文件 |

真实 Trae 触发失败时记录客户端版本、使用模式和错误，不将文件安装成功视为运行验收通过。
