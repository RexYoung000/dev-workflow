"""仅供隔离测试：直接运行 CLI，将所有 gh 调用送至 Python 假后端。

不靠 PATH 中的脚本扩展名、shebang 或真实 gh；测试代码不会进入安装包。
"""

from pathlib import Path
import runpy
import shutil
import subprocess
import sys

FAKE = Path(__file__).resolve().parent / "fixtures/fake_gh.py"
real_which = shutil.which
real_popen = subprocess.Popen


def isolated_which(command, *args, **kwargs):
    if Path(command).name.lower() in ("gh", "gh.exe"):
        return str(FAKE)
    return real_which(command, *args, **kwargs)


def isolated_popen(command, *args, **kwargs):
    if isinstance(command, (str, bytes)) or kwargs.get("shell"):
        raise AssertionError("CLI 测试禁止 shell 或字符串命令")
    if Path(command[0]) == FAKE or Path(command[0]).name.lower() in ("gh", "gh.exe"):
        command = [sys.executable, str(FAKE), *command[1:]]
    return real_popen(command, *args, **kwargs)


if __name__ == "__main__":
    shutil.which = isolated_which
    subprocess.Popen = isolated_popen
    sys.argv = sys.argv[1:]
    runpy.run_path(sys.argv[0], run_name="__main__")
