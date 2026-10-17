# AGENTS.md — agent 操作手册

> 任何 agent 进入本仓库，先读本文件。本地文件是唯一事实源，GitHub Issue 为单向镜像存档。

## 项目流程（6 阶段）

1. 需求/PRD → 2. 技术规范 → 3. Demo 验证 → 4. Task/Issue 拆解 → 5. Agent 执行 → 6. 测试与验收

- 门槛不通过不得进入下一阶段：`python3 scripts/workflow.py phase next`
- 新需求从阶段 6 回流到阶段 1，缺陷从阶段 6 回到阶段 5。

## 文件地图

| 路径 | 说明 |
|---|---|
| docs/prd.md | 唯一 PRD 事实源 |
| docs/tech-spec.md | 技术文档与规范 |
| docs/templates/ | prd / tech-spec / task 模板 |
| tasks/ | Task 文件（front-matter 的 status 字段为状态事实源） |
| .workflow/state.json | 项目阶段与配置（phase / repo / config.max_parallel） |
| scripts/workflow.py | 流程管理 CLI |

## 基本规则

- commit 格式：`<type>(<module>): 中文描述 #<Issue号>`，type ∈ feat / fix / docs / refactor / test / chore
- Task 状态机：todo → in-progress → review → done；blocked 任意时刻可进入
- 并发执行：不同模块且无依赖的 Task 可并行，上限见 state.json 的 config.max_parallel
- 禁止 force push、禁止跳过 hooks
