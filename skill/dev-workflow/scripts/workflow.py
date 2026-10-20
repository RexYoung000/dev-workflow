#!/usr/bin/env python3
"""Trae 项目级 trae-Rex-workflow CLI。Python >=3.9，仅标准库。"""

import argparse
from collections import deque
from datetime import datetime
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
from urllib.parse import urlsplit

VERSION = "1.1.1"
PACKAGE = Path(__file__).resolve().parents[1]
STATUSES = ("todo", "in-progress", "review", "done", "blocked")
FIELD_ORDER = ("id", "title", "module", "status", "deps", "issue", "assignee")
PHASES = {1: "需求/PRD", 2: "技术规范", 3: "Demo 验证", 4: "Task/Issue 拆解", 5: "Agent 执行", 6: "测试与验收"}
ID_RE = re.compile(r"T-\d+\Z")
REPO_RE = re.compile(r"[A-Za-z0-9_.-]+/[A-Za-z0-9_.-]+\Z")


class WorkflowError(Exception):
    pass


def fail(message):
    raise WorkflowError(message)


def run(command, cwd=None, check=True, env=None):
    try:
        result = subprocess.run(command, cwd=cwd, env=env, capture_output=True, text=True, timeout=45)
    except FileNotFoundError:
        fail(f"未找到命令 {command[0]}，请先安装")
    except subprocess.TimeoutExpired:
        fail(f"命令 {command[0]} 超时，请检查网络后重试")
    if check and result.returncode:
        fail(f"命令失败：{' '.join(command[:3])}\n{(result.stderr or result.stdout).strip()}")
    return result


def gh(args):
    # 本版只支持 github.com origin，不能让本机 GH_HOST 将写入转向其他主机。
    result = run(["gh", *args], check=False, env=dict(os.environ, GH_HOST="github.com"))
    if result.returncode:
        fail(f"gh {args[0]} 失败：{(result.stderr or result.stdout).strip()}\n请检查 gh auth status、仓库权限与网络后重试。")
    return result.stdout


def inside(path, root):
    try:
        path.relative_to(root)
        return True
    except ValueError:
        return False


def plain_path(root, path):
    """不跟随项目内托管路径的链接，避免升级/初始化写到其他目录。"""
    current = root
    for part in path.relative_to(root).parts:
        current = current / part
        if current.is_symlink():
            fail(f"托管路径不能是符号链接：{current}")


def installed_root():
    if PACKAGE.parent.name == "skills" and PACKAGE.parent.parent.name == ".trae":
        return PACKAGE.parents[2]
    return None


def source_root():
    if PACKAGE.parent.name == "skill":
        return PACKAGE.parents[1]
    return None


def find_root():
    cwd = Path.cwd().resolve()
    owner = installed_root()
    if owner is not None and not inside(cwd, owner):
        fail("请在此 Skill 所安装的业务项目内运行命令，不可操作其他项目。")
    for path in (cwd, *cwd.parents):
        if (path / ".workflow/state.json").is_file():
            if owner is not None and path != owner:
                fail("当前 workflow 根与 Skill 所安装的项目不一致，请使用当前项目自己的 CLI。")
            return path
    fail("未找到 .workflow/state.json，请先运行此项目的 workflow.py init。")


def load_state(root):
    plain_path(root, root / ".workflow/state.json")
    try:
        state = json.loads((root / ".workflow/state.json").read_text(encoding="utf-8"))
    except (ValueError, OSError) as error:
        fail(f"无法读取 .workflow/state.json：{error}")
    if not isinstance(state, dict):
        fail("state.json 必须为 JSON 对象")
    if type(state.get("phase")) is not int or state["phase"] not in PHASES:
        fail("state.json 的 phase 必须为 1-6 整数")
    config = state.get("config")
    if not isinstance(config, dict) or type(config.get("max_parallel")) is not int or config["max_parallel"] < 1:
        fail("state.json 的 config.max_parallel 必须为正整数")
    repo = state.get("repo", "")
    if not isinstance(repo, str) or (repo and not REPO_RE.fullmatch(repo)):
        fail("state.json 的 repo 必须为空或 owner/name")
    return state


def atomic_text(path, text):
    descriptor, temporary = tempfile.mkstemp(prefix=f".{path.name}.", dir=path.parent)
    try:
        with os.fdopen(descriptor, "w", encoding="utf-8", newline="\n") as handle:
            handle.write(text)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def save_state(root, state):
    state["updated_at"] = datetime.now().astimezone().isoformat(timespec="seconds")
    atomic_text(root / ".workflow/state.json", json.dumps(state, ensure_ascii=False, indent=2) + "\n")


def detect_repo(root):
    result = run(["git", "remote", "get-url", "origin"], cwd=root, check=False)
    remote = result.stdout.strip()
    if remote.startswith("git@github.com:"):
        path = remote[len("git@github.com:"):]
    else:
        parsed = urlsplit(remote)
        if parsed.scheme not in ("https", "http", "ssh", "git") or parsed.hostname != "github.com":
            return ""
        path = parsed.path.lstrip("/")
    repo = path.rstrip("/").removesuffix(".git")
    return repo if REPO_RE.fullmatch(repo) else ""


def checked_repo(root, state, required=False, persist=False):
    origin = detect_repo(root)
    cached = state.get("repo", "")
    if origin and cached and origin.casefold() != cached.casefold():
        fail(f"仓库不一致：origin={origin}，state.json repo={cached}。\n已停止，未迁移旧 Issue。请核对项目仓库及 tasks/ 的 Issue 映射后再修正配置。")
    if required and not origin:
        fail("同步需要本项目的 GitHub origin。请配置自己的远端，不能仅依赖 state.json 的仓库缓存。")
    if origin and not cached and persist:
        state["repo"] = origin
        save_state(root, state)
    return origin or cached


def context():
    root = find_root()
    return root, load_state(root)


def payload():
    required = ["SKILL.md", "scripts/workflow.py", "assets/project-agents.md", "assets/trae-rule.md"]
    required += [f"references/{name}.md" for name in ("phases", "commands", "questioning")]
    required += [f"assets/templates/{name}-template.md" for name in ("prd", "tech-spec", "task")]
    for name in required:
        if not (PACKAGE / name).is_file():
            fail(f"源 Skill 不完整，缺少 {name}；请重新获取完整分发仓库。")
    files = {}
    for path in sorted(PACKAGE.rglob("*")):
        if "__pycache__" in path.parts or path.suffix == ".pyc" or path.name == ".DS_Store":
            continue
        if path.is_symlink():
            fail(f"源 Skill 不支持符号链接：{path}")
        if path.is_file():
            files[path.relative_to(PACKAGE).as_posix()] = path.read_bytes()
    license_path = PACKAGE / "LICENSE"
    if source_root() is not None:
        license_path = source_root() / "LICENSE"
    if not license_path.is_file() or license_path.is_symlink():
        fail("分发源缺少 LICENSE，请重新获取完整分发包。")
    files["LICENSE"] = license_path.read_bytes()
    return files


def check_target(root):
    if root.exists() and not root.is_dir():
        fail(f"安装目标不是目录：{root}")
    for rel in (".trae/skills/dev-workflow", ".trae/.dev-workflow-backups", ".trae/rules/dev-workflow.md", ".workflow/state.json", "AGENTS.md", "tasks", "docs/templates"):
        plain_path(root, root / rel)
    directories = (".trae", ".trae/skills", ".trae/skills/dev-workflow", ".trae/rules", ".trae/.dev-workflow-backups", ".workflow", "tasks", "docs", "docs/templates")
    for rel in directories:
        path = root / rel
        if path.exists() and not path.is_dir():
            fail(f"应为目录的路径已被文件占用：{path}")
    files = ["AGENTS.md", ".trae/rules/dev-workflow.md", ".workflow/state.json"]
    files += [f"docs/templates/{name}-template.md" for name in ("prd", "tech-spec", "task")]
    for rel in files:
        path = root / rel
        plain_path(root, path)
        if path.exists() and not path.is_file():
            fail(f"应为文件的路径已被目录占用：{path}")
    if (root / ".workflow/state.json").exists():
        checked_repo(root, load_state(root))


def seed(root, relative, data):
    path = root / relative
    plain_path(root, path)
    if path.exists():
        if not path.is_file():
            fail(f"应为文件的路径已被目录占用：{path}")
        print(f"[保留] {relative}")
        return
    path.parent.mkdir(parents=True, exist_ok=True)
    atomic_text(path, data)
    print(f"[生成] {relative}")


def init_project(root):
    check_target(root)
    root.mkdir(parents=True, exist_ok=True)
    for relative in ("docs/templates", "tasks", ".workflow"):
        (root / relative).mkdir(parents=True, exist_ok=True)
    seed(root, "AGENTS.md", (PACKAGE / "assets/project-agents.md").read_text(encoding="utf-8"))
    for name in ("prd", "tech-spec", "task"):
        relative = f"docs/templates/{name}-template.md"
        seed(root, relative, (PACKAGE / "assets/templates" / f"{name}-template.md").read_text(encoding="utf-8"))
    if not (root / ".git").exists():
        run(["git", "init", "-b", "main"], cwd=root)
        print("[git] 已初始化 main；未配置远端、未推送")
    if (root / ".workflow/state.json").exists():
        print("[保留] .workflow/state.json")
    else:
        save_state(root, {"phase": 1, "repo": detect_repo(root), "config": {"max_parallel": 3}})
        print("[生成] .workflow/state.json（阶段 1，未复制源项目任务）")


def existing_payload(destination):
    files = {}
    if destination.exists():
        for path in destination.rglob("*"):
            if path.is_symlink():
                fail(f"已安装包含符号链接，请先核对：{path}")
            if path.is_file() and "__pycache__" not in path.parts and path.suffix != ".pyc":
                files[path.relative_to(destination).as_posix()] = path.read_bytes()
    return files


def install_project(root, initialize=False):
    if source_root() == root:
        print("[跳过] 目标是 trae-Rex-workflow 源码仓库；请安装到自己的业务项目。")
        return
    files = payload()
    check_target(root)
    destination = root / ".trae/skills/dev-workflow"
    old = existing_payload(destination)
    root.mkdir(parents=True, exist_ok=True)
    if old == files:
        print(f"[跳过] trae-Rex-workflow {VERSION} 安装内容已一致")
    else:
        (root / ".trae/skills").mkdir(parents=True, exist_ok=True)
        temporary = Path(tempfile.mkdtemp(prefix=".dev-workflow-stage-", dir=root / ".trae"))
        backup = None
        staged = temporary / "dev-workflow"
        try:
            for relative, data in files.items():
                path = staged / relative
                path.parent.mkdir(parents=True, exist_ok=True)
                path.write_bytes(data)
            if destination.exists():
                backup_parent = root / ".trae/.dev-workflow-backups"
                backup_parent.mkdir(parents=True, exist_ok=True)
                backup = Path(tempfile.mkdtemp(prefix=datetime.now().strftime("%Y%m%d-%H%M%S-"), dir=backup_parent)) / "dev-workflow"
                destination.rename(backup)
            try:
                staged.rename(destination)
            except OSError:
                if backup is not None:
                    backup.rename(destination)
                raise
            if backup is not None:
                print(f"[备份] {backup}")
            print(f"[安装] trae-Rex-workflow {VERSION} → {destination}")
        finally:
            shutil.rmtree(temporary)
    seed(root, ".trae/rules/dev-workflow.md", (PACKAGE / "assets/trae-rule.md").read_text(encoding="utf-8"))
    if initialize:
        init_project(root)
    print("安装文件：")
    for relative in sorted(files):
        print(f"  .trae/skills/dev-workflow/{relative}")
    print("请在 Trae 打开目标项目，在技能与命令中确认 Skill dev-workflow 已启用，新开会话点名 trae-Rex-workflow 触发。")


def cmd_init(_args):
    root = installed_root() or Path.cwd().resolve()
    if installed_root() is not None and not inside(Path.cwd().resolve(), root):
        fail("请在此 Skill 所安装的业务项目内执行 init。")
    if not (root / ".trae/skills/dev-workflow/SKILL.md").exists() and root != source_root():
        install_project(root, initialize=True)
    else:
        init_project(root)


def parse_task(path):
    text = path.read_text(encoding="utf-8")
    match = re.match(r"\A---\n(.*?)\n---\n(.*)\Z", text, re.S)
    if not match:
        return {}, text
    fields = {}
    for line in match.group(1).splitlines():
        if ":" in line:
            key, value = line.split(":", 1)
            if key.strip() in fields:
                fail(f"Task {path.name} 存在重复字段：{key.strip()}")
            fields[key.strip()] = value.strip()
    return fields, match.group(2)


def render_task(fields, body):
    keys = [key for key in FIELD_ORDER if key in fields] + [key for key in fields if key not in FIELD_ORDER]
    return "---\n" + "\n".join(f"{key}: {fields[key]}" for key in keys) + "\n---\n" + body


def save_task(task):
    atomic_text(task["path"], render_task(task["fields"], task["body"]))


def acceptance_errors(body):
    match = re.search(r"(?m)^##\s+验收标准\s*$", body)
    if not match:
        return ["缺少验收标准节"]
    section = re.split(r"(?m)^#{1,2}\s+", body[match.end():], maxsplit=1)[0]
    section = re.sub(r"(?ms)^\s*```[^\n]*\n.*?^\s*```[^\n]*$", "", section)
    checks = re.findall(r"(?m)^\s*[-*]\s+\[([ xX])\]\s+(.+)$", section)
    if not checks:
        return ["done 缺少实际验收 checkbox"]
    if any(mark == " " for mark, _ in checks):
        return ["done 的验收 checkbox 尚未全部勾选"]
    if any("待补充" in text or "待填写" in text for _, text in checks):
        return ["done 的验收标准仍为模板占位内容"]
    return []


def scan_tasks(root):
    tasks = []
    directory = root / "tasks"
    plain_path(root, directory)
    for path in sorted(directory.glob("*.md")):
        plain_path(root, path)
        try:
            fields, body = parse_task(path)
            errors = []
        except (WorkflowError, UnicodeError) as error:
            fields, body, errors = {}, "", [str(error)]
        for name in ("id", "title", "module", "status"):
            if not fields.get(name):
                errors.append(f"缺少 {name}")
        tid = fields.get("id", "")
        if tid and not ID_RE.fullmatch(tid):
            errors.append("id 格式应为 T-数字")
        if fields.get("status") and fields["status"] not in STATUSES:
            errors.append("status 非法")
        issue = fields.get("issue", "")
        if issue and not re.fullmatch(r"[1-9]\d*", issue):
            errors.append("issue 必须为正整数")
        deps = [part.strip() for part in fields.get("deps", "").split(",") if part.strip()]
        if len(set(deps)) != len(deps) or any(not ID_RE.fullmatch(dep) for dep in deps):
            errors.append("deps 应为不重复的 T-数字，逗号分隔")
        if not re.search(r"(?m)^##\s+描述\s*$", body):
            errors.append("缺少描述节")
        if not re.search(r"(?m)^##\s+验收标准\s*$", body):
            errors.append("缺少验收标准节")
        if fields.get("status") == "done":
            errors += acceptance_errors(body)
        tasks.append({"path": path, "fields": fields, "body": body, "deps": deps, "errors": errors})
    by_id = {}
    for task in tasks:
        by_id.setdefault(task["fields"].get("id", ""), []).append(task)
    for tid, matches in by_id.items():
        if tid and len(matches) > 1:
            for task in matches:
                task["errors"].append(f"重复 id：{tid}")
    graph = {tid: matches[0] for tid, matches in by_id.items() if tid and len(matches) == 1}
    for task in tasks:
        for dep in task["deps"]:
            if dep not in graph:
                task["errors"].append(f"缺失或重复的依赖：{dep}")
    degrees = {tid: len(set(task["deps"]) & graph.keys()) for tid, task in graph.items()}
    children = {tid: [] for tid in graph}
    for tid, task in graph.items():
        for dep in set(task["deps"]) & graph.keys():
            children[dep].append(tid)
    queue = deque(tid for tid, count in degrees.items() if not count)
    while queue:
        tid = queue.popleft()
        for child in children[tid]:
            degrees[child] -= 1
            if not degrees[child]:
                queue.append(child)
    for tid, count in degrees.items():
        if count:
            graph[tid]["errors"].append("存在依赖环或依赖环上的任务")
    # 异常依赖不能把其后续任务变成可执行候选。
    changed = True
    while changed:
        changed = False
        for task in tasks:
            if not task["errors"] and any(graph[dep]["errors"] for dep in task["deps"]):
                task["errors"].append("依赖的 Task 存在校验异常")
                changed = True
    return [t for t in tasks if not t["errors"]], [t for t in tasks if t["errors"]]


def report_invalid(invalid):
    for task in invalid:
        print(f"[异常] {task['path'].name}：{'；'.join(task['errors'])}")


def cmd_task_new(args):
    root, _ = context()
    if not args.title.strip() or not args.module.strip() or any(c in args.title + args.module for c in "\r\n"):
        fail("title 和 module 必须为非空单行文本")
    valid, invalid = scan_tasks(root)
    if invalid:
        report_invalid(invalid)
        fail("请先修正异常 Task，再创建任务。")
    deps = [part.strip() for part in args.deps.split(",") if part.strip()]
    ids = {task["fields"]["id"] for task in valid}
    if len(set(deps)) != len(deps) or any(dep not in ids for dep in deps):
        fail("deps 必须是不重复的已存在 Task ID")
    next_id = f"T-{max((int(tid[2:]) for tid in ids), default=0) + 1:03d}"
    template = root / "docs/templates/task-template.md"
    plain_path(root, template)
    if not template.is_file():
        template = PACKAGE / "assets/templates/task-template.md"
    fields = dict(zip(FIELD_ORDER, (next_id, args.title.strip(), args.module.strip(), "todo", ",".join(deps), "", "")))
    slug = re.sub(r'[\\/:*?"<>|#%\s]+', "-", args.title).strip("-.") or "task"
    (root / "tasks").mkdir(exist_ok=True)
    path = root / "tasks" / f"{next_id}-{slug}.md"
    task = {"path": path, "fields": fields, "body": parse_task(template)[1]}
    if path.exists():
        fail(f"任务文件已存在：{path.name}")
    save_task(task)
    print(f"已创建 tasks/{path.name}（{next_id}）")


def preflight_github(repo):
    gh(["auth", "status", "--hostname", "github.com"])
    info = json.loads(gh(["repo", "view", repo, "--json", "nameWithOwner,hasIssuesEnabled,viewerPermission"]))
    if info.get("nameWithOwner", "").casefold() != repo.casefold():
        fail("GitHub 返回的仓库与目标不一致，已停止同步。")
    if not info.get("hasIssuesEnabled"):
        fail("目标仓库未开启 Issues，请先启用。")
    if info.get("viewerPermission") not in ("ADMIN", "MAINTAIN", "WRITE"):
        fail("当前 gh 账号缺少目标仓库写权限，已停止同步。")


def issue_title(fields):
    return f"[{fields['id']}] {fields['title']}"


def build_issue_body(task):
    fields = task["fields"]
    rows = "\n".join(f"| {key} | {fields.get(key) or '（无）'} |" for key in FIELD_ORDER)
    return (f"> 本地 tasks/{task['path'].name} 为唯一事实源；本 Issue 仅单向创建/关闭，不持续刷新正文。\n\n"
            f"| 字段 | 值 |\n|---|---|\n{rows}\n\n{task['body'].strip()}\n")


def find_issue(repo, tid):
    matches = json.loads(gh(["issue", "list", "--repo", repo, "--state", "all", "--search", f'"{tid}" in:title', "--limit", "100", "--json", "number,title"]))
    matches = [item["number"] for item in matches if item["title"].startswith(f"[{tid}]")]
    if len(matches) > 1:
        fail(f"远端有多个 [{tid}] Issue，请先核对映射。")
    return matches[0] if matches else None


def cmd_task_sync(_args):
    root, state = context()
    repo = checked_repo(root, state, required=True)
    valid, invalid = scan_tasks(root)
    report_invalid(invalid)
    if not valid:
        if invalid:
            fail("没有有效 Task，未执行远端操作。")
        print("没有 Task，无需同步。")
        return
    preflight_github(repo)
    checked_repo(root, state, required=True, persist=True)
    created = backfilled = closed = 0
    for task in valid:
        fields = task["fields"]
        if not fields.get("issue"):
            number = find_issue(repo, fields["id"])
            if number is None:
                for name, color in (("task", "0E8A16"), (f"module:{fields['module']}", "1D76DB")):
                    gh(["label", "create", name, "--repo", repo, "--color", color, "--force"])
                url = gh(["issue", "create", "--repo", repo, "--title", issue_title(fields), "--body", build_issue_body(task), "--label", "task", "--label", f"module:{fields['module']}"])
                match = re.fullmatch(r"https://github\.com/([^/]+/[^/]+)/issues/([1-9]\d*)/?", url.strip())
                if not match or match[1].casefold() != repo.casefold():
                    fail("创建 Issue 返回值异常，未回填；请重跑按 Task ID 查重恢复。")
                number = match[2]
                created += 1
                print(f"[创建] {fields['id']} → Issue #{number}")
            else:
                backfilled += 1
                print(f"[回填] {fields['id']} ← Issue #{number}")
            fields["issue"] = str(number)
            save_task(task)
        if fields["status"] == "done":
            info = json.loads(gh(["issue", "view", fields["issue"], "--repo", repo, "--json", "state,title"]))
            if not info.get("title", "").startswith(f"[{fields['id']}]"):
                fail(f"{fields['id']} 的 Issue #{fields['issue']} 标题不匹配，拒绝关闭。")
            if info.get("state") == "OPEN":
                gh(["issue", "close", fields["issue"], "--repo", repo])
                closed += 1
                print(f"[关闭] {fields['id']} → Issue #{fields['issue']}")
    print(f"同步汇总：新建 {created} / 回填 {backfilled} / 关闭 {closed} / 异常跳过 {len(invalid)}")
    if invalid:
        fail("有效 Task 已同步，仍有异常 Task 需要修正。")


def execution_preview(valid, limit):
    by_id = {task["fields"]["id"]: task for task in valid}
    groups, waiting = {}, []
    for task in valid:
        fields = task["fields"]
        if fields["status"] not in ("todo", "in-progress"):
            continue
        pending = [dep for dep in task["deps"] if by_id[dep]["fields"]["status"] != "done"]
        if pending:
            waiting.append(f"{fields['id']} 等待依赖：{', '.join(pending)}")
        else:
            groups.setdefault(fields["module"], []).append(task)
    chosen = []
    # 已在执行的任务先占模块和全局名额。
    ordered = sorted(groups.items(), key=lambda pair: not any(t["fields"]["status"] == "in-progress" for t in pair[1]))
    for module, tasks in ordered:
        tasks.sort(key=lambda task: task["fields"]["status"] != "in-progress")
        active = [task for task in tasks if task["fields"]["status"] == "in-progress"]
        if len(active) > 1:
            waiting.append(f"模块 {module} 有多个 in-progress 冲突，请先协调")
        if len(chosen) < limit:
            chosen.append(tasks[0])
        else:
            waiting.append(f"{tasks[0]['fields']['id']} 等待全局执行名额")
        for task in tasks[1:]:
            waiting.append(f"{task['fields']['id']} 等待同模块任务完成")
    return chosen, waiting


def cmd_status(_args):
    root, state = context()
    origin = detect_repo(root)
    cached = state.get("repo", "")
    print(f"项目阶段: {state['phase']}（{PHASES[state['phase']]}）")
    print(f"GitHub origin: {origin or '（未配置）'}")
    print(f"仓库缓存: {cached or '（未配置）'}")
    if origin and cached and origin.casefold() != cached.casefold():
        print("[冲突] origin 与缓存不一致，sync 将拒绝；请核对仓库和 Issue 映射。")
    limit = state["config"]["max_parallel"]
    print(f"并发上限: {limit}")
    valid, invalid = scan_tasks(root)
    report_invalid(invalid)
    counts = {status: sum(t["fields"]["status"] == status for t in valid) for status in STATUSES}
    print(f"Task 统计: 有效 {len(valid)} / 异常 {len(invalid)}" + "".join(f" | {status} {counts[status]}" for status in STATUSES))
    unsynced = [t["fields"]["id"] for t in valid if not t["fields"].get("issue")]
    blocked = [t["fields"]["id"] for t in valid if t["fields"]["status"] == "blocked"]
    print(f"未同步: {', '.join(unsynced) or '无'}")
    print(f"blocked: {', '.join(blocked) or '无'}")
    chosen, waiting = execution_preview(valid, limit)
    print("执行候选（每模块一个，依赖已完成；仍须核对共享文件与 Trae 运行时能力）:")
    for task in chosen:
        print(f"  - {task['fields']['module']}: {task['fields']['id']}")
    if not chosen:
        print("  （无）")
    for reason in waiting:
        print(f"[等待] {reason}")


def gate_gaps(root, target):
    valid, invalid = scan_tasks(root)
    gaps = [f"{task['path'].name}: {'；'.join(task['errors'])}" for task in invalid]
    for minimum, name in ((2, "prd"), (3, "tech-spec")):
        path = root / f"docs/{name}.md"
        if target >= minimum and (not path.is_file() or not path.read_text(encoding="utf-8").strip()):
            gaps.append(f"缺少或空白 docs/{name}.md")
    if target >= 4 and not valid:
        gaps.append("tasks/ 下没有有效 Task")
    if target >= 5:
        unsynced = [task["fields"]["id"] for task in valid if not task["fields"].get("issue")]
        if unsynced:
            gaps.append("未回填 Issue: " + ", ".join(unsynced))
    if target >= 6:
        pending = [task["fields"]["id"] for task in valid if task["fields"]["status"] != "done"]
        if pending:
            gaps.append("Task 未完成: " + ", ".join(pending))
    return gaps


def cmd_phase(args):
    root, state = context()
    current = state["phase"]
    target = current + 1 if args.phase_cmd == "next" else args.n
    if target not in PHASES:
        fail("阶段编号必须是 1-6；阶段 6 无下一步。")
    if target > current:
        gaps = gate_gaps(root, target)
        if gaps:
            fail(f"无法进入阶段 {target}（{PHASES[target]}）：\n  - " + "\n  - ".join(gaps))
    state["phase"] = target
    save_state(root, state)
    print(f"已进入阶段 {target}（{PHASES[target]}）；CLI 不代替用户确认、运行验证和推送核对。")


def main():
    parser = argparse.ArgumentParser(prog="workflow", description="Trae 项目级 trae-Rex-workflow CLI")
    parser.add_argument("--version", action="version", version=VERSION)
    commands = parser.add_subparsers(dest="cmd", required=True)
    install = commands.add_parser("install", help="安装完整 Trae 项目 Skill")
    install.add_argument("--target", type=Path, default=Path.cwd(), help="目标项目根目录")
    install.add_argument("--init", action="store_true", help="同时初始化项目骨架")
    commands.add_parser("init", help="初始化，保留已有资料")
    commands.add_parser("status", help="只读状态和依赖预览")
    task = commands.add_parser("task", help="任务管理").add_subparsers(dest="task_cmd", required=True)
    new = task.add_parser("new", help="创建 Task")
    new.add_argument("--title", required=True)
    new.add_argument("--module", required=True)
    new.add_argument("--deps", default="")
    task.add_parser("sync", help="单向创建/关闭 GitHub Issues")
    phase = commands.add_parser("phase", help="阶段管理").add_subparsers(dest="phase_cmd", required=True)
    phase.add_parser("next", help="校验后进入下一阶段")
    setting = phase.add_parser("set", help="设置阶段；前进仍需校验")
    setting.add_argument("n", type=int)
    args = parser.parse_args()
    try:
        if args.cmd == "install":
            install_project(args.target.expanduser().resolve(), args.init)
        elif args.cmd == "init":
            cmd_init(args)
        elif args.cmd == "status":
            cmd_status(args)
        elif args.cmd == "phase":
            cmd_phase(args)
        elif args.task_cmd == "new":
            cmd_task_new(args)
        else:
            cmd_task_sync(args)
    except (WorkflowError, OSError, ValueError, UnicodeError) as error:
        print(f"[错误] {error}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
