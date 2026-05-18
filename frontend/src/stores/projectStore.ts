import { defineStore } from 'pinia'
import type {
  Calibration,
  CourtKeypointPair,
  Detection,
  FrameAsset,
  PlayerAliasListResponse,
  PlayerTrack,
  ProjectBundleResponse,
  ProjectedPlayerTrack,
  RunTrackingResponse,
  TrackReviewResponse,
  VideoAsset,
  VideoSourceRecord
} from '../api/client'

export type ProjectSource = 'upload' | 'youtube' | 'sample'

export interface ProjectRecord {
  id: string
  name: string
  source: ProjectSource
  description?: string | null
  youtubeUrl?: string
  videoAsset?: VideoAsset | null
  videoPreviewUrl?: string
  videoFileName?: string
  sourceGovernance?: VideoSourceRecord | null
  frames: FrameAsset[]
  calibration?: Calibration | null
  calibrationPairs: CourtKeypointPair[]
  detections: Detection[]
  tracks: PlayerTrack[]
  projectedTracks: ProjectedPlayerTrack[]
  trackingPipelineOutput?: RunTrackingResponse['pipeline_output'] | null
  trackingDebugMetadata?: RunTrackingResponse['debug_metadata'] | null
  trackingReview?: TrackReviewResponse | null
  playerAliases?: PlayerAliasListResponse | null
}

interface ProjectState {
  projects: ProjectRecord[]
  activeProjectId: string
}

function createEmptyProject(input: Omit<Partial<ProjectRecord>, 'frames' | 'calibrationPairs' | 'detections' | 'tracks' | 'projectedTracks'> & Pick<ProjectRecord, 'id' | 'name' | 'source'>): ProjectRecord {
  return {
    id: input.id,
    name: input.name,
    source: input.source,
    description: input.description,
    youtubeUrl: input.youtubeUrl,
    videoAsset: input.videoAsset ?? null,
    videoPreviewUrl: input.videoPreviewUrl,
    videoFileName: input.videoFileName,
    sourceGovernance: input.sourceGovernance ?? null,
    frames: [],
    calibration: null,
    calibrationPairs: [],
    detections: [],
    tracks: [],
    projectedTracks: [],
    trackingPipelineOutput: null,
    trackingDebugMetadata: null,
    trackingReview: null,
    playerAliases: null
  }
}

export const useProjectStore = defineStore('projectStore', {
  state: (): ProjectState => ({
    projects: [],
    activeProjectId: ''
  }),
  getters: {
    activeProject: (state) => state.projects.find((project) => project.id === state.activeProjectId),
    getProject: (state) => (projectId: string) => state.projects.find((project) => project.id === projectId)
  },
  actions: {
    addProject(project: Omit<Partial<ProjectRecord>, 'frames' | 'calibrationPairs' | 'detections' | 'tracks' | 'projectedTracks'> & Pick<ProjectRecord, 'id' | 'name' | 'source'>) {
      const existing = this.projects.find((item) => item.id === project.id)
      if (existing) {
        Object.assign(existing, project)
      } else {
        this.projects.push(createEmptyProject(project))
      }
      this.activeProjectId = project.id
    },
    setActiveProject(projectId: string) {
      this.activeProjectId = projectId
    },
    setVideoAsset(projectId: string, videoAsset: VideoAsset, preview?: { url?: string; fileName?: string }) {
      const project = this.getProject(projectId)
      if (!project) return
      project.videoAsset = videoAsset
      project.videoPreviewUrl = preview?.url ?? project.videoPreviewUrl
      project.videoFileName = preview?.fileName ?? videoAsset.filename ?? project.videoFileName
    },
    setSourceGovernance(projectId: string, sourceGovernance: VideoSourceRecord) {
      const project = this.getProject(projectId)
      if (project) project.sourceGovernance = sourceGovernance
    },
    setFrames(projectId: string, frames: FrameAsset[]) {
      const project = this.getProject(projectId)
      if (project) project.frames = frames
    },
    setCalibrationPairs(projectId: string, pairs: CourtKeypointPair[]) {
      const project = this.getProject(projectId)
      if (project) project.calibrationPairs = pairs
    },
    setCalibration(projectId: string, calibration: Calibration) {
      const project = this.getProject(projectId)
      if (!project) return
      project.calibration = calibration
      project.calibrationPairs = calibration.keypoint_pairs
    },
    setTracks(
      projectId: string,
      payload: {
        detections?: Detection[]
        tracks?: PlayerTrack[]
        projectedTracks?: ProjectedPlayerTrack[]
        pipelineOutput?: RunTrackingResponse['pipeline_output'] | null
        debugMetadata?: RunTrackingResponse['debug_metadata'] | null
      }
    ) {
      const project = this.getProject(projectId)
      if (!project) return
      project.detections = payload.detections ?? project.detections
      project.tracks = payload.tracks ?? project.tracks
      project.projectedTracks = payload.projectedTracks ?? project.projectedTracks
      project.trackingPipelineOutput = payload.pipelineOutput ?? project.trackingPipelineOutput
      project.trackingDebugMetadata = payload.debugMetadata ?? project.trackingDebugMetadata
    },
    setPlayerAliases(projectId: string, playerAliases: PlayerAliasListResponse | null) {
      const project = this.getProject(projectId)
      if (project) project.playerAliases = playerAliases
    },
    hydrateProjectFromBundle(bundle: ProjectBundleResponse) {
      const projectId = bundle.project.project_id
      const existing = this.getProject(projectId)
      const source = bundle.project.metadata?.is_sample_data ? 'sample' : (bundle.video?.source_type ?? existing?.source ?? 'upload')
      const project = existing ?? createEmptyProject({ id: projectId, name: bundle.project.name, source })

      project.id = projectId
      project.name = bundle.project.name
      project.source = source
      project.description = bundle.project.description
      project.videoAsset = bundle.video
      project.sourceGovernance = bundle.source ?? null
      project.videoFileName = bundle.video?.filename ?? project.videoFileName
      project.frames = bundle.frames?.frames ?? []
      project.calibration = bundle.calibration
      project.calibrationPairs = bundle.calibration?.keypoint_pairs ?? []
      project.detections = bundle.tracking?.detections ?? []
      project.tracks = bundle.tracking?.tracks ?? []
      project.projectedTracks = bundle.projected_tracks?.projected_tracks ?? []
      project.trackingPipelineOutput = bundle.tracking?.pipeline_output ?? null
      project.trackingDebugMetadata = bundle.tracking?.debug_metadata ?? null
      project.trackingReview = bundle.tracking_review ?? null
      project.playerAliases = bundle.player_aliases

      if (!existing) {
        this.projects.push(project)
      }
      this.activeProjectId = projectId
    }
  }
})
