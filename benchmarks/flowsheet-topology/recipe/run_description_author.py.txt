"""Stand in for the approved assistant in the description workflow: give a model only the prepared packet, return check diagnostics for correction, then build.

The documented route (examples/from-description/README.md, "Use your own description with an approved assistant") is:
give the assistant prompt.md, contract.md, source_numbered.txt, reference_source.txt and reference_answer.json from
a packet made by `description_workflow.py prepare`; save its JSON as answer.json; run `check`; return the check's
diagnostics for correction; then `build`. This runner does exactly that with the toolkit's existing model path
(the Claude Code CLI, as run_extraction.py uses it: a neutral one-line system prompt, an empty temporary folder, no
MCP servers, no slash commands) and with every tool disabled, so the model sees the packet text and nothing else.
The scored output is the model.json that `description_workflow.py build` writes, never the raw reply.

    python scripts/run_description_author.py --packet <prepared packet> --out <new folder> [--rounds 4] [--model M]

Writes <out>/round<N>-answer.json (each reply's JSON), <out>/answer.json (the last one), <out>/result/ (the build,
only if a check passed), and <out>/record.json: served model, CLI version, prompt hashes, per-round check result,
seconds and notional cost. A reply that never passes `check` leaves no build; it is a failed answer, not a partial
one. Calls a model; nothing here runs in the test suite or the corpus matrix, which re-score saved answers offline.
"""
import argparse
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
from datetime import datetime, timezone

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT / 'scripts'))
import description_workflow as dw  # noqa: E402

SYSTEM_LINE = 'You author structured JSON for an engineering description workflow. Follow the user\'s output format exactly.'
PACKET_FILES = ('prompt.md', 'contract.md', 'reference_source.txt', 'reference_answer.json', 'source_numbered.txt')
TIMEOUT_S = 1800


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def packet_message(packet):
    parts = []
    for name in PACKET_FILES:
        parts.append(f'===== {name} =====\n' + (packet / name).read_text(encoding='utf-8'))
    parts.append('===== end of packet =====\nAuthor the answer for source.txt (shown above as source_numbered.txt). '
                 'Reply with the single raw JSON object only.')
    return '\n\n'.join(parts)


def feedback_message(first, answer_text, report):
    return (first + '\n\n===== your previous answer =====\n' + answer_text +
            '\n\n===== check diagnostics for that answer =====\n' + json.dumps(report, indent=2) +
            '\n\nCorrect only what these diagnostics and the source support. Reply with the complete corrected raw '
            'JSON object only.')


def extract_json(text):
    """The reply's outermost JSON object as text (code fences or stray prose tolerated), or None."""
    if not text:
        return None
    start, end = text.find('{'), text.rfind('}')
    if start < 0 or end <= start:
        return None
    candidate = text[start:end + 1]
    try:
        json.loads(candidate)
    except json.JSONDecodeError:
        return None
    return candidate


def tool(action, *args, **kwargs):
    """The workflow's check/build with its own command-line error handling: a refusal is a report, not a crash."""
    try:
        return action(*args, **kwargs)
    except subprocess.TimeoutExpired:
        return {'ok': False, 'errors': ['A native generation step exceeded 60 seconds; no output was published.']}
    except ImportError:
        return {'ok': False, 'errors': ['Drawing validation needs the approved drawing dependencies from requirements.txt.']}
    except (OSError, ValueError, UnicodeError, RecursionError, KeyError, TypeError, AttributeError, IndexError,
            OverflowError, StopIteration) as exc:
        return {'ok': False, 'errors': [str(exc)]}


def call_model(message, model):
    work = Path(tempfile.mkdtemp(prefix='description-author-'))
    cmd = ['claude', '-p', '--output-format', 'json', '--system-prompt', SYSTEM_LINE, '--tools', '',
           '--strict-mcp-config', '--disable-slash-commands']
    if model:
        cmd += ['--model', model]
    t0 = time.time()
    try:
        p = subprocess.run(cmd, cwd=work, input=message, capture_output=True, text=True, encoding='utf-8',
                           timeout=TIMEOUT_S, shell=(os.name == 'nt'))
        seconds = round(time.time() - t0, 1)
        if not p.stdout.strip():
            return {'text': None, 'model': model, 'error': (p.stderr or 'no output')[-2000:], 'seconds': seconds}
        out = json.loads(p.stdout)
        return {'text': out.get('result'), 'model': ','.join((out.get('modelUsage') or {}).keys()) or model or 'default',
                'cost_usd_notional': out.get('total_cost_usd'), 'seconds': seconds,
                'error': out.get('result') if out.get('is_error') else None}
    finally:
        shutil.rmtree(work, ignore_errors=True)


def cli_version():
    try:
        p = subprocess.run(['claude', '--version'], capture_output=True, text=True, timeout=60, shell=(os.name == 'nt'))
        return p.stdout.strip() or None
    except (OSError, subprocess.SubprocessError):
        return None


def run(packet, out, rounds=4, model=None, caller=call_model):
    packet, out = Path(packet), Path(out)
    if out.exists():
        raise ValueError('Choose a new output folder')
    out.mkdir(parents=True)
    first = packet_message(packet)
    message = first
    record = {'schema': 'description-author-run/1', 'ran_at': datetime.now(timezone.utc).strftime('%Y-%m-%dT%H:%M:%SZ'),
              'interface': 'claude-code-cli -p, --tools "" (no tools), --system-prompt (one neutral line), empty '
                           'temporary folder, --strict-mcp-config, --disable-slash-commands',
              'requested_model': model, 'cli_version': cli_version() if caller is call_model else None,
              'system_line': SYSTEM_LINE, 'packet_sha256': {n: sha((packet / n).read_bytes()) for n in PACKET_FILES},
              'source_sha256': json.loads((packet / 'packet.json').read_text(encoding='utf-8'))['source_sha256'],
              'max_rounds': rounds, 'rounds': [], 'built': False}
    answer_path = None
    for n in range(1, rounds + 1):
        reply = caller(message, model)
        text = extract_json(reply.get('text'))
        row = {'round': n, 'prompt_sha256': sha(message.encode('utf-8')), 'served_model': reply.get('model'),
               'seconds': reply.get('seconds'), 'cost_usd_notional': reply.get('cost_usd_notional'),
               'error': reply.get('error')}
        if text is None:
            row['check'] = {'ok': False, 'errors': ['reply held no JSON object']}
            (out / f'round{n}-reply.txt').write_text(reply.get('text') or '', encoding='utf-8', newline='\n')
            record['rounds'].append(row)
            message = feedback_message(first, reply.get('text') or '', row['check'])
            continue
        answer_path = out / f'round{n}-answer.json'
        answer_path.write_text(text, encoding='utf-8', newline='\n')
        report = tool(dw.check, packet, answer_path)
        row['check'] = {'ok': report.get('ok'), 'errors': report.get('errors', [])}
        record['rounds'].append(row)
        if report.get('ok'):
            break
        message = feedback_message(first, text, report)
    if answer_path is not None:
        shutil.copyfile(answer_path, out / 'answer.json')
        if record['rounds'][-1]['check']['ok']:
            built = tool(dw.build, packet, out / 'answer.json', out / 'result')
            record['built'] = bool(built.get('ok'))
            record['build_errors'] = built.get('errors', [])
    served = sorted({r['served_model'] for r in record['rounds'] if r.get('served_model')})
    record['served_model'] = ','.join(served) or None
    record['seconds'] = round(sum(r['seconds'] or 0 for r in record['rounds']), 1)
    costs = [r['cost_usd_notional'] for r in record['rounds'] if r.get('cost_usd_notional') is not None]
    record['cost_usd_notional'] = round(sum(costs), 4) if costs else None
    (out / 'record.json').write_text(json.dumps(record, indent=2) + '\n', encoding='utf-8', newline='\n')
    return record


def main(argv=None):
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument('--packet', type=Path, required=True)
    ap.add_argument('--out', type=Path, required=True)
    ap.add_argument('--rounds', type=int, default=4)
    ap.add_argument('--model', default=None)
    args = ap.parse_args(argv)
    try:
        record = run(args.packet, args.out, args.rounds, args.model)
    except (OSError, ValueError) as exc:
        print(str(exc), file=sys.stderr)
        return 2
    print(json.dumps({k: record[k] for k in ('served_model', 'built', 'seconds', 'cost_usd_notional')} |
                     {'rounds': [(r['round'], r['check']['ok'], len(r['check']['errors'])) for r in record['rounds']]}))
    return 0 if record['built'] else 1


if __name__ == '__main__':
    raise SystemExit(main())
