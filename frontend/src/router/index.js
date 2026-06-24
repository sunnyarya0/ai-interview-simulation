import { createRouter, createWebHistory } from 'vue-router'
import UploadView from '@/views/UploadView.vue'
import InterviewRoomView from '@/views/InterviewRoomView.vue'
import FeedbackView from '@/views/FeedbackView.vue'

const routes = [
  { path: '/', component: UploadView },
  { path: '/interview/:id', component: InterviewRoomView },
  { path: '/feedback/:id', component: FeedbackView },
]

export default createRouter({
  history: createWebHistory(),
  routes,
})
