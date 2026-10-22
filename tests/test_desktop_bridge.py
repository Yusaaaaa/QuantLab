import json
from pathlib import Path
import pytest
from quantlab.desktop_bridge import dispatch, scoped


def test_file_scope_and_external_change(tmp_path):
    (tmp_path / 'strategies').mkdir()
    path = tmp_path / 'strategies/demo.py'
    path.write_text('original')
    doc = dispatch(tmp_path, {'action':'read','path':'strategies/demo.py'})
    path.write_text('external edit')
    with pytest.raises(ValueError, match='外部修改'):
        dispatch(tmp_path, {'action':'save','path':'strategies/demo.py','text':'editor edit','hash':doc['hash']})
    assert path.read_text() == 'external edit'
    with pytest.raises(ValueError):
        scoped(tmp_path, '../outside.py', ['strategies'], {'.py'})
    outside = tmp_path / 'private.py'
    outside.write_text('secret')
    (tmp_path / 'strategies/link.py').symlink_to(outside)
    with pytest.raises(ValueError):
        dispatch(tmp_path, {'action':'read','path':'strategies/link.py'})


def test_new_file_never_overwrites(tmp_path):
    request = {'action':'save','path':'factors/new_factor.py','text':'x = 1','hash':None}
    dispatch(tmp_path, request)
    with pytest.raises(ValueError):
        dispatch(tmp_path, {**request,'text':'x = 2'})
    assert (tmp_path / request['path']).read_text() == 'x = 1'


def test_prepare_freezes_sources_and_keeps_config(tmp_path):
    (tmp_path / 'strategies').mkdir()
    (tmp_path / 'factors').mkdir()
    strategy = tmp_path / 'strategies/s.py'
    factor = tmp_path / 'factors/f.py'
    strategy.write_text('strategy before')
    factor.write_text('factor before')
    config = {'strategy':{'path':'strategies/s.py','factor_paths':{'factors.f':'factors/f.py'}},'data':{'path':'data/raw/prices.csv'}}
    prepared = dispatch(tmp_path, {'action':'prepare','config':config})
    strategy.write_text('strategy after')
    factor.write_text('factor after')
    job = Path(prepared['directory'])
    frozen = json.loads((job / 'config.json').read_text())
    assert Path(frozen['strategy']['path']).read_text() == 'strategy before'
    assert Path(frozen['strategy']['factor_paths']['factors.f']).read_text() == 'factor before'
    assert frozen['report']['runs_dir'] == str(tmp_path / 'runs')
    assert json.loads((job / 'original.json').read_text())['strategy']['path'] == str(strategy)


def test_invalid_config_and_run_id_rejected(tmp_path):
    with pytest.raises(ValueError):
        dispatch(tmp_path, {'action':'prepare','config':{'strategy':{'path':'outside.py'}}})
    with pytest.raises(ValueError):
        dispatch(tmp_path, {'action':'run','id':'../other'})
    with pytest.raises(ValueError):
        dispatch(tmp_path, {'action':'report','id':'../private'})


def test_catalog_does_not_enumerate_external_directory_symlink(tmp_path):
    workspace = tmp_path / 'workspace'
    workspace.mkdir()
    outside = tmp_path / 'external'
    outside.mkdir()
    (outside / 'private.csv').write_text('not workspace data')
    (workspace / 'data').symlink_to(outside, target_is_directory=True)
    assert dispatch(workspace, {'action': 'catalog'})['data'] == []


def test_history_isolates_corrupt_run_and_failure_wins(tmp_path):
    runs = tmp_path / 'runs'
    for name in ['01-good', '02-broken', '03-failed']:
        run = runs / name
        run.mkdir(parents=True)
        (run / 'metadata.json').write_text(json.dumps({'status': 'complete'}))
        (run / 'summary.json').write_text(json.dumps({'final_equity': 123}))
    (runs / '02-broken' / 'summary.json').write_text('{broken json')
    (runs / '03-failed' / 'failure.json').write_text(json.dumps({'error': 'failed after write'}))
    result = dispatch(tmp_path, {'action': 'history'})
    assert [(x['id'], x['status']) for x in result] == [
        ('03-failed', 'failed'), ('02-broken', 'failed'), ('01-good', 'complete')]
    assert 'unreadable' in result[1]['error'].lower()
    assert result[2]['final_equity'] == 123


def test_history_rejects_external_run_directory(tmp_path):
    workspace = tmp_path / 'workspace'
    (workspace / 'runs').mkdir(parents=True)
    outside = tmp_path / 'external'
    outside.mkdir()
    (outside / 'summary.json').write_text(json.dumps({'final_equity': 'private'}))
    (outside / 'metadata.json').write_text(json.dumps({'status': 'complete'}))
    (workspace / 'runs' / 'link').symlink_to(outside, target_is_directory=True)
    result = dispatch(workspace, {'action': 'history'})
    assert result[0]['status'] == 'failed'
    assert 'final_equity' not in result[0]


def test_history_requires_complete_metadata(tmp_path):
    run = tmp_path / 'runs' / 'unfinished'
    run.mkdir(parents=True)
    (run / 'summary.json').write_text('{}')
    (run / 'metadata.json').write_text(json.dumps({'status': 'pending'}))
    assert dispatch(tmp_path, {'action': 'history'})[0]['status'] == 'failed'
