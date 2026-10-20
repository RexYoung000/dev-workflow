"""记录参数和 stdin 的离线 gh 替身，无网络和真实凭据访问。"""

import json
import os
from pathlib import Path
import sys

sys.stdout.reconfigure(encoding="utf-8")
sys.stderr.reconfigure(encoding="utf-8")
p = Path(os.environ["WORKFLOW_TEST_BACKEND"])
s = json.loads(p.read_text(encoding="utf-8"))
a = sys.argv[1:]
s["calls"].append(a)
s.setdefault("hosts", []).append(os.environ.get("GH_HOST"))


def finish(output="", code=0):
    p.write_text(json.dumps(s, ensure_ascii=False), encoding="utf-8")
    print(output)
    sys.exit(code)


def option(name):
    return a[a.index(name) + 1]


if a[:2] == ["auth", "status"]:
    finish("logged in" if s["logged_in"] else "not logged in", 0 if s["logged_in"] else 1)
if a[:2] == ["repo", "view"]:
    assert a[2] == s["repo"], a
    finish(json.dumps({"nameWithOwner": s["repo"], "hasIssuesEnabled": s["issues_enabled"], "viewerPermission": s["permission"]}))
assert option("--repo") == s["repo"], a
if a[:2] == ["label", "create"]:
    finish()
if a[:2] == ["issue", "list"]:
    finish(json.dumps([{"number": i["number"], "title": i["title"]} for i in s["issues"]], ensure_ascii=False))
if a[:2] == ["issue", "create"]:
    n = max([i["number"] for i in s["issues"]] + [0]) + 1
    assert option("--body-file") == "-", a
    body = sys.stdin.buffer.read().decode("utf-8")
    s["issues"].append({"number": n, "title": option("--title"), "state": "OPEN", "body": body})
    if s.get("lose_create_response"):
        s["lose_create_response"] = False
        finish("network lost after creation", 1)
    finish("https://github.com/" + s["repo"] + "/issues/" + str(n))
if a[:2] == ["issue", "view"]:
    finish(json.dumps(next(i for i in s["issues"] if str(i["number"]) == a[2]), ensure_ascii=False))
if a[:2] == ["issue", "close"]:
    next(i for i in s["issues"] if str(i["number"]) == a[2])["state"] = "CLOSED"
    finish()
finish("unexpected fake gh arguments", 9)
