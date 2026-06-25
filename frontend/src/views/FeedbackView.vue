<script setup>
import { onMounted, onUnmounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { useInterviewStore } from '@/stores/interviewStore'
import { getFeedback } from '@/services/httpClient'

const route = useRoute()
const router = useRouter()
const store = useInterviewStore()
const interviewId = route.params.id

const feedback = ref(null)
const error = ref('')
let pollTimer = null

async function poll() {
  try {
    const data = await getFeedback(interviewId)
    if (data) {
      feedback.value = data
      clearInterval(pollTimer)
    }
  } catch (e) {
    error.value = e.message
    clearInterval(pollTimer)
  }
}

function scoreColor(score) {
  if (score >= 80) return 'text-green-600'
  if (score >= 60) return 'text-amber-600'
  return 'text-red-600'
}

function startNew() {
  store.reset()
  router.push('/')
}

onMounted(() => {
  poll()
  pollTimer = setInterval(poll, 2000)
})
onUnmounted(() => clearInterval(pollTimer))
</script>

<template>
  <div class="min-h-screen bg-slate-50 py-10 px-4">
    <div class="max-w-3xl mx-auto">
      <!-- loading -->
      <div v-if="!feedback && !error" class="flex flex-col items-center justify-center gap-4 py-32">
        <div class="h-10 w-10 border-4 border-indigo-200 border-t-indigo-600 rounded-full animate-spin"></div>
        <p class="text-slate-600">Generating your feedback…</p>
      </div>

      <p v-else-if="error" class="text-center text-red-600 py-32">{{ error }}</p>

      <!-- report -->
      <div v-else class="space-y-6">
        <div class="text-center">
          <h1 class="text-2xl font-bold text-slate-800">Interview Feedback</h1>
        </div>

        <!-- overall score -->
        <div class="bg-white rounded-2xl shadow-sm p-8 flex flex-col items-center">
          <p class="text-slate-500 text-sm uppercase tracking-wide mb-2">Overall Score</p>
          <p :class="['text-6xl font-bold', scoreColor(feedback.overall_score)]">{{ feedback.overall_score }}</p>
          <p class="text-slate-400 text-sm">out of 100</p>
        </div>

        <!-- assessments -->
        <div class="grid gap-4 sm:grid-cols-3">
          <div v-for="key in ['communication','technical','resume_knowledge']" :key="key" class="bg-white rounded-xl shadow-sm p-5">
            <p class="text-slate-500 text-xs uppercase tracking-wide capitalize">{{ key.replace('_',' ') }}</p>
            <p :class="['text-3xl font-bold my-1', scoreColor(feedback[key].score)]">{{ feedback[key].score }}</p>
            <p class="text-slate-600 text-sm">{{ feedback[key].comment }}</p>
          </div>
        </div>

        <!-- lists -->
        <div class="grid gap-4 sm:grid-cols-3">
          <div class="bg-white rounded-xl shadow-sm p-5">
            <h2 class="font-semibold text-green-700 mb-2">Strengths</h2>
            <ul class="list-disc list-inside text-sm text-slate-600 space-y-1">
              <li v-for="(s, i) in feedback.strengths" :key="i">{{ s }}</li>
            </ul>
          </div>
          <div class="bg-white rounded-xl shadow-sm p-5">
            <h2 class="font-semibold text-amber-700 mb-2">Weaknesses</h2>
            <ul class="list-disc list-inside text-sm text-slate-600 space-y-1">
              <li v-for="(w, i) in feedback.weaknesses" :key="i">{{ w }}</li>
            </ul>
          </div>
          <div class="bg-white rounded-xl shadow-sm p-5">
            <h2 class="font-semibold text-indigo-700 mb-2">Improvements</h2>
            <ul class="list-disc list-inside text-sm text-slate-600 space-y-1">
              <li v-for="(im, i) in feedback.improvements" :key="i">{{ im }}</li>
            </ul>
          </div>
        </div>

        <div class="text-center pt-2">
          <button @click="startNew" class="px-6 py-3 rounded-lg bg-indigo-600 text-white font-semibold hover:bg-indigo-700">
            Start New Interview
          </button>
        </div>
      </div>
    </div>
  </div>
</template>
