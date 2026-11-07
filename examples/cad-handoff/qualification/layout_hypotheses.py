"""Create all predeclared exposed layout diagnostic revisions; never overwrite source or call native CAD."""
import argparse
import hashlib
import json
from pathlib import Path
import shutil

import ezdxf

HERE = Path(__file__).resolve().parent


def sha(path):
    return hashlib.sha256(Path(path).read_bytes()).hexdigest()


def main():
    ap = argparse.ArgumentParser(description=__doc__)
    ap.add_argument('--out', type=Path, required=True)
    args = ap.parse_args()
    if args.out.exists():
        ap.error('Choose a new destination; retain all attempts')
    source = HERE / 'validation-2/authored/validation-cp1251.dxf'
    pin = sha(source)
    args.out.mkdir(parents=True)
    cases = []
    for label in ('original', 'library-save', 'add-main', 'add-main-restore-current', 'set-current-only', 'activate-only'):
        target = args.out / (label + '.dxf')
        if label == 'original':
            shutil.copyfile(source, target)
        else:
            doc = ezdxf.readfile(source)
            layout = doc.layouts.get('Qualification sheet')
            prior = layout.dxf_layout.dxf.get('viewport_handle', '0')
            display = list(layout.query('VIEWPORT'))
            if len(display) != 1 or layout.main_viewport() is not None:
                raise ValueError('Declared diagnostic source structure changed')
            if label.startswith('add-main'):
                layout.add_new_main_viewport()
                if label == 'add-main-restore-current':
                    layout.set_current_viewport_handle(prior)
            elif label == 'set-current-only':
                layout.set_current_viewport_handle(display[0].dxf.handle)
            elif label == 'activate-only':
                doc.layouts.set_active_layout('Qualification sheet')
            doc.saveas(target)
        cases.append(dict(id=label, source=str(target.resolve()), candidate=str(target.resolve()), sha256=sha(target)))
    if sha(source) != pin:
        raise ValueError('Original diagnostic source changed')
    report = dict(role='Six exposed compatibility diagnoses; not preservation or qualification candidates',
                  source_sha256=pin, generator_sha256_lf=hashlib.sha256(Path(__file__).read_bytes().replace(b'\r\n', b'\n')).hexdigest(),
                  ezdxf=ezdxf.__version__, cases=cases)
    (args.out / 'manifest.json').write_text(json.dumps(report, indent=2)+'\n', encoding='utf-8', newline='\n')
    print('Six diagnostic revisions frozen; original unchanged')


if __name__ == '__main__':
    main()
