import { defineStore } from 'pinia'
import { ref } from 'vue'

export const useMediaStore = defineStore('media', () => {
  const connected = ref(false)
  const reconnecting = ref(false)
  const isListening = ref(false)
  const isAiSpeaking = ref(false)
  const transcript = ref([]) // [{ speaker: 'ai'|'candidate', text }]

  function reset() {
    connected.value = false
    reconnecting.value = false
    isListening.value = false
    isAiSpeaking.value = false
    transcript.value = []
  }

  return { connected, reconnecting, isListening, isAiSpeaking, transcript, reset }
})
