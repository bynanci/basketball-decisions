import { defineStore } from 'pinia'

export type ProjectSource = 'upload' | 'youtube'

export interface ProjectSummary {
  id: string
  name: string
  source: ProjectSource
  videoPath?: string
  youtubeUrl?: string
}

export const useProjectsStore = defineStore('projects', {
  state: () => ({
    projects: [] as ProjectSummary[],
    activeProjectId: ''
  }),
  getters: {
    activeProject: (state) => state.projects.find((project) => project.id === state.activeProjectId)
  },
  actions: {
    addProject(project: ProjectSummary) {
      this.projects.push(project)
      this.activeProjectId = project.id
    }
  }
})
