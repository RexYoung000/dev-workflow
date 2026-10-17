---
id: T-001
title: 编写 AGENTS.md 通用操作手册
module: docs
status: done
deps: 
issue: 1
assignee: agent-A
---

## 描述

依据 PRD 与技术规范，将根目录 AGENTS.md 从 init 骨架重写为完整的 agent 操作手册（PRD FR-3）：事实源原则、文件地图、六阶段流程与门槛指引、CLI 速查、commit / 状态机 / 并发规则、新 agent 上下文恢复路径。

## 验收标准

- [x] 覆盖 FR-3 要求：6 阶段流程指引、文件地图、规则引用入口
- [x] 事实源表述与技术规范 §2 一致（Task 状态以 front-matter 为准）
- [x] commit 格式、状态机、并发规则与技术规范 §6/§7 一致
- [x] 引用 PRD / tech-spec 标注章节号，无大段复制
