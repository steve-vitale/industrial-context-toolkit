"""Make labelled QA contact sheets and exact RGB difference diagnostics; original native PNGs are never altered."""
import argparse
import hashlib
import json
from pathlib import Path
from PIL import Image, ImageChops, ImageDraw, ImageFont


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('renders', type=Path)
    ap.add_argument('--out', type=Path, required=True, help='new QA artifact directory')
    args = ap.parse_args(argv)
    if args.out.exists():
        ap.error('Output exists; retain previous review artifacts')
    receipt = json.loads((args.renders / 'receipts.json').read_bytes())
    rows = receipt['results']
    groups = {}
    for r in rows:
        if r.get('error') or r['exit'] != 0 or not r['input_unchanged']:
            ap.error('Failed native render; inspect retained receipts')
        key = (r['case'], r['view'])
        if r['route'] in groups.setdefault(key, {}):
            ap.error('Duplicate paired view')
        groups[key][r['route']] = r
    if len(rows) != 82 or len(groups) != 41 or any(set(g) != {'source', 'candidate'} for g in groups.values()):
        ap.error('Omitted/extra source or candidate views')
    args.out.mkdir(parents=True)
    results, paired_images = [], []
    for (case, view), group in groups.items():
        left, right = group['source'], group['candidate']
        for key in ('window', 'block', 'width', 'height', 'identity'):
            if left[key] != right[key]:
                raise ValueError('Unmatched native render settings')
        images, paths = [], []
        for route, item in [('source', left), ('candidate', right)]:
            path = args.renders / f'{case}-{view}-{route}.png'
            if hashlib.sha256(path.read_bytes()).hexdigest() != item['image_sha256']:
                raise ValueError('Changed native image')
            with Image.open(path) as opened:
                images.append(opened.convert('RGB'))
            paths.append(path.name)
        a, b = images
        if a.size != (3200, 2200) or b.size != a.size:
            raise ValueError('Unexpected native image dimensions')
        diff = ImageChops.difference(a, b)
        channels = diff.split()
        maximum = ImageChops.lighter(ImageChops.lighter(channels[0], channels[1]), channels[2])
        changed = a.width * a.height - maximum.histogram()[0]
        def ink(image):
            d = ImageChops.difference(image, Image.new('RGB', image.size, 'white')).split()
            m = ImageChops.lighter(ImageChops.lighter(d[0], d[1]), d[2])
            return image.width * image.height - m.histogram()[0]
        result = dict(case=case, view=view, identity=left['identity'], images=paths,
            source_sha256=left['image_sha256'], candidate_sha256=right['image_sha256'],
            source_ink_pixels=ink(a), candidate_ink_pixels=ink(b), changed_pixels=changed,
            changed_bbox=diff.getbbox(), window=left['window'], block=left['block'],
            scope='Exact RGB diagnostic, not an acceptance score. Contact sheet is a labelled resized QA derivative; native PNGs remain exact.')
        results.append(result)
        paired_images.append((case + ' / ' + view, images))
    font = ImageFont.load_default(size=22)
    for start in range(0, len(paired_images), 6):
        selected = paired_images[start:start+6]
        sheet = Image.new('RGB', (1600, 586 * len(selected)), 'white')
        draw = ImageDraw.Draw(sheet)
        for row, (title, images) in enumerate(selected):
            for col, image in enumerate(images):
                draw.text((col*800+8, row*586+5), title + (' | SOURCE' if col == 0 else ' | CANDIDATE'), font=font, fill='black')
                sheet.paste(image.resize((800, 550), Image.Resampling.LANCZOS), (col*800, row*586+36))
        sheet.save(args.out / f'contact-{start//6+1}.png')
    (args.out / 'pairs.json').write_text(json.dumps(dict(
        scope='Native display diagnostics and QA contact sheets; requires direct visual inspection. '
              'No original typography, GUI editing, plant or engineering acceptance inferred.',
        pairs=results, font_substitution=['Standard', 'Arial'], monochrome=True,
        reporter_sha256_lf=hashlib.sha256(Path(__file__).read_bytes().replace(b'\r\n', b'\n')).hexdigest()), indent=2)+'\n', encoding='utf-8')
    print(json.dumps(dict(pairs=len(results), identical_pairs=sum(r['changed_pixels'] == 0 for r in results),
        empty_source_views=[(r['case'],r['view']) for r in results if r['source_ink_pixels']==0],
        changed_pairs=[dict(case=r['case'],view=r['view'],pixels=r['changed_pixels']) for r in results if r['changed_pixels']]), indent=2))


if __name__ == '__main__':
    main()
