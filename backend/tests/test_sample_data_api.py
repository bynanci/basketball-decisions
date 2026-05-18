from app.models import SAMPLE_PROJECT_ID, SAMPLE_PROJECT_NAME


def test_sample_data_seed_status_bundle_and_delete(client):
    initial = client.get('/api/sample-data/status')
    assert initial.status_code == 200
    assert initial.json()['installed'] is False
    assert initial.json()['can_seed'] is True

    seeded = client.post('/api/sample-data/seed')
    assert seeded.status_code == 200
    payload = seeded.json()
    assert payload['changed'] is True
    assert payload['installed'] is True
    assert payload['project_id'] == SAMPLE_PROJECT_ID
    assert payload['project_name'] == SAMPLE_PROJECT_NAME
    assert any(link['href'] == f'/projects/{SAMPLE_PROJECT_ID}' for link in payload['quick_links'])

    projects = client.get('/api/projects').json()['projects']
    assert any(project['id'] == SAMPLE_PROJECT_ID and project['name'] == SAMPLE_PROJECT_NAME for project in projects)

    bundle = client.get(f'/api/projects/{SAMPLE_PROJECT_ID}/bundle')
    assert bundle.status_code == 200
    bundle_payload = bundle.json()
    assert bundle_payload['project']['metadata']['is_sample_data'] is True
    assert bundle_payload['source']['usage_scope'] == 'DEMO_ONLY'
    assert len(bundle_payload['frames']['frames']) == 3
    assert len(bundle_payload['tracking']['tracks']) == 3
    assert len(bundle_payload['projected_tracks']['projected_tracks']) == 3
    assert bundle_payload['tracking_review']['review_patch']['track_id_aliases']['track-ball-handler'] == 'player-sample-guard'
    assert len(bundle_payload['player_aliases']['aliases']) == 3

    prompts = client.get(f'/api/projects/{SAMPLE_PROJECT_ID}/quiz-prompts')
    assert prompts.status_code == 200
    assert prompts.json()[0]['prompt_id'] == 'sample-pnr-prompt-1'

    reports = client.get('/api/reports/coach')
    assert reports.status_code == 200
    assert reports.json()['reports'][0]['report_id'] == 'sample-pnr-report'
    assert client.get('/api/reports/coach/sample-pnr-report').status_code == 200

    workflows = client.get('/api/workflows')
    assert workflows.status_code == 200
    assert workflows.json()['workflows'][0]['workflow_id'] == 'workflow-sample-pnr'
    assert client.get('/api/workflows/workflow-sample-pnr').status_code == 200

    review_items = client.get('/api/review-queue')
    assert review_items.status_code == 200
    assert review_items.json()[0]['item_id'] == 'sample-review-pnr-tag'

    player_value = client.get('/api/local-lab/player-value')
    assert player_value.status_code == 200
    assert player_value.json()['summaries'][0]['player_key'] == 'player-sample-guard'

    player_value_builds = client.get('/api/local-lab/player-value/builds')
    assert player_value_builds.status_code == 200
    assert player_value_builds.json()['builds'][0]['build_id'] == 'sample-pnr-build'

    evidence = client.get(f'/api/local-lab/player-value/{SAMPLE_PROJECT_ID}/player-sample-guard/evidence')
    assert evidence.status_code == 200
    assert evidence.json()['events'][0]['attempt_id'] == 'sample-attempt-1'

    deleted = client.delete('/api/sample-data')
    assert deleted.status_code == 200
    assert deleted.json()['changed'] is True
    assert deleted.json()['installed'] is False
    assert client.get(f'/api/projects/{SAMPLE_PROJECT_ID}/bundle').status_code == 404


def test_sample_data_seed_does_not_overwrite_non_sample_project(client):
    # Create a normal project at the deterministic sample path to simulate user data.
    from app.services import sample_data_service

    project_dir = sample_data_service.DATA_DIR / SAMPLE_PROJECT_ID
    project_dir.mkdir(parents=True)
    (project_dir / 'project.json').write_text(
        '{"schema_version":"1.0","project_id":"sample-court-iq-pnr","created_at":"2026-01-01T00:00:00Z","updated_at":"2026-01-01T00:00:00Z","name":"User Project","metadata":{},"original_input":{},"pipeline_output":{},"debug_metadata":{}}',
        encoding='utf-8',
    )

    response = client.post('/api/sample-data/seed')
    assert response.status_code == 409
    assert response.json()['code'] == 'SAMPLE_PROJECT_ID_IN_USE'
