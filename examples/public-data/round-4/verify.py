"""Reproduce cached admission with network refused, check planted losses, optionally re-fetch one pinned response."""
import argparse
import contextlib
import hashlib
import io
import json
from pathlib import Path
import reproduce
import check_controls


def run(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--out', type=Path, required=True, help='new verification directory')
    ap.add_argument('--fresh', action='store_true', help='opt in to one HTTPS work-order response re-fetch')
    args = ap.parse_args(argv)
    if args.out.exists():
        ap.error('--out exists')
    args.out.mkdir(parents=True)
    fetcher = reproduce.fetcher
    baseline = json.loads(Path(__file__).with_name('baseline.json').read_bytes())
    current_pins = fetcher.load_pins()
    for name, expected in baseline['prior_pin_values'].items():
        actual = hashlib.sha256(json.dumps(current_pins[name], sort_keys=True, separators=(',', ':')).encode()).hexdigest()
        assert actual == expected, f'Preexisting pin value changed: {name}'
    for path, expected in baseline['existing_methods'].items():
        assert reproduce.fingerprint(reproduce.ROOT / path) == expected, f'Existing evaluated method changed: {path}'
    guide = Path(__file__).parent
    acquisition = json.loads((guide / 'acquisition.json').read_bytes())
    assert not acquisition['errors']
    assert acquisition['recipe_sha256'] == reproduce.fingerprint(guide / 'acquire.py')
    assert acquisition['selection_sha256'] == reproduce.fingerprint(guide / 'SELECTION.md')
    source_pins = current_pins[reproduce.SOURCE]
    assert {f['path']: {k: f[k] for k in ('bytes', 'sha256', 'url', 'role')}
            for f in acquisition['files']} == source_pins
    for name in ('acquisition-incomplete-1.json', 'acquisition-incomplete-2.json'):
        failed = json.loads((guide / 'history' / name).read_bytes())
        assert failed['errors'] and '503' in failed['errors'][0]
        assert failed['recipe_sha256'] == reproduce.fingerprint(guide / 'history/acquire-initial.py')
        assert failed['selection_sha256'] == reproduce.fingerprint(guide / 'history/SELECTION-initial.md')
    registry = json.loads(reproduce.REGISTRY.read_bytes())['sources'][reproduce.SOURCE]
    assert hashlib.sha256((reproduce.ROOT / registry['metadata_snapshot']).read_bytes()).hexdigest() == registry['metadata_snapshot_sha256']
    original = fetcher.http_get
    calls = []

    def refuse(*args, **kwargs):
        calls.append(str(args))
        raise AssertionError('Network disabled for cached verification')

    fetcher.http_get = refuse
    with contextlib.redirect_stdout(io.StringIO()):
        code = reproduce.run(['--fetch', '--max-mb', '0', '--out', str(args.out / 'cached')])
    fetcher.http_get = original
    assert code == 0 and not calls
    admission = json.loads((args.out / 'cached/admission.json').read_bytes())
    receipt = admission['fetch_receipts'][0]
    assert all(f['fetched_bytes'] == 0 for f in receipt['files'])
    pins = fetcher.load_pins()[reproduce.SOURCE]
    path = reproduce.ROOT / 'data/external' / reproduce.SOURCE / 'work-orders-000.json'
    raw = path.read_bytes()
    pin = pins[path.name]
    altered = dict(truncation=raw[:-1], same_size_mutation=bytes([raw[0] ^ 1]) + raw[1:])
    refusals = {}
    for name, data in altered.items():
        try:
            fetcher.check_bytes(name, data, pin['bytes'], pin['sha256'])
        except fetcher.PinError as error:
            refusals[name] = dict(status='refused', error=str(error))
        else:
            raise AssertionError('Changed original accepted')
    with contextlib.redirect_stdout(io.StringIO()) as captured:
        check_controls.run()
    result = dict(schema='public-source-verification-4', offline_cached_replay=dict(
        exit_code=code, files=len(admission['files']), response_bytes=sum(p['bytes'] for p in pins.values()),
        network_calls=len(calls), fetched_bytes=sum(f['fetched_bytes'] for f in receipt['files'])),
        prior_source_groups_unchanged=baseline['prior_source_groups'], existing_methods_unchanged=True,
        acquisition_selection_history_and_metadata_bindings='match',
        changed_original_controls=refusals, relationship_controls=json.loads(captured.getvalue()),
        methods={p.name: reproduce.fingerprint(p) for p in [Path(__file__), Path(check_controls.__file__)]})
    if args.fresh:
        # A single query is fresh integrity evidence, not a fresh full-cohort/transactional replay.
        data = original(pin['url'], None)
        fetcher.check_bytes(path.name, data, pin['bytes'], pin['sha256'])
        (args.out / 'fresh-work-orders.json').write_bytes(data)
        result['fresh_https_query'] = dict(path=path.name, url=pin['url'], bytes=len(data),
                                          sha256=hashlib.sha256(data).hexdigest(), status='pin match')
    (args.out / 'verification.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(result, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(run())
