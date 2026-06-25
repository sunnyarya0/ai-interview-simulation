<script setup>
import { onMounted, onUnmounted, ref, nextTick } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useMediaStore } from '@/stores/mediaStore'
import * as ws from '@/services/wsClient'
import * as audio from '@/services/audioEngine'

const route = useRoute()
const router = useRouter()
const media = useMediaStore()
const interviewId = route.params.id

const error = ref('')
const muted = ref(false)
const ending = ref(false)
const captionsEl = ref(null)

function scrollCaptions() {
  nextTick(() => {
    if (captionsEl.value) captionsEl.value.scrollTop = captionsEl.value.scrollHeight
  })
}

let cleanedUp = false
async function cleanup() {
  if (cleanedUp) return
  cleanedUp = true
  await audio.stopCapture()
  ws.disconnect()
}

onMounted(async () => {
  media.reset()

  ws.on('open', () => (media.connected = true))
  ws.on('close', () => (media.connected = false))
  ws.on('state', (m) => {
    const listening = m.value === 'listening'
    media.isListening = listening
    media.isAiSpeaking = !listening && m.value !== 'done'
    audio.setListening(listening)
  })
  ws.on('transcript', (m) => {
    media.transcript.push({ speaker: m.speaker, text: m.text })
    scrollCaptions()
  })
  ws.on('audio', (buf) => audio.playAudioChunk(buf))
  ws.on('interview_end', async () => {
    await cleanup()
    router.push(`/feedback/${interviewId}`)
  })
  ws.on('error', (m) => (error.value = m.message || 'Something went wrong.'))

  ws.connect(interviewId)
  try {
    await audio.startCapture({
      onFrame: (buf) => ws.sendAudioFrame(buf),
      onUtteranceEnd: () => ws.sendControl({ type: 'end_of_utterance' }),
    })
  } catch (e) {
    error.value = 'Microphone access is required for the interview. ' + e.message
  }
})

function toggleMute() {
  muted.value = !muted.value
  audio.setMuted(muted.value)
}

function endInterview() {
  ending.value = true
  ws.sendControl({ type: 'end_interview' })
}

onUnmounted(cleanup)
</script>

<template>
  <div class="min-h-screen flex flex-col bg-slate-900 text-slate-100">
    <!-- header -->
    <div class="flex items-center justify-between px-6 py-3 border-b border-slate-700">
      <h1 class="font-semibold">AI Interview</h1>
      <div class="flex items-center gap-2 text-sm">
        <span :class="['h-2 w-2 rounded-full', media.connected ? 'bg-green-400' : 'bg-slate-500']"></span>
        <span class="text-slate-400">{{ media.connected ? 'Connected' : 'Connecting…' }}</span>
      </div>
    </div>

    <div class="flex-1 flex flex-col md:flex-row overflow-hidden">
      <!-- AI orb -->
      <div class="flex-1 flex flex-col items-center justify-center gap-6 p-8">
        <div
          :class="['h-40 w-40 rounded-full flex items-center justify-center transition-all duration-300',
                   media.isAiSpeaking ? 'bg-indigo-500 scale-110 shadow-[0_0_60px_rgba(99,102,241,0.6)] animate-pulse'
                   : media.isListening ? 'bg-green-600/30 ring-4 ring-green-400'
                   : 'bg-slate-700']"
        >
          <span class="text-5xl">🤖</span>
        </div>
        <p class="text-slate-300 h-6">
          <span v-if="media.isAiSpeaking">AI is speaking…</span>
          <span v-else-if="media.isListening">Listening — go ahead</span>
          <span v-else>…</span>
        </p>
      </div>

      <!-- captions -->
      <div class="w-full md:w-96 border-t md:border-t-0 md:border-l border-slate-700 flex flex-col">
        <div class="px-4 py-2 text-xs uppercase tracking-wide text-slate-500 border-b border-slate-700">Transcript</div>
        <div ref="captionsEl" class="flex-1 overflow-y-auto p-4 space-y-3">
          <div v-for="(t, i) in media.transcript" :key="i" :class="t.speaker === 'candidate' ? 'text-right' : 'text-left'">
            <span
              :class="['inline-block px-3 py-2 rounded-lg text-sm max-w-[85%]',
                       t.speaker === 'candidate' ? 'bg-indigo-600 text-white' : 'bg-slate-700 text-slate-100']"
            >{{ t.text }}</span>
          </div>
        </div>
      </div>
    </div>

    <!-- controls -->
    <div class="flex items-center justify-center gap-4 px-6 py-4 border-t border-slate-700">
      <button
        @click="toggleMute"
        :class="['px-5 py-2 rounded-lg font-medium', muted ? 'bg-amber-600' : 'bg-slate-700 hover:bg-slate-600']"
      >{{ muted ? '🔇 Unmute' : '🎤 Mute' }}</button>
      <button
        @click="endInterview"
        :disabled="ending"
        class="px-5 py-2 rounded-lg bg-red-600 hover:bg-red-700 font-medium disabled:opacity-50"
      >{{ ending ? 'Ending…' : 'End Interview' }}</button>
    </div>

    <p v-if="error" class="text-center text-red-400 text-sm pb-4">{{ error }}</p>
  </div>
</template>
