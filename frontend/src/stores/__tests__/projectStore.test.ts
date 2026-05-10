import { beforeEach, describe, expect, it } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'
import { useProjectStore } from '../projectStore'
import type { ProjectBundleResponse } from '../../api/client'

function bundle(overrides: Partial<ProjectBundleResponse> = {}): ProjectBundleResponse {
  return {
    project: {
      schema_version: '1.0',
      project_id: 'project-1',
      created_at: '2026-01-01T00:00:00Z',
      updated_at: '2026-01-01T00:00:00Z',
      name: 'Hydrated Project',
      description: 'Recovered from backend',
      metadata: {},
      original_input: {},
      pipeline_output: {},
      debug_metadata: {}
    },
    video: {
      project_id: 'project-1',
      asset_id: 'video-1',
      source_type: 'upload',
      uri: '/backend/local/file.mp4',
      filename: 'file.mp4'
    },
    frames: {
      schema_version: '1.0',
      project_id: 'project-1',
      created_at: '2026-01-01T00:00:00Z',
      updated_at: '2026-01-01T00:00:00Z',
      original_input: {},
      pipeline_output: {},
      debug_metadata: {},
      request: { project_id: 'project-1', video_asset_id: 'video-1' },
      frames: [{ frame_id: 'frame-1', frame_index: 7, timestamp_seconds: 2.5, image_path: '/tmp/frame.jpg', metadata: {} }]
    },
    calibration: {
      project_id: 'project-1',
      frame_id: 'frame-1',
      homography: [[1, 0, 0], [0, 1, 0], [0, 0, 1]],
      keypoint_pairs: [
        { keypoint_id: 'corner', image_point: { x: 10, y: 20 }, court_point: { x: 0, y: 0, label: 'corner' } }
      ]
    },
    tracking: {
      project_id: 'project-1',
      pipeline_output: { detector_mode: 'hydrated-detector' },
      debug_metadata: { detector: { mode: 'hydrated-debug-detector' } },
      detections: [
        {
          detection_id: 'detection-1',
          frame_id: 'frame-1',
          frame_index: 7,
          box: { x: 1, y: 2, width: 3, height: 4 },
          confidence: 0.9,
          class_name: 'player',
          track_id: 'track-1',
          metadata: {}
        }
      ],
      tracks: [{ track_id: 'track-1', points: [], metadata: {} }]
    },
    projected_tracks: {
      project_id: 'project-1',
      tracking: null,
      projected_tracks: [{ track_id: 'track-1', points: [], metadata: {} }],
      storage_paths: {}
    },
    ...overrides
  }
}

describe('projectStore.hydrateProjectFromBundle', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
  })

  it('creates a project record from a backend bundle', () => {
    const store = useProjectStore()

    store.hydrateProjectFromBundle(bundle())

    const project = store.getProject('project-1')
    expect(project?.name).toBe('Hydrated Project')
    expect(project?.source).toBe('upload')
    expect(project?.videoAsset?.asset_id).toBe('video-1')
    expect(project?.frames).toHaveLength(1)
    expect(project?.calibrationPairs).toHaveLength(1)
    expect(project?.detections).toHaveLength(1)
    expect(project?.tracks).toHaveLength(1)
    expect(project?.projectedTracks).toHaveLength(1)
    expect(project?.trackingPipelineOutput?.detector_mode).toBe('hydrated-detector')
    expect(project?.trackingDebugMetadata?.detector).toEqual({ mode: 'hydrated-debug-detector' })
  })

  it('preserves an existing browser-only video preview URL', () => {
    const store = useProjectStore()
    store.addProject({ id: 'project-1', name: 'Local Project', source: 'upload', videoPreviewUrl: 'blob:local-preview' })

    store.hydrateProjectFromBundle(bundle())

    expect(store.getProject('project-1')?.videoPreviewUrl).toBe('blob:local-preview')
  })

  it('updates tracking metadata with run results', () => {
    const store = useProjectStore()
    store.addProject({ id: 'project-1', name: 'Local Project', source: 'upload' })

    store.setTracks('project-1', {
      pipelineOutput: { detector_mode: 'run-detector' },
      debugMetadata: { detector: { mode: 'run-debug-detector' } }
    })

    expect(store.getProject('project-1')?.trackingPipelineOutput?.detector_mode).toBe('run-detector')
    expect(store.getProject('project-1')?.trackingDebugMetadata?.detector).toEqual({ mode: 'run-debug-detector' })
  })

  it('clears existing tracking arrays and metadata when backend tracking artifacts are missing', () => {
    const store = useProjectStore()
    store.addProject({ id: 'project-1', name: 'Local Project', source: 'upload' })
    store.setTracks('project-1', {
      detections: [
        {
          detection_id: 'existing-detection',
          frame_id: 'frame-1',
          frame_index: 1,
          box: { x: 1, y: 2, width: 3, height: 4 },
          confidence: 0.8,
          class_name: 'player',
          metadata: {}
        }
      ],
      tracks: [{ track_id: 'existing-track', points: [], metadata: {} }],
      projectedTracks: [{ track_id: 'existing-projected-track', points: [], metadata: {} }],
      pipelineOutput: { detector_mode: 'existing-detector' },
      debugMetadata: { detector: { mode: 'existing-debug-detector' } }
    })

    store.hydrateProjectFromBundle(bundle({ tracking: null, projected_tracks: null }))

    expect(store.getProject('project-1')?.detections).toHaveLength(0)
    expect(store.getProject('project-1')?.tracks).toHaveLength(0)
    expect(store.getProject('project-1')?.projectedTracks).toHaveLength(0)
    expect(store.getProject('project-1')?.trackingPipelineOutput).toBeNull()
    expect(store.getProject('project-1')?.trackingDebugMetadata).toBeNull()
  })

})
