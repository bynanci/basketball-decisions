import json
from pathlib import Path

from fastapi.testclient import TestClient


def _write_json(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding='utf-8')


def _seed_report(client: TestClient, tmp_path: Path) -> str:
    _write_json(tmp_path / 'datasets' / 'player_value' / 'player_value_summary.json', {'summaries':[{'project_id':'project-1','player_key':'player-1','display_name':'Alias','player_value_score':72,'confidence':0.81,'decision_event_count':3,'warnings':['keep warning']}], 'warnings':['keep warning']})
    _write_json(tmp_path / 'datasets' / 'player_value' / 'player_value_build_index.json', {'builds':[]})
    _write_json(tmp_path / 'datasets' / 'decision' / 'decision_diagnostics.json', {'global_summary': {'attempt_count': 3, 'correct_rate': 0.67, 'avg_role_adjusted_score': 72}})
    _write_json(tmp_path / 'decision_rules' / 'active_rule_set.json', {'rules':[]})
    (tmp_path / 'datasets' / 'player_value' / 'player_decision_events.jsonl').write_text(json.dumps({'project_id':'project-1','prompt_id':'prompt-1','attempt_id':'attempt-1'})+'\n', encoding='utf-8')
    _write_json(tmp_path / 'review_queue' / 'review_queue.json', [])
    _write_json(tmp_path / 'review_queue' / 'review_action_log.json', [])
    _write_json(tmp_path / 'reference_videos' / 'reference_videos.json', [])
    _write_json(tmp_path / 'source_registry.json', [])
    return client.post('/api/reports/coach', json={'title':'R'}).json()['report_id']


def test_mock_provider_and_persistence(client: TestClient, tmp_path: Path) -> None:
    report_id = _seed_report(client, tmp_path)
    response = client.post('/api/reports/coach/evidence-locked-summary', json={'report_id': report_id, 'provider': 'mock'})
    assert response.status_code == 200
    payload = response.json()
    assert payload['provider'] == 'mock'
    assert 'validation' in payload
    assert payload['source_report_json_path']
    fetched = client.get(f"/api/reports/coach/evidence-locked-summary/{payload['summary_id']}")
    assert fetched.status_code == 200


def test_unsupported_provider_returns_clear_error(client: TestClient, tmp_path: Path) -> None:
    report_id = _seed_report(client, tmp_path)
    response = client.post('/api/reports/coach/evidence-locked-summary', json={'report_id': report_id, 'provider': 'external'})
    assert response.status_code == 400
    assert response.json()['code'] == 'LLM_PROVIDER_UNSUPPORTED'


def test_original_report_not_overwritten(client: TestClient, tmp_path: Path) -> None:
    report_id = _seed_report(client, tmp_path)
    original = client.get(f'/api/reports/coach/{report_id}').json()['markdown']
    client.post('/api/reports/coach/evidence-locked-summary', json={'report_id': report_id, 'provider': 'mock'})
    latest = client.get(f'/api/reports/coach/{report_id}').json()['markdown']
    assert original == latest
