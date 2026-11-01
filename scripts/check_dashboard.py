"""Artifact integrity, additive invariants and Python-reference/browser parity."""
import gzip,hashlib,json,subprocess,sys
from pathlib import Path
ROOT=Path(__file__).resolve().parents[1]
manifest=json.loads((ROOT/'dashboard/manifest.json').read_text(encoding='utf-8'))
artifact=ROOT/'dashboard'/manifest['file']
assert hashlib.sha256(artifact.read_bytes()).hexdigest()==manifest['sha256']
data=json.loads(gzip.decompress(artifact.read_bytes()))
assert data['rows']==manifest['rows']==sum(data['cohort_n'])
assert data['positive']==manifest['positive']==sum(data['cohort_positive'])
assert len(data['source_profile'])==(19 if data['project']=='bank' else 159)
for name,v in data['variables'].items():
    assert [sum(row) for row in v['counts']]==data['cohort_n'],name
    assert [sum(row) for row in v['positives']]==data['cohort_positive'],name
    assert all(0<=p<=n for ns,ps in zip(v['counts'],v['positives']) for n,p in zip(ns,ps)),name
for pair in data['pairs']:
    assert sum(r[3] for r in pair['rows'])==data['rows']
    assert sum(r[4] for r in pair['rows'])==data['positive']
if data.get('previous_analysis'):
    for name,v in data['previous_analysis']['distributions'].items():assert sum(b['n'] for b in v['bins'])==data['meta']['previous_rows'],name
    for name,groups in data['previous_analysis']['category_presence'].items():
        for group in groups:assert 0<=group['positive']<=group['n']<=data['meta']['current_with_history'],name
subprocess.run(['node',str(ROOT/'tests/dashboard-parity.mjs'),str(artifact),str(ROOT/'dashboard/check-fixtures.json')],check=True)
print('Artifact integrity and count conservation passed:',data['project'],data['rows'],'records,',len(data['variables']),'analytical variables')
