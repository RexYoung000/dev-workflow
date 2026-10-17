---
name: dev-workflow
description: "dev-workflow 开发流程的触发器与操作手册：当用户点名 dev-workflow，或请求开始新项目、继续项目、写 PRD、拆 Task、同步 Issue 等与项目流程相关的操作时使用。本 Skill 只负责触发流程并指引 agent 按手册推进，不复制事实内容；事实源始终是项目仓库内的 AGENTS.md、docs/ 与 tasks/。"
---

# dev-workflow Skill

## 定位

本 Skill 是 dev-workflow 开发流程的**触发器与操作手册**：识别流程意图、指引 agent 按约定流程推进项目，不复制事实内容。

## 触发方式

- **用户点名**：用户在对话中直接提及 dev-workflow，例如「用 dev-workflow 开始新项目」「用 dev-workflow 继续当前项目」。
- **语义匹配**：用户请求与 description 中的触发场景匹配时自动调用，例如要求开始新项目、继续项目、写 PRD、拆 Task、同步 Issue。

## 使用前置

- 进入被管理的项目后，**必须先读取项目根目录的 `AGENTS.md`**，再按其指引获取流程与规则；本 Skill 不重复其内容。

## 参考文件索引

| 文件 | 用途 |
|---|---|
| `references/phases.md` | 六阶段流程定义与阶段门槛检查清单 |
| `references/questioning.md` | 需求阶段的逐题 + 选项卡提问规范 |
| `references/commands.md` | CLI 命令用法、错误处理，以及本 Skill 的安装与更新方法 |
