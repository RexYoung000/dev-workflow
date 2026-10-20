"""隔离验证公开安装契约及远端写入边界；绝不调用真实 gh。"""

import ast
from contextlib import redirect_stdout
import ctypes
import importlib.util
import io
import json
import locale
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

TEST_RUNNER = ROOT / "tests/cli_runner.py"


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
        self.backend.write_text(json.dumps({"repo": "other-owner/their-app", "logged_in": True, "permission": "WRITE", "issues_enabled": True, "issues": [], "calls": []}), encoding="utf-8")
        self.env = dict(os.environ, WORKFLOW_TEST_BACKEND=str(self.backend), PYTHONDONTWRITEBYTECODE="1")

    def command(self, *args, cwd=None, cli=None, ok=True):
        result = subprocess.run([sys.executable, str(TEST_RUNNER), str(cli or SOURCE_CLI), *map(str, args)], cwd=cwd or self.project, env=self.env, text=True, encoding="utf-8", capture_output=True, timeout=20)
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
        return subprocess.run(["git", *args], cwd=self.project, check=True, capture_output=True, text=True, encoding="utf-8").stdout.strip()

    def own_origin(self, url="https://github.com/other-owner/their-app.git"):
        self.git("remote", "add", "origin", url)

    def state(self, **updates):
        path = self.project / ".workflow/state.json"
        state = json.loads(path.read_text(encoding="utf-8"))
        state.update(updates)
        path.write_text(json.dumps(state), encoding="utf-8")
        return state

    def read_backend(self):
        return json.loads(self.backend.read_text(encoding="utf-8"))

    def change_backend(self, **updates):
        state = self.read_backend()
        state.update(updates)
        self.backend.write_text(json.dumps(state), encoding="utf-8")

    def mutations(self):
        return [a for a in self.read_backend()["calls"] if a[:2] in (["issue", "create"], ["issue", "close"], ["label", "create"])]

    def documents(self):
        (self.project / "docs/prd.md").write_text("# 本项目需求\n", encoding="utf-8")
        (self.project / "docs/tech-spec.md").write_text("# 本项目技术规范\n", encoding="utf-8")

    def task(self, tid="T-001", status="todo", issue="", deps="", module="app", checked=False):
        path = self.project / "tasks" / (tid + ".md")
        path.write_text(f"---\nid: {tid}\ntitle: 本项目任务\nmodule: {module}\nstatus: {status}\ndeps: {deps}\nissue: {issue}\n---\n\n## 描述\n实际需求。\n\n## 验收标准\n- [{'x' if checked else ' '}] 运行核心场景通过\n", encoding="utf-8")
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
        self.assertNotIn("本仓库是 dev-workflow 的本体", (self.project / "AGENTS.md").read_text(encoding="utf-8"))
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
        self.assertEqual(json.loads((second / ".workflow/state.json").read_text(encoding="utf-8"))["phase"], 1)
        self.assertEqual(list((second / "tasks").iterdir()), [])

    def test_existing_project_files_and_state_are_preserved(self):
        self.install()
        self.own_origin()
        self.state(phase=3, repo="other-owner/their-app", config={"max_parallel": 1})
        self.task()
        self.documents()
        custom = {"AGENTS.md": "# Existing rules\n", ".trae/rules/dev-workflow.md": "# Own rule\n", "docs/templates/task-template.md": "# Own template\n"}
        for relative, text in custom.items():
            (self.project / relative).write_text(text, encoding="utf-8")
        paths = [".workflow/state.json", "tasks/T-001.md", "docs/prd.md", "docs/tech-spec.md", *custom]
        before = {p: (self.project / p).read_bytes() for p in paths}
        self.install()
        self.assertEqual(before, {p: (self.project / p).read_bytes() for p in paths})

    def test_upgrade_backs_up_old_package_and_same_content_is_idempotent(self):
        self.install()
        package = self.project / ".trae/skills/dev-workflow"
        (package / "SKILL.md").write_text("old local version", encoding="utf-8")
        before = (self.project / ".workflow/state.json").read_bytes()
        self.install()
        backups = list((self.project / ".trae/.dev-workflow-backups").glob("*/dev-workflow/SKILL.md"))
        self.assertEqual(len(backups), 1)
        self.assertEqual(backups[0].read_text(encoding="utf-8"), "old local version")
        self.assertEqual(before, (self.project / ".workflow/state.json").read_bytes())
        self.install()
        self.assertEqual(len(list((self.project / ".trae/.dev-workflow-backups").iterdir())), 1)

    def test_failed_package_swap_restores_old_package(self):
        self.install()
        package = self.project / ".trae/skills/dev-workflow"
        (package / "SKILL.md").write_text("old version to restore", encoding="utf-8")
        module = load_module()
        rename = Path.rename
        def failing_rename(path, target):
            if ".dev-workflow-stage-" in str(path):
                raise OSError("simulated swap failure")
            return rename(path, target)
        with patch.object(Path, "rename", failing_rename), redirect_stdout(io.StringIO()):
            with self.assertRaisesRegex(module.WorkflowError, "旧包已恢复"):
                module.install_project(self.project)
        self.assertEqual((package / "SKILL.md").read_text(encoding="utf-8"), "old version to restore")
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
        (outside / "keep").write_text("unchanged", encoding="utf-8")
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
        self.state(repo="RexYoung000/trae-Rex-workflow")
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
        path.write_text(path.read_text(encoding="utf-8").replace("status: todo\n", ""), encoding="utf-8")
        self.assertIn("缺少 status", self.local("phase", "next", ok=False).stderr)
        self.assertEqual(self.state()["phase"], 5)

    def test_done_requires_checked_real_acceptance_section(self):
        self.install()
        self.documents()
        self.state(phase=5)
        for body in ["## 验收标准\n- [ ] 未完成\n", "## 验收标准\n暂无检查点\n", "## 描述\n- [x] 别处的 checkbox\n## 验收标准\n没有\n", "## 验收标准\n- [x] （待补充：可检验的完成条件）\n"]:
            with self.subTest(body=body):
                path = self.task(status="done", issue="1", checked=True)
                path.write_text(path.read_text(encoding="utf-8").split("## 验收标准")[0] + body, encoding="utf-8")
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
        (self.project / "docs/prd.md").write_text("   \n", encoding="utf-8")
        self.local("phase", "next", ok=False)
        self.documents()
        self.local("phase", "next")
        self.local("phase", "next")
        self.local("phase", "next", ok=False)
        path = self.task()
        self.local("phase", "next")
        self.local("phase", "next", ok=False)
        path.write_text(path.read_text(encoding="utf-8").replace("issue: \n", "issue: 7\n"), encoding="utf-8")
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
        text = path.read_text(encoding="utf-8").replace("status: todo", "custom: keep-me\nstatus: todo")
        path.write_text(text, encoding="utf-8")
        self.local("task", "sync")
        self.assertIn("custom: keep-me", path.read_text(encoding="utf-8"))
        self.assertEqual(text.split("\n---\n", 1)[1], path.read_text(encoding="utf-8").split("\n---\n", 1)[1])

    def test_sync_lifecycle_is_idempotent_and_only_uses_own_repository(self):
        self.install()
        self.own_origin()
        path = self.task()
        self.local("task", "sync")
        self.local("task", "sync")
        self.assertEqual(len(self.read_backend()["issues"]), 1)
        self.assertIn("issue: 1", path.read_text(encoding="utf-8"))
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
        self.assertIn("issue: \n", path.read_text(encoding="utf-8"))
        self.local("task", "sync")
        self.assertIn("issue: 1", path.read_text(encoding="utf-8"))
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

    def test_cli_output_and_error_ignore_legacy_stream_encoding(self):
        self.env["PYTHONIOENCODING"] = "cp1252"
        self.assertIn("Trae 项目级", self.command("--help").stdout)
        self.assertIn("未找到", self.command("status", ok=False).stderr)
        self.install()
        self.own_origin()
        self.task()
        self.local("task", "sync")
        self.local("task", "sync")  # 远端中文 JSON 查重，不依赖 ANSI 默认解码。
        self.assertEqual(len(self.read_backend()["issues"]), 1)

    def test_utf8_subprocess_output_is_strict_even_under_legacy_locale(self):
        module = load_module()
        source = "import sys; sys.stdout.buffer.write(bytes.fromhex('e4b8ade69687'))"
        with patch.object(locale, "getpreferredencoding", return_value="cp936"):
            self.assertEqual(module.run([sys.executable, "-c", source]).stdout, "中文")
            source = "import sys; sys.stderr.buffer.write(bytes.fromhex('b4edcef3')); sys.exit(2)"
            with self.assertRaisesRegex(module.WorkflowError, "错误"):
                module.run([sys.executable, "-c", source])
        with self.assertRaisesRegex(module.WorkflowError, "非 UTF-8"):
            module.run([sys.executable, "-c", "import sys; sys.stdout.buffer.write(b'\\xff')"])

    def test_relative_executable_is_resolved_before_changing_working_directory(self):
        module = load_module()
        previous = Path.cwd()
        try:
            # Windows runner 的解释器和项目可处于不同盘符，不对它们求 relpath。
            os.chdir(Path(sys.executable).parent)
            with patch.object(module.shutil, "which", return_value=os.curdir + os.sep + Path(sys.executable).name):
                result = module.run(["python-for-test", "-c", "print('resolved')"], cwd=self.project)
        finally:
            os.chdir(previous)
        self.assertEqual(result.stdout.strip(), "resolved")

    def test_bom_crlf_state_tasks_and_documents_are_read_without_rewriting(self):
        self.install()
        self.documents()
        path = self.task()
        files = [path, self.project / ".workflow/state.json", self.project / "docs/prd.md", self.project / "docs/tech-spec.md"]
        for file in files:
            file.write_bytes(b"\xef\xbb\xbf" + file.read_text(encoding="utf-8").replace("\n", "\r\n").encode("utf-8"))
        before = {file: file.read_bytes() for file in files}
        self.assertIn("有效 1 / 异常 0", self.local("status").stdout)
        self.assertEqual(before, {file: file.read_bytes() for file in files})
        self.local("phase", "next")
        self.assertFalse((self.project / ".workflow/state.json").read_bytes().startswith(b"\xef\xbb\xbf"))
        self.local("phase", "next")
        self.own_origin()
        self.local("task", "sync")
        self.assertFalse(path.read_bytes().startswith(b"\xef\xbb\xbf"))
        self.assertNotIn(b"\r\n", path.read_bytes())

    def test_bom_template_works_but_bom_only_prd_is_empty(self):
        self.install()
        template = self.project / "docs/templates/task-template.md"
        template.write_bytes(b"\xef\xbb\xbf" + template.read_bytes().replace(b"\n", b"\r\n"))
        self.local("task", "new", "--title", "中文模板", "--module", "app")
        self.assertIn("有效 1 / 异常 0", self.local("status").stdout)
        (self.project / "docs/prd.md").write_bytes(b"\xef\xbb\xbf\r\n")
        self.local("phase", "next", ok=False)

    def test_long_issue_body_uses_utf8_stdin_and_short_arguments(self):
        self.install()
        self.own_origin()
        path = self.task()
        body = "中文 é 😀 '引号\" 与 $()\n" * 2000
        path.write_text(path.read_text(encoding="utf-8") + body, encoding="utf-8")
        self.assertGreater(len(body.encode("utf-16-le")) // 2, 32767)
        self.local("task", "sync")
        issue = self.read_backend()["issues"][0]
        self.assertTrue(issue["body"].endswith(body))
        args = next(a for a in self.mutations() if a[:2] == ["issue", "create"])
        self.assertNotIn("--body", args)
        self.assertEqual(args[args.index("--body-file") + 1], "-")
        self.assertLess(len(subprocess.list2cmdline(args).encode("utf-16-le")) // 2, 1000)

    def test_long_task_title_has_short_filename_and_complete_content(self):
        self.install()
        title = "中文长标题😀" * 50
        self.local("task", "new", "--title", title, "--module", "app")
        path = next((self.project / "tasks").glob("*.md"))
        self.assertLess(len(path.name.encode("utf-8")), 100)
        self.assertIn("title: " + title + "\n", path.read_text(encoding="utf-8"))
        self.assertIn("有效 1 / 异常 0", self.local("status").stdout)

    def test_oversized_windows_install_path_is_rejected_before_writes(self):
        target = self.base.joinpath(*(["长路径" * 25] * 3))
        module = load_module()
        with patch.object(module.os, "name", "nt"):
            with self.assertRaisesRegex(module.WorkflowError, "路径过长"):
                module.check_target(target)
        self.assertFalse(target.exists())

    def test_atomic_save_retries_transient_lock_and_preserves_original_if_locked(self):
        module = load_module()
        path = self.project / "saved.txt"
        path.write_text("original", encoding="utf-8")
        replace = os.replace
        attempts = []
        def transient(source, destination):
            attempts.append(source)
            if len(attempts) < 3:
                raise PermissionError("file busy")
            return replace(source, destination)
        with patch.object(os, "replace", transient), patch.object(module.time, "sleep"):
            module.atomic_text(path, "新内容\n")
        self.assertEqual(path.read_bytes(), "新内容\n".encode("utf-8"))
        with patch.object(os, "replace", side_effect=PermissionError("file busy")), patch.object(module.time, "sleep"):
            with self.assertRaisesRegex(module.WorkflowError, "原文件未替换"):
                module.atomic_text(path, "unwritten")
        self.assertEqual(path.read_text(encoding="utf-8"), "新内容\n")
        self.assertEqual(list(self.project.glob(".saved.txt.*")), [])

    def test_failed_upgrade_and_failed_restore_leave_recoverable_backup(self):
        self.install()
        package = self.project / ".trae/skills/dev-workflow"
        (package / "SKILL.md").write_text("recover this version", encoding="utf-8")
        module = load_module()
        rename = Path.rename
        def locked(path, target):
            if ".dev-workflow-stage-" in str(path) or ".dev-workflow-backups" in str(path):
                raise PermissionError("file busy")
            return rename(path, target)
        with patch.object(Path, "rename", locked), patch.object(module.time, "sleep"), redirect_stdout(io.StringIO()):
            with self.assertRaisesRegex(module.WorkflowError, "旧包完整保留在") as result:
                module.install_project(self.project)
        backup = next((self.project / ".trae/.dev-workflow-backups").glob("*/dev-workflow"))
        self.assertIn(str(backup), str(result.exception))
        self.assertEqual((backup / "SKILL.md").read_text(encoding="utf-8"), "recover this version")
        self.assertFalse(package.exists())
        rename(backup, package)
        self.local("status")

    @unittest.skipUnless(os.name == "nt", "Windows 文件共享锁专用测试")
    def test_real_windows_file_lock_blocks_upgrade_without_losing_package(self):
        self.install()
        package = self.project / ".trae/skills/dev-workflow"
        path = package / "SKILL.md"
        path.write_text("locked old package", encoding="utf-8")
        kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel.CreateFileW.argtypes = [ctypes.c_wchar_p, ctypes.c_uint32, ctypes.c_uint32, ctypes.c_void_p, ctypes.c_uint32, ctypes.c_uint32, ctypes.c_void_p]
        kernel.CreateFileW.restype = ctypes.c_void_p
        kernel.CloseHandle.argtypes = [ctypes.c_void_p]
        handle = kernel.CreateFileW(str(path), 0x80000000, 1, None, 3, 0x80, None)
        self.assertNotEqual(handle, ctypes.c_void_p(-1).value, ctypes.get_last_error())
        try:
            result = self.command("install", "--target", self.project, "--init", cwd=self.base, ok=False)
            self.assertIn("占用", result.stderr)
            self.assertEqual(path.read_text(encoding="utf-8"), "locked old package")
        finally:
            kernel.CloseHandle(handle)
        self.install()
        self.local("status")

    @unittest.skipUnless(os.name == "nt", "Windows 目录联接专用测试")
    def test_windows_junction_cannot_write_outside_project(self):
        outside = self.base / "outside"
        outside.mkdir()
        keep = outside / "keep.txt"
        keep.write_bytes(b"unchanged")
        target = self.project / ".trae"
        subprocess.run(["cmd", "/c", "mklink", "/J", str(target), str(outside)], check=True, capture_output=True)
        try:
            result = self.command("install", "--target", self.project, "--init", ok=False)
            self.assertIn("目录联接", result.stderr)
            self.assertEqual(list(outside.iterdir()), [keep])
            self.assertEqual(keep.read_bytes(), b"unchanged")
        finally:
            target.rmdir()

    def test_python_39_syntax_and_skill_resource_links(self):
        ast.parse(CANONICAL_CLI.read_text(encoding="utf-8"), feature_version=(3, 9))
        package = ROOT / "skill/dev-workflow"
        for relative in ("SKILL.md", "references/phases.md", "references/commands.md", "references/questioning.md"):
            text = (package / relative).read_text(encoding="utf-8")
            import re
            for target in re.findall(r"\]\(([^)]+)\)", text):
                if not target.startswith("http"):
                    self.assertTrue(((package / relative).parent / target).is_file(), target)


if __name__ == "__main__":
    unittest.main()
