// @vitest-environment happy-dom
import { mount, type VueWrapper } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { nextTick } from 'vue'
import App from '../App.vue'
import { router } from '../router'

const SAMPLE_PROJECT_ID = 'sample-court-iq-pnr'
const GENERATED_AT = '2026-01-01T00:00:00.000Z'

function jsonResponse(payload: unknown, status = 200) {
  return new Response(JSON.stringify(payload), {
    status,
    headers: { 'Content-Type': 'application/json' }
  })
}

function sampleProject() {
  return {
    schema_version: '1.0',
    project_id: SAMPLE_PROJECT_ID,
    created_at: GENERATED_AT,
    updated_at: GENERATED_AT,
    name: 'Court IQ Sample: Pick-and-Roll Reads',
    description: 'Deterministic metadata-only S1 smoke sample.',
    metadata: { is_sample_data: true },
    original_input: {},
    pipeline_output: {},
    debug_metadata: {}
  }
}

function sampleBundle() {
  return {
    project: sampleProject(),
    video: null,
    source: {
      project_id: SAMPLE_PROJECT_ID,
      source_type: 'DATASET',
      uri: 'synthetic://sample-court-iq-pnr/frame.svg',
      license_type: 'PUBLIC_DOMAIN',
      usage_scope: 'DEMO_ONLY',
      rights_confirmed: true,
      allowed_for_training: false,
      attribution: 'Synthetic test fixture',
      notes: 'No real video, external network, YouTube, copyrighted media, or model training.',
      created_at: GENERATED_AT,
      updated_at: GENERATED_AT
    },
    frames: { project_id: SAMPLE_PROJECT_ID, frames: [] },
    calibration: null,
    tracking: null,
    projected_tracks: null,
    tracking_review: null,
    player_aliases: { project_id: SAMPLE_PROJECT_ID, aliases: [] }
  }
}

function samplePlayerValue() {
  return {
    schema_version: '1.0',
    generated_at: GENERATED_AT,
    summaries: [
      {
        project_id: SAMPLE_PROJECT_ID,
        player_key: 'BALL_HANDLER',
        display_name: 'Sample Ball Handler',
        team_side: 'OFFENSE',
        player_value_score: 7.4,
        confidence: 0.82,
        decision_event_count: 3,
        components: [],
        trace: { decision_event_ids: ['sample-event-1'] },
        warnings: []
      }
    ],
    warnings: [],
    build_id: 'sample-build-1'
  }
}

function sampleDashboard() {
  return {
    schema_version: '1.0',
    generated_at: GENERATED_AT,
    metrics: [{ key: 'sample-ready', label: 'Sample artifacts', value: 1, detail: 'S1 sample seeded', severity: 'info' }],
    team_summary: {
      player_count: 1,
      average_player_value_score: 7.4,
      average_confidence: 0.82,
      total_decision_events: 3,
      trend_series_count: 1,
      practice_plan_count: 1,
      practice_execution_count: 1,
      coach_report_count: 1,
      notes: ['Deterministic smoke fixture']
    },
    player_summaries: [{
      project_id: SAMPLE_PROJECT_ID,
      player_key: 'BALL_HANDLER',
      display_name: 'Sample Ball Handler',
      team_side: 'OFFENSE',
      role_hint: 'Primary ball handler',
      player_value_score: 7.4,
      confidence: 0.82,
      decision_event_count: 3,
      trend_points: 2,
      latest_trend_delta: 0.4,
      warnings: []
    }],
    next_best_actions: [],
    dataset_health_summary: { available: true, recognition_sample_count: 1, recognition_label_count: 1, recognition_warning_count: 0, decision_sample_count: 1, decision_label_count: 1, decision_warning_count: 0, generated_at: GENERATED_AT },
    model_registry_summary: { available: true, active_version: 'baseline-sample', model_count: 1, latest_version: 'baseline-sample', updated_at: GENERATED_AT },
    practice_feedback_summary: { signal_count: 1, action_signal_count: 1, warning_signal_count: 0, latest_signal_at: GENERATED_AT, completion_rate_average: 1, skipped_count: 0, modified_count: 0 },
    review_queue_summary: { item_count: 1, open_count: 1, high_priority_count: 0, action_log_count: 0 },
    warnings: [],
    artifact_counts: { projects: 1 },
    artifact_status: { sample_seeded: true },
    raw_artifact_refs: {}
  }
}

function installFetchMock() {
  const calls: string[] = []
  vi.stubGlobal('fetch', vi.fn(async (input: RequestInfo | URL) => {
    const url = new URL(input.toString(), 'http://localhost')
    const path = url.pathname
    calls.push(path)

    if (path === '/api/sample-data/status') return jsonResponse({ installed: false, protected_existing_project: false, project_id: SAMPLE_PROJECT_ID, message: 'Sample data is not installed.', artifact_count: 0, quick_links: [] })
    if (path === '/api/sample-data/seed') return jsonResponse({ installed: true, protected_existing_project: false, project_id: SAMPLE_PROJECT_ID, message: 'Seeded deterministic S1 sample data.', artifact_count: 12, quick_links: [{ label: 'Development Dashboard', href: '/development-dashboard' }] })
    if (path === `/api/projects/${SAMPLE_PROJECT_ID}/bundle`) return jsonResponse(sampleBundle())
    if (path === `/api/projects/${SAMPLE_PROJECT_ID}/quiz-prompts`) return jsonResponse([])
    if (path === '/api/local-lab/decision-diagnostics') return jsonResponse({ schema_version: '1.0', generated_at: GENERATED_AT, prompt_diagnostics: [], warnings: [] })
    if (path === '/api/development-dashboard') return jsonResponse(sampleDashboard())
    if (path === '/api/local-lab/player-value') return jsonResponse(samplePlayerValue())
    if (path === '/api/local-lab/player-value/trends') return jsonResponse({ schema_version: '1.0', generated_at: GENERATED_AT, trends: [{ project_id: SAMPLE_PROJECT_ID, player_key: 'BALL_HANDLER', display_name: 'Sample Ball Handler', points: [{ build_id: 'sample-build-1', generated_at: GENERATED_AT, player_value_score: 7.4, confidence: 0.82 }], warnings: [] }], warnings: [] })
    if (path === '/api/drills/catalog') return jsonResponse({ drills: [{ drill_id: 'sample-pnr-read', title: 'Sample PnR Read', description: 'Synthetic drill fixture.', role: 'GUARD', situation: 'PICK_AND_ROLL', coaching_cues: [], success_metrics: [] }] })
    if (path === '/api/drills/recommendations/latest') return jsonResponse({ schema_version: '1.0', generated_at: GENERATED_AT, recommendations: [], feedback_signal_count: 0, adjustment_summary: [], warnings: [] })
    if (path === '/api/drills/feedback-signals') return jsonResponse({ signals: [] })
    if (path === '/api/practice-plans') return jsonResponse({ plans: [] })
    if (path === '/api/practice-executions') return jsonResponse({ executions: [] })
    if (path === '/api/practice-executions/signals') return jsonResponse({ signals: [] })
    if (path === '/api/review-queue') return jsonResponse([])
    if (path === '/api/review-queue/actions') return jsonResponse([])
    if (path === '/api/workflows') return jsonResponse({ workflows: [] })

    throw new Error(`Unexpected network call during S4 smoke test: ${path}`)
  }))
  return calls
}

async function flushUi() {
  await nextTick()
  await new Promise((resolve) => setTimeout(resolve, 0))
  await nextTick()
}

async function clickAndWait(wrapper: VueWrapper, selector: string) {
  const element = wrapper.get(selector)
  await element.trigger('click')
  await flushUi()
}

describe('S4 deterministic end-to-end smoke test', () => {
  let fetchCalls: string[]

  beforeEach(async () => {
    window.history.pushState({}, '', '/')
    setActivePinia(createPinia())
    fetchCalls = installFetchMock()
    await router.push('/')
    await router.isReady()
  })

  afterEach(() => {
    vi.unstubAllGlobals()
  })

  it('seeds the S1 sample and opens the core S4 product surfaces without external media or training calls', async () => {
    const wrapper = mount(App, { global: { plugins: [createPinia(), router] } })
    await flushUi()

    await clickAndWait(wrapper, '[data-testid="seed-sample-data"]')
    expect(fetchCalls).toContain('/api/sample-data/seed')
    expect(fetchCalls).toContain(`/api/projects/${SAMPLE_PROJECT_ID}/bundle`)

    await clickAndWait(wrapper, '[data-testid="nav-development-dashboard"]')
    expect(wrapper.get('[data-testid="development-dashboard-page"]').text()).toContain('Development Dashboard Command Center')

    await clickAndWait(wrapper, '[data-testid="nav-player-value"]')
    expect(wrapper.get('[data-testid="player-value-page"]').text()).toContain('Player Value v1')

    await clickAndWait(wrapper, '[data-testid="player-value-trends-link"]')
    expect(wrapper.get('[data-testid="player-value-trends-page"]').text()).toContain('Player Value Trends')

    await clickAndWait(wrapper, '[data-testid="nav-drills"]')
    expect(wrapper.get('[data-testid="drills-page"]').text()).toContain('Drill Recommendations')

    await clickAndWait(wrapper, '[data-testid="nav-practice-plans"]')
    expect(wrapper.get('[data-testid="practice-plans-page"]').text()).toContain('Practice Plans')

    await clickAndWait(wrapper, '[data-testid="nav-practice-executions"]')
    expect(wrapper.get('[data-testid="practice-executions-page"]').text()).toContain('Practice Executions')

    await clickAndWait(wrapper, '[data-testid="nav-review-queue"]')
    expect(wrapper.get('[data-testid="review-queue-page"]').text()).toContain('Review Queue')

    await clickAndWait(wrapper, '[data-testid="nav-workflows"]')
    expect(wrapper.get('[data-testid="workflows-page"]').text()).toContain('Guided Workflows')

    expect(fetchCalls.some((path) => path.includes('youtube') || path.includes('video/source') || path.includes('train'))).toBe(false)
  })
})
