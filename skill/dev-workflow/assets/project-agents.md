# 项目操作入口

本项目使用 Trae 项目级 dev-workflow 管理开发流程。

- 开始或继续流程前，读取 `.trae/skills/dev-workflow/SKILL.md` 和其中需要的参考手册。
- 产品与技术事实以本项目 `docs/prd.md`、`docs/tech-spec.md` 及实际实现为准。
- 任务以本项目 `tasks/*.md` 为准，阶段与配置见 `.workflow/state.json`。
- CLI 入口：`python3 .trae/skills/dev-workflow/scripts/workflow.py`；先运行 `status` 恢复上下文。
- 新需求先对齐再实施，代理验证与用户最终体验验收分别记录；发布和生产部署另行获得授权。
