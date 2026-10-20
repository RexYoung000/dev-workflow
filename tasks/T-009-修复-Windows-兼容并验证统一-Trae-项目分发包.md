---
id: T-009
title: 修复 Windows 兼容并验证统一 Trae 项目分发包
module: workflow
status: in-progress
deps: 
issue: 
assignee: 
---

## 描述

按用户授权修复 Windows 编码、BOM/换行、长 Issue 正文、测试替身及更新恢复；国内版和国际版共用项目分发包。先提交契约，再实施和真实跨平台自动测试；客户端验收单独记录。

## 验收标准

- [ ] 文档先提交，统一地区版本与 Windows 处理契约
- [ ] 编码、BOM/CRLF、长正文与路径/文件占用修复通过回归
- [ ] Windows/macOS/Linux 的真实 CI 测试通过，假 gh 不访问网络
- [ ] 安装包及资源验证通过，真实客户端覆盖与限制准确记录
- [ ] 普通提交推送完成，完整体验留待用户验收
