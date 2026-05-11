import type { DecisionArrowPoint, FrameAsset, PlayerTrack, TrackReviewResponse } from '../api/client'

export interface TrackProjectLike {
  tracks: PlayerTrack[]
  trackingReview?: TrackReviewResponse | null
}

function excludedTrackIds(project: TrackProjectLike): Set<string> {
  return new Set(project.trackingReview?.review_patch.excluded_track_ids ?? [])
}

export function effectiveQuizBuilderTracks(project: TrackProjectLike): PlayerTrack[] {
  const excluded = excludedTrackIds(project)
  const sourceTracks = project.trackingReview?.cleaned_tracking?.tracks?.length
    ? project.trackingReview.cleaned_tracking.tracks
    : project.tracks
  return sourceTracks.filter((track) => !excluded.has(track.track_id))
}

export function normalizeTrackPointForFrame(point: { image_point_x: number; image_point_y: number }, frame: Pick<FrameAsset, 'width' | 'height'>): DecisionArrowPoint {
  if (point.image_point_x <= 1 && point.image_point_y <= 1) {
    return { x: point.image_point_x, y: point.image_point_y }
  }
  const width = frame.width ?? 0
  const height = frame.height ?? 0
  if (width <= 0 || height <= 0) {
    return { x: point.image_point_x, y: point.image_point_y }
  }
  return { x: point.image_point_x / width, y: point.image_point_y / height }
}

export function frameContextTrackIds(project: TrackProjectLike, frameIndex: number): string[] {
  return effectiveQuizBuilderTracks(project)
    .filter((track) => track.points.some((point) => point.frame_index === frameIndex))
    .map((track) => track.track_id)
    .sort()
}

export function nearestSourceTrackIdsForOption(
  project: TrackProjectLike,
  frame: Pick<FrameAsset, 'frame_index' | 'width' | 'height'>,
  optionStart: DecisionArrowPoint,
  existing: string[] = [],
  threshold = 0.12
): string[] {
  const candidates = effectiveQuizBuilderTracks(project)
    .map((track) => {
      const point = track.points.find((item) => item.frame_index === frame.frame_index)
      if (!point) return null
      const normalized = normalizeTrackPointForFrame(point, frame)
      const distance = Math.hypot(normalized.x - optionStart.x, normalized.y - optionStart.y)
      return { trackId: track.track_id, distance }
    })
    .filter((item): item is { trackId: string; distance: number } => item !== null)
    .sort((a, b) => a.distance - b.distance)
  const nearest = candidates[0]
  if (!nearest || nearest.distance > threshold) return existing
  return Array.from(new Set([...existing, nearest.trackId])).sort()
}

export function quizBuilderTrackPayload<TOption extends { start: DecisionArrowPoint; source_track_ids?: string[] }>(
  project: TrackProjectLike,
  frame: Pick<FrameAsset, 'frame_index' | 'width' | 'height'>,
  options: TOption[]
): { context_track_ids: string[]; source_track_ids: string[]; options: Array<TOption & { source_track_ids: string[] }> } {
  return {
    context_track_ids: frameContextTrackIds(project, frame.frame_index),
    source_track_ids: [],
    options: options.map((option) => ({
      ...option,
      source_track_ids: nearestSourceTrackIdsForOption(project, frame, option.start, option.source_track_ids ?? [])
    }))
  }
}
