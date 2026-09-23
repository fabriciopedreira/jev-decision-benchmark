"""Verifica SDKs reais com HTTP simulado, ambiente limpo e rede bloqueada."""
import json
import os
import socket
import sys
from pathlib import Path
from unittest.mock import patch

if not __debug__:
    raise RuntimeError('Execute sem -O para manter as verificações ativas')

import httpx2

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'experimento'))
from harness.core import InputCase, validate_runtime_versions
from harness.judges import JevJudge, OpenAIJudge

CASE = InputCase('fixture', 'calibration', 'synthetic', {'claim':'A is 2.', 'evidence':['A is 2.']}, 'fixture', False)
requests = []

def fake_send(client, request, **kwargs):
    body = json.loads(request.content)
    requests.append(body)
    if request.url.path.endswith('/systemone'):
        assert body['model'] == 'jev-1.13.0'
        assert body['state'] == CASE.state
        payload = {'model':'jev-1.13.0', 'answers':{'attribution':{'type':'noul','noul':.8}}, 'usage':{'input_tokens':20,'output_tokens':1}}
    elif request.url.path.endswith('/responses'):
        assert body['store'] is False
        assert body['text']['format']['type'] == 'json_schema'
        assert body.get('reasoning') == ({'effort':'none'} if body['model'] == 'gpt-5.6-luna' else None)
        payload = {'id':'fixture-response', 'object':'response', 'created_at':0, 'status':'completed', 'error':None, 'incomplete_details':None, 'model':body['model'], 'output':[{'id':'fixture-message','type':'message','role':'assistant','status':'completed','content':[{'type':'output_text','text':'{"answers":{"attribution":true}}','annotations':[]}]}], 'usage':{'input_tokens':20,'output_tokens':1,'total_tokens':21,'input_tokens_details':{'cached_tokens':5},'output_tokens_details':{'reasoning_tokens':0}}}
    else:
        raise AssertionError('Unexpected request path')
    return httpx2.Response(200, request=request, json=payload)

with patch.dict(os.environ, {'OPENAI_API_KEY':'fixture-not-a-real-key','TYPESAFE_API_KEY':'fixture-not-a-real-key'}, clear=True), patch.object(socket.socket, 'connect', side_effect=AssertionError('Network forbidden')), patch.object(httpx2.Client, 'send', new=fake_send):
    validate_runtime_versions(require_openai=True)
    judges=[JevJudge(),OpenAIJudge('gpt-5.6-luna',reasoning_effort='none'),OpenAIJudge('gpt-5.6-terra',reasoning_effort=None)]
    for judge in judges:
        result=judge.classify(CASE)
        assert result.status == 'ok', (judge.model,result.error_type,result.raw)
        assert result.label == 'ATTRIBUTABLE'
        assert result.usage is not None
        assert result.model == judge.model
        if result.provider=='openai':assert result.usage['cached_input_tokens']==5
        judge.close()
        print(json.dumps({'model':judge.model,'status':result.status,'usage':result.usage,'real_network_calls':0}))
assert len(requests)==3
print('SDK parsing and transport smoke: OK; 3 synthetic responses; no network')
