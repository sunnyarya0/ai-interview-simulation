const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000'

export async function uploadResume(_file) {
  throw new Error('not implemented')
}

export async function getResumeStatus(_id) {
  throw new Error('not implemented')
}

export async function createInterview(_resumeId) {
  throw new Error('not implemented')
}

export async function getFeedback(_interviewId) {
  throw new Error('not implemented')
}

export { BASE_URL }
