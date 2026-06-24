import { defineStore } from 'pinia'
import { ref } from 'vue'

export const useMediaStore = defineStore('media', () => {
  const isMicActive = ref(false)
  const isAiSpeaking = ref(false)

  return { isMicActive, isAiSpeaking }
})
