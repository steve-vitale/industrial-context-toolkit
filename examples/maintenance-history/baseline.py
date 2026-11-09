"""Predeclared raw-ID grouping baseline; input is a canonical work-order JSON array."""
import argparse
from collections import Counter
import json
from pathlib import Path


def group(rows):
    counts = Counter(row.get('asset_id', '') for row in rows)
    return {'method': 'raw-asset-id-row-count',
            'counts': dict(sorted(counts.items())),
            'boundary': 'Counts supplied rows by raw asset ID. No scoped identity, join, status, repair or ledger qualification.'}


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('records', type=Path)
    a = p.parse_args()
    print(json.dumps(group(json.loads(a.records.read_bytes())), indent=2))
