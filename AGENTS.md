# AGENTS.md — trae-Rex-workflow 仓库维护入口

本仓库项目名为 **trae-Rex-workflow**，稳定 Skill ID 与安装路径保留 `dev-workflow` 以兼容既有项目。维护一个 **仅面向 Trae 的项目级工作流包**，由 Skill、Python CLI、参考手册和模板组成。这里的 PRD、技术规范、Task 和状态属于 dev-workflow 自身，禁止作为业务项目的初始数据分发。

## 事实源与文件地图

- `docs/prd.md`：产品范围、用户决定与六阶段流程。
- `docs/tech-spec.md`：安装、数据模型、CLI 与校验契约。
- `skill/dev-workflow/`：可独立运行的分发包；`scripts/workflow.py` 为唯一 CLI 实现，`assets/templates/` 为模板唯一维护来源，`references/` 为操作手册。
- 根目录 `scripts/workflow.py`：兼容维护仓库旧命令的薄入口，不复制实现。
- `tasks/*.md`：本仓库 Task 的唯一状态事实源。
- `.workflow/state.json`：本仓库阶段、仓库地址、并发配置，不含 Task 状态。
- `README.md`：面向使用者的安装和验收入口；`docs/acceptance.md` 区分历史验收、本轮自动验证和待用户验收。

## 维护规则

1. 先更新产品或技术契约，再实施；仅修复已明确的既有行为时不制造无意义文档改动。
2. 六阶段为需求 → 技术规范 → Demo → Task/Issue → 执行 → 测试与用户验收。用户本轮明确授权的范围不重复确认；新的产品选择才重新对齐。
3. 阶段通过 `python3 scripts/workflow.py phase next` 推进，不手工改状态跳过校验。CLI 只校验文件与 Task 条件；用户确认、Demo 运行、实际推送及体验验收由主 Agent 核实，不能宣称机器已证明。
4. 单人维护，main 普通提交；格式 `<type>(<module>): 中文描述 #<Issue号>`。禁止 force push、跳过 hooks；普通 push 不包含合并 PR、发布版本或生产部署授权。
5. Task 使用 `todo → in-progress → review → done`，可进入 blocked；done 必须有实际检查点且全部勾选。只在工作和代理验证完成后标 done；用户最终体验验收单独记录。
6. 不同模块、依赖已完成且文件集不重叠的 Task 才可并行。缺少 Trae 子智能体能力时串行执行；`max_parallel` 只是调度上限，不代表配置了运行时工具。提交由主 Agent 串行完成。
7. 安装和同步测试默认在隔离目录与假 gh 后端执行，禁止用真实业务仓库制造测试 Issue。实际跟踪本次工作的 Issue 可正常同步。
8. 自测至少覆盖空项目、已有项目保留、升级备份、删除源仓库后运行、跨仓库保护、异常 Task 门槛与依赖判断。Skill 文件结构检查不能替代真实 Trae 客户端触发测试；未验证项如实记录。
9. 修改 Skill 时检查所有相对资源引用；不修改系统技能、插件缓存或用户全局配置。禁止在根 CLI 和包内 CLI 分别维护两份实现。

## 恢复上下文

读本文件 → PRD → 技术规范 → `python3 scripts/workflow.py status` → 当前 Task。消费项目的操作手册由包内 `assets/project-agents.md` 生成，不复制本文件。
