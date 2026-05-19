import json
from pathlib import Path

from fastapi.testclient import TestClient


def _write_json(path: Path, payload) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload), encoding='utf-8')


def test_player_home_empty_state(client: TestClient) -> None:
    response = client.get('/api/player-home?player_key=P1')
    assert response.status_code == 200
    payload = response.json()
    assert payload['today_focus'] == 'No player summary yet'
    assert payload['warnings']


def test_player_home_with_sample_data_and_simple_warning(client: TestClient, tmp_path: Path) -> None:
    _write_json(tmp_path / 'datasets' / 'player_value' / 'player_value_summary.json', {
        'summaries': [{
            'project_id': 'p', 'player_key': 'P1', 'display_name': 'Player One', 'team_side': 'HOME', 'role_hint': 'guard', 'track_ids': [],
            'decision_event_count': 2, 'avg_raw_decision_score': 0.4, 'avg_role_adjusted_score': 0.4, 'correct_rate': 0.4, 'timeout_rate': 0.0,
            'recognition_reliability_score': 0.4, 'consistency_score': 0.4, 'improvement_score': 0.4, 'participation_score': 0.4,
            'player_value_score': 0.5, 'confidence': 0.5, 'warnings': [], 'trace': {}
        }], 'warnings': []
    })
    _write_json(tmp_path / 'datasets' / 'player_value' / 'player_value_trends.json', {'trends': [{'project_id': 'p', 'player_key': 'P1', 'points': [
        {'build_id': 'b1', 'generated_at': '2026-01-01T00:00:00Z', 'project_id': 'p', 'player_key': 'P1', 'player_value_score': 0.4, 'confidence': 0.4, 'decision_event_count': 1, 'player_value_formula_version': 'v1', 'dataset_fingerprint': 'a'},
        {'build_id': 'b2', 'generated_at': '2026-01-02T00:00:00Z', 'project_id': 'p', 'player_key': 'P1', 'player_value_score': 0.5, 'confidence': 0.5, 'decision_event_count': 2, 'player_value_formula_version': 'v1', 'dataset_fingerprint': 'b'}
    ]}]})
    _write_json(tmp_path / 'drills' / 'latest_recommendations.json', {'recommendations': [{'player_key': 'P1', 'title': 'Closeout Drill', 'reason': 'Recover faster'}]})
    _write_json(tmp_path / 'practice_executions' / 'index.json', {'executions': [{'execution_id': 'e1', 'plan_id': 'pl', 'plan_title': 'Plan A', 'created_at': '2026-01-01T00:00:00Z', 'updated_at': '2026-01-01T00:00:00Z', 'planned_duration_minutes': 45, 'completion_rate': 0.8, 'skipped_count': 0, 'modified_count': 0, 'json_path': 'x.json', 'player_keys': ['P1']}]})

    response = client.get('/api/player-home?player_key=P1')
    assert response.status_code == 200
    payload = response.json()
    assert payload['display_name'] == 'Player One'
    assert payload['trend_direction'] == 'up'
    assert payload['recommended_drill'] == 'Closeout Drill'
    assert 'fully trusted' in ' '.join(payload['warnings'])
