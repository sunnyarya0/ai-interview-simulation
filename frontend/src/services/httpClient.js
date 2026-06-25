const BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000'

async function _json(res) {
  if (!res.ok) {
    let detail = `HTTP ${res.status}`
    try {
      const body = await res.json()
      detail = body.detail ?? detail
    } catch {
      // non-JSON error body
    }
    throw new Error(detail)
  }
  return res.json()
}

export async function uploadResume(file) {
  const form = new FormData()
  form.append('file', file)
  const res = await fetch(`${BASE_URL}/resumes`, { method: 'POST', body: form })
  return _json(res) // { resume_id, status }
}

export async function getResumeStatus(id) {
  const res = await fetch(`${BASE_URL}/resumes/${id}/status`)
  return _json(res) // { resume_id, status }
}

export async function createInterview(resumeId) {
  const res = await fetch(`${BASE_URL}/interviews`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({ resume_id: resumeId }),
  })
  return _json(res) // { interview_id, ... }
}

export async function getFeedback(interviewId) {
  const res = await fetch(`${BASE_URL}/interviews/${interviewId}/feedback`)
  if (res.status === 404) return null // not ready yet
  return _json(res)
}

export { BASE_URL }
