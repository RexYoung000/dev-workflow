---
id: T-006
title: 安装 Skill 到 Trae 项目级技能目录并实测触发
module: skill
status: review
deps: T-004
issue: 6
assignee: main-agent
---

## 描述

将 `skill/dev-workflow/` 复制安装到 Trae 项目级技能目录（`.trae/skills/dev-workflow/`，以实际生效路径为准），并在 Trae 新会话实测：点名「用 dev-workflow 开始新项目 / 继续当前项目」能触发 Skill（PRD FR-10 触发约定）。这是 workflow 可被日常使用的最后一步。

## 验收标准

- [x] 安装目录结构完整（SKILL.md + references/ 三份）
- [ ] Trae 新会话中点名触发成功
- [x] 实测确认的安装路径与步骤回写至 references/commands.md
