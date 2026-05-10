const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? '/api'

export interface ApiErrorResponse {
  code: string
  message: string
  details: Record<string, unknown>
  debug_hint?: string | null
}

export class ApiClientError extends Error {
  code: string
  details: Record<string, unknown>
  debug_hint?: string | null
  status: number

  constructor(status: number, payload: ApiErrorResponse) {
    super(payload.message)
    this.name = 'ApiClientError'
    this.status = status
    this.code = payload.code
    this.details = payload.details
    this.debug_hint = payload.debug_hint
  }
}

export function isApiClientError(error: unknown): error is ApiClientError {
  return error instanceof ApiClientError
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

export interface ProjectBundleResponse {
  project: Project
  video: VideoAsset | null
  frames: ExtractFramesResponse | null
  calibration: Calibration | null
  tracking: RunTrackingResponse | null
  projected_tracks: ProjectTracksResponse | null
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

export type DecisionActionType = 'PASS' | 'DRIVE' | 'SHOT' | 'RESET' | 'HOLD'

export interface DecisionArrowPoint {
  x: number
  y: number
}

export interface DecisionQuizOption {
  option_id: string
  label: string
  action_type: DecisionActionType
  start: DecisionArrowPoint
  end: DecisionArrowPoint
  expected_value?: number | null
  is_correct: boolean
  explanation: string
}

export interface QuizPrompt {
  project_id: string
  prompt_id: string
  question: string
  frame_id: string
  frame_index: number
  timestamp_seconds: number
  image_url?: string | null
  image_path?: string | null
  options: DecisionQuizOption[]
  explanation: string
  created_at: string
  updated_at: string
}

export interface CreateQuizPromptRequest {
  question: string
  frame_id: string
  frame_index: number
  timestamp_seconds: number
  image_url?: string | null
  image_path?: string | null
  options: DecisionQuizOption[]
  explanation: string
}

export interface QuizAttemptRequest {
  selected_option_id: string
}

export interface QuizAttemptResponse {
  prompt_id: string
  selected_option_id: string
  correct_option_id: string
  is_correct: boolean
  selected_expected_value?: number | null
  correct_expected_value?: number | null
  opportunity_cost?: number | null
  selected_explanation: string
  correct_explanation: string
  summary_explanation: string
}

export function normalizeApiErrorPayload(status: number, payload?: Partial<ApiErrorResponse> | null): ApiErrorResponse {
  return {
    code: payload?.code ?? 'HTTP_ERROR',
    message: payload?.message ?? `API request failed with status ${status}`,
    details: payload?.details ?? {},
    debug_hint: payload?.debug_hint ?? null
  }
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
    const normalizedPayload = normalizeApiErrorPayload(response.status, payload)
    throw new ApiClientError(response.status, normalizedPayload)
  }
  return (await response.json()) as T
}

export const apiClient = {
  listProjects: () => request<ListProjectsResponse>('/projects'),
  getProjectBundle: (projectId: string) => request<ProjectBundleResponse>(`/projects/${projectId}/bundle`),
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
  getTracks: (projectId: string) => request<ProjectTracksResponse>(`/projects/${projectId}/tracks`),
  listQuizPrompts: (projectId: string) => request<QuizPrompt[]>(`/projects/${projectId}/quiz-prompts`),
  createQuizPrompt: (projectId: string, payload: CreateQuizPromptRequest) =>
    request<QuizPrompt>(`/projects/${projectId}/quiz-prompts`, {
      method: 'POST',
      body: JSON.stringify(payload)
    }),
  getQuizPrompt: (projectId: string, promptId: string) => request<QuizPrompt>(`/projects/${projectId}/quiz-prompts/${promptId}`),
  submitQuizAttempt: (projectId: string, promptId: string, payload: QuizAttemptRequest) =>
    request<QuizAttemptResponse>(`/projects/${projectId}/quiz-prompts/${promptId}/attempts`, {
      method: 'POST',
      body: JSON.stringify(payload)
    })
}
