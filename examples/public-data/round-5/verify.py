"""Check acquired originals, a cached replay with networking refused, and altered-byte refusals."""
import argparse
import contextlib
import hashlib
import io
import json
from pathlib import Path
import reproduce


def value_hash(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, separators=(',', ':')).encode()).hexdigest()


def run(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--fresh', action='store_true', help='opt in to a complete second yeast-deposit fetch')
    args = ap.parse_args(argv)
    if args.out.exists():
        ap.error('--out must be new')
    args.out.mkdir(parents=True)
    here, root = Path(__file__).parent, reproduce.ROOT
    baseline = json.loads((here / 'baseline.json').read_bytes())
    pins = reproduce.fetch_corpus.load_pins()
    for key, expected in baseline['prior_pin_values'].items():
        assert value_hash(pins[key]) == expected, f'Prior pins changed: {key}'
    for name, expected in baseline['methods'].items():
        assert reproduce.previous.fingerprint(root / name) == expected, f'Prior method changed: {name}'
    registry = json.loads(reproduce.REGISTRY.read_bytes())['sources']
    for sid, source in registry.items():
        assert reproduce.previous.fingerprint(root / source['metadata_snapshot']) == source['metadata_snapshot_sha256'], sid
    acquisition = json.loads((here / 'acquisition.json').read_bytes())
    assert acquisition['selection_sha256'] == reproduce.previous.fingerprint(here / 'SELECTION.json')
    acquired = [f for f in acquisition['files'] if f['status'] == 'acquired']
    observed = {(f['source'], f['path']): {k: f[k] for k in ('bytes', 'sha256', 'url')} for f in acquired}
    expected = {(sid, name): {k: pin[k] for k in ('bytes', 'sha256', 'url')}
                for sid in registry for name, pin in pins[sid].items()}
    assert observed == expected, 'Acquisition/pin coverage differs'
    original, calls = reproduce.fetch_corpus.http_get, []

    def refuse(*args, **kwargs):
        calls.append(str(args))
        raise AssertionError('Network disabled for cached verification')

    reproduce.fetch_corpus.http_get = refuse
    try:
        with contextlib.redirect_stdout(io.StringIO()):
            code = reproduce.run(['--fetch', '--max-mb', '0', '--out', str(args.out / 'cached')])
    finally:
        reproduce.fetch_corpus.http_get = original
    assert code == 0 and not calls
    admission = json.loads((args.out / 'cached/admission.json').read_bytes())
    receipts = [f for r in admission['fetch_receipts'] for f in r['files']]
    assert len(receipts) == len(acquired) and all(f['fetched_bytes'] == 0 for f in receipts)
    altered = {}
    for sid in registry:
        name, pin = next(iter(pins[sid].items()))
        raw = (root / 'data/external' / sid / name).read_bytes()
        for label, data in [('truncation', raw[:-1]), ('same-size mutation', bytes([raw[0] ^ 1]) + raw[1:])]:
            try:
                reproduce.fetch_corpus.check_bytes(name, data, pin['bytes'], pin['sha256'])
            except reproduce.fetch_corpus.PinError:
                altered[f'{sid}/{label}'] = 'refused'
            else:
                raise AssertionError('Changed original accepted')
    result = dict(schema='public-source-verification-5', files=len(acquired),
                  bytes=sum(f['bytes'] for f in acquired), groups=len(registry),
                  cached_replay=dict(exit_code=code, network_calls=len(calls), fetched_bytes=0),
                  prior_pin_groups_unchanged=len(baseline['prior_pin_values']),
                  prior_methods_unchanged=True, metadata_and_acquisition_bindings='match',
                  altered_original_controls=altered,
                  limitations='Integrity/structural admission only; no model, solver, CAD or engineering acceptance.')
    if args.fresh:
        fresh = []
        for name, pin in pins['industrial-yeast'].items():
            data = original(pin['url'], None)
            reproduce.fetch_corpus.check_bytes(name, data, pin['bytes'], pin['sha256'])
            dest = args.out / 'fresh-yeast' / name
            dest.parent.mkdir(parents=True, exist_ok=True)
            dest.write_bytes(data)
            fresh.append(dict(path=name, bytes=len(data), sha256=hashlib.sha256(data).hexdigest()))
        result['fresh_https'] = dict(source='industrial-yeast', files=fresh, status='all pins match')
    (args.out / 'verification.json').write_text(json.dumps(result, indent=2) + '\n', encoding='utf-8')
    print(json.dumps(result, indent=2))
    return 0


if __name__ == '__main__':
    raise SystemExit(run())
