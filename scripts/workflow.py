#!/usr/bin/env python3
"""源码仓库兼容入口；唯一实现随 Trae Skill 分发。"""

import runpy
from pathlib import Path


if __name__ == "__main__":
    runpy.run_path(
        str(Path(__file__).resolve().parents[1] / "skill/dev-workflow/scripts/workflow.py"),
        run_name="__main__",
    )
