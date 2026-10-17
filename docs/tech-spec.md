# dev-workflow 技术文档与技术规范

| 项 | 值 |
|---|---|
| 版本 | v1.0 已确认（2026-10-17） |
| 日期 | 2026-10-17 |
| 依据 | PRD v1.0 定稿（D1-D12） |
| 环境实测 | Python 3.13.3 / git 2.54.0 / gh CLI 2.73.0（已登录 RexYoung000） |

## 1. 技术栈决策（解决 PRD §12 全部 TBD）

| 决策点 | 选择 | 理由 |
|---|---|---|
| CLI 实现语言 | **Python 3（≥3.9，仅标准库）** | 本机实测可用；JSON/文件处理原生；零第三方依赖，任何机器开箱即跑 |
| Task 状态载体 | `tasks/*.md` + **轻量 front-matter**（`key: value` 简单子集） | 人可读、agent 可直接编辑；自写约 20 行解析器，不引入 YAML 库 |
| 项目状态载体 | `.workflow/state.json` | 标准库 json；存阶段与配置 |
| 外部依赖 | `gh` CLI、`git`、`python3` | 均已实测存在 |

## 2. 事实源划分（对 PRD §4 的技术性澄清）

- **Task 状态唯一事实源 = Task 文件 front-matter 的 `status` 字段**。
- `workflow status` 实时扫描 `tasks/` 汇总统计；**state.json 不存 Task 状态**，只存项目阶段与配置 → 从根上消除双源不一致。
- PRD 中「状态文件记录全部 Task 状态」据此澄清为：「状态文件记录项目阶段与配置；Task 状态以 Task 文件为准，汇总由命令实时计算」。

## 3. 仓库结构（目录规范）

```
dev-workflow/
├── AGENTS.md                 # agent 操作手册：流程入口、文件地图、规则引用
├── docs/
│   ├── prd.md                # 唯一 PRD 事实源
│   ├── tech-spec.md          # 本文件
│   └── templates/            # prd / tech-spec / task 三套模板
├── tasks/                    # T-001-<slug>.md
├── scripts/workflow.py       # 单文件 CLI（Python 标准库）
├── .workflow/state.json      # 项目阶段 + 配置
└── skill/dev-workflow/       # Trae 项目级 skill 源码（随仓库版本化）
    ├── SKILL.md
    └── references/           # phases.md / questioning.md / commands.md
```

## 4. 数据模型

### 4.1 Task 文件 front-matter 字段

| 字段 | 必填 | 说明 |
|---|---|---|
| `id` | 是 | `T-001` 起递增，全局唯一 |
| `title` | 是 | 中文短句 |
| `module` | 是 | 模块名（scripts / docs / skill / …），并发分组依据 |
| `status` | 是 | `todo / in-progress / review / done / blocked` |
| `deps` | 否 | 依赖的 Task id 列表 |
| `issue` | 否 | Issue 编号，sync 后回填 |
| `assignee` | 否 | 执行 agent 标识 |

正文固定两节：`## 描述`、`## 验收标准`（checkbox 列表，全部勾选才允许置 done）。

### 4.2 state.json

```json
{
  "phase": 1,
  "repo": "RexYoung000/dev-workflow",
  "config": { "max_parallel": 3 },
  "updated_at": "2026-10-17T00:00:00+08:00"
}
```

### 4.3 Issue 映射规则

- 标题：`[T-001] 中文标题`（Task id 二次校验依据）
- 标签：`task` + `module:<模块>`
- 正文：Task 全字段 + 验收标准，注明「本地 tasks/ 文件为事实源」
- 关闭：Task `status=done` → 同步时关闭对应 Issue

## 5. CLI 命令规格（scripts/workflow.py）

| 命令 | 行为 | 幂等策略 |
|---|---|---|
| `workflow init` | 建目录骨架 + 生成约定文件 + `git init` + 写 state.json | 已存在的文件跳过不覆盖 |
| `workflow task new --title --module [--deps]` | 按模板生成下一个 T-xxx 文件 | id 取现有最大值 +1 |
| `workflow task sync` | 扫描 tasks/：无 issue 的创建 Issue 并回填编号；done 的关闭 Issue；输出同步汇总 | 以 front-matter `issue` 字段去重 + Issue 标题 `[T-xxx]` 二次校验 |
| `workflow status` | 输出：当前阶段、各状态 Task 计数、未同步 Task、blocked 项、并行分组预览 | 只读 |
| `workflow phase next` / `phase set N` | 推进项目阶段，执行门槛校验（§5.1） | 校验失败拒绝推进并列出缺口 |

### 5.1 阶段门槛校验规则（V4 依据）

| 目标阶段 | 门槛 |
|---|---|
| ≥2 | `docs/prd.md` 存在 |
| ≥3 | `docs/tech-spec.md` 存在 |
| ≥4 | `tasks/` 下至少 1 个 Task 且 `docs/prd.md`、`docs/tech-spec.md` 齐备 |
| ≥5 | 全部 Task `issue` 字段已回填 |
| ≥6 | 全部 Task `status=done` |
| 阶段 1 | 允许从任意阶段回退（迭代回流），无需校验 |

错误处理：

- `gh` 未登录 / 无网络：非零退出码 + 中文报错，不静默失败。
- Task 必填字段缺失：列出缺失字段、跳过该 Task、继续处理其余。
- sync 中断：可安全重跑（去重策略保证不产生重复 Issue）。

## 6. commit 与分支规范

- 分支策略：单人单机，**main 直接提交**（简单优先，练习项目不设分支矩阵）。
- 格式：`<type>(<module>): 中文描述 #<issue>`，type ∈ feat / fix / docs / refactor / test / chore。
- 时机：Task 进入 review 或 done 即 commit + push。
- 禁止：跳过 hooks、force push；push 失败重试或报告。

## 7. 并发模型（落实 FR-8 / D11）

- **并行 = 多个子代理同时执行各自 Task 的工作；git commit 由主 agent 串行执行**（Task 完成一个提交一个，规避 git index 竞争）。
- 文件隔离：并发 Task 的文件集不得相交，由 `module` 维度约束。
- 并发上限读 `state.json → config.max_parallel`，默认 3，用户可随时改。

## 8. Skill 规格（FR-10 / D9）

- `skill/dev-workflow/SKILL.md`：name + description（内嵌触发词：dev-workflow、开始新项目、继续项目、写 PRD、拆 Task、同步 Issue）。
- `references/` 三份：
  - `phases.md`：六阶段定义 + 严格门槛检查清单
  - `questioning.md`：逐题 + 选项卡提问规范（对应 FR-1）
  - `commands.md`：CLI 四命令用法与错误处理
- 安装：源码随 dev-workflow 仓库版本化；使用时复制到目标项目的 Trae 项目技能目录（确切路径在 Demo 阶段实测确认）。

## 9. 技术验证清单（阶段 3 Demo 执行）

| # | 验证点 | 通过标准 |
|---|---|---|
| V1 | front-matter 轻量解析器 | Task 字段读写无损、缺失字段正确报告 |
| V2 | gh 创建 Issue + 回填 | 创建成功、编号回填、重跑 sync 零重复 |
| V3 | status 汇总 | 各状态计数与实际文件一致 |
| V4 | 阶段门槛检查 | 非法跳阶段被拦截并提示 |
| Demo 闭环 | 示例项目全流程 | init → 2 个示例 Task → sync → status 全链路跑通 |

## 10. 已确认项（2026-10-17 用户确认）

三项均按本文件方案确认执行：

1. **事实源划分**（§2）：Task 状态以 front-matter 为准、state.json 只存阶段与配置。
2. **分支策略**（§6）：main 直接提交。
3. **CLI 形态**（§5）：单文件 `workflow.py`（含 `phase` 子命令）。
