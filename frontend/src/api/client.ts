const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? '/api'

export interface ApiErrorResponse {
  code: string
  message: string
  details: Record<string, unknown>
  debug_hint?: string | null
}

export interface ProjectCreateRequest {
  name: string
  description?: string | null
  metadata?: Record<string, unknown>
}

export interface Project {
  schema_version: string
  project_id: string
  created_at: string
  updated_at: string
  name: string
  description?: string | null
  metadata: Record<string, unknown>
  original_input: Record<string, unknown>
  pipeline_output: Record<string, unknown>
  debug_metadata: Record<string, unknown>
}

export interface ProjectCreateResponse {
  project: Project
  storage_path: string
}

export interface ListProjectsResponse {
  projects: Array<{ id: string; name: string; description?: string | null }>
}

export type VideoSourceType = 'upload' | 'youtube'

export interface YouTubeVideoRequest {
  url: string
  rights_confirmed: boolean
}

export interface VideoAsset {
  schema_version?: string
  project_id: string
  created_at?: string
  updated_at?: string
  original_input?: Record<string, unknown>
  pipeline_output?: Record<string, unknown>
  debug_metadata?: Record<string, unknown>
  asset_id: string
  source_type: VideoSourceType
  uri?: string | null
  filename?: string | null
  content_type?: string | null
  duration_seconds?: number | null
  fps?: number | null
  frame_count?: number | null
  width?: number | null
  height?: number | null
}

export interface FrameAsset {
  frame_id: string
  frame_index: number
  timestamp_seconds: number
  image_path: string
  width?: number | null
  height?: number | null
  metadata: Record<string, unknown>
}

export interface ExtractFramesRequest {
  project_id: string
  video_asset_id: string
  target_fps?: number | null
  start_time_seconds?: number | null
  end_time_seconds?: number | null
  max_frames?: number | null
}

export interface ExtractFramesResponse {
  schema_version: string
  project_id: string
  created_at: string
  updated_at: string
  original_input: Record<string, unknown>
  pipeline_output: Record<string, unknown>
  debug_metadata: Record<string, unknown>
  request: ExtractFramesRequest
  frames: FrameAsset[]
}

export interface ImagePoint {
  x: number
  y: number
}

export interface CourtPoint {
  x: number
  y: number
  label?: string | null
}

export interface CourtKeypointPair {
  keypoint_id: string
  image_point: ImagePoint
  court_point: CourtPoint
  confidence?: number | null
}

export interface SaveCalibrationRequest {
  project_id: string
  frame_id?: string | null
  keypoint_pairs: CourtKeypointPair[]
  homography?: number[][] | null
  debug_metadata?: Record<string, unknown>
}

export interface Calibration {
  schema_version?: string
  project_id: string
  created_at?: string
  updated_at?: string
  original_input?: Record<string, unknown>
  pipeline_output?: Record<string, unknown>
  debug_metadata?: Record<string, unknown>
  frame_id?: string | null
  homography?: number[][] | null
  keypoint_pairs: CourtKeypointPair[]
  reprojection_error?: number | null
}

export interface SaveCalibrationResponse {
  calibration: Calibration
  storage_path: string
}

export interface DetectionBox {
  x: number
  y: number
  width: number
  height: number
}

export interface Detection {
  detection_id: string
  frame_id: string
  frame_index: number
  box: DetectionBox
  confidence: number
  class_name: string
  track_id?: string | null
  metadata: Record<string, unknown>
}

export interface TrackPoint {
  frame_id: string
  frame_index: number
  timestamp_seconds: number
  image_point_x: number
  image_point_y: number
  detection_id?: string | null
  confidence?: number | null
}

export interface PlayerTrack {
  track_id: string
  player_id?: string | null
  points: TrackPoint[]
  metadata: Record<string, unknown>
}

export interface RunTrackingRequest {
  project_id: string
  frame_ids?: string[] | null
  model_name?: string | null
  confidence_threshold?: number | null
  iou_threshold?: number | null
  max_players?: number | null
}

export interface RunTrackingResponse {
  schema_version?: string
  project_id: string
  created_at?: string
  updated_at?: string
  original_input?: Record<string, unknown>
  pipeline_output?: Record<string, unknown>
  debug_metadata?: Record<string, unknown>
  request?: RunTrackingRequest
  detections: Detection[]
  tracks: PlayerTrack[]
}

export interface ProjectedTrackPoint {
  frame_id: string
  frame_index: number
  timestamp_seconds: number
  court_x: number
  court_y: number
  source_image_point_x?: number | null
  source_image_point_y?: number | null
  confidence?: number | null
  metadata: Record<string, unknown>
}

export interface ProjectedPlayerTrack {
  track_id: string
  player_id?: string | null
  points: ProjectedTrackPoint[]
  metadata: Record<string, unknown>
}

export interface ProjectTracksResponse {
  project_id: string
  tracking?: RunTrackingResponse | null
  projected_tracks: ProjectedPlayerTrack[]
  storage_paths: Record<string, string>
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  const headers = new Headers(init.headers)
  const isFormData = init.body instanceof FormData
  if (!isFormData && init.body && !headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json')
  }

  const response = await fetch(`${API_BASE_URL}${path}`, { ...init, headers })
  if (!response.ok) {
    let payload: ApiErrorResponse | undefined
    try {
      payload = (await response.json()) as ApiErrorResponse
    } catch {
      payload = undefined
    }
    throw new Error(payload?.message ?? `API request failed with status ${response.status}`)
  }
  return (await response.json()) as T
}

export const apiClient = {
  listProjects: () => request<ListProjectsResponse>('/projects'),
  createProject: (payload: ProjectCreateRequest) =>
    request<ProjectCreateResponse>('/projects', { method: 'POST', body: JSON.stringify(payload) }),
  uploadVideo: (projectId: string, file: File) => {
    const formData = new FormData()
    formData.append('file', file)
    return request<VideoAsset>(`/projects/${projectId}/video/upload`, { method: 'POST', body: formData })
  },
  createYouTubeVideo: (projectId: string, payload: YouTubeVideoRequest) =>
    request<VideoAsset>(`/projects/${projectId}/video/youtube`, { method: 'POST', body: JSON.stringify(payload) }),
  extractFrames: (projectId: string, payload: ExtractFramesRequest) =>
    request<ExtractFramesResponse>(`/projects/${projectId}/frames/extract`, {
      method: 'POST',
      body: JSON.stringify(payload)
    }),
  frameImageUrl: (projectId: string, frameIndex: number) => `${API_BASE_URL}/projects/${projectId}/frames/${frameIndex}`,
  saveCalibration: (projectId: string, payload: SaveCalibrationRequest) =>
    request<SaveCalibrationResponse>(`/projects/${projectId}/calibration`, {
      method: 'POST',
      body: JSON.stringify(payload)
    }),
  runTracking: (projectId: string, payload: RunTrackingRequest) =>
    request<RunTrackingResponse>(`/projects/${projectId}/tracking/run`, {
      method: 'POST',
      body: JSON.stringify(payload)
    }),
  getTracks: (projectId: string) => request<ProjectTracksResponse>(`/projects/${projectId}/tracks`)
}
