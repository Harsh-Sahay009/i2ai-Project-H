"""Persistent spending reservations must precede every paid HTTP attempt."""
from decimal import Decimal
import json
import threading
from concurrent.futures import ThreadPoolExecutor

import pytest

from itemizer.bootstrap.data import ContractError
from itemizer.providers import ModelSpec, ProviderError
from itemizer.paid import CappedOpenAITransport, SpendingLimitExceeded


def spec(**changes):
    fields = dict(name='openai-gpt-5.4-mini', provider='openai_compatible',
                  model='gpt-5.4-mini-2026-03-17', base_url='https://api.openai.com/v1',
                  api_key_env='OPENAI_API_KEY', effort='medium', temperature=None,
                  max_tokens=16000, refusal_fallback=False,
                  input_usd_per_mtok='0.75', output_usd_per_mtok='4.50',
                  cache_read_usd_per_mtok='0.075', cache_write_usd_per_mtok='0')
    return ModelSpec(**{**fields, **changes})


def body():
    return {'model': spec().model, 'max_tokens': 16000,
            'messages': [{'role':'user','content':'PRIVATE NOTE'}]}


def reply(prompt=100, output=10, cached=0):
    return {'usage': {'prompt_tokens':prompt,'completion_tokens':output,
                      'prompt_tokens_details':{'cached_tokens':cached}}}


def test_reserves_before_http_settles_usage_and_preserves_restart(tmp_path):
    path=tmp_path/'ledger.json'
    def http(url, headers, wire):
        state=json.loads(path.read_text())
        assert state['calls'][-1]['status']=='reserved'
        assert Decimal(state['calls'][-1]['accounted_usd'])==Decimal('0.372')
        assert wire['max_completion_tokens']==16000 and 'max_tokens' not in wire
        assert wire['store'] is False and wire['service_tier']=='default'
        return reply()
    client=CappedOpenAITransport(spec(), path, '5', transport=http)
    client('https://api.openai.com/v1/chat/completions', {'Authorization':'PRIVATE KEY'}, body())
    assert client.summary()['settled_usd']=='0.00012'
    restarted=CappedOpenAITransport(spec(), path, '5', transport=http)
    restarted('https://api.openai.com/v1/chat/completions', {}, body())
    assert Decimal(restarted.summary()['settled_usd'])==Decimal('0.00024')
    assert 'PRIVATE' not in path.read_text()


def test_denied_reservation_sends_no_request(tmp_path):
    sent=[]
    client=CappedOpenAITransport(spec(), tmp_path/'ledger.json', '0.1',
                                transport=lambda *args: sent.append(args))
    with pytest.raises(SpendingLimitExceeded):
        client('https://api.openai.com/v1/chat/completions', {}, body())
    assert sent==[] and client.summary()['blocked_by_limit'] is True


def test_transport_failure_keeps_reservation_across_restart(tmp_path):
    path=tmp_path/'ledger.json'; sent=[]
    def fail(*args):
        sent.append(True)
        raise OSError('PRIVATE REQUEST MUST NOT BE RECORDED')
    first=CappedOpenAITransport(spec(), path, '0.5', transport=fail)
    with pytest.raises(OSError):
        first('https://api.openai.com/v1/chat/completions', {}, body())
    assert first.summary()['unsettled_usd']=='0.372'
    restarted=CappedOpenAITransport(spec(), path, '0.5', transport=fail)
    with pytest.raises(SpendingLimitExceeded):
        restarted('https://api.openai.com/v1/chat/completions', {}, body())
    assert len(sent)==1 and 'PRIVATE' not in path.read_text()


@pytest.mark.parametrize('answer',[{}, {'usage':{'prompt_tokens':-1,'completion_tokens':1}},
                                  {'usage':{'prompt_tokens':100,'completion_tokens':16001}},
                                  {'usage':{'prompt_tokens':100,'completion_tokens':1,
                                            'prompt_tokens_details':{'cached_tokens':101}}}])
def test_unusable_usage_cannot_release_reservation(tmp_path, answer):
    client=CappedOpenAITransport(spec(), tmp_path/'ledger.json', '5', transport=lambda *args:answer)
    with pytest.raises(ProviderError):
        client('https://api.openai.com/v1/chat/completions', {}, body())
    assert client.summary()['unsettled_usd']=='0.372'


def test_corrupt_or_changed_ledger_fails_closed(tmp_path):
    path=tmp_path/'ledger.json';path.write_text('{broken')
    client=CappedOpenAITransport(spec(),path,'5',transport=lambda *args:pytest.fail('HTTP sent'))
    with pytest.raises(ContractError):
        client('https://api.openai.com/v1/chat/completions',{},body())


@pytest.mark.parametrize('changes',[{'input_usd_per_mtok':'0'}, {'model':'different'},
                                     {'base_url':'https://different.invalid/v1'}, {'max_tokens':128001}])
def test_unpriced_or_unbounded_models_are_rejected(tmp_path, changes):
    with pytest.raises(ContractError):
        CappedOpenAITransport(spec(**changes),tmp_path/'ledger.json','5')


def test_separate_instances_share_one_locked_allowance(tmp_path):
    path=tmp_path/'ledger.json';sent=[]
    def fail(*args):
        sent.append(True)
        raise OSError('service unavailable')
    clients=[CappedOpenAITransport(spec(),path,'0.5',transport=fail) for _ in range(2)]
    def send(client):
        try:client('https://api.openai.com/v1/chat/completions',{},body())
        except (OSError, SpendingLimitExceeded):pass
    with ThreadPoolExecutor(max_workers=2) as pool:
        list(pool.map(send,clients))
    assert len(sent)==1
    assert clients[0].summary()['unsettled_usd']=='0.372'


def test_authorization_is_required_and_dataset_scoped(tmp_path):
    from itemizer.paid import authorized_transport
    with pytest.raises(ContractError):
        authorized_transport(tmp_path,spec(),'5','dataset-a')
    folder=tmp_path/'data/evaluation';folder.mkdir(parents=True)
    path=folder/'openai_spending_authorization.json'
    path.write_text(json.dumps({'status':'user_authorized','limit_usd':'5','dataset_sha256':'dataset-b'}))
    with pytest.raises(ContractError):
        authorized_transport(tmp_path,spec(),'5','dataset-a')
    path.write_text(json.dumps({'status':'user_authorized','limit_usd':'5','dataset_sha256':'dataset-a'}))
    paid=authorized_transport(tmp_path,spec(),'5','dataset-a')
    assert paid.path==folder/'openai_spending.json'
    with pytest.raises(ContractError):
        authorized_transport(tmp_path,spec(),'5.01','dataset-a')


def test_existing_ledger_cap_cannot_be_reset_by_new_instance(tmp_path):
    path=tmp_path/'ledger.json'
    first=CappedOpenAITransport(spec(),path,'0.5',transport=lambda *args:reply())
    first('https://api.openai.com/v1/chat/completions',{},body())
    with pytest.raises(ContractError):
        CappedOpenAITransport(spec(),path,'5').summary()


def test_direct_openai_factory_cannot_bypass_spending_guard(tmp_path,monkeypatch):
    from itemizer import providers
    monkeypatch.setattr(providers,'load_secret',lambda *args:'FAKE KEY')
    with pytest.raises(ContractError):
        providers.get_provider(spec(),project_root=tmp_path)
    with pytest.raises(ContractError):
        providers.get_provider(spec(),client=lambda *args:reply(),project_root=tmp_path)
    def valid(*args):
        return {**reply(),'choices':[{'finish_reason':'stop','message':{'content':'{}'}}]}
    paid=CappedOpenAITransport(spec(),tmp_path/'ledger.json','5',transport=valid)
    provider=providers.get_provider(spec(),client=paid,project_root=tmp_path)
    assert provider.complete('system','user',{}).text=='{}'
    assert paid.summary()['settled_usd']=='0.00012'


@pytest.mark.parametrize('mutation',[{'status':'unknown','accounted_usd':'0'},
                                     {'status':'reserved','accounted_usd':'0'},
                                     {'reservation_usd':'0','accounted_usd':'0'}])
def test_malformed_unsettled_cost_cannot_release_reserved_money(tmp_path,mutation):
    path=tmp_path/'ledger.json'
    def fail(*args):raise OSError('failed request')
    client=CappedOpenAITransport(spec(),path,'5',transport=fail)
    with pytest.raises(OSError):client('https://api.openai.com/v1/chat/completions',{},body())
    state=json.loads(path.read_text());state['calls'][0].update(mutation);path.write_text(json.dumps(state))
    with pytest.raises(ContractError):client.summary()


def test_processes_share_durable_reservations(tmp_path):
    import os
    import subprocess
    import sys
    path=tmp_path/'ledger.json'
    script='''
import json,sys
from pathlib import Path
from itemizer.paid import CappedOpenAITransport,SpendingLimitExceeded
from itemizer.providers import ModelSpec
spec=ModelSpec(**json.loads(sys.argv[2]))
def failed(*args):raise OSError('failed request')
client=CappedOpenAITransport(spec,Path(sys.argv[1]),'0.5',transport=failed)
try:client('https://api.openai.com/v1/chat/completions',{}, {'model':spec.model,'max_tokens':16000})
except (OSError,SpendingLimitExceeded):pass
'''
    env={**os.environ,'PYTHONPATH':str(__import__('pathlib').Path(__file__).resolve().parents[1]/'src')}
    children=[subprocess.Popen([sys.executable,'-c',script,str(path),spec().model_dump_json()],env=env,
                               stdout=subprocess.PIPE,stderr=subprocess.PIPE) for _ in range(2)]
    for child in children:
        out,err=child.communicate(timeout=15)
        assert child.returncode==0,err.decode()
    state=json.loads(path.read_text())
    assert len(state['calls'])==1 and state['calls'][0]['accounted_usd']=='0.372'
