---
id: T-004
title: 编写 Skill 完整内容（SKILL.md 与 references 三份）
module: skill
status: done
deps: T-002
issue: 4
assignee: agent-C
---

## 描述

在 T-002 骨架基础上完成 Skill 全部内容（PRD FR-10 / 技术规范 §8）：

- `SKILL.md`：name + description，description 内嵌触发词（dev-workflow、开始新项目、继续项目、写 PRD、拆 Task、同步 Issue）。
- `references/phases.md`：六阶段定义 + 严格门槛检查清单（技术规范 §5.1）。
- `references/questioning.md`：逐题 + 选项卡提问规范（PRD FR-1）。
- `references/commands.md`：CLI 四类命令用法与错误处理（技术规范 §5）。

Skill 定位为流程触发器与操作手册，只引用事实源（AGENTS.md、docs/、tasks/），不复制事实内容。

## 验收标准

- [x] SKILL.md front-matter 含 name 与 description，触发词齐全
- [x] references/ 下 phases.md、questioning.md、commands.md 三份齐全
- [x] 文中引用的阶段门槛、命令行为与技术规范一致，无复制漂移
