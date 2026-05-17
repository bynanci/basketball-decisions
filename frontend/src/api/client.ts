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

export type TeamSide = 'HOME' | 'AWAY' | 'UNKNOWN'
export type PlayerAliasSource = 'MANUAL' | 'HEURISTIC' | 'MODEL'

export interface PlayerAlias {
  player_key: string
  project_id: string
  track_ids: string[]
  display_name?: string | null
  team_side: TeamSide
  role_hint?: string | null
  confidence: number
  source: PlayerAliasSource
  notes?: string | null
  created_at?: string
  updated_at?: string
}

export interface PlayerAliasListResponse {
  project_id: string
  aliases: PlayerAlias[]
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
  player_aliases: PlayerAliasListResponse
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
  model_version?: string | null
  scoring_source?: 'RULE' | 'MODEL' | string
}

export interface TrackRecognitionScore {
  track_id: string
  false_positive_risk: number
  recommended_label: 'LOW' | 'MEDIUM' | 'HIGH' | string
  reasons: string[]
  features: TrackRecognitionFeatures
  model_version?: string | null
  scoring_source?: 'RULE' | 'MODEL' | string
}

export interface RecognitionScoreProjectResponse {
  project_id: string
  model_version?: string | null
  scoring_source?: 'RULE' | 'MODEL' | string
  detection_scores: DetectionRecognitionScore[]
  track_scores: TrackRecognitionScore[]
  summary: {
    high_risk_detection_count: number
    high_risk_track_count: number
    model_version?: string | null
    scoring_source?: 'RULE' | 'MODEL' | string
  }
}

export interface RecognitionModelMetrics {
  accuracy: number
  precision: number
  recall: number
  f1: number
  confusion_matrix: number[][]
  train_sample_count: number
  test_sample_count: number
  feature_importance?: Record<string, number> | null
}

export interface RecognitionDatasetLineage {
  dataset_type: 'recognition'
  manifest_path: string
  samples_path: string
  labels_path: string
  dataset_fingerprint: string
  manifest_fingerprint?: string | null
  samples_fingerprint?: string | null
  labels_fingerprint?: string | null
  sample_count: number
  label_count: number
  source_project_ids: string[]
  exported_at?: string | null
}

export interface RecognitionEvaluationReport {
  report_id: string
  model_version: string
  created_at: string
  metrics_path: string
  report_path: string
  dataset_fingerprint: string
  metrics: RecognitionModelMetrics
}

export interface RecognitionModelInfo {
  version: string
  active: boolean
  created_at: string
  model_path: string
  metrics_path: string
  feature_schema_path: string
  lineage_path?: string | null
  evaluation_report_path?: string | null
  dataset_fingerprint?: string | null
  dataset_lineage?: RecognitionDatasetLineage | null
  metrics?: RecognitionModelMetrics | null
}

export interface RecognitionModelRegistry {
  active_version?: string | null
  updated_at: string
  models: RecognitionModelInfo[]
  active_model?: RecognitionModelInfo | null
}

export interface RecognitionModelComparison {
  base_version: string
  candidate_version: string
  base_model: RecognitionModelInfo
  candidate_model: RecognitionModelInfo
  metric_deltas: Record<string, number>
}

export interface RecognitionActivationResponse {
  active_version?: string | null
  previous_active_version?: string | null
  activated_version: string
  updated_at: string
  reason?: string | null
  registry: RecognitionModelRegistry
}

export interface RecognitionEvaluationReportRegistry {
  reports: RecognitionEvaluationReport[]
  updated_at: string
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
  source_track_ids?: string[]
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
  context_track_ids: string[]
  source_track_ids: string[]
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
  context_track_ids?: string[]
  source_track_ids?: string[]
  options: DecisionQuizOption[]
  explanation: string
}
export type DecisionPromptDifficulty = 'TOO_EASY' | 'BALANCED' | 'TOO_HARD' | 'INSUFFICIENT_DATA'

export interface DecisionPromptDiagnostics {
  prompt_id: string
  project_id: string
  court_role_target: CourtRoleTarget
  situation_type: SituationType
  question_mode: QuizQuestionMode
  attempt_count: number
  correct_rate: number
  avg_score: number
  avg_role_adjusted_score: number
  avg_opportunity_cost: number
  timeout_rate: number
  most_selected_wrong_option_id?: string | null
  difficulty: DecisionPromptDifficulty
  suspected_label_issue: boolean
  rule_evaluated_count: number
  rule_matched_count: number
  rule_missed_count: number
  avg_rule_score_delta: number
  score_capped_count: number
  reasons: string[]
}

export interface DecisionRoleDiagnostics {
  court_role: CourtRoleTarget
  prompt_count: number
  attempt_count: number
  avg_score: number
  avg_opportunity_cost: number
  timeout_rate: number
  weakest_situation_types: SituationType[]
}

export interface DecisionSituationDiagnostics {
  situation_type: SituationType
  prompt_count: number
  attempt_count: number
  avg_score: number
  avg_opportunity_cost: number
  timeout_rate: number
}

export interface DecisionDiagnosticsGlobalSummary {
  prompt_count: number
  attempt_count: number
  too_easy_count: number
  too_hard_count: number
  balanced_count: number
  insufficient_data_count: number
  suspected_label_issue_count: number
  high_cost_prompt_count: number
  time_pressure_prompt_count: number
  rule_evaluated_count: number
  rule_matched_count: number
  rule_missed_count: number
  avg_rule_score_delta: number
  score_capped_count: number
  analytics_only: boolean
}

export interface DecisionDiagnosticsReport {
  generated_at: string
  prompt_diagnostics: DecisionPromptDiagnostics[]
  role_diagnostics: DecisionRoleDiagnostics[]
  situation_diagnostics: DecisionSituationDiagnostics[]
  global_summary: DecisionDiagnosticsGlobalSummary
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
  player_alias_count: number
  aliased_track_count: number
  unaliased_track_count: number
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

export type DatasetHealthSeverity = 'LOW' | 'MEDIUM' | 'HIGH'

export interface DatasetHealthWarning {
  code: string
  severity: DatasetHealthSeverity
  message: string
  recommendation: string
}

export interface RecognitionDatasetHealth {
  dataset_type: 'recognition'
  sample_count: number
  label_count: number
  positive_sample_count: number
  negative_sample_count: number
  positive_negative_ratio?: number | null
  label_distribution: Record<string, number>
  source_project_count: number
  skipped_project_count: number
  has_minimum_samples: boolean
  has_balanced_labels: boolean
  warnings: DatasetHealthWarning[]
}

export interface DecisionDatasetHealth {
  dataset_type: 'decision'
  sample_count: number
  label_count: number
  prompt_count: number
  option_count: number
  attempt_count: number
  positive_sample_count: number
  negative_sample_count: number
  positive_negative_ratio?: number | null
  role_distribution: Record<string, number>
  situation_distribution: Record<string, number>
  missing_expected_value_rate: number
  timeout_rate: number
  has_minimum_prompts: boolean
  has_role_coverage: boolean
  has_balanced_labels: boolean
  warnings: DatasetHealthWarning[]
}

export interface DatasetHealthResponse {
  recognition: RecognitionDatasetHealth
  decision: DecisionDatasetHealth
  generated_at: string
}

export interface DatasetListResponse {
  datasets: DatasetSummary[]
}


export interface PlayerValueComponent {
  name: string
  value: number
  weight: number
  contribution: number
  explanation: string
}

export interface PlayerValueTrace {
  project_ids: string[]
  track_ids: string[]
  decision_event_ids: string[]
  prompt_ids: string[]
  source_ids: string[]
}

export interface PlayerValueSummary {
  project_id: string
  player_key: string
  display_name?: string | null
  team_side: TeamSide
  role_hint?: string | null
  track_ids: string[]
  decision_event_count: number
  avg_raw_decision_score: number
  avg_role_adjusted_score: number
  avg_opportunity_cost?: number | null
  correct_rate: number
  timeout_rate: number
  recognition_reliability_score: number
  consistency_score: number
  improvement_score: number
  participation_score: number
  player_value_score: number
  components: PlayerValueComponent[]
  confidence: number
  warnings: string[]
  trace: PlayerValueTrace
  created_at: string
}

export interface PlayerValueBuildResponse {
  summaries: PlayerValueSummary[]
  generated_at: string
  warnings: string[]
}

export interface PlayerValueBuildMetadata {
  player_value_formula_version: string
  recognition_model_version?: string | null
  decision_rule_set_version?: string | null
  dataset_fingerprint: string
}

export interface PlayerValueBuildIndexEntry extends PlayerValueBuildMetadata {
  build_id: string
  generated_at: string
  summary_count: number
  snapshot_path: string
  warnings: string[]
}

export interface PlayerValueBuildIndexResponse {
  builds: PlayerValueBuildIndexEntry[]
  updated_at: string
}

export interface PlayerValueBuildSnapshot {
  build_id: string
  metadata: PlayerValueBuildMetadata
  build: PlayerValueBuildResponse
}

export interface PlayerValueTrendPoint extends PlayerValueBuildMetadata {
  build_id: string
  generated_at: string
  project_id: string
  player_key: string
  player_value_score: number
  confidence: number
  warnings: string[]
  decision_event_count: number
}

export interface PlayerValueTrendSeries {
  project_id: string
  player_key: string
  display_name?: string | null
  points: PlayerValueTrendPoint[]
  warnings: string[]
}

export interface PlayerValueTrendsResponse {
  trends: PlayerValueTrendSeries[]
  warnings: string[]
  generated_at: string
}

export interface PlayerValueTrendResponse {
  player_key: string
  trends: PlayerValueTrendSeries[]
  warnings: string[]
  generated_at: string
}

export interface PlayerValueCompareResponse {
  player_keys: string[]
  trends: PlayerValueTrendSeries[]
  warnings: string[]
  generated_at: string
}


export type ReviewQueueItemType =
  | 'RECOGNITION_TRACK'
  | 'RECOGNITION_DETECTION'
  | 'DECISION_PROMPT'
  | 'DECISION_ATTEMPT'
  | 'PLAYER_VALUE_ATTRIBUTION'
  | 'RULE_DRAFT'

export type ReviewQueuePriority = 'LOW' | 'MEDIUM' | 'HIGH'
export type ReviewQueueStatus = 'OPEN' | 'RESOLVED' | 'DISMISSED'
export type ReviewActionType =
  | 'MARK_TRACK_FALSE_POSITIVE'
  | 'MARK_TRACK_VALID_PLAYER'
  | 'ASSIGN_TRACK_TO_PLAYER_ALIAS'
  | 'OPEN_ALIAS_REVIEW'
  | 'FLAG_PROMPT_LABEL_ISSUE'
  | 'UPDATE_PROMPT_EXPECTED_VALUE'
  | 'MARK_ATTEMPT_TEACHING_CASE'
  | 'APPROVE_RULE_DRAFT'
  | 'REJECT_RULE_DRAFT'
  | 'ACCEPT_UNKNOWN_ATTRIBUTION'
  | 'DISMISS_WITH_NOTE'
export type ReviewActionStatus = 'APPLIED' | 'FAILED' | 'NO_OP'

export interface ReviewQueueItem {
  item_id: string
  item_type: ReviewQueueItemType
  priority: ReviewQueuePriority
  project_id?: string | null
  prompt_id?: string | null
  attempt_id?: string | null
  track_id?: string | null
  detection_id?: string | null
  player_key?: string | null
  reason: string
  recommended_action: string
  status: ReviewQueueStatus
  created_at: string
  resolved_at?: string | null
  allowed_actions: ReviewActionType[]
}

export interface ReviewActionRequest {
  action_type: ReviewActionType
  note?: string | null
  payload?: Record<string, unknown>
}

export interface ReviewActionLog {
  action_id: string
  item_id: string
  item_type: ReviewQueueItemType
  action_type: ReviewActionType
  project_id?: string | null
  target_ref: Record<string, unknown>
  payload: Record<string, unknown>
  note?: string | null
  status: ReviewActionStatus
  warnings: string[]
  created_at: string
}

export interface ReviewActionResponse {
  item: ReviewQueueItem
  action: ReviewActionLog
}

export interface ReviewActionFilters {
  item_id?: string
  project_id?: string
  action_type?: ReviewActionType
}

export interface ReviewQueueGenerateResponse {
  items: ReviewQueueItem[]
  generated_count: number
  open_count: number
  resolved_count: number
  dismissed_count: number
}

export interface RoleBreakdownItem {
  court_role?: string | null
  event_count: number
  avg_role_adjusted_score: number
  avg_opportunity_cost?: number | null
  correct_rate: number
  timeout_rate: number
}

export interface SituationBreakdownItem {
  situation_type?: string | null
  event_count: number
  avg_role_adjusted_score: number
  avg_opportunity_cost?: number | null
  correct_rate: number
  timeout_rate: number
}

export interface RuleEvaluationResult {
  rule_id: string
  court_role: CourtRoleTarget
  situation_type: SituationType
  matched: boolean
  score_delta: number
  weight: number
  condition_text: string
  positive_cue: string
  negative_cue: string
  explanation: string
  reason: string
}

export interface DecisionRuleApplicationSummary {
  enabled: boolean
  rule_set_id?: string | null
  rule_set_version?: number | null
  evaluated_rule_count: number
  matched_rule_count: number
  missed_rule_count: number
  total_delta: number
  delta_bounded: boolean
  results: RuleEvaluationResult[]
  notes: string[]
}

export interface PlayerValueEvidenceEvent {
  decision_event_id: string
  project_id: string
  prompt_id: string
  attempt_id: string
  frame_id?: string | null
  frame_index?: number | null
  user_role?: string | null
  court_role_target?: string | null
  situation_type?: string | null
  question_mode?: string | null
  selected_option_id?: string | null
  correct_option_id?: string | null
  is_correct: boolean
  raw_score: number
  role_adjusted_score: number
  decision_engine_version: string
  active_rule_set_id?: string | null
  active_rule_set_version?: number | null
  base_score?: number | null
  rule_score_delta: number
  final_score?: number | null
  score_capped: boolean
  rule_application: DecisionRuleApplicationSummary
  opportunity_cost?: number | null
  response_time_ms?: number | null
  timed_out: boolean
  source_track_ids: string[]
  context_track_ids: string[]
  prompt_question?: string | null
  prompt_explanation?: string | null
  selected_option_label?: string | null
  correct_option_label?: string | null
  alias_player_key?: string | null
  alias_display_name?: string | null
  alias_team_side?: string | null
  evidence_warnings: string[]
}

export interface PlayerValueEvidenceResponse {
  summary: PlayerValueSummary
  events: PlayerValueEvidenceEvent[]
  role_breakdown: RoleBreakdownItem[]
  situation_breakdown: SituationBreakdownItem[]
  warning_summary: string[]
  generated_at: string
}

export interface DecisionEventsBuildSummary {
  event_count: number
  avg_raw_score: number
  avg_role_adjusted_score: number
  opportunity_cost_avg: number
  decision_engine_version: string
  use_active_rules: boolean
  active_rule_set_id?: string | null
  active_rule_set_version?: number | null
  rule_evaluated_count: number
  rule_matched_count: number
  rule_missed_count: number
  avg_rule_score_delta: number
  score_capped_count: number
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


export type DecisionRuleStatus = 'ACTIVE' | 'DISABLED'

export interface DecisionRule {
  rule_id: string
  source_draft_id?: string | null
  court_role: CourtRoleTarget
  situation_type: SituationType
  condition_text: string
  positive_cue: string
  negative_cue: string
  weight: number
  explanation: string
  status: DecisionRuleStatus
  created_at: string
  updated_at: string
  approved_at: string
  approved_by?: string | null
}

export interface DecisionRuleSet {
  rule_set_id: string
  name: string
  version: number
  rules: DecisionRule[]
  active: boolean
  created_at: string
  updated_at: string
}

export interface DecisionRuleSetListResponse {
  rule_sets: DecisionRuleSet[]
  active_rule_set?: DecisionRuleSet | null
}

export interface ApproveDecisionRuleDraftRequest {
  rule_set_id?: string | null
  approved_by?: string | null
}

export interface CreateDecisionRuleSetRequest {
  name: string
  version?: number
  active?: boolean
}

export interface UpdateDecisionRuleRequest {
  condition_text?: string
  positive_cue?: string
  negative_cue?: string
  weight?: number
  explanation?: string
  status?: DecisionRuleStatus
}

export interface ReferenceVideoDraftSummary {
  reference_only_source_count: number
  quiz_prompt_draft_count: number
  decision_rule_draft_count: number
}


export type DrillPriority = 'LOW' | 'MEDIUM' | 'HIGH'
export type DrillEvidenceSource = 'DECISION_DIAGNOSTICS' | 'PLAYER_VALUE' | 'PLAYER_VALUE_TRENDS' | 'TEACHING_CASE' | 'REVIEW_QUEUE'

export interface DrillCatalogItem {
  drill_id: string
  title: string
  role?: string | null
  situation: string
  description: string
  coaching_cues: string[]
  success_metrics: string[]
  tags: string[]
}

export interface DrillCatalogResponse {
  drills: DrillCatalogItem[]
  generated_at: string
}

export interface DrillEvidenceRef {
  source: DrillEvidenceSource
  artifact: string
  ref_id?: string | null
  project_id?: string | null
  player_key?: string | null
  prompt_id?: string | null
  detail: string
}

export interface DrillRecommendation {
  recommendation_id: string
  drill_id: string
  title: string
  priority: DrillPriority
  confidence: number
  role?: string | null
  situation: string
  reason: string
  coaching_cues: string[]
  success_metrics: string[]
  evidence_refs: DrillEvidenceRef[]
}

export interface DrillRecommendationRequest {
  project_id?: string | null
  player_key?: string | null
  max_recommendations?: number
}

export interface DrillRecommendationResponse {
  schema_version: string
  generated_at: string
  project_id?: string | null
  player_key?: string | null
  recommendations: DrillRecommendation[]
  warnings: string[]
  catalog_path: string
  latest_path: string
}


export type PracticePlanDuration = 60 | 75 | 90 | 120
export type PracticePlanBlockType = 'warmup' | 'drill' | 'scrimmage' | 'review'

export interface PracticePlanBuildRequest {
  title?: string
  total_duration_minutes?: PracticePlanDuration
  project_id?: string | null
  player_key?: string | null
  player_keys?: string[]
  max_drill_blocks?: number
  created_by?: string | null
  notes?: string | null
}

export interface PracticePlanBlock {
  block_id: string
  block_type: PracticePlanBlockType
  title: string
  start_minute: number
  end_minute: number
  duration_minutes: number
  drill_id?: string | null
  recommendation_id?: string | null
  priority?: string | null
  target_roles: string[]
  target_situations: string[]
  player_keys: string[]
  coaching_cues: string[]
  success_metrics: string[]
  evidence_refs: DrillEvidenceRef[]
  warnings: string[]
}

export interface PracticePlan {
  schema_version: string
  plan_id: string
  title: string
  created_at: string
  created_by?: string | null
  notes?: string | null
  project_id?: string | null
  player_key?: string | null
  total_duration_minutes: PracticePlanDuration
  target_roles: string[]
  target_situations: string[]
  player_keys: string[]
  source_recommendation_ids: string[]
  blocks: PracticePlanBlock[]
  warnings: string[]
  evidence_refs: DrillEvidenceRef[]
  markdown: string
  json_path: string
  markdown_path: string
}

export interface PracticePlanListItem {
  plan_id: string
  title: string
  created_at: string
  created_by?: string | null
  notes?: string | null
  project_id?: string | null
  player_key?: string | null
  total_duration_minutes: PracticePlanDuration
  target_roles: string[]
  target_situations: string[]
  player_keys: string[]
  warning_count: number
  json_path: string
  markdown_path: string
}

export interface PracticePlanListResponse {
  plans: PracticePlanListItem[]
  updated_at: string
}

export type CoachReportSectionName =
  | 'Player Value'
  | 'Trends'
  | 'Decision Diagnostics'
  | 'Rule Contributions'
  | 'Teaching Cases'
  | 'Review Findings'
  | 'Source Governance'
  | 'Drill Recommendations'
  | 'Methodology & Limitations'

export const COACH_REPORT_SECTIONS: CoachReportSectionName[] = [
  'Player Value',
  'Trends',
  'Decision Diagnostics',
  'Rule Contributions',
  'Teaching Cases',
  'Review Findings',
  'Source Governance',
  'Drill Recommendations',
  'Methodology & Limitations'
]

export interface CoachReportBuildRequest {
  title?: string
  project_id?: string | null
  player_key?: string | null
  sections?: CoachReportSectionName[]
  created_by?: string | null
  notes?: string | null
}

export interface CoachReportArtifactStatus {
  artifact: string
  path: string
  available: boolean
  warning?: string | null
}

export interface CoachReportSection {
  name: CoachReportSectionName
  heading: string
  markdown: string
  data: Record<string, unknown>
  warnings: string[]
}

export interface CoachReport {
  schema_version: string
  report_id: string
  title: string
  created_at: string
  created_by?: string | null
  project_id?: string | null
  player_key?: string | null
  sections: CoachReportSection[]
  warnings: string[]
  artifact_status: CoachReportArtifactStatus[]
  markdown: string
  json_path: string
  markdown_path: string
}

export interface CoachReportListItem {
  report_id: string
  title: string
  created_at: string
  created_by?: string | null
  project_id?: string | null
  player_key?: string | null
  section_names: string[]
  warning_count: number
  json_path: string
  markdown_path: string
}

export interface CoachReportListResponse {
  reports: CoachReportListItem[]
  updated_at: string
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

async function requestText(path: string, init: RequestInit = {}): Promise<string> {
  const headers = new Headers(init.headers)
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
  return response.text()
}

export const apiClient = {
  listProjects: () => request<ListProjectsResponse>('/projects'),
  listDrillCatalog: () => request<DrillCatalogResponse>('/drills/catalog'),
  buildDrillRecommendations: (payload: DrillRecommendationRequest) =>
    request<DrillRecommendationResponse>('/drills/recommendations', { method: 'POST', body: JSON.stringify(payload) }),
  getLatestDrillRecommendations: () => request<DrillRecommendationResponse>('/drills/recommendations/latest'),
  buildPracticePlan: (payload: PracticePlanBuildRequest) =>
    request<PracticePlan>('/practice-plans', { method: 'POST', body: JSON.stringify(payload) }),
  listPracticePlans: () => request<PracticePlanListResponse>('/practice-plans'),
  getPracticePlan: (planId: string) => request<PracticePlan>(`/practice-plans/${encodeURIComponent(planId)}`),
  getPracticePlanJson: (planId: string) => request<PracticePlan>(`/practice-plans/${encodeURIComponent(planId)}/json`),
  getPracticePlanMarkdown: (planId: string) => requestText(`/practice-plans/${encodeURIComponent(planId)}/markdown`),
  practicePlanMarkdownUrl: (planId: string) => `${API_BASE_URL}/practice-plans/${encodeURIComponent(planId)}/markdown`,
  practicePlanJsonUrl: (planId: string) => `${API_BASE_URL}/practice-plans/${encodeURIComponent(planId)}/json`,
  buildCoachReport: (payload: CoachReportBuildRequest) =>
    request<CoachReport>('/reports/coach', { method: 'POST', body: JSON.stringify(payload) }),
  listCoachReports: () => request<CoachReportListResponse>('/reports/coach'),
  getCoachReport: (reportId: string) => request<CoachReport>(`/reports/coach/${encodeURIComponent(reportId)}`),
  getCoachReportJson: (reportId: string) => request<CoachReport>(`/reports/coach/${encodeURIComponent(reportId)}/json`),
  getCoachReportMarkdown: (reportId: string) => requestText(`/reports/coach/${encodeURIComponent(reportId)}/markdown`),
  coachReportMarkdownUrl: (reportId: string) => `${API_BASE_URL}/reports/coach/${encodeURIComponent(reportId)}/markdown`,
  coachReportJsonUrl: (reportId: string) => `${API_BASE_URL}/reports/coach/${encodeURIComponent(reportId)}/json`,
  listLocalLabProjects: () => request<LocalLabProjectsResponse>('/local-lab/projects'),
  listSources: () => request<SourceRegistryResponse>('/sources'),
  seedCandidateSources: () => request<SourceRegistryResponse>('/sources/seed-candidates', { method: 'POST' }),
  listDatasets: () => request<DatasetListResponse>('/local-lab/datasets'),
  getDatasetHealth: () => request<DatasetHealthResponse>('/local-lab/datasets/health'),
  exportRecognitionDataset: () => request<DatasetManifest>('/local-lab/datasets/recognition/export', { method: 'POST' }),
  exportDecisionDataset: () => request<DatasetManifest>('/local-lab/datasets/decision/export', { method: 'POST' }),
  curateRecognitionDataset: () => request<DatasetManifest>('/local-lab/datasets/recognition/curate', { method: 'POST' }),
  curateDecisionDataset: () => request<DatasetManifest>('/local-lab/datasets/decision/curate', { method: 'POST' }),
  buildDecisionEvents: (useActiveRules = true) => request<DecisionEventsBuildSummary>(`/local-lab/decision-events/build?use_active_rules=${useActiveRules}`, { method: 'POST' }),
  buildDecisionDiagnostics: () => request<DecisionDiagnosticsReport>('/local-lab/decision-diagnostics/build', { method: 'POST' }),
  buildPlayerValue: () => request<PlayerValueBuildResponse>('/local-lab/player-value/build', { method: 'POST' }),
  getPlayerValue: () => request<PlayerValueBuildResponse>('/local-lab/player-value'),
  getPlayerValueEvidence: (projectId: string, playerKey: string) =>
    request<PlayerValueEvidenceResponse>(`/local-lab/player-value/${encodeURIComponent(projectId)}/${encodeURIComponent(playerKey)}/evidence`),
  getPlayerValueTrends: () => request<PlayerValueTrendsResponse>('/local-lab/player-value/trends'),
  getPlayerValueTrend: (playerKey: string) => request<PlayerValueTrendResponse>(`/local-lab/player-value/trends/${encodeURIComponent(playerKey)}`),
  comparePlayerValue: (playerKeys: string[]) =>
    request<PlayerValueCompareResponse>('/local-lab/player-value/compare', { method: 'POST', body: JSON.stringify({ player_keys: playerKeys }) }),
  listPlayerValueBuilds: () => request<PlayerValueBuildIndexResponse>('/local-lab/player-value/builds'),
  getPlayerValueBuild: (buildId: string) => request<PlayerValueBuildSnapshot>(`/local-lab/player-value/builds/${encodeURIComponent(buildId)}`),
  getDecisionDiagnostics: () => request<DecisionDiagnosticsReport>('/local-lab/decision-diagnostics'),
  generateReviewQueue: () => request<ReviewQueueGenerateResponse>('/review-queue/generate', { method: 'POST' }),
  listReviewQueue: () => request<ReviewQueueItem[]>('/review-queue'),
  updateReviewQueueItem: (itemId: string, status: ReviewQueueStatus) =>
    request<ReviewQueueItem>(`/review-queue/${encodeURIComponent(itemId)}`, { method: 'PUT', body: JSON.stringify({ status }) }),
  performReviewAction: (itemId: string, payload: ReviewActionRequest) =>
    request<ReviewActionResponse>(`/review-queue/${encodeURIComponent(itemId)}/actions`, { method: 'POST', body: JSON.stringify(payload) }),
  listReviewActions: (filters: ReviewActionFilters = {}) => {
    const params = new URLSearchParams()
    if (filters.item_id) params.set('item_id', filters.item_id)
    if (filters.project_id) params.set('project_id', filters.project_id)
    if (filters.action_type) params.set('action_type', filters.action_type)
    const query = params.toString()
    return request<ReviewActionLog[]>(`/review-queue/actions${query ? `?${query}` : ''}`)
  },
  getRecognitionModelRegistry: () => request<RecognitionModelRegistry>('/local-lab/models/recognition'),
  compareRecognitionModels: (baseVersion: string, candidateVersion: string) =>
    request<RecognitionModelComparison>(`/local-lab/models/recognition/compare?base_version=${encodeURIComponent(baseVersion)}&candidate_version=${encodeURIComponent(candidateVersion)}`),
  activateRecognitionModel: (version: string, reason?: string) =>
    request<RecognitionActivationResponse>(`/local-lab/models/recognition/${encodeURIComponent(version)}/activate`, {
      method: 'POST',
      body: JSON.stringify({ activate: true, reason: reason ?? null })
    }),
  getRecognitionEvaluationReports: () => request<RecognitionEvaluationReportRegistry>('/local-lab/models/recognition/evaluation-reports'),
  trainRecognitionBaseline: (activate = false) => request<RecognitionModelInfo>(`/local-lab/models/recognition/train-baseline${activate ? '?activate=true' : ''}`, { method: 'POST' }),
  scoreRecognitionQuality: (projectId: string) =>
    request<RecognitionScoreProjectResponse>(`/local-lab/recognition/score-project/${projectId}`, { method: 'POST' }),
  scoreRecognitionModel: (projectId: string) =>
    request<RecognitionScoreProjectResponse>(`/local-lab/models/recognition/score-project/${projectId}`, { method: 'POST' }),
  getProjectBundle: (projectId: string) => request<ProjectBundleResponse>(`/projects/${projectId}/bundle`),
  getPlayerAliases: (projectId: string) => request<PlayerAliasListResponse>(`/projects/${projectId}/player-aliases`),
  savePlayerAliases: (projectId: string, payload: PlayerAliasListResponse, strict = false) =>
    request<PlayerAliasListResponse>(`/projects/${projectId}/player-aliases${strict ? '?strict=true' : ''}`, { method: 'PUT', body: JSON.stringify(payload) }),
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
  listDecisionRuleDrafts: () => request<DecisionRuleDraft[]>('/decision-rules/drafts'),
  approveDecisionRuleDraft: (draftId: string, payload: ApproveDecisionRuleDraftRequest = {}) =>
    request<DecisionRule>(`/decision-rules/drafts/${draftId}/approve`, { method: 'POST', body: JSON.stringify(payload) }),
  rejectDecisionRuleDraft: (draftId: string) =>
    request<DecisionRuleDraft>(`/decision-rules/drafts/${draftId}/reject`, { method: 'POST' }),
  listDecisionRuleSets: () => request<DecisionRuleSetListResponse>('/decision-rules/rule-sets'),
  createDecisionRuleSet: (payload: CreateDecisionRuleSetRequest) =>
    request<DecisionRuleSet>('/decision-rules/rule-sets', { method: 'POST', body: JSON.stringify(payload) }),
  activateDecisionRuleSet: (ruleSetId: string) =>
    request<DecisionRuleSet>(`/decision-rules/rule-sets/${ruleSetId}/activate`, { method: 'PUT' }),
  updateDecisionRule: (ruleId: string, payload: UpdateDecisionRuleRequest) =>
    request<DecisionRule>(`/decision-rules/rules/${ruleId}`, { method: 'PUT', body: JSON.stringify(payload) }),
  getReferenceVideoSummary: () => request<ReferenceVideoDraftSummary>('/local-lab/reference-video-summary')
}
