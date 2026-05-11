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
import LocalLabPage from '../pages/LocalLabPage.vue'
import ReferenceVideosPage from '../pages/ReferenceVideosPage.vue'
import ReferenceVideoDetailPage from '../pages/ReferenceVideoDetailPage.vue'
import DecisionRulesPage from '../pages/DecisionRulesPage.vue'
import PlayerValuePage from '../pages/PlayerValuePage.vue'
import PlayerValueDetailPage from '../pages/PlayerValueDetailPage.vue'

export const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', name: 'home', component: HomePage },
    { path: '/start', name: 'role-entry', component: RoleEntryPage },
    { path: '/training', name: 'training-lobby', component: TrainingLobbyPage },
    { path: '/situations', name: 'situation-preview', component: SituationPreviewPage },
    { path: '/local-lab', name: 'local-lab', component: LocalLabPage },
    { path: '/player-value', name: 'player-value', component: PlayerValuePage },
    { path: '/player-value/:projectId/:playerKey', name: 'player-value-detail', component: PlayerValueDetailPage, props: true },
    { path: '/reference-videos', name: 'reference-videos', component: ReferenceVideosPage },
    { path: '/reference-videos/:referenceId', name: 'reference-video-detail', component: ReferenceVideoDetailPage, props: true },
    { path: '/decision-rules', name: 'decision-rules', component: DecisionRulesPage },
    { path: '/projects/:projectId', name: 'project', component: ProjectPage, props: true },
    { path: '/projects/:projectId/calibration', name: 'calibration', component: CalibrationPage, props: true },
    { path: '/projects/:projectId/pipeline', name: 'pipeline', component: PipelinePage, props: true },
    { path: '/projects/:projectId/tracking', name: 'tracking', component: TrackingPage, props: true },
    { path: '/projects/:projectId/tracking-review', name: 'tracking-review', component: TrackingReviewPage, props: true },
    { path: '/projects/:projectId/quiz-builder', name: 'quiz-builder', component: QuizBuilderPage, props: true },
    { path: '/projects/:projectId/quiz/:promptId', name: 'quiz-play', component: QuizPlayPage, props: true }
  ]
})
