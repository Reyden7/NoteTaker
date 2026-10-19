"""Cache identity and budgets with an explicitly fake subprocess fixture."""
import json
import pytest
from notetaker.engines.direct_runtime import DirectRuntime
from notetaker.engines.hierarchical_summary import object_schema


def test_native_adapter_distinguishes_fresh_and_cached_results_and_model_changes(tmp_path, monkeypatch):
    from notetaker.engines import direct_runtime as module
    binary, model = tmp_path/'llama.exe', tmp_path/'Instruct-2507.gguf'
    binary.write_bytes(b'fixture runtime not executable')
    model.write_bytes(b'fixture model not executable')
    work = tmp_path/'work'
    work.mkdir()
    request = {'binary': str(binary), 'model': str(model), 'workspace': str(work)}
    processes = []
    class FixtureProcess:
        returncode = 0
        def __init__(self, command, **kwargs):
            processes.append(command)
        def communicate(self, **kwargs):
            return '{"answer":"fixture"}', 'fixture only'
    monkeypatch.setattr(module.subprocess, 'Popen', FixtureProcess)
    monkeypatch.setattr(module, 'process_cpu', lambda p: {'user_seconds': .1, 'kernel_seconds': 0})
    schema = object_schema({'answer': {'type': 'string'}})
    first = DirectRuntime(request)
    assert first.call('context-000', 'Instruction', {'text': 'Texte'}, schema) == {'answer': 'fixture'}
    assert len(processes) == 1 and first.profile[0]['cache_hit'] is False
    assert first.identity['arguments'][first.identity['arguments'].index('--temp')+1] == '0.7'
    assert '--offline' in processes[0] and processes[0][processes[0].index('-ngl')+1] == '0'
    with pytest.raises(ValueError, match='NOT_EMPTY'):
        DirectRuntime(request)
    resumed = DirectRuntime({**request, 'cache_mode': 'resume'})
    resumed.call('context-000', 'Instruction', {'text': 'Texte'}, schema)
    assert len(processes) == 1 and resumed.profile[0]['cache_hit'] is True
    (work/'context-000.result.json').write_text('{"answer":"tampered fixture"}', encoding='utf-8')
    integrity = DirectRuntime({**request, 'cache_mode': 'resume'})
    assert integrity.call('context-000', 'Instruction', {'text': 'Texte'}, schema) == {'answer': 'fixture'}
    assert len(processes) == 2 and not integrity.profile[0]['cache_hit']
    model.write_bytes(b'different fixture weights')
    changed = DirectRuntime({**request, 'cache_mode': 'resume'})
    changed.call('context-000', 'Instruction', {'text': 'Texte'}, schema)
    assert len(processes) == 3
    with pytest.raises(ValueError, match='BUDGET'):
        changed.call('oversize', 'Instruction', {'text': 'x'*27000}, schema)
    assert len(processes) == 3


def test_timeout_preserves_partial_native_output_and_cpu_profile(tmp_path, monkeypatch):
    from notetaker.engines import direct_runtime as module
    binary, model = tmp_path/'llama.exe', tmp_path/'Instruct-2507.gguf'
    binary.write_bytes(b'non executable fixture')
    model.write_bytes(b'non executable fixture')
    killed = []
    class TimedOut:
        returncode = 1
        def __init__(self, *args, **kwargs): pass
        def communicate(self, **kwargs):
            if kwargs:
                raise module.subprocess.TimeoutExpired('fixture', kwargs['timeout'])
            return '{"incomplete":', 'partial diagnostic fixture'
        def kill(self): killed.append(True)
    monkeypatch.setattr(module.subprocess, 'Popen', TimedOut)
    monkeypatch.setattr(module, 'process_cpu', lambda p: {'user_seconds': 1., 'kernel_seconds': .1})
    runtime = DirectRuntime({'binary': str(binary), 'model': str(model), 'workspace': str(tmp_path)})
    with pytest.raises(TimeoutError, match='DIRECT_MODEL_TIMEOUT'):
        runtime.call('context-000', 'Instruction', {}, object_schema({}))
    assert killed == [True]
    assert (tmp_path/'context-000.partial.raw.txt').read_text(encoding='utf-8') == '{"incomplete":'
    assert (tmp_path/'context-000.partial.stderr.txt').read_text(encoding='utf-8') == 'partial diagnostic fixture'
    assert not (tmp_path/'context-000.identity.json').exists()
    profile = json.loads((tmp_path/'direct-profile.json').read_text(encoding='utf-8'))
    assert profile['fresh_calls'] == 1 and profile['cached_calls'] == 0
    assert profile['calls'][0]['failure_type'] == 'TimeoutExpired'
