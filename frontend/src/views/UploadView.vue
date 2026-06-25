<script setup>
import { ref, onUnmounted } from 'vue'
import { useRouter } from 'vue-router'
import { useInterviewStore } from '@/stores/interviewStore'
import { uploadResume, getResumeStatus, createInterview } from '@/services/httpClient'

const router = useRouter()
const store = useInterviewStore()

const dragging = ref(false)
const error = ref('')
const status = ref('') // '' | uploading | uploaded | processing | ready | failed
const starting = ref(false)
let pollTimer = null

const ALLOWED = ['application/pdf', 'application/vnd.openxmlformats-officedocument.wordprocessingml.document']

function pickFile() {
  const input = document.createElement('input')
  input.type = 'file'
  input.accept = '.pdf,.docx'
  input.onchange = (e) => handleFile(e.target.files[0])
  input.click()
}

function onDrop(e) {
  dragging.value = false
  handleFile(e.dataTransfer.files[0])
}

async function handleFile(file) {
  error.value = ''
  if (!file) return
  if (file.type && !ALLOWED.includes(file.type) && !/\.(pdf|docx)$/i.test(file.name)) {
    error.value = 'Please upload a PDF or DOCX file.'
    return
  }
  status.value = 'uploading'
  try {
    const { resume_id } = await uploadResume(file)
    store.resumeId = resume_id
    status.value = 'processing'
    startPolling(resume_id)
  } catch (e) {
    error.value = e.message
    status.value = 'failed'
  }
}

function startPolling(id) {
  clearInterval(pollTimer)
  pollTimer = setInterval(async () => {
    try {
      const { status: s } = await getResumeStatus(id)
      status.value = s
      store.resumeStatus = s
      if (s === 'ready' || s === 'failed') clearInterval(pollTimer)
    } catch (e) {
      error.value = e.message
      clearInterval(pollTimer)
    }
  }, 2000)
}

async function start() {
  starting.value = true
  error.value = ''
  try {
    const { interview_id } = await createInterview(store.resumeId)
    store.interviewId = interview_id
    router.push(`/interview/${interview_id}`)
  } catch (e) {
    error.value = e.message
    starting.value = false
  }
}

onUnmounted(() => clearInterval(pollTimer))
</script>

<template>
  <div class="min-h-screen flex flex-col items-center justify-center bg-slate-50 p-6">
    <div class="w-full max-w-xl text-center">
      <h1 class="text-3xl font-bold text-slate-800 mb-2">AI Interview Simulator</h1>
      <p class="text-slate-500 mb-8">Upload your resume to begin a personalized voice interview.</p>

      <div
        v-if="!status || status === 'failed'"
        @dragover.prevent="dragging = true"
        @dragleave.prevent="dragging = false"
        @drop.prevent="onDrop"
        @click="pickFile"
        :class="['border-2 border-dashed rounded-xl p-12 cursor-pointer transition',
                 dragging ? 'border-indigo-500 bg-indigo-50' : 'border-slate-300 bg-white hover:border-indigo-400']"
      >
        <p class="text-slate-600 font-medium">Drag & drop your resume here</p>
        <p class="text-slate-400 text-sm mt-1">or click to browse — PDF or DOCX</p>
      </div>

      <div v-else class="bg-white rounded-xl p-10 shadow-sm">
        <div v-if="status !== 'ready'" class="flex flex-col items-center gap-4">
          <div class="h-10 w-10 border-4 border-indigo-200 border-t-indigo-600 rounded-full animate-spin"></div>
          <p class="text-slate-600 capitalize">{{ status === 'uploading' ? 'Uploading…' : 'Processing your resume…' }}</p>
        </div>
        <div v-else class="flex flex-col items-center gap-5">
          <div class="h-12 w-12 rounded-full bg-green-100 flex items-center justify-center text-green-600 text-2xl">✓</div>
          <p class="text-slate-700 font-medium">Resume ready!</p>
          <button
            @click="start"
            :disabled="starting"
            class="px-6 py-3 rounded-lg bg-indigo-600 text-white font-semibold hover:bg-indigo-700 disabled:opacity-50"
          >
            {{ starting ? 'Starting…' : 'Start Interview' }}
          </button>
        </div>
      </div>

      <p v-if="error" class="mt-4 text-red-600 text-sm">{{ error }}</p>
    </div>
  </div>
</template>
