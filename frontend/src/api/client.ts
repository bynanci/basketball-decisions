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

export type SourceType = 'UPLOAD' | 'YOUTUBE' | 'URL' | 'DATASET' | 'MANUAL_IMPORT'
export type SourceLicenseType = 'OWNED' | 'PERMISSION_GRANTED' | 'PUBLIC_DOMAIN' | 'CREATIVE_COMMONS' | 'RESEARCH_DATASET' | 'YOUTUBE_REFERENCE_ONLY' | 'UNKNOWN'
export type UsageScope = 'TRAINING' | 'EVALUATION' | 'REFERENCE_ONLY' | 'DEMO_ONLY'
export type LeagueTag = 'NBA' | 'EUROLEAGUE' | 'NCAA' | 'LOCAL' | 'OTHER' | 'UNKNOWN'

export interface VideoSourceRecord {
  schema_version?: string
  project_id?: string | null
  created_at?: string
  updated_at?: string
  original_input?: Record<string, unknown>
  pipeline_output?: Record<string, unknown>
  debug_metadata?: Record<string, unknown>
  source_id: string
  name: string
  source_type: SourceType
  source_url?: string | null
  title?: string | null
  license_type: SourceLicenseType
  rights_confirmed: boolean
  allowed_for_training: boolean
  allowed_for_redistribution: boolean
  allowed_for_local_storage: boolean
  league_tag: LeagueTag
  usage_scope: UsageScope
  notes?: string | null
}

export interface ProjectBundleResponse {
  project: Project
  video?: VideoAsset | null
  source?: VideoSourceRecord | null
  frames?: ExtractFramesResponse | null
  calibration?: Calibration | null
  tracking?: RunTrackingResponse | null
  projected_tracks?: ProjectTracksResponse | null
  tracking_review?: TrackReviewResponse | null
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

export interface TrackReviewPatch {
  excluded_detection_ids: string[]
  excluded_track_ids: string[]
  track_id_aliases?: Record<string, string>
  notes?: string | null
}

export interface TrackReviewResponse {
  project_id: string
  tracking: RunTrackingResponse
  review_patch: TrackReviewPatch
  cleaned_tracking?: RunTrackingResponse | null
  cleaned_projected_tracks: ProjectedPlayerTrack[]
  storage_paths: Record<string, string>
}

export interface DetectionRecognitionFeatures {
  bbox_x: number
  bbox_y: number
  bbox_width: number
  bbox_height: number
  bbox_area: number
  bbox_aspect_ratio: number
  confidence: number
  frame_index: number
  has_track_id: boolean
  track_point_count?: number | null
  inside_projected_court?: boolean | null
}

export interface TrackRecognitionFeatures {
  point_count: number
  avg_confidence?: number | null
  min_confidence?: number | null
  max_confidence?: number | null
  avg_bbox_area?: number | null
  bbox_area_variance?: number | null
  avg_speed_image?: number | null
  max_jump_distance_image?: number | null
  frame_span: number
  gap_count: number
  projected_inside_court_ratio?: number | null
}

export interface DetectionRecognitionScore {
  detection_id: string
  track_id?: string | null
  false_positive_risk: number
  recommended_label: 'LOW' | 'MEDIUM' | 'HIGH' | string
  reasons: string[]
  features: DetectionRecognitionFeatures
}

export interface TrackRecognitionScore {
  track_id: string
  false_positive_risk: number
  recommended_label: 'LOW' | 'MEDIUM' | 'HIGH' | string
  reasons: string[]
  features: TrackRecognitionFeatures
}

export interface RecognitionScoreProjectResponse {
  project_id: string
  detection_scores: DetectionRecognitionScore[]
  track_scores: TrackRecognitionScore[]
  summary: {
    high_risk_detection_count: number
    high_risk_track_count: number
  }
}

export type DecisionActionType = 'PASS' | 'DRIVE' | 'SHOT' | 'RESET' | 'HOLD'
export type CourtRoleTarget =
  | 'BALL_HANDLER'
  | 'OFF_BALL_SHOOTER'
  | 'ROLLER'
  | 'SCREENER'
  | 'ON_BALL_DEFENDER'
  | 'HELP_DEFENDER'
  | 'LOW_MAN'
  | 'TRAILER'
  | 'WEAK_SIDE_WING'
export type SituationType =
  | 'PICK_AND_ROLL'
  | 'SHORT_ROLL'
  | 'SPOT_UP'
  | 'CLOSEOUT_ATTACK'
  | 'TRANSITION_3_ON_2'
  | 'LATE_CLOCK'
  | 'POST_DOUBLE'
  | 'DRIVE_AND_KICK'
  | 'HELP_ROTATION'
  | 'LOW_MAN_DECISION'
  | 'OFF_BALL_RELOCATION'
export type QuizPromptMode = 'STILL_FRAME' | 'VIDEO_FREEZE'
export type QuizQuestionMode = 'FREEZE_FRAME' | 'QUICK_DECISION' | 'ROLE_READ'
export type QuizScoringMode = 'EXPECTED_VALUE' | 'CORRECTNESS_ONLY'
export type QuizUserRole = 'COACH' | 'PLAYER' | 'ANALYST' | 'FAN'

export interface DecisionRoleFeedback {
  coach?: string | null
  player?: string | null
  analyst?: string | null
  fan?: string | null
}

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
  role_feedback?: DecisionRoleFeedback | null
}

export interface QuizPrompt {
  project_id: string
  prompt_id: string
  question: string
  court_role_target: CourtRoleTarget
  situation_type: SituationType
  user_role_targets: CourtRoleTarget[]
  role_instruction?: string | null
  frame_id: string
  frame_index: number
  timestamp_seconds: number
  image_url?: string | null
  image_path?: string | null
  video_asset_id?: string | null
  clip_start_seconds?: number | null
  freeze_frame_seconds?: number | null
  clip_end_seconds?: number | null
  mode: QuizPromptMode
  question_mode: QuizQuestionMode
  time_limit_ms?: number | null
  options: DecisionQuizOption[]
  explanation: string
  created_at: string
  updated_at: string
}

export interface CreateQuizPromptRequest {
  question: string
  court_role_target: CourtRoleTarget
  situation_type: SituationType
  user_role_targets?: CourtRoleTarget[]
  role_instruction?: string | null
  frame_id: string
  frame_index: number
  timestamp_seconds: number
  image_url?: string | null
  image_path?: string | null
  video_asset_id?: string | null
  clip_start_seconds?: number | null
  freeze_frame_seconds?: number | null
  clip_end_seconds?: number | null
  mode: QuizPromptMode
  question_mode: QuizQuestionMode
  time_limit_ms?: number | null
  options: DecisionQuizOption[]
  explanation: string
}

export interface QuizAttemptRequest {
  selected_option_id?: string | null
  user_role?: QuizUserRole | null
  response_time_ms?: number | null
  timed_out?: boolean
}

export interface QuizAttemptResponse {
  prompt_id: string
  selected_option_id?: string | null
  correct_option_id: string
  is_correct: boolean
  selected_expected_value?: number | null
  correct_expected_value?: number | null
  opportunity_cost?: number | null
  score: number
  scoring_mode: QuizScoringMode
  selected_explanation: string
  correct_explanation: string
  selected_role_feedback: string
  correct_role_feedback: string
  summary_explanation: string
  response_time_ms?: number | null
  timed_out: boolean
}


export type SourceRegistryResponse = VideoSourceRecord[]

export interface LocalLabProjectArtifact {
  project_id: string
  name: string
  has_video: boolean
  frame_count: number
  has_calibration: boolean
  has_tracking: boolean
  has_tracking_review: boolean
  has_cleaned_tracking: boolean
  has_projected_tracks: boolean
  quiz_prompt_count: number
  quiz_attempt_count: number
  updated_at?: string | null
  source?: VideoSourceRecord | null
}

export interface LocalLabProjectsResponse {
  projects: LocalLabProjectArtifact[]
}

export type DatasetType = 'recognition' | 'decision' | 'player_value'

export interface DatasetSummary {
  dataset_type: DatasetType
  sample_count: number
  label_count: number
  project_count: number
  last_exported_at?: string | null
  storage_paths: Record<string, string>
  positive_sample_count: number
  negative_sample_count: number
  positive_negative_ratio?: number | null
  label_distribution: Record<string, number>
}

export interface DatasetManifest {
  dataset_type: DatasetType
  schema_version: string
  sample_count: number
  label_count: number
  project_count: number
  exported_at: string
  storage_paths: Record<string, string>
  notes?: string | null
  included_project_count: number
  skipped_project_count: number
  skipped_projects: Array<{ project_id: string; name?: string | null; reason: string }>
  positive_sample_count: number
  negative_sample_count: number
  positive_negative_ratio?: number | null
  source_project_ids: string[]
  skipped_project_ids: string[]
  label_distribution: Record<string, number>
  source_license_distribution: Record<string, number>
  usage_scope_distribution: Record<string, number>
  created_at: string
}

export interface DatasetListResponse {
  datasets: DatasetSummary[]
}

export interface DecisionEventsBuildSummary {
  event_count: number
  avg_raw_score: number
  avg_role_adjusted_score: number
  opportunity_cost_avg: number
}

export type BreakdownConfidence = 'LOW' | 'MEDIUM' | 'HIGH'
export type DraftStatus = 'DRAFT' | 'APPROVED' | 'REJECTED'

export interface ReferenceVideo {
  reference_id: string
  source_id: string
  title: string
  url: string
  source_type: 'YOUTUBE' | 'URL'
  license_type: SourceLicenseType
  usage_scope: UsageScope
  allowed_for_training: boolean
  tags: string[]
  notes?: string | null
  created_at: string
  updated_at: string
}

export interface CreateReferenceVideoRequest {
  title: string
  url: string
  source_type?: 'YOUTUBE' | 'URL' | null
  license_type?: SourceLicenseType | null
  usage_scope?: UsageScope | null
  allowed_for_training?: boolean | null
  tags?: string[]
  notes?: string | null
}

export interface ReferenceVideoListResponse {
  reference_videos: ReferenceVideo[]
}

export interface ReferenceBreakdownNote {
  note_id: string
  reference_id: string
  timestamp_sec?: number | null
  timestamp_label?: string | null
  court_role: CourtRoleTarget
  situation_type: SituationType
  concept: string
  good_read: string
  bad_read: string
  coaching_cue: string
  tags: string[]
  confidence: BreakdownConfidence
  created_at: string
  updated_at: string
}

export interface UpsertReferenceBreakdownNoteRequest {
  timestamp_sec?: number | null
  timestamp_label?: string | null
  court_role: CourtRoleTarget
  situation_type: SituationType
  concept: string
  good_read: string
  bad_read: string
  coaching_cue: string
  tags?: string[]
  confidence: BreakdownConfidence
}

export interface QuizPromptDraftOption {
  option_id: string
  label: string
  is_correct: boolean
}

export interface QuizPromptDraft {
  draft_id: string
  reference_id: string
  source_note_id: string
  question: string
  court_role_target: CourtRoleTarget
  situation_type: SituationType
  role_instruction: string
  options: QuizPromptDraftOption[]
  explanation: string
  status: DraftStatus
  created_at: string
  updated_at: string
}

export interface DecisionRuleDraft {
  draft_id: string
  reference_id: string
  source_note_id: string
  court_role: CourtRoleTarget
  situation_type: SituationType
  condition_text: string
  positive_cue: string
  negative_cue: string
  suggested_weight: number
  explanation: string
  status: DraftStatus
  created_at: string
  updated_at: string
}

export interface ReferenceVideoDraftSummary {
  reference_only_source_count: number
  quiz_prompt_draft_count: number
  decision_rule_draft_count: number
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
  listLocalLabProjects: () => request<LocalLabProjectsResponse>('/local-lab/projects'),
  listSources: () => request<SourceRegistryResponse>('/sources'),
  seedCandidateSources: () => request<SourceRegistryResponse>('/sources/seed-candidates', { method: 'POST' }),
  listDatasets: () => request<DatasetListResponse>('/local-lab/datasets'),
  exportRecognitionDataset: () => request<DatasetManifest>('/local-lab/datasets/recognition/export', { method: 'POST' }),
  exportDecisionDataset: () => request<DatasetManifest>('/local-lab/datasets/decision/export', { method: 'POST' }),
  curateRecognitionDataset: () => request<DatasetManifest>('/local-lab/datasets/recognition/curate', { method: 'POST' }),
  curateDecisionDataset: () => request<DatasetManifest>('/local-lab/datasets/decision/curate', { method: 'POST' }),
  buildDecisionEvents: () => request<DecisionEventsBuildSummary>('/local-lab/decision-events/build', { method: 'POST' }),
  scoreRecognitionQuality: (projectId: string) =>
    request<RecognitionScoreProjectResponse>(`/local-lab/recognition/score-project/${projectId}`, { method: 'POST' }),
  getProjectBundle: (projectId: string) => request<ProjectBundleResponse>(`/projects/${projectId}/bundle`),
  getProjectSource: (projectId: string) => request<VideoSourceRecord>(`/projects/${projectId}/source`),
  updateProjectSource: (projectId: string, payload: VideoSourceRecord) =>
    request<VideoSourceRecord>(`/projects/${projectId}/source`, { method: 'PUT', body: JSON.stringify(payload) }),
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
  videoSourceUrl: (projectId: string) => `${API_BASE_URL}/projects/${projectId}/video/source`,
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
  getTrackingReview: (projectId: string) => request<TrackReviewResponse>(`/projects/${projectId}/tracking/review`),
  saveTrackingReview: (projectId: string, payload: TrackReviewPatch) =>
    request<TrackReviewResponse>(`/projects/${projectId}/tracking/review`, {
      method: 'POST',
      body: JSON.stringify(payload)
    }),
  listQuizPrompts: (projectId: string, filters: { court_role?: CourtRoleTarget; situation_type?: SituationType } = {}) => {
    const query = new URLSearchParams()
    if (filters.court_role) query.set('court_role', filters.court_role)
    if (filters.situation_type) query.set('situation_type', filters.situation_type)
    const suffix = query.toString() ? `?${query.toString()}` : ''
    return request<QuizPrompt[]>(`/projects/${projectId}/quiz-prompts${suffix}`)
  },
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
    }),
  listReferenceVideos: () => request<ReferenceVideoListResponse>('/reference-videos'),
  createReferenceVideo: (payload: CreateReferenceVideoRequest) =>
    request<ReferenceVideo>('/reference-videos', { method: 'POST', body: JSON.stringify(payload) }),
  listReferenceNotes: (referenceId: string) => request<ReferenceBreakdownNote[]>(`/reference-videos/${referenceId}/notes`),
  createReferenceNote: (referenceId: string, payload: UpsertReferenceBreakdownNoteRequest) =>
    request<ReferenceBreakdownNote>(`/reference-videos/${referenceId}/notes`, { method: 'POST', body: JSON.stringify(payload) }),
  updateReferenceNote: (referenceId: string, noteId: string, payload: UpsertReferenceBreakdownNoteRequest) =>
    request<ReferenceBreakdownNote>(`/reference-videos/${referenceId}/notes/${noteId}`, { method: 'PUT', body: JSON.stringify(payload) }),
  deleteReferenceNote: (referenceId: string, noteId: string) =>
    request<{ status: string; note_id: string }>(`/reference-videos/${referenceId}/notes/${noteId}`, { method: 'DELETE' }),
  convertReferenceNoteToQuizDraft: (referenceId: string, noteId: string) =>
    request<QuizPromptDraft>(`/reference-videos/${referenceId}/notes/${noteId}/quiz-draft`, { method: 'POST' }),
  convertReferenceNoteToRuleDraft: (referenceId: string, noteId: string) =>
    request<DecisionRuleDraft>(`/reference-videos/${referenceId}/notes/${noteId}/rule-draft`, { method: 'POST' }),
  listReferenceQuizDrafts: (referenceId: string) => request<QuizPromptDraft[]>(`/reference-videos/${referenceId}/quiz-drafts`),
  listReferenceRuleDrafts: (referenceId: string) => request<DecisionRuleDraft[]>(`/reference-videos/${referenceId}/rule-drafts`),
  getReferenceVideoSummary: () => request<ReferenceVideoDraftSummary>('/local-lab/reference-video-summary')
}
