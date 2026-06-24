import { defineStore } from 'pinia'
import { ref } from 'vue'

export const useInterviewStore = defineStore('interview', () => {
  const interviewId = ref(null)
  const resumeId = ref(null)
  const status = ref(null)

  return { interviewId, resumeId, status }
})
