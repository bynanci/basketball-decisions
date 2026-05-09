import { defineStore } from 'pinia'
import type {
  Calibration,
  CourtKeypointPair,
  Detection,
  FrameAsset,
  PlayerTrack,
  ProjectedPlayerTrack,
  VideoAsset
} from '../api/client'

export type ProjectSource = 'upload' | 'youtube'

export interface ProjectRecord {
  id: string
  name: string
  source: ProjectSource
  description?: string | null
  youtubeUrl?: string
  videoAsset?: VideoAsset | null
  videoPreviewUrl?: string
  videoFileName?: string
  frames: FrameAsset[]
  calibration?: Calibration | null
  calibrationPairs: CourtKeypointPair[]
  detections: Detection[]
  tracks: PlayerTrack[]
  projectedTracks: ProjectedPlayerTrack[]
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
    frames: [],
    calibration: null,
    calibrationPairs: [],
    detections: [],
    tracks: [],
    projectedTracks: []
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
    setTracks(projectId: string, payload: { detections?: Detection[]; tracks?: PlayerTrack[]; projectedTracks?: ProjectedPlayerTrack[] }) {
      const project = this.getProject(projectId)
      if (!project) return
      project.detections = payload.detections ?? project.detections
      project.tracks = payload.tracks ?? project.tracks
      project.projectedTracks = payload.projectedTracks ?? project.projectedTracks
    }
  }
})
