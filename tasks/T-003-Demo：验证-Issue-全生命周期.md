---
id: T-003
title: Demo：验证 Issue 全生命周期
module: scripts
status: done
deps: 
issue: 3
assignee: 
---

## 描述

阶段 3 Demo 的验证载体：用真实 GitHub 仓库跑通 Issue 创建、编号回填、幂等重跑、done 关闭四步，验证 task sync 的完整生命周期。

## 验收标准

- [x] 首次 sync：3 个 Task 均创建 Issue 并回填编号
- [x] 重跑 sync：新建 0，远端 Issue 数量不增加（幂等）
- [x] 清空 issue 字段后 sync：按标题 [T-xxx] 二次校验回填，不产生重复
- [x] status=done 后 sync：对应 Issue 被关闭
