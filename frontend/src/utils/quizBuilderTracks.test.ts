import { describe, expect, it } from 'vitest'
import { effectiveQuizBuilderTracks, frameContextTrackIds, nearestSourceTrackIdsForOption, quizBuilderTrackPayload } from './quizBuilderTracks'
import type { PlayerTrack, TrackReviewResponse } from '../api/client'

function track(track_id: string, image_point_x: number, image_point_y: number): PlayerTrack {
  return {
    track_id,
    points: [{ frame_id: 'frame-1', frame_index: 7, timestamp_seconds: 1, image_point_x, image_point_y }],
    metadata: {}
  }
}

describe('quizBuilderTracks', () => {
  it('normalizes pixel track coordinates against frame dimensions for nearest matching', () => {
    const project = { tracks: [track('track-1', 320, 180)] }

    expect(nearestSourceTrackIdsForOption(project, { frame_index: 7, width: 1280, height: 720 }, { x: 0.25, y: 0.25 })).toEqual(['track-1'])
  })

  it('matches normalized arrows to pixel tracking points using frame dimensions', () => {
    const project = { tracks: [track('track-1', 960, 540)] }

    expect(nearestSourceTrackIdsForOption(project, { frame_index: 7, width: 1920, height: 1080 }, { x: 0.5, y: 0.5 })).toEqual(['track-1'])
  })

  it('prefers cleaned reviewed tracks and excludes rejected tracks', () => {
    const cleaned = track('clean-track', 0.25, 0.25)
    const excluded = track('excluded-track', 0.25, 0.25)
    const trackingReview: TrackReviewResponse = {
      project_id: 'project-1',
      tracking: { project_id: 'project-1', detections: [], tracks: [excluded] },
      review_patch: { excluded_detection_ids: [], excluded_track_ids: ['excluded-track'] },
      cleaned_tracking: { project_id: 'project-1', detections: [], tracks: [cleaned, excluded] },
      cleaned_projected_tracks: [],
      storage_paths: {}
    }

    const project = { tracks: [track('raw-track', 0.25, 0.25)], trackingReview }

    expect(effectiveQuizBuilderTracks(project).map((item) => item.track_id)).toEqual(['clean-track'])
    expect(frameContextTrackIds(project, 7)).toEqual(['clean-track'])
    expect(nearestSourceTrackIdsForOption(project, { frame_index: 7, width: 1280, height: 720 }, { x: 0.25, y: 0.25 })).toEqual(['clean-track'])
  })

  it('uses reviewed tracking before stale project tracks when cleaned tracking is absent', () => {
    const reviewed = track('reviewed-track', 0.25, 0.25)
    const trackingReview: TrackReviewResponse = {
      project_id: 'project-1',
      tracking: { project_id: 'project-1', detections: [], tracks: [reviewed] },
      review_patch: { excluded_detection_ids: [], excluded_track_ids: [] },
      cleaned_tracking: null,
      cleaned_projected_tracks: [],
      storage_paths: {}
    }

    const project = { tracks: [track('stale-raw-track', 0.25, 0.25)], trackingReview }

    expect(effectiveQuizBuilderTracks(project).map((item) => item.track_id)).toEqual(['reviewed-track'])
  })
})


describe('quizBuilderTrackPayload', () => {
  it('sends context_track_ids separately from option source_track_ids', () => {
    const project = { tracks: [track('track-1', 0.25, 0.25), track('track-2', 0.75, 0.75)] }
    const payload = quizBuilderTrackPayload(project, { frame_index: 7, width: 1280, height: 720 }, [
      { option_id: 'A', start: { x: 0.25, y: 0.25 } },
      { option_id: 'B', start: { x: 0.1, y: 0.1 } }
    ])

    expect(payload.context_track_ids).toEqual(['track-1', 'track-2'])
    expect(payload.source_track_ids).toEqual([])
    expect(payload.options[0].source_track_ids).toEqual(['track-1'])
    expect(payload.options[1].source_track_ids).toEqual([])
  })
})
