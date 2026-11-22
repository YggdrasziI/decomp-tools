#!/usr/bin/env python3
"""Check files against SHA-1 checksums in sha1sum format (`<sha1>  <path>` lines).

  python sha1.py <checksum file>             # every file the list names (paths as written)
  python sha1.py <file> -c <checksum file>   # one file against the list's first checksum
                                             # (the name in the list is not read)
"""

import argparse
import hashlib
import sys
from pathlib import Path


def check(path: Path, target: str, name: str) -> bool:
    if not path.exists():
        print(f"{name}: MISSING", file=sys.stderr)
        return False
    digest = hashlib.sha1(path.read_bytes()).hexdigest()
    if digest != target:
        print(f"{name}: FAILED\nExpected: {target}\nGot:      {digest}", file=sys.stderr)
        return False
    print(f"{name}: OK")
    return True


def entries(checksum_file: Path) -> list[tuple[str, str]]:
    out = []
    for line in checksum_file.read_text().splitlines():
        if line.strip():
            target, name = line.split(maxsplit=1)
            out.append((target.lower(), name.lstrip("*")))
    return out


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("file", type=Path, help="checksum file, or the file to check with -c")
    parser.add_argument("-c", dest="checksum_file", type=Path,
                        help="checksum file whose first checksum `file` must have")
    args = parser.parse_args()

    if args.checksum_file:
        listed = entries(args.checksum_file)
        if not listed:
            sys.exit(f"{args.checksum_file}: no checksum")
        ok = check(args.file, listed[0][0], str(args.file))
    else:
        ok = all([check(Path(name), target, name) for target, name in entries(args.file)])
    sys.exit(0 if ok else 1)


if __name__ == "__main__":
    main()
