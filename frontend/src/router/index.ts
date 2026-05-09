import { createRouter, createWebHistory } from 'vue-router'
import HomePage from '../pages/HomePage.vue'
import ProjectPage from '../pages/ProjectPage.vue'
import CalibrationPage from '../pages/CalibrationPage.vue'
import TrackingPage from '../pages/TrackingPage.vue'

export const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', name: 'home', component: HomePage },
    { path: '/projects/:projectId', name: 'project', component: ProjectPage, props: true },
    { path: '/projects/:projectId/calibration', name: 'calibration', component: CalibrationPage, props: true },
    { path: '/projects/:projectId/tracking', name: 'tracking', component: TrackingPage, props: true }
  ]
})
