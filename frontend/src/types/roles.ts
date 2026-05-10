export type UserRole = 'COACH' | 'PLAYER' | 'ANALYST' | 'FAN'

export type CourtRole =
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

export interface RoleProfile {
  userRole: UserRole
  courtRole: CourtRole
  situationTypes: SituationType[]
}

export const USER_ROLES: UserRole[] = ['COACH', 'PLAYER', 'ANALYST', 'FAN']

export const COURT_ROLES: CourtRole[] = [
  'BALL_HANDLER',
  'OFF_BALL_SHOOTER',
  'ROLLER',
  'SCREENER',
  'ON_BALL_DEFENDER',
  'HELP_DEFENDER',
  'LOW_MAN',
  'TRAILER',
  'WEAK_SIDE_WING'
]

export const SITUATION_TYPES: SituationType[] = [
  'PICK_AND_ROLL',
  'SHORT_ROLL',
  'SPOT_UP',
  'CLOSEOUT_ATTACK',
  'TRANSITION_3_ON_2',
  'LATE_CLOCK',
  'POST_DOUBLE',
  'DRIVE_AND_KICK',
  'HELP_ROTATION',
  'LOW_MAN_DECISION',
  'OFF_BALL_RELOCATION'
]
