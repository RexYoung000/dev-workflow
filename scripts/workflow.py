#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""workflow.py — dev-workflow 项目流程管理 CLI（Python 标准库单文件实现）

用法:
  workflow init                                        初始化项目骨架（幂等，已存在文件跳过）
  workflow task new --title 标题 --module 模块 [--deps T-002,T-003]   新建 Task
  workflow task sync                                   Task → GitHub Issues 单向同步（幂等）
  workflow status                                      项目状态汇总（只读）
  workflow phase next                                  进入下一阶段（校验门槛）
  workflow phase set N                                 设置阶段（前进校验门槛，回退免校验）
"""

import argparse
import json
import re
import subprocess
import sys
from datetime import datetime
from pathlib import Path

VALID_STATUS = ["todo", "in-progress", "review", "done", "blocked"]
REQUIRED_FIELDS = ["id", "title", "module", "status"]
FIELD_ORDER = ["id", "title", "module", "status", "deps", "issue", "assignee"]
PHASE_NAMES = {
    1: "需求/PRD",
    2: "技术规范",
    3: "Demo 验证",
    4: "Task/Issue 拆解",
    5: "Agent 执行",
    6: "测试与验收",
}

AGENTS_SKELETON = """# AGENTS.md — agent 操作手册

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
"""

PRD_TEMPLATE = """# （项目名）产品需求文档（PRD）

| 项 | 值 |
|---|---|
| 版本 | v0.1 草稿 |
| 状态 | 草稿（待用户确认） |
| 日期 | （日期） |
| 载体约定 | 本文件为唯一 PRD 事实源，纯 Markdown，随仓库版本化 |

## 1. 背景与问题
（待补充）

## 2. 产品定位与用户
（待补充）

## 3. 产品契约

| 要素 | 定义 |
|---|---|
| 触发 | （待补充） |
| 核心工作 | （待补充） |
| 完成条件 | （待补充） |
| 信任原则 | 本地文件是唯一事实源；GitHub 是单向镜像存档 |

## 4. 核心对象（唯一定义）
（待补充）

## 5. 核心旅程
（待补充）

## 6. 功能需求
（待补充）

## 7. 非目标（本期不做）
（待补充）

## 8. 已确认决策记录

| # | 决策点 | 结论 | 依据 |
|---|---|---|---|

## 9. 待定项

- [TBD]（待补充）
"""

TECH_SPEC_TEMPLATE = """# （项目名）技术文档与技术规范

| 项 | 值 |
|---|---|
| 版本 | v0.1 草稿 |
| 日期 | （日期） |
| 依据 | PRD 版本号 |

## 1. 技术栈决策
（待补充）

## 2. 架构与目录规范
（待补充）

## 3. 数据模型 / 接口约定
（待补充）

## 4. 错误处理与边界
（待补充）

## 5. 技术验证清单（阶段 3 Demo 依据）

| # | 验证点 | 通过标准 | 结论 |
|---|---|---|---|

## 6. 已确认项
（待补充）
"""

TASK_TEMPLATE = """---
id:
title:
module:
status: todo
deps:
issue:
assignee:
---

## 描述

（待补充：背景、目标与范围）

## 验收标准

- [ ] （待补充：可检验的完成条件）
"""


# ---------- 通用工具 ----------

def die(msg, code=1):
    print(f"[错误] {msg}", file=sys.stderr)
    sys.exit(code)


def run(cmd, cwd=None, check=True):
    try:
        r = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    except FileNotFoundError:
        die(f"未找到命令 {cmd[0]}，请先安装")
    if check and r.returncode != 0:
        die(f"命令执行失败：{' '.join(cmd)}\n  {(r.stderr or r.stdout).strip()}")
    return r


def gh(args, check=True):
    try:
        r = subprocess.run(["gh", *args], capture_output=True, text=True)
    except FileNotFoundError:
        die("未找到 gh 命令，请先安装 GitHub CLI")
    if r.returncode != 0:
        tail = (r.stderr or r.stdout or "未知错误").strip().splitlines()
        if check:
            die(
                "gh 命令失败：gh " + " ".join(args)
                + f"\n  {tail[-1] if tail else ''}"
                + "\n  请检查 gh 登录状态（gh auth status）与网络连接。",
                2,
            )
    return r.stdout


def find_root():
    p = Path.cwd().resolve()
    for d in (p, *p.parents):
        if (d / ".workflow" / "state.json").is_file():
            return d
    die("当前目录不在 workflow 管理的项目内（未找到 .workflow/state.json）。请先运行: workflow init")


def load_context():
    root = find_root()
    return root, load_state(root)


def load_state(root):
    return json.loads((root / ".workflow" / "state.json").read_text(encoding="utf-8"))


def save_state(root, state):
    state["updated_at"] = datetime.now().astimezone().isoformat(timespec="seconds")
    (root / ".workflow" / "state.json").write_text(
        json.dumps(state, ensure_ascii=False, indent=2) + "\n", encoding="utf-8"
    )


def detect_repo(root):
    """从 git remote origin URL 推断 GitHub 仓库（owner/name），失败返回空串。"""
    r = run(["git", "remote", "get-url", "origin"], cwd=root, check=False)
    m = re.search(r"github\.com[:/]([^/]+/[^/]+?)(?:\.git)?/?$", r.stdout.strip())
    return m.group(1) if m else ""


def resolve_repo(root, state, required=False):
    repo = state.get("repo") or detect_repo(root)
    if repo and repo != state.get("repo"):
        state["repo"] = repo
        save_state(root, state)
        print(f"[配置] repo 已写入 state.json: {repo}")
    if required and not repo:
        die("无法确定 GitHub 仓库：state.json 未配置 repo，且 git remote origin 缺失")
    return repo


# ---------- Task 文件解析（front-matter 轻量子集） ----------

def parse_task(path):
    """返回 (fields, body)。front-matter 为 'key: value' 简单子集，body 原样保留。"""
    text = path.read_text(encoding="utf-8")
    m = re.match(r"\A---\n(.*?)\n---\n(.*)\Z", text, re.S)
    if not m:
        return {}, text
    fields = {}
    for line in m.group(1).splitlines():
        if ":" in line:
            k, v = line.split(":", 1)
            fields[k.strip()] = v.strip()
    return fields, m.group(2)


def render_task(fields, body):
    keys = [k for k in FIELD_ORDER if k in fields] + [k for k in fields if k not in FIELD_ORDER]
    fm = "\n".join(f"{k}: {fields[k]}" for k in keys)
    return f"---\n{fm}\n---\n{body}"


def save_task(t):
    t["path"].write_text(render_task(t["fields"], t["body"]), encoding="utf-8")


def scan_tasks(root):
    """扫描 tasks/*.md，返回 (valid, invalid)。

    invalid 元素为 (path, fields, missing_fields, bad_status)。
    """
    valid, invalid = [], []
    tasks_dir = root / "tasks"
    if not tasks_dir.is_dir():
        return valid, invalid
    for p in sorted(tasks_dir.glob("*.md")):
        fields, body = parse_task(p)
        missing = [k for k in REQUIRED_FIELDS if not fields.get(k)]
        status = fields.get("status", "")
        bad_status = status if status and status not in VALID_STATUS else ""
        if missing or bad_status:
            invalid.append((p, fields, missing, bad_status))
        else:
            valid.append({"path": p, "fields": fields, "body": body})
    return valid, invalid


# ---------- init ----------

def cmd_init(_args):
    root = Path.cwd().resolve()
    for d in ("docs/templates", "tasks", "scripts", ".workflow"):
        (root / d).mkdir(parents=True, exist_ok=True)
    for rel, content in (
        ("AGENTS.md", AGENTS_SKELETON),
        ("docs/templates/prd-template.md", PRD_TEMPLATE),
        ("docs/templates/tech-spec-template.md", TECH_SPEC_TEMPLATE),
        ("docs/templates/task-template.md", TASK_TEMPLATE),
    ):
        p = root / rel
        if p.exists():
            print(f"[跳过] {rel} 已存在")
        else:
            p.write_text(content, encoding="utf-8")
            print(f"[生成] {rel}")
    if not (root / ".git").exists():
        run(["git", "init", "-b", "main"], cwd=root)
        print("[git] 已初始化仓库（main 分支）")
    sf = root / ".workflow" / "state.json"
    if sf.exists():
        print("[跳过] .workflow/state.json 已存在")
    else:
        state = {"phase": 1, "repo": detect_repo(root), "config": {"max_parallel": 3}}
        save_state(root, state)
        print("[状态] 已写入 .workflow/state.json（阶段 1）")
    print("init 完成")


# ---------- task new ----------

def cmd_task_new(args):
    root, _ = load_context()
    tasks_dir = root / "tasks"
    tasks_dir.mkdir(exist_ok=True)
    valid, invalid = scan_tasks(root)
    nums = []
    for t in valid + [{"fields": f} for _, f, _, _ in invalid]:
        m = re.match(r"T-(\d+)$", t["fields"].get("id", ""))
        if m:
            nums.append(int(m.group(1)))
    next_id = f"T-{max(nums, default=0) + 1:03d}"
    deps = ",".join(d.strip() for d in args.deps.split(",") if d.strip()) if args.deps else ""
    fields = {
        "id": next_id,
        "title": args.title,
        "module": args.module,
        "status": "todo",
        "deps": deps,
        "issue": "",
        "assignee": "",
    }
    tpl_path = root / "docs" / "templates" / "task-template.md"
    if tpl_path.is_file():
        body = parse_task(tpl_path)[1]
    else:
        body = re.sub(r"\A---\n.*?\n---\n", "", TASK_TEMPLATE, flags=re.S)
    slug = re.sub(r'[\\/:*?"<>|#%\s]+', "-", args.title).strip("-") or "task"
    t = {"path": tasks_dir / f"{next_id}-{slug}.md", "fields": fields, "body": body}
    save_task(t)
    print(f"已创建 tasks/{t['path'].name}（{next_id}）")


# ---------- task sync（本地 → GitHub，单向幂等） ----------

def issue_title(fields):
    return f"[{fields['id']}] {fields['title']}"


def build_issue_body(t):
    f = t["fields"]
    rows = "\n".join(f"| {k} | {f.get(k) or '（无）'} |" for k in FIELD_ORDER)
    return (
        f"> 本地 Task 文件 `tasks/{t['path'].name}` 为唯一事实源，本 Issue 为单向镜像存档，请勿在远端编辑。\n\n"
        f"| 字段 | 值 |\n|---|---|\n{rows}\n\n{t['body'].strip()}\n"
    )


def gh_find_issue(repo, tid):
    """按 Issue 标题 [T-xxx] 二次校验查找远端已有 Issue，返回编号或 None。"""
    out = gh(["issue", "list", "--repo", repo, "--state", "all",
              "--search", f'"{tid}" in:title', "--limit", "20", "--json", "number,title"])
    for it in json.loads(out or "[]"):
        if it["title"].startswith(f"[{tid}]"):
            return it["number"]
    return None


def ensure_labels(repo, module):
    for name, color in (("task", "0E8A16"), (f"module:{module}", "1D76DB")):
        gh(["label", "create", name, "--repo", repo, "--color", color, "--force"], check=False)


def cmd_task_sync(_args):
    root, state = load_context()
    repo = resolve_repo(root, state, required=True)
    valid, invalid = scan_tasks(root)
    for p, _f, missing, bad_status in invalid:
        reason = []
        if missing:
            reason.append("缺少必填字段: " + ", ".join(missing))
        if bad_status:
            reason.append(f"status 非法: {bad_status}")
        print(f"[跳过] {p.name}（{'；'.join(reason)}）")

    created = backfilled = closed = 0

    # 第一步：无 Issue 编号的 Task → 先按标题查重，再创建或回填
    for t in valid:
        if t["fields"].get("issue"):
            continue
        tid = t["fields"]["id"]
        existing = gh_find_issue(repo, tid)
        if existing:
            t["fields"]["issue"] = str(existing)
            save_task(t)
            backfilled += 1
            print(f"[回填] {tid} ← 已存在 Issue #{existing}")
        else:
            ensure_labels(repo, t["fields"]["module"])
            url = gh(["issue", "create", "--repo", repo,
                      "--title", issue_title(t["fields"]),
                      "--body", build_issue_body(t),
                      "--label", "task",
                      "--label", f"module:{t['fields']['module']}"])
            num = url.strip().rstrip("/").rsplit("/", 1)[-1]
            t["fields"]["issue"] = num
            save_task(t)
            created += 1
            print(f"[创建] {tid} → Issue #{num}")

    # 第二步：status=done 的 Task → 关闭对应 Issue
    for t in valid:
        f = t["fields"]
        if f["status"] != "done" or not f.get("issue"):
            continue
        st = gh(["issue", "view", f["issue"], "--repo", repo,
                 "--json", "state", "-q", ".state"]).strip()
        if st == "OPEN":
            gh(["issue", "close", f["issue"], "--repo", repo])
            closed += 1
            print(f"[关闭] {f['id']} → Issue #{f['issue']}")

    print(f"\n同步汇总：新建 {created} / 回填 {backfilled} / 关闭 {closed} / 异常跳过 {len(invalid)}")


# ---------- status ----------

def cmd_status(_args):
    root, state = load_context()
    repo = state.get("repo") or detect_repo(root)
    valid, invalid = scan_tasks(root)
    phase = state.get("phase", 1)
    print(f"项目阶段: {phase}（{PHASE_NAMES.get(phase, '?')}）")
    print(f"GitHub 仓库: {repo or '（未配置）'}")
    print(f"并发上限: {state.get('config', {}).get('max_parallel', 3)}")

    if invalid:
        print(f"\n[异常] {len(invalid)} 个 Task 文件字段缺失/非法：")
        for p, _f, missing, bad in invalid:
            det = ", ".join(filter(None, [
                f"缺少 {', '.join(missing)}" if missing else "",
                f"status 非法 {bad}" if bad else "",
            ]))
            print(f"  - {p.name}（{det}）")

    counts = {s: 0 for s in VALID_STATUS}
    for t in valid:
        counts[t["fields"]["status"]] += 1
    print(f"\nTask 统计: 共 {len(valid)}"
          + "".join(f" | {s} {counts[s]}" for s in VALID_STATUS))
    unsynced = [t["fields"]["id"] for t in valid if not t["fields"].get("issue")]
    print(f"未同步（无 Issue 编号）: {', '.join(unsynced) if unsynced else '无'}")
    blocked = [t["fields"]["id"] for t in valid if t["fields"]["status"] == "blocked"]
    print(f"blocked: {', '.join(blocked) if blocked else '无'}")

    limit = state.get("config", {}).get("max_parallel", 3)
    groups = {}
    for t in valid:
        if t["fields"]["status"] in ("todo", "in-progress"):
            groups.setdefault(t["fields"]["module"], []).append(t["fields"]["id"])
    print(f"\n并行分组预览（上限 {limit}）:")
    if groups:
        for m, ids in groups.items():
            print(f"  - {m}: {', '.join(ids)}")
        note = "可并行" if len(groups) <= limit else f"超出上限 {limit}，请分批或调大 max_parallel"
        print(f"  → {len(groups)} 个模块组，{note}")
    else:
        print("  （无可执行 Task）")


# ---------- phase（阶段门槛） ----------

def gate_gaps(root, target):
    """进入 target 阶段（含累积门槛）未满足项列表。"""
    gaps = []
    valid, invalid = scan_tasks(root)
    if target >= 2 and not (root / "docs" / "prd.md").is_file():
        gaps.append("缺少 docs/prd.md")
    if target >= 3 and not (root / "docs" / "tech-spec.md").is_file():
        gaps.append("缺少 docs/tech-spec.md")
    if target >= 4 and len(valid) + len(invalid) == 0:
        gaps.append("tasks/ 下没有任何 Task")
    if target >= 5:
        no_issue = [t["fields"]["id"] for t in valid if not t["fields"].get("issue")]
        if no_issue:
            gaps.append("以下 Task 未回填 Issue 编号: " + ", ".join(no_issue))
    if target >= 6:
        not_done = [t["fields"]["id"] for t in valid if t["fields"]["status"] != "done"]
        if not_done:
            gaps.append("以下 Task 未完成: " + ", ".join(not_done))
    return gaps


def cmd_phase(args):
    root, state = load_context()
    cur = state.get("phase", 1)
    if args.phase_cmd == "next":
        if cur >= 6:
            die("已在最后阶段（6），无下一步")
        target = cur + 1
    else:
        target = args.n
        if not 1 <= target <= 6:
            die("阶段编号必须是 1-6")
    if target <= cur:
        state["phase"] = target
        save_state(root, state)
        verb = "回退" if target < cur else "保持"
        extra = "（迭代回流，无需校验）" if target == 1 and target < cur else ""
        print(f"已{verb}到阶段 {target}（{PHASE_NAMES[target]}）{extra}")
        return
    gaps = gate_gaps(root, target)
    if gaps:
        print(f"无法进入阶段 {target}（{PHASE_NAMES[target]}），未满足门槛：")
        for g in gaps:
            print(f"  - {g}")
        sys.exit(1)
    state["phase"] = target
    save_state(root, state)
    print(f"门槛校验通过，已进入阶段 {target}（{PHASE_NAMES[target]}）")


# ---------- 入口 ----------

def main():
    ap = argparse.ArgumentParser(prog="workflow", description="dev-workflow 项目流程管理 CLI")
    sub = ap.add_subparsers(dest="cmd", required=True)
    sub.add_parser("init", help="初始化项目骨架（幂等）")
    task_ap = sub.add_parser("task", help="Task 管理")
    task_sub = task_ap.add_subparsers(dest="task_cmd", required=True)
    tn = task_sub.add_parser("new", help="新建 Task")
    tn.add_argument("--title", required=True, help="中文标题")
    tn.add_argument("--module", required=True, help="模块名（如 docs / scripts / skill）")
    tn.add_argument("--deps", default="", help="依赖 Task id，逗号分隔")
    task_sub.add_parser("sync", help="Task → GitHub Issues 单向同步（幂等）")
    sub.add_parser("status", help="项目状态汇总（只读）")
    ph = sub.add_parser("phase", help="阶段管理")
    ph_sub = ph.add_subparsers(dest="phase_cmd", required=True)
    ph_sub.add_parser("next", help="进入下一阶段（校验门槛）")
    ps = ph_sub.add_parser("set", help="设置阶段（前进校验门槛，回退免校验）")
    ps.add_argument("n", type=int, help="目标阶段 1-6")
    args = ap.parse_args()

    if args.cmd == "init":
        cmd_init(args)
    elif args.cmd == "task":
        if args.task_cmd == "new":
            cmd_task_new(args)
        else:
            cmd_task_sync(args)
    elif args.cmd == "status":
        cmd_status(args)
    elif args.cmd == "phase":
        cmd_phase(args)


if __name__ == "__main__":
    main()
