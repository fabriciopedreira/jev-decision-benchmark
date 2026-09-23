"""Auditoria e recálculo offline da exportação pública. Biblioteca padrão apenas."""
from pathlib import Path
import hashlib
import json
import math
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT/'experimento'))
from analisar_wice_v4 import analyze, test_labels, response_ids

def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def compare(actual, expected, path='analysis'):
    if isinstance(expected, dict):
        assert actual.keys() == expected.keys(), path
        for key in expected:
            compare(actual[key],expected[key],f'{path}.{key}')
    elif isinstance(expected,list):
        assert len(actual)==len(expected), path
        for i,(a,b) in enumerate(zip(actual,expected)):
            compare(a,b,f'{path}[{i}]')
    elif isinstance(expected,float):
        assert math.isclose(actual,expected,rel_tol=1e-12,abs_tol=1e-12), (path,actual,expected)
    else:
        assert actual==expected, (path,actual,expected)

def main():
    manifest=json.loads((ROOT/'manifesto-exportacao.json').read_text())
    for name,digest in manifest['exact_copies_sha256'].items():
        assert sha(ROOT/name)==digest, f'Arquivo alterado: {name}'
    for name,hashes in manifest['transformed_documents'].items():
        assert sha(ROOT/name)==hashes['public_sha256'], f'Documento alterado: {name}'
    result=ROOT/manifest['public_results_path']
    assert sha(result)==manifest['public_results_sha256'], 'Resultado público alterado'
    rows=[json.loads(line) for line in result.read_text().splitlines() if line]
    labels,originals=test_labels()
    assert len(rows)==355 and len({r['case_id'] for r in rows})==355
    assert {r['case_id'] for r in rows}==set(labels)
    ids=[]
    for row in rows:
        c=row['cascade']; j=c['jev']; p=j['probability_attributable']
        route='jev' if j['status']=='ok' and p is not None and (p<=.30 or p>=.70) else 'luna_after_jev'
        assert c['route']==route
        assert (c['luna'] is None)==(route=='jev')
        chosen=j if route=='jev' else c['luna']
        assert c['final_label']==(chosen['label'] if chosen['status']=='ok' else None)
        assert c['latency_ms']+5 >= j['latency_ms']+(c['luna']['latency_ms'] if c['luna'] else 0)
        for pred in (row['luna_baseline'],row['terra_baseline'],c['luna']):
            if pred:
                ids.extend(response_ids(pred))
    assert len(ids)==len(set(ids))==785
    actual=analyze(rows,labels,originals)
    expected=json.loads((ROOT/'experimento/resultados/v4-wice-analysis.json').read_text())
    compare(actual,expected)
    def no_cache(pred):
        u=pred['usage']
        return (u.get('input_tokens_total',u['input_tokens'])*.20+u.get('output_tokens_total',u['output_tokens'])*1.20)/1e6
    base=sum(no_cache(r['luna_baseline']) for r in rows)
    casc=actual['costs']['jev']['calculated_total_usd']+sum(no_cache(r['cascade']['luna']) for r in rows if r['cascade']['luna'])
    assert round(100*(1-casc/base),2)==51.85
    print(json.dumps({'status':'OK','cases':actual['cases'],'groups':actual['groups'],'routes':actual['routes'],
          'distinct_openai_id_hashes':len(ids),'full_analysis_matches':True,'bootstrap_resamples':10000,
          'no_cache_savings_percent':round(100*(1-casc/base),2),'external_api_calls':0},indent=2))

if __name__=='__main__':
    main()
