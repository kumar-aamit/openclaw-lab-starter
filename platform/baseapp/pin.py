import hashlib
import sys
from pathlib import Path


def tree_hash(root: Path) -> str:
    h = hashlib.sha256()
    for path in sorted(p for p in Path(root).rglob("*") if p.is_file() and "__pycache__" not in p.parts):
        h.update(path.relative_to(root).as_posix().encode() + b"\0")
        h.update(path.read_bytes() + b"\0")
    return h.hexdigest()


if __name__ == "__main__":
    print(tree_hash(Path(sys.argv[1])))
