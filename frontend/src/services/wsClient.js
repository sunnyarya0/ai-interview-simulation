// Thin WebSocket wrapper for the live interview. Binary frames carry AI audio;
// text frames carry JSON control messages. Events are emitted by message type
// (state, transcript, interview_end, error) plus 'audio', 'open', 'close',
// 'reconnecting', 'reconnected'. Auto-reconnects on unexpected drops.

const WS_BASE_URL = import.meta.env.VITE_WS_BASE_URL ?? 'ws://localhost:8000'
const MAX_RETRIES = 5

let ws = null
let listeners = {}
let currentId = null
let intentional = false
let retries = 0
let retryTimer = null

export function on(event, handler) {
  ;(listeners[event] ||= []).push(handler)
}

function emit(event, payload) {
  ;(listeners[event] || []).forEach((h) => h(payload))
}

function open(interviewId, isRetry) {
  ws = new WebSocket(`${WS_BASE_URL}/interviews/${interviewId}/stream`)
  ws.binaryType = 'arraybuffer'
  ws.onopen = () => {
    if (isRetry) {
      retries = 0
      emit('reconnected')
    }
    emit('open')
  }
  ws.onclose = () => {
    if (intentional) return
    if (retries < MAX_RETRIES) {
      retries += 1
      const delay = Math.min(1000 * 2 ** (retries - 1), 8000)
      emit('reconnecting', { attempt: retries, delay })
      retryTimer = setTimeout(() => open(currentId, true), delay)
    } else {
      emit('close')
    }
  }
  ws.onerror = (e) => emit('wserror', e)
  ws.onmessage = (ev) => {
    if (typeof ev.data === 'string') {
      const msg = JSON.parse(ev.data)
      emit(msg.type, msg)
    } else {
      emit('audio', ev.data) // ArrayBuffer (WAV)
    }
  }
}

export function connect(interviewId) {
  currentId = interviewId
  intentional = false
  retries = 0
  open(interviewId, false)
}

export function sendAudioFrame(buffer) {
  if (ws && ws.readyState === WebSocket.OPEN) ws.send(buffer)
}

export function sendControl(obj) {
  if (ws && ws.readyState === WebSocket.OPEN) ws.send(JSON.stringify(obj))
}

export function disconnect() {
  intentional = true
  clearTimeout(retryTimer)
  if (ws) {
    ws.onclose = null
    ws.close()
    ws = null
  }
  listeners = {}
}

export { WS_BASE_URL }
