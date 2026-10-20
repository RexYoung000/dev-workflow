# dev-workflow 验证与验收记录

## v1.1 Trae 项目级分发（2026-10-20）

状态：实现与代理验证通过；真实 Trae 新会话点名烟测通过；首次提交推送与公开 clone 复核进行中。用户完整体验验收待确认，不归档本轮迭代。

### 先文档后实施

本轮范围由用户明确授权，许可证由用户选择 MIT。PRD、技术规范、维护入口、README 与 LICENSE 先独立提交于 `bab7d2c`，然后迁移并实现自包含分发包。跟踪任务 T-007 / Issue #7。

### 实现与代理验证

| 项目 | 结果与实际覆盖 |
|---|---|
| 完整分发 | Skill 内含 CLI、模板、参考文件；安装带 LICENSE 和薄规则；根 CLI 为兼容入口，唯一实现位于 Skill |
| 空项目 | install --init → 阶段 1、空 Task、无业务 PRD；无源账号和历史状态 |
| 自包含 | 测试复制完整分发源、安装后删除源 checkout，包内 new/status 仍可用；可再次安装到另一个空项目 |
| 已有项目 | AGENTS、业务文档、同名规则、自定义模板、Task、phase/config 逐字保留 |
| 更新与回退 | 内容相同不备份；变更先备份；模拟包替换失败时恢复旧包；链接/缺资源/错误目标在写入前拒绝 |
| 项目隔离 | 目标 origin 自动识别；缓存冲突、无 origin、伪 GitHub 主机、GH_HOST 指向其他主机、跨项目使用已安装 CLI 均拒绝危险路径 |
| 同步 | 假 gh 后端验证登录、权限、Issues 前置；创建/回填/关闭、重复同步、创建后响应丢失恢复；异常 done 与错误 Issue 映射不关闭 |
| 门槛与依赖 | 缺字段、重复 ID、缺依赖、依赖环、非法 Issue、done 未验收无法前进；候选尊重依赖、模块及上限 |
| 自动测试 | `python3 -m unittest discover -s tests -v`：34 项通过（Python 3.13.3） |
| Skill 检查 | skill-creator quick_validate 通过；相对资源引用与 Python 3.9 语法检查通过 |

测试所需 PyYAML 仅安装于仓库外的隔离验证目录；产品运行仍仅依赖 Python 标准库。GitHub 模拟测试没有访问或写入真实业务仓库。真实远端操作仅用于本仓库正式跟踪任务。

### 真实 Trae 客户端烟测

- 环境：macOS，Trae CN **3.4.4**，本地 Agent 会话，GLM-5.3-Flash；Python 3.13.3、Git 2.54.0、gh 2.73.0。
- 独立项目：`trae-client-verification`，通过 install --init 安装；不使用原有开发项目或会话。
- 新会话请求：点名 dev-workflow，只读加载技能、读取 AGENTS、运行 status，禁止写文件、联网和 Issue/提交/推送操作。
- UI 工具记录实际显示“调用技能：dev-workflow”，描述与新版包一致；随后读取 1 个文件并执行 1 条命令。
- 结果：项目内 `.trae/skills/dev-workflow/scripts/workflow.py status` 返回阶段 1、并发上限 3、有效/异常 Task 都为 0、origin 与仓库缓存未配置。
- 再由外部 CLI 检查同一项目，状态与 Task 数量一致，无新增 Task 或业务文档。
- 结论：**项目 Skill 被真实 Trae 发现，点名加载与包内 CLI 运行通过**。该结论仅覆盖本机版本与只读入口。

### 加载量与分发资源

- 默认发现的 name/description 元数据：309 字节。
- 调用时 SKILL.md 入口全文：2370 字节（约 2.37 KB）。
- 完整安装包：11 个文件，43503 字节（约 43.50 KB，含脚本、模板、参考文件及许可，不含运行缓存）。
- 参考与资产是按需资源，迁移进包不算删除或减少总资源；不会在 Skill 被调用时自动把全部 CLI/模板源码注入上下文。

### 尚未覆盖与用户验收

- Windows、Linux、Trae 国际版及其他客户端版本未做真实运行；Python 3.9 仅语法核对，实际测试为 3.13.3。
- 不点名的语义自动匹配、规则独立自动注入、子智能体并发和完整六阶段业务体验未逐项 UI 验证。
- GitHub 测试使用假后端覆盖生命周期；未为测试创建新的真实业务仓库或制造测试 Issue。
- 用户可在自己的项目安装，Trae 新开会话发送“用 dev-workflow 继续当前项目”，核对仅出现该项目的阶段、仓库与 Task。最终使用体验由用户验收。

---

下列内容为 v1.0 历史原文，旧章节编号与完成状态只指当时版本，不代表 v1.1 已获用户验收。

## v1.0 历史验收（2026-10-18）

| 项 | 值 |
|---|---|
| 验收日期 | 2026-10-18 |
| 验收人 | Rex（项目所有者，PRD §2） |
| 结论 | **验收通过，项目归档** |

## 交付物

| 交付物 | 位置 |
|---|---|
| PRD v1.0 | docs/prd.md |
| 技术规范 v1.0 | docs/tech-spec.md |
| AGENTS.md 操作手册 | AGENTS.md |
| CLI（Python 标准库单文件） | scripts/workflow.py |
| Trae 项目级 Skill（已安装可触发） | skill/dev-workflow/ → .trae/skills/dev-workflow/ |
| GitHub 镜像 | github.com/RexYoung000/dev-workflow（Issue #1-#6 全部关闭） |

## Agent 测试复查结论（2026-10-18）

sync 幂等复测 0 新建 / 0 关闭；init 内嵌 AGENTS 模板与定稿逐字一致；安装副本与仓库源 diff 无差异；远端 Issue 全部 CLOSED；本地与 origin/main 同步且工作区干净。

## 用户验收

- Skill 新会话触发实测通过（T-006，2026-10-18）。
- 2026-10-18 用户确认整体验收通过。

## 迭代回流记录

- 缺陷：无。
- 新需求：无。后续迭代候选见 PRD §10 非目标（Web 面板、Issue 双向同步等）。
