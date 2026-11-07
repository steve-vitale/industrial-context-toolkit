"""Initial bounded acquisition of the declared round-5 files, without execution.

The committed selection contains publisher checksums where available. Later users
should use reproduce.py and the acquired SHA-256 pins instead of this discovery step.
"""
import argparse
import hashlib
import json
import subprocess
import tempfile
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
UA = 'industrial-context-toolkit public source acquisition https://github.com/steve-vitale/industrial-context-toolkit'


def run():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--out', type=Path, required=True)
    args = ap.parse_args()
    if args.out.exists():
        ap.error('--out must be new')
    selection = json.loads((HERE / 'SELECTION.json').read_bytes())
    args.out.mkdir(parents=True)
    report = dict(created=datetime.now(timezone.utc).isoformat(), files=[], errors=[],
                  role='initial acquisition, not model evaluation',
                  selection_sha256=hashlib.sha256((HERE / 'SELECTION.json').read_bytes().replace(b'\r\n', b'\n')).hexdigest())
    consumed = 0
    for source, files in selection['files'].items():
        for item in files:
            row = dict(source=source, **item)
            dest = ROOT / 'data/external' / source / item['path']
            try:
                cap = min(selection['file_cap_bytes'], selection['total_cap_bytes'] - consumed)
                if cap <= 0:
                    raise ValueError('total acquisition ceiling exhausted')
                if dest.exists():
                    raise ValueError('existing original refused; use pinned reproduction')
                if 'cached_original' in item:
                    data = (ROOT / item['cached_original']).read_bytes()
                    row['transport'] = 'earlier original HTTPS response, unchanged bytes'
                else:
                    try:
                        request = urllib.request.Request(item['url'], headers={'User-Agent': UA})
                        with urllib.request.urlopen(request, timeout=60) as response:
                            data = response.read(cap + 1)
                            row['resolved_url'] = response.url
                        row['transport'] = 'Python urllib, verified HTTPS'
                    except urllib.error.URLError as error:
                        # Use Windows system trust for the publisher's incomplete chain;
                        # no insecure TLS switch, authentication or access-control bypass.
                        if 'CERTIFICATE_VERIFY_FAILED' not in str(error):
                            raise
                        with tempfile.TemporaryDirectory(prefix='ict-public-fetch-') as tmp:
                            target = Path(tmp) / 'response'
                            command = ['curl.exe', '--fail', '--location', '--silent', '--show-error',
                                       '--max-time', '90', '--max-filesize', str(cap),
                                       '--user-agent', UA, '--output', str(target), item['url']]
                            result = subprocess.run(command, capture_output=True, text=True, timeout=100)
                            if result.returncode:
                                raise ValueError(f'verified system HTTPS failed: {result.stderr.strip()}')
                            data = target.read_bytes()
                        row['transport'] = 'Windows curl/Schannel, verified HTTPS'
                        row['python_tls_error'] = str(error)
                if len(data) > cap:
                    raise ValueError('file exceeds acquisition ceiling')
                consumed += len(data)
                if 'bytes' in item and len(data) != item['bytes']:
                    raise ValueError('publisher byte count mismatch')
                for algo in ('md5', 'sha256', 'sha1'):
                    if algo in item and hashlib.new(algo, data).hexdigest() != item[algo]:
                        raise ValueError(f'publisher {algo} mismatch')
                if item.get('format') == 'zip' and not data.startswith(b'PK'):
                    raise ValueError('not a ZIP response')
                if item.get('format') == 'pdf' and not data.startswith(b'%PDF-'):
                    raise ValueError('not a PDF response')
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_bytes(data)
                row.update(bytes=len(data), sha256=hashlib.sha256(data).hexdigest(), status='acquired')
                print(source, item['path'], len(data), flush=True)
            except Exception as error:
                row.update(status='failed', error=f'{type(error).__name__}: {error}')
                report['errors'].append(row.copy())
                print(source, item['path'], row['error'], flush=True)
            report['files'].append(row)
            (args.out / 'acquisition.json').write_text(json.dumps(report, indent=2) + '\n', encoding='utf-8')
    return int(bool(report['errors']))


if __name__ == '__main__':
    raise SystemExit(run())
