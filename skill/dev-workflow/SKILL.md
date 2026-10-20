---
name: dev-workflow
description: trae-Rex-workflow（兼容名 dev-workflow）：在 Trae 中开始或继续已安装项目的六阶段开发流程，编写项目 PRD、拆分 Task 或同步 GitHub Issue。用户点名 trae-Rex-workflow、dev-workflow 或明确需要项目流程管理时使用；单个问答和不涉及项目流程的小修复不强制进入完整六阶段。
---

# trae-Rex-workflow

项目名已更改；稳定 Skill ID 与安装目录仍为 `dev-workflow`，识别新旧两种点名方式。

仅支持 Trae 项目级使用。项目自己的 AGENTS.md、业务文档、Task 与实际实现是事实源；不要把分发仓库的需求、历史任务或状态当作当前项目资料。

## 进入项目

1. 读取目标项目已有 AGENTS.md（若有）及与任务有关的业务资料，遵守用户当前授权；工作流本身不扩大修改、同步或发布权限。
2. 在目标项目根目录使用 `python3 .trae/skills/dev-workflow/scripts/workflow.py`；这是自带 CLI，不依赖源码 checkout，也不要求目标已有 scripts/workflow.py。Windows 可使用 `py -3`。
3. 尚无 `.workflow/state.json` 时运行上述入口的 `init`；随后运行 `status`，确认当前阶段、异常 Task、仓库配置与执行候选。中途接手再读取本项目 docs/prd.md、docs/tech-spec.md 和当前 Task。
4. 按当前任务读取 [阶段与执行约定](references/phases.md)。需求决策按 [提问规范](references/questioning.md)；初始化、同步、升级或命令出错时按 [CLI 与安装说明](references/commands.md)。无需一次加载全部参考文件。

## 推进边界

- 先对齐需求与方案，再实施和验证；用户已明确授权的范围不重复确认。工作流不要求已有项目把所有阶段重新做一遍。
- 推进阶段用 CLI 的 `phase next` 或 `phase set N`，不手工改 state.json 绕过门槛。CLI 检查结构与任务条件；用户确认、Demo 实际运行、推送和产品验收另行核实。
- Issue 同步必须使用当前项目自己的 origin、gh 登录和权限；配置不一致时停止，不自动重置 Issue 映射，不使用分发仓库的账号或地址。
- 并行预览只是建议。依赖已完成且无共享文件冲突才分派；仅在当前 Trae 内置 Agent 支持相关子智能体时采用并行，否则串行。提交由主 Agent 串行处理。
- done 需要实际验收检查点全部完成；Agent 自测和用户体验验收分别记录。不将“Skill 被识别”或“命令通过”当作产品验收。
