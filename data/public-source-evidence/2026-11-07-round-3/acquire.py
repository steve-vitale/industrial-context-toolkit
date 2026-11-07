"""One-time acquisition. Download originals only; never execute downloaded content."""
import concurrent.futures
import hashlib
import json
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[3]
HERE = Path(__file__).resolve().parent
plan = []

def add(group, name, url, **extra):
    plan.append(dict(group=group, name=name, url=url, **extra))

def github(group, repo, commit, names):
    for name in names:
        add(group, name, f"https://raw.githubusercontent.com/{repo}/{commit}/" + urllib.parse.quote(name))

github('tina-mining', 'ari-dasci/OD-TINA', '927b1584ea4aeac2ac7daa084a82f899b114419b',
       ['LICENSE', 'README.md'] + [f'data/day={d}/data.parquet' for d in
        ['2017-09-06', '2018-01-01', '2018-05-01', '2018-12-25']])
github('epanet-networks', 'OpenWaterAnalytics/EPANET', '57d8bd8ad60e89b57f2a1ac591f05c8e13589866',
       ['LICENSE', 'README.md', 'example-networks/Net1.inp', 'example-networks/Net2.inp', 'example-networks/Net3.inp'])
github('freecad-originals', 'FreeCAD/Examples', '40a806f3f3ef0e6a248fd5aed168a4d29213c421',
       ['README.md', 'AttachmentTutorial.FCStd', '100CadExercises/Page_015_Exercise2D-07_fillets_byHannu.fcstd',
        '100CadExercises/Page_091_Exercise3D-32_Overconstrained_byHannu.fcstd'])
z = json.loads((HERE / 'bms-zenodo.json').read_bytes())
for f in z['files']:
    add('bms-alarms', f['key'], f['links']['self'], expected_bytes=f['size'], published_checksum=f['checksum'])
github('bms-alarms', 'industrial-alarms-datasets/bms-alarm-timeseries-periodic',
       'd3b143ba11c6f0e2b651bb5cacf91dc44bf83474', ['README.md', 'LICENSE'])
m = json.loads((HERE / 'mro-api.txt').read_bytes())
for f in m['files']:
    if f['filename'] in ['product-E-14-02-2026.csv', 'product-E-20-09-2026.csv']:
        d = f['content_details']
        add('mro-catalog', f['filename'], d['download_url'], expected_bytes=d['size'],
            published_checksum='sha256:' + d['sha256_hash'])
for group, name, url, size in [
    ('nasa-milling', '3. Milling.zip', 'https://phm-datasets.s3.amazonaws.com/NASA/3.+Milling.zip', 14731306),
    ('nasa-cmapss', '6. Turbofan Engine Degradation Simulation Data Set.zip',
     'https://phm-datasets.s3.amazonaws.com/NASA/6.+Turbofan+Engine+Degradation+Simulation+Data+Set.zip', 12429152),
    ('usda-pumping', 'Chapter 8 - Irrigation Pumping Plants.pdf',
     'https://directives.nrcs.usda.gov/sites/default/files2/1720457430/Chapter%208%20-%20Irrigation%20Pumping%20Plants.pdf', None),
    ('phoenix-nameplate', 'PPI_Pump_Nameplate_Guidelines.pdf',
     'https://www.phoenixpumps.com/pdf/PPI_Pump_Nameplate_Guidelines.pdf', None),
]:
    add(group, name, url, **({'expected_bytes': size} if size else {}))
c = json.loads((HERE / 'commons-fireboat.json').read_bytes())
image = next(iter(c['query']['pages'].values()))['imageinfo'][0]
add('commons-fireboat', 'Nameplate_for_one_of_Fireboat_Firefighter_s_600V_DC_Marine_Motors.jpg', image['url'])
(HERE / 'selection.json').write_text(json.dumps(dict(
    role='acquired-unscored',
    selection='TiNA: first, January 1, May 1 and last published day, before reading rows; BMS: all deposit files including rejected/held-out labels; MRO: first/latest English snapshot; FreeCAD: named attachment, fillet and overconstraint examples chosen by filename, contents reserved; all other small named sources.',
    per_file_cap_bytes=40_000_000, total_cap_bytes=125_000_000, files=plan), indent=2) + '\n', encoding='utf-8')

def fetch(item):
    path = ROOT / 'data/external' / item['group'] / item['name']
    record = dict(item)
    try:
        if path.exists():
            raise FileExistsError('Acquisition refuses existing destination')
        request = urllib.request.Request(item['url'], headers={'User-Agent': 'industrial-context-toolkit public source research'})
        with urllib.request.urlopen(request, timeout=45) as response:
            data = response.read(40_000_001)
            record['final_url'] = response.url
            record['content_type'] = response.headers.get('Content-Type')
        if len(data) > 40_000_000:
            raise ValueError('per-file cap exceeded')
        if item.get('expected_bytes') is not None and len(data) != item['expected_bytes']:
            raise ValueError('Publisher byte size mismatch')
        if item.get('published_checksum'):
            algo, expected = item['published_checksum'].split(':', 1)
            if hashlib.new(algo, data).hexdigest() != expected:
                raise ValueError('Publisher checksum mismatch')
        path.parent.mkdir(parents=True, exist_ok=True)
        with path.open('xb') as stream:
            stream.write(data)
        record.update(bytes=len(data), sha256=hashlib.sha256(data).hexdigest(), status='acquired')
    except Exception as error:
        record.update(status='failed', error=f'{type(error).__name__}: {error}')
    print(item['group'], item['name'], record['status'], record.get('bytes', record.get('error')), flush=True)
    return record

with concurrent.futures.ThreadPoolExecutor(max_workers=5) as pool:
    records = list(pool.map(fetch, plan))
total = sum(r.get('bytes', 0) for r in records)
if total > 125_000_000:
    raise ValueError('Total acquisition cap exceeded')
(HERE / 'downloads.json').write_text(json.dumps(dict(bytes=total, files=records), indent=2) + '\n', encoding='utf-8')
