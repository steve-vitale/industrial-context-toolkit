"""Require the offline evidence replay to reject altered, omitted and inconsistent retained records."""
import copy
import hashlib
import json
from pathlib import Path
import shutil
import tempfile
import zipfile

import recheck


def refused(label, action, expected):
    try:
        action()
    except ValueError as error:
        if expected not in str(error):
            raise AssertionError(f'{label}: unexpected refusal: {error}') from error
        print(label, 'refused:', error)
    else:
        raise AssertionError(label + ': altered evidence accepted')


def main():
    evidence = Path(__file__).resolve().parent / 'round-2'
    with tempfile.TemporaryDirectory(prefix='cad-evidence-controls-') as temp:
        root = Path(temp)
        raw, _ = recheck.unpack(evidence, root / 'positive')
        recheck.native_receipts(raw, 'native-validation-2', 12, 36)
        print('positive archive and retained native cohort pass')
        inventory = recheck.read(evidence / 'INVENTORY.json')
        changed = root / 'changed'
        changed.mkdir()
        shutil.copyfile(evidence / 'INVENTORY.json', changed / 'INVENTORY.json')
        archive = changed / 'evidence.zip'
        shutil.copyfile(evidence / 'evidence.zip', archive)
        with archive.open('r+b') as handle:
            handle.seek(100)
            value = handle.read(1)
            handle.seek(100)
            handle.write(bytes([value[0] ^ 1]))
        refused('same-size archive mutation', lambda: recheck.unpack(changed, root / 'bad-archive'), 'Archive integrity mismatch')
        omitted = root / 'omitted'
        omitted.mkdir()
        missing = next(iter(inventory['files']))
        with zipfile.ZipFile(evidence / 'evidence.zip') as original, zipfile.ZipFile(omitted / 'evidence.zip', 'w') as target:
            for member in original.infolist():
                if member.filename != missing:
                    target.writestr(member, original.read(member))
        admitted = copy.deepcopy(inventory)
        admitted['archive'].update(bytes=(omitted / 'evidence.zip').stat().st_size,
                                  sha256=hashlib.sha256((omitted / 'evidence.zip').read_bytes()).hexdigest())
        (omitted / 'INVENTORY.json').write_text(json.dumps(admitted), encoding='utf-8')
        refused('omitted member despite updated outer hash', lambda: recheck.unpack(omitted, root / 'bad-member'), 'Omitted/extra/duplicate archive members')
        receipt_path = raw / 'native-validation-2/edited-receipt.json'
        original = receipt_path.read_bytes()
        receipt = json.loads(original)
        receipt['readbacks'].pop()
        receipt_path.write_text(json.dumps(receipt), encoding='utf-8')
        refused('omitted native readback', lambda: recheck.native_receipts(raw, 'native-validation-2', 12, 36), 'Native case ordering changed')
        receipt = json.loads(original)
        asset = next(row for row in receipt['readbacks'][0]['candidate'] if row['attributes'].get('ICT_ID'))
        asset['attributes']['MODEL'] = 'PLANTED-WRONG-VALUE'
        receipt_path.write_text(json.dumps(receipt), encoding='utf-8')
        refused('changed native stored value', lambda: recheck.native_receipts(raw, 'native-validation-2', 12, 36), 'Native stored/foreign values differ')
        receipt_path.write_bytes(original)
    print('4 negative controls pass; fictional mutations, no CAD/UI execution')


if __name__ == '__main__':
    main()
