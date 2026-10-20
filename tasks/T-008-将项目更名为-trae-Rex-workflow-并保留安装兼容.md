---
id: T-008
title: 将项目更名为 trae-Rex-workflow 并保留安装兼容
module: workflow
status: in-progress
deps: 
issue: 8
assignee: 
---

## 描述

按用户确认将项目和 GitHub 仓库更名为 trae-Rex-workflow。保留 dev-workflow 作为稳定 Skill ID 与安装目录；支持新名称点名，旧项目不需迁移。Windows 与国际版本轮仅做兼容性评估，不把改名等同于平台兼容修复。

## 验收标准

- [ ] 先更新命名契约、README 与维护文档
- [ ] 同步仓库名、origin 和本仓库 repo 缓存，保留历史和 Issue
- [ ] 新名称可点名触发，旧 Skill ID 与路径保持兼容
- [ ] 必要回归、结构检查和新地址安装验证通过
- [ ] 普通提交推送完成，最终体验验收仍待用户确认
