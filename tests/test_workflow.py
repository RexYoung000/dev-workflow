"""隔离验证公开安装契约及远端写入边界；绝不调用真实 gh。"""

import ast
import importlib.util
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SOURCE_CLI = ROOT / "scripts/workflow.py"
CANONICAL_CLI = ROOT / "skill/dev-workflow/scripts/workflow.py"
ENTRY = Path(".trae/skills/dev-workflow/scripts/workflow.py")

FAKE_GH = r'''#!/usr/bin/env python3
import json
import os
from pathlib import Path
import sys
p = Path(os.environ['WORKFLOW_TEST_BACKEND'])
s = json.loads(p.read_text())
a = sys.argv[1:]
s['calls'].append(a)
s.setdefault('hosts', []).append(os.environ.get('GH_HOST'))
def finish(output='', code=0):
    p.write_text(json.dumps(s))
    print(output)
    sys.exit(code)
def option(name):
    return a[a.index(name) + 1]
if a[:2] == ['auth', 'status']:
    finish('logged in' if s['logged_in'] else 'not logged in', 0 if s['logged_in'] else 1)
if a[:2] == ['repo', 'view']:
    assert a[2] == s['repo'], a
    finish(json.dumps({'nameWithOwner': s['repo'], 'hasIssuesEnabled': s['issues_enabled'], 'viewerPermission': s['permission']}))
assert option('--repo') == s['repo'], a
if a[:2] == ['label', 'create']:
    finish()
if a[:2] == ['issue', 'list']:
    finish(json.dumps([{'number': i['number'], 'title': i['title']} for i in s['issues']]))
if a[:2] == ['issue', 'create']:
    n = max([i['number'] for i in s['issues']] + [0]) + 1
    s['issues'].append({'number': n, 'title': option('--title'), 'state': 'OPEN', 'body': option('--body')})
    if s.get('lose_create_response'):
        s['lose_create_response'] = False
        finish('network lost after creation', 1)
    finish('https://github.com/' + s['repo'] + '/issues/' + str(n))
if a[:2] == ['issue', 'view']:
    finish(json.dumps(next(i for i in s['issues'] if str(i['number']) == a[2])))
if a[:2] == ['issue', 'close']:
    next(i for i in s['issues'] if str(i['number']) == a[2])['state'] = 'CLOSED'
    finish()
finish('unexpected fake gh arguments', 9)
'''


def load_module():
    spec = importlib.util.spec_from_file_location("workflow_under_test", CANONICAL_CLI)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class WorkflowTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="workflow-test-")
        self.addCleanup(self.temporary.cleanup)
        self.base = Path(self.temporary.name)
        self.project = self.base / "自己的项目 with spaces"
        self.project.mkdir()
        self.backend = self.base / "github.json"
        self.backend.write_text(json.dumps({"repo": "other-owner/their-app", "logged_in": True, "permission": "WRITE", "issues_enabled": True, "issues": [], "calls": []}))
        fake_bin = self.base / "bin"
        fake_bin.mkdir()
        fake = fake_bin / "gh"
        fake.write_text(FAKE_GH)
        fake.chmod(0o755)
        self.env = dict(os.environ, PATH=str(fake_bin) + os.pathsep + os.environ.get("PATH", ""), WORKFLOW_TEST_BACKEND=str(self.backend), PYTHONDONTWRITEBYTECODE="1")

    def command(self, *args, cwd=None, cli=None, ok=True):
        result = subprocess.run([sys.executable, str(cli or SOURCE_CLI), *map(str, args)], cwd=cwd or self.project, env=self.env, text=True, capture_output=True, timeout=20)
        if ok:
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        else:
            self.assertNotEqual(result.returncode, 0, result.stdout + result.stderr)
        return result

    def install(self, target=None, initialize=True, cli=None):
        args = ["install", "--target", target or self.project]
        if initialize:
            args.append("--init")
        return self.command(*args, cwd=self.base, cli=cli)

    def local(self, *args, **kwargs):
        return self.command(*args, cli=self.project / ENTRY, **kwargs)

    def git(self, *args):
        return subprocess.run(["git", *args], cwd=self.project, check=True, capture_output=True, text=True).stdout.strip()

    def own_origin(self, url="https://github.com/other-owner/their-app.git"):
        self.git("remote", "add", "origin", url)

    def state(self, **updates):
        path = self.project / ".workflow/state.json"
        state = json.loads(path.read_text())
        state.update(updates)
        path.write_text(json.dumps(state))
        return state

    def read_backend(self):
        return json.loads(self.backend.read_text())

    def change_backend(self, **updates):
        state = self.read_backend()
        state.update(updates)
        self.backend.write_text(json.dumps(state))

    def mutations(self):
        return [a for a in self.read_backend()["calls"] if a[:2] in (["issue", "create"], ["issue", "close"], ["label", "create"])]

    def documents(self):
        (self.project / "docs/prd.md").write_text("# 本项目需求\n")
        (self.project / "docs/tech-spec.md").write_text("# 本项目技术规范\n")

    def task(self, tid="T-001", status="todo", issue="", deps="", module="app", checked=False):
        path = self.project / "tasks" / (tid + ".md")
        path.write_text(f"---\nid: {tid}\ntitle: 本项目任务\nmodule: {module}\nstatus: {status}\ndeps: {deps}\nissue: {issue}\n---\n\n## 描述\n实际需求。\n\n## 验收标准\n- [{'x' if checked else ' '}] 运行核心场景通过\n")
        return path

    def test_install_into_empty_project_has_all_runtime_resources_and_no_source_state(self):
        self.install()
        self.assertTrue((self.project / ENTRY).is_file())
        self.assertEqual((self.project / ".trae/skills/dev-workflow/LICENSE").read_bytes(), (ROOT / "LICENSE").read_bytes())
        state = self.state()
        self.assertEqual((state["phase"], state["repo"]), (1, ""))
        self.assertEqual(list((self.project / "tasks").iterdir()), [])
        self.assertFalse((self.project / "docs/prd.md").exists())
        self.assertFalse((self.project / "scripts").exists())
        self.assertNotIn("本仓库是 dev-workflow 的本体", (self.project / "AGENTS.md").read_text())
        self.local("task", "new", "--title", "第一个任务", "--module", "app")
        self.assertIn("有效 1 / 异常 0", self.local("status").stdout)
        self.assertEqual(self.read_backend()["calls"], [])

    def test_source_init_bootstraps_complete_package(self):
        self.command("init")
        self.assertTrue((self.project / ENTRY).exists())
        self.local("status")

    def test_install_without_init_then_initialize_from_skill(self):
        self.install(initialize=False)
        self.assertFalse((self.project / ".workflow").exists())
        self.assertTrue((self.project / ".trae/rules/dev-workflow.md").is_file())
        self.local("init")
        self.local("status")

    def test_installed_package_survives_source_deletion_and_can_redistribute(self):
        checkout = self.base / "checkout"
        shutil.copytree(ROOT / "skill", checkout / "skill")
        shutil.copy2(ROOT / "LICENSE", checkout / "LICENSE")
        self.install(cli=checkout / "skill/dev-workflow/scripts/workflow.py")
        shutil.rmtree(checkout)
        self.local("task", "new", "--title", "离线运行", "--module", "app")
        second = self.base / "second"
        self.install(target=second, cli=self.project / ENTRY)
        self.command("status", cwd=second, cli=second / ENTRY)
        self.assertEqual(json.loads((second / ".workflow/state.json").read_text())["phase"], 1)
        self.assertEqual(list((second / "tasks").iterdir()), [])

    def test_existing_project_files_and_state_are_preserved(self):
        self.install()
        self.own_origin()
        self.state(phase=3, repo="other-owner/their-app", config={"max_parallel": 1})
        self.task()
        self.documents()
        custom = {"AGENTS.md": "# Existing rules\n", ".trae/rules/dev-workflow.md": "# Own rule\n", "docs/templates/task-template.md": "# Own template\n"}
        for relative, text in custom.items():
            (self.project / relative).write_text(text)
        paths = [".workflow/state.json", "tasks/T-001.md", "docs/prd.md", "docs/tech-spec.md", *custom]
        before = {p: (self.project / p).read_bytes() for p in paths}
        self.install()
        self.assertEqual(before, {p: (self.project / p).read_bytes() for p in paths})

    def test_upgrade_backs_up_old_package_and_same_content_is_idempotent(self):
        self.install()
        package = self.project / ".trae/skills/dev-workflow"
        (package / "SKILL.md").write_text("old local version")
        before = (self.project / ".workflow/state.json").read_bytes()
        self.install()
        backups = list((self.project / ".trae/.dev-workflow-backups").glob("*/dev-workflow/SKILL.md"))
        self.assertEqual(len(backups), 1)
        self.assertEqual(backups[0].read_text(), "old local version")
        self.assertEqual(before, (self.project / ".workflow/state.json").read_bytes())
        self.install()
        self.assertEqual(len(list((self.project / ".trae/.dev-workflow-backups").iterdir())), 1)

    def test_failed_package_swap_restores_old_package(self):
        self.install()
        package = self.project / ".trae/skills/dev-workflow"
        (package / "SKILL.md").write_text("old version to restore")
        module = load_module()
        rename = Path.rename
        def failing_rename(path, target):
            if ".dev-workflow-stage-" in str(path):
                raise OSError("simulated swap failure")
            return rename(path, target)
        with patch.object(Path, "rename", failing_rename):
            with self.assertRaises(OSError):
                module.install_project(self.project)
        self.assertEqual((package / "SKILL.md").read_text(), "old version to restore")
        self.assertEqual(list((self.project / ".trae").glob(".dev-workflow-stage-*")), [])

    def test_invalid_target_is_rejected_before_package_write(self):
        (self.project / "AGENTS.md").mkdir()
        self.command("install", "--target", self.project, "--init", ok=False)
        self.assertFalse((self.project / ".trae").exists())

    def test_missing_source_resource_fails_without_target_mutation(self):
        checkout = self.base / "incomplete"
        shutil.copytree(ROOT / "skill", checkout / "skill")
        shutil.copy2(ROOT / "LICENSE", checkout / "LICENSE")
        (checkout / "skill/dev-workflow/assets/templates/task-template.md").unlink()
        self.command("install", "--target", self.project, cli=checkout / "skill/dev-workflow/scripts/workflow.py", ok=False)
        self.assertEqual(list(self.project.iterdir()), [])

    def test_managed_symlink_cannot_overwrite_outside_project(self):
        outside = self.base / "outside"
        outside.mkdir()
        (outside / "keep").write_text("unchanged")
        try:
            (self.project / ".trae").symlink_to(outside, target_is_directory=True)
        except OSError:
            self.skipTest("symlink unavailable")
        self.command("install", "--target", self.project, "--init", ok=False)
        self.assertEqual(list(outside.iterdir()), [outside / "keep"])

    def test_source_repository_target_is_noop(self):
        before = (ROOT / ".workflow/state.json").read_bytes()
        result = self.command("install", "--target", ROOT, "--init")
        self.assertIn("跳过", result.stdout)
        self.assertEqual(before, (ROOT / ".workflow/state.json").read_bytes())

    def test_init_uses_targets_own_origin(self):
        self.git("init", "-b", "main")
        self.own_origin()
        self.install()
        self.assertEqual(self.state()["repo"], "other-owner/their-app")

    def test_cached_repo_conflict_prevents_install_and_sync_writes(self):
        self.install()
        self.own_origin()
        self.state(repo="RexYoung000/dev-workflow")
        self.task()
        before = (self.project / ".workflow/state.json").read_bytes()
        self.command("install", "--target", self.project, "--init", ok=False)
        result = self.local("task", "sync", ok=False)
        self.assertIn("仓库不一致", result.stderr)
        self.assertEqual(before, (self.project / ".workflow/state.json").read_bytes())
        self.assertEqual(self.read_backend()["calls"], [])

    def test_cached_repo_without_origin_cannot_sync(self):
        self.install()
        self.state(repo="other-owner/their-app")
        self.task()
        self.local("task", "sync", ok=False)
        self.assertEqual(self.read_backend()["calls"], [])

    def test_status_reports_conflict_without_writing(self):
        self.install()
        self.own_origin()
        self.state(repo="wrong-owner/wrong-app")
        before = (self.project / ".workflow/state.json").read_bytes()
        self.assertIn("冲突", self.local("status").stdout)
        self.assertEqual(before, (self.project / ".workflow/state.json").read_bytes())

    def test_fake_github_hostname_is_not_accepted(self):
        self.install()
        self.own_origin("https://evilgithub.com/other-owner/their-app.git")
        self.task()
        self.local("task", "sync", ok=False)
        self.assertEqual(self.read_backend()["calls"], [])

    def test_installed_cli_cannot_target_other_project(self):
        self.install()
        other = self.base / "other"
        self.install(target=other)
        self.local("status", cwd=other, ok=False)
        self.local("init", cwd=other, ok=False)

    def test_subdirectory_uses_owning_root(self):
        self.install()
        child = self.project / "src"
        child.mkdir()
        self.assertIn("项目阶段: 1", self.local("status", cwd=child).stdout)
        self.local("init", cwd=child)
        self.assertFalse((child / ".workflow").exists())

    def test_invalid_task_cannot_disappear_from_phase_gate(self):
        self.install()
        self.documents()
        self.state(phase=5)
        path = self.task()
        path.write_text(path.read_text().replace("status: todo\n", ""))
        self.assertIn("缺少 status", self.local("phase", "next", ok=False).stderr)
        self.assertEqual(self.state()["phase"], 5)

    def test_done_requires_checked_real_acceptance_section(self):
        self.install()
        self.documents()
        self.state(phase=5)
        for body in ["## 验收标准\n- [ ] 未完成\n", "## 验收标准\n暂无检查点\n", "## 描述\n- [x] 别处的 checkbox\n## 验收标准\n没有\n", "## 验收标准\n- [x] （待补充：可检验的完成条件）\n"]:
            with self.subTest(body=body):
                path = self.task(status="done", issue="1", checked=True)
                path.write_text(path.read_text().split("## 验收标准")[0] + body)
                self.local("phase", "next", ok=False)
                self.assertEqual(self.state()["phase"], 5)

    def test_duplicate_ids_missing_dependencies_and_cycles_block_phase(self):
        self.install()
        self.documents()
        for problem in ("duplicate", "missing", "cycle"):
            with self.subTest(problem=problem):
                for path in (self.project / "tasks").glob("*.md"):
                    path.unlink()
                self.state(phase=3)
                first = self.task(deps="T-002" if problem == "cycle" else "T-999" if problem == "missing" else "")
                if problem == "duplicate":
                    shutil.copy2(first, self.project / "tasks/duplicate.md")
                elif problem == "cycle":
                    self.task("T-002", deps="T-001")
                self.local("phase", "next", ok=False)
                self.assertEqual(self.state()["phase"], 3)

    def test_illegal_issue_and_state_are_rejected(self):
        self.install()
        self.documents()
        self.state(phase=4)
        self.task(issue="not-an-issue")
        self.local("phase", "next", ok=False)
        self.state(config={"max_parallel": 0})
        self.assertIn("max_parallel", self.local("status", ok=False).stderr)

    def test_forward_gates_and_backward_iteration(self):
        self.install()
        self.local("phase", "next", ok=False)
        (self.project / "docs/prd.md").write_text("   \n")
        self.local("phase", "next", ok=False)
        self.documents()
        self.local("phase", "next")
        self.local("phase", "next")
        self.local("phase", "next", ok=False)
        path = self.task()
        self.local("phase", "next")
        self.local("phase", "next", ok=False)
        path.write_text(path.read_text().replace("issue: \n", "issue: 7\n"))
        self.local("phase", "next")
        self.local("phase", "next", ok=False)
        self.task(status="done", issue="7", checked=True)
        self.local("phase", "next")
        self.assertEqual(self.state()["phase"], 6)
        self.local("phase", "next", ok=False)
        self.local("phase", "set", "1")
        self.assertEqual(self.state()["phase"], 1)

    def test_dependency_preview_waits_until_parent_done(self):
        self.install()
        self.task(module="api")
        self.task("T-002", deps="T-001", module="ui")
        result = self.local("status").stdout
        self.assertIn("api: T-001", result)
        self.assertNotIn("ui: T-002", result)
        self.assertIn("T-002 等待依赖：T-001", result)
        self.task(status="done", issue="1", checked=True, module="api")
        self.assertIn("ui: T-002", self.local("status").stdout)

    def test_preview_obeys_module_and_global_limits(self):
        self.install()
        self.state(config={"max_parallel": 1})
        self.task(module="api")
        self.task("T-002", module="api")
        self.task("T-003", module="ui")
        result = self.local("status").stdout
        self.assertIn("api: T-001", result)
        self.assertNotIn("api: T-002", result)
        self.assertNotIn("ui: T-003", result)
        self.assertIn("等待同模块", result)
        self.assertIn("等待全局", result)

    def test_new_task_rejects_unknown_dependencies_and_multiline_values(self):
        self.install()
        self.local("task", "new", "--title", "valid", "--module", "app", "--deps", "T-999", ok=False)
        self.local("task", "new", "--title", "bad\nstatus: done", "--module", "app", ok=False)
        self.assertEqual(list((self.project / "tasks").iterdir()), [])

    def test_task_frontmatter_extra_fields_and_body_survive_sync(self):
        self.install()
        self.own_origin()
        path = self.task()
        text = path.read_text().replace("status: todo", "custom: keep-me\nstatus: todo")
        path.write_text(text)
        self.local("task", "sync")
        self.assertIn("custom: keep-me", path.read_text())
        self.assertEqual(text.split("\n---\n", 1)[1], path.read_text().split("\n---\n", 1)[1])

    def test_sync_lifecycle_is_idempotent_and_only_uses_own_repository(self):
        self.install()
        self.own_origin()
        path = self.task()
        self.local("task", "sync")
        self.local("task", "sync")
        self.assertEqual(len(self.read_backend()["issues"]), 1)
        self.assertIn("issue: 1", path.read_text())
        self.task(status="done", issue="1", checked=True)
        self.local("task", "sync")
        self.local("task", "sync")
        self.assertEqual(self.read_backend()["issues"][0]["state"], "CLOSED")
        self.assertEqual(len([a for a in self.mutations() if a[:2] == ["issue", "close"]]), 1)
        self.assertEqual(self.state()["repo"], "other-owner/their-app")

    def test_sync_recovers_after_create_response_is_lost(self):
        self.install()
        self.own_origin()
        path = self.task()
        self.change_backend(lose_create_response=True)
        self.local("task", "sync", ok=False)
        self.assertEqual(len(self.read_backend()["issues"]), 1)
        self.assertIn("issue: \n", path.read_text())
        self.local("task", "sync")
        self.assertIn("issue: 1", path.read_text())
        self.assertEqual(len(self.read_backend()["issues"]), 1)

    def test_sync_does_not_inherit_another_github_host(self):
        self.install()
        self.own_origin()
        self.task()
        self.env["GH_HOST"] = "github.company.example"
        self.local("task", "sync")
        self.assertEqual(set(self.read_backend()["hosts"]), {"github.com"})

    def test_auth_permissions_and_issues_are_checked_before_writes(self):
        self.install()
        self.own_origin()
        self.task()
        for updates in ({"logged_in": False}, {"permission": "READ"}, {"issues_enabled": False}):
            with self.subTest(updates=updates):
                self.change_backend(logged_in=True, permission="WRITE", issues_enabled=True, calls=[])
                self.change_backend(**updates)
                self.local("task", "sync", ok=False)
                self.assertEqual(self.mutations(), [])

    def test_invalid_done_task_is_never_closed_while_valid_task_can_sync(self):
        self.install()
        self.own_origin()
        self.task(status="done", issue="1", checked=False)
        self.task("T-002", module="ui")
        self.change_backend(issues=[{"number": 1, "title": "[T-001] 本项目任务", "state": "OPEN"}])
        self.local("task", "sync", ok=False)
        self.assertEqual(self.read_backend()["issues"][0]["state"], "OPEN")
        self.assertEqual(len(self.read_backend()["issues"]), 2)
        self.assertFalse(any(a[:2] == ["issue", "close"] for a in self.mutations()))

    def test_mismatched_issue_title_is_not_closed(self):
        self.install()
        self.own_origin()
        self.task(status="done", issue="1", checked=True)
        self.change_backend(issues=[{"number": 1, "title": "Unrelated issue", "state": "OPEN"}])
        self.local("task", "sync", ok=False)
        self.assertEqual(self.mutations(), [])

    def test_python_39_syntax_and_skill_resource_links(self):
        ast.parse(CANONICAL_CLI.read_text(), feature_version=(3, 9))
        package = ROOT / "skill/dev-workflow"
        for relative in ("SKILL.md", "references/phases.md", "references/commands.md", "references/questioning.md"):
            text = (package / relative).read_text()
            import re
            for target in re.findall(r"\]\(([^)]+)\)", text):
                if not target.startswith("http"):
                    self.assertTrue(((package / relative).parent / target).is_file(), target)


if __name__ == "__main__":
    unittest.main()
