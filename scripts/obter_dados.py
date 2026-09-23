"""Baixa a fonte oficial fixada e reconstrói inputs; não chama modelos."""
from pathlib import Path
import hashlib
import json
import shutil
import sys
import tempfile

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'experimento'))
from preparar_dados import build

def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()

def main():
    snapshot=ROOT/'experimento/snapshots/entradas.jsonl'
    freeze=json.loads((ROOT/'experimento/resultados/freeze-original.json').read_text())
    if snapshot.exists():
        assert digest(snapshot)==freeze['snapshot_sha256'], 'Snapshot existente divergente; não sobrescrito'
        print('Snapshot já existe e coincide com o freeze original.')
        return
    with tempfile.TemporaryDirectory(prefix='jev-wice-download-') as tmp:
        out=Path(tmp)
        build(out)
        for name,field in [('entradas.jsonl','snapshot_sha256'),('gabarito.csv','labels_sha256'),('manifesto.csv','manifest_sha256')]:
            assert digest(out/name)==freeze[field], f'Fonte divergente: {name}'
        original=json.loads((ROOT/'experimento/snapshots/auditoria.json').read_text())
        rebuilt=json.loads((out/'auditoria.json').read_text())
        assert rebuilt==original, 'Auditoria de origem divergente'
        shutil.copyfile(out/snapshot.name,snapshot)
    print('Inputs reconstruídos da fonte oficial e hashes conferidos. Nenhuma API de modelo chamada.')

if __name__=='__main__':
    main()
