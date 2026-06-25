import { defineStore } from 'pinia'
import { ref } from 'vue'

export const useInterviewStore = defineStore('interview', () => {
  const resumeId = ref(null)
  const resumeStatus = ref(null)
  const interviewId = ref(null)

  function reset() {
    resumeId.value = null
    resumeStatus.value = null
    interviewId.value = null
  }

  return { resumeId, resumeStatus, interviewId, reset }
})
