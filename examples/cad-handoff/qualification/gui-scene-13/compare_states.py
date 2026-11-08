"""Check the replayer applied the recorded state and exact primitive, independently via interposition."""
import json
from pathlib import Path
import sys
import replay_input

def compare(root):
    groups=replay_input.select(root)
    expected=[r for role in ('source','candidate')for g in groups if g['role']==role for r in g['rows']]
    actual=[json.loads(s)for s in(root/'replay/replay-state.jsonl').read_text().splitlines()]
    actual=[r for r in actual if r['kind']not in('begin','end')]
    assert len(actual)==len(expected),(len(actual),len(expected))
    ignore={'serial','epoch','painter','device_address'}
    changes=[]
    for i,(a,b)in enumerate(zip(expected,actual)):
        for key in a.keys()|b.keys():
            if key not in ignore and a.get(key)!=b.get(key):changes.append(dict(index=i,key=key,expected=a.get(key),actual=b.get(key)))
    return changes

if __name__=='__main__':
    changes=compare(Path(sys.argv[1]));print(json.dumps(changes[:10],indent=2));print('State/primitive discrepancies:',len(changes))
