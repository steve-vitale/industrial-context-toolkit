"""Matched inventory-only baseline: byte identity without engineering/context semantics."""
import argparse
import hashlib
import json
from pathlib import Path


def inventory(root):
    root = Path(root)
    return dict(method='file-inventory-only',
                files={p.relative_to(root).as_posix(): dict(bytes=p.stat().st_size,
                       sha256=hashlib.sha256(p.read_bytes()).hexdigest()) for p in sorted(root.rglob('*')) if p.is_file()},
                boundary='No scoped crosswalk, receiving schema, source meaning, dependency/review state or revision reconciliation.')


if __name__ == '__main__':
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('root', type=Path)
    print(json.dumps(inventory(parser.parse_args().root), indent=2))
