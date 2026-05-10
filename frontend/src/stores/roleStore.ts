import { defineStore } from 'pinia'
import type { RoleProfile } from '../types/roles'

const ROLE_PROFILE_STORAGE_KEY = 'court-iq-role-profile'

interface RoleState {
  roleProfile: RoleProfile | null
}

function isRoleProfile(value: unknown): value is RoleProfile {
  if (!value || typeof value !== 'object') return false
  const profile = value as Partial<RoleProfile>
  return typeof profile.userRole === 'string' && typeof profile.courtRole === 'string' && Array.isArray(profile.situationTypes)
}

export const useRoleStore = defineStore('roleStore', {
  state: (): RoleState => ({
    roleProfile: null
  }),
  getters: {
    hasRoleProfile: (state) => state.roleProfile !== null,
    isCoach: (state) => state.roleProfile?.userRole === 'COACH',
    isPlayer: (state) => state.roleProfile?.userRole === 'PLAYER',
    isAnalyst: (state) => state.roleProfile?.userRole === 'ANALYST',
    isFan: (state) => state.roleProfile?.userRole === 'FAN'
  },
  actions: {
    setRoleProfile(profile: RoleProfile) {
      this.roleProfile = {
        userRole: profile.userRole,
        courtRole: profile.courtRole,
        situationTypes: [...profile.situationTypes]
      }
      this.persistRoleProfile()
    },
    clearRoleProfile() {
      this.roleProfile = null
      if (typeof window !== 'undefined') {
        window.localStorage.removeItem(ROLE_PROFILE_STORAGE_KEY)
      }
    },
    restoreRoleProfile() {
      if (typeof window === 'undefined') return
      const storedProfile = window.localStorage.getItem(ROLE_PROFILE_STORAGE_KEY)
      if (!storedProfile) return

      try {
        const parsedProfile = JSON.parse(storedProfile)
        if (isRoleProfile(parsedProfile)) {
          this.roleProfile = parsedProfile
        } else {
          window.localStorage.removeItem(ROLE_PROFILE_STORAGE_KEY)
        }
      } catch {
        window.localStorage.removeItem(ROLE_PROFILE_STORAGE_KEY)
      }
    },
    persistRoleProfile() {
      if (typeof window === 'undefined') return
      if (this.roleProfile) {
        window.localStorage.setItem(ROLE_PROFILE_STORAGE_KEY, JSON.stringify(this.roleProfile))
      } else {
        window.localStorage.removeItem(ROLE_PROFILE_STORAGE_KEY)
      }
    }
  }
})
