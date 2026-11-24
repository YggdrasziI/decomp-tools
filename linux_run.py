#!/usr/bin/env python3
"""Run a Linux program: directly on Linux, through WSL on Windows.

  python tools/common/linux_run.py <program> [args...]

For a compiler that only exists as a Linux build (built from source in WSL, for
example). <program> may start with `~/`: the Linux home of the user running it.

On Windows, the program runs in the default WSL distribution (`wsl.exe -e`), in the
current directory, and each argument that holds an absolute Windows path (alone or
after an option, as in `-IE:\\x` or `-o` `E:\\x\\y.o`) is turned into its WSL path
under the default automount root (`E:\\x` -> `/mnt/e/x`). Backslashes in an argument
that is not an option are turned into slashes (relative paths). The exit code is the
program's.
"""

import os
import re
import shlex
import subprocess
import sys

MOUNT_ROOT = "/mnt"  # WSL default ([automount] root of /etc/wsl.conf)
WINDOWS_PATH = re.compile(r"^(-[A-Za-z][A-Za-z-]*=?)?([A-Za-z]):[\\/](.*)$", re.S)


def to_wsl(arg: str) -> str:
    m = WINDOWS_PATH.match(arg)
    if m:
        prefix, drive, rest = m.groups()
        return f"{prefix or ''}{MOUNT_ROOT}/{drive.lower()}/{rest.replace(chr(92), '/')}"
    if not arg.startswith("-"):
        return arg.replace("\\", "/")
    return arg


def main() -> int:
    if len(sys.argv) < 2:
        sys.exit(__doc__)
    program, args = sys.argv[1], sys.argv[2:]
    if os.name != "nt":
        return subprocess.run([os.path.expanduser(program), *args]).returncode
    if program.startswith("~/"):
        # wsl.exe -e does not go through a shell: expand the home there
        command = ["sh", "-c", f'exec "$HOME"/{shlex.quote(program[2:])} "$@"', "sh"]
    else:
        command = [program]
    return subprocess.run(["wsl.exe", "--cd", os.getcwd(), "-e", *command,
                           *(to_wsl(a) for a in args)]).returncode


if __name__ == "__main__":
    sys.exit(main())
