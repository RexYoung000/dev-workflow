---
id: T-005
title: AGENTS.md 定稿同步进 workflow init 内嵌模板
module: scripts
status: done
deps: T-001
issue: 5
assignee: agent-D
---

## 描述

T-001 定稿 AGENTS.md 后，将定稿内容同步为 `scripts/workflow.py` 的内嵌模板常量，使 `workflow init` 在新项目产出的操作手册与本仓库定稿版一致（PRD §7：init 需生成约定文件）。保持幂等语义不变：已存在文件跳过不覆盖。

## 验收标准

- [x] workflow.py 内嵌 AGENTS 模板与仓库根 AGENTS.md 定稿内容一致
- [x] 在空目录执行 init 产出完整骨架且 AGENTS.md 为定稿版
- [x] 重复执行 init 不覆盖已有文件，status 命令正常运行
