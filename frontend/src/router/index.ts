import { createRouter, createWebHistory } from 'vue-router'
import HomePage from '../pages/HomePage.vue'
import ProjectPage from '../pages/ProjectPage.vue'
import CalibrationPage from '../pages/CalibrationPage.vue'
import TrackingPage from '../pages/TrackingPage.vue'
import TrackingReviewPage from '../pages/TrackingReviewPage.vue'
import PipelinePage from '../pages/PipelinePage.vue'
import QuizBuilderPage from '../pages/QuizBuilderPage.vue'
import QuizPlayPage from '../pages/QuizPlayPage.vue'
import RoleEntryPage from '../pages/RoleEntryPage.vue'
import TrainingLobbyPage from '../pages/TrainingLobbyPage.vue'
import SituationPreviewPage from '../pages/SituationPreviewPage.vue'

export const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', name: 'home', component: HomePage },
    { path: '/start', name: 'role-entry', component: RoleEntryPage },
    { path: '/training', name: 'training-lobby', component: TrainingLobbyPage },
    { path: '/situations', name: 'situation-preview', component: SituationPreviewPage },
    { path: '/projects/:projectId', name: 'project', component: ProjectPage, props: true },
    { path: '/projects/:projectId/calibration', name: 'calibration', component: CalibrationPage, props: true },
    { path: '/projects/:projectId/pipeline', name: 'pipeline', component: PipelinePage, props: true },
    { path: '/projects/:projectId/tracking', name: 'tracking', component: TrackingPage, props: true },
    { path: '/projects/:projectId/tracking-review', name: 'tracking-review', component: TrackingReviewPage, props: true },
    { path: '/projects/:projectId/quiz-builder', name: 'quiz-builder', component: QuizBuilderPage, props: true },
    { path: '/projects/:projectId/quiz/:promptId', name: 'quiz-play', component: QuizPlayPage, props: true }
  ]
})
