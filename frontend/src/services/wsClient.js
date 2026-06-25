// Thin WebSocket wrapper for the live interview. Binary frames carry AI audio;
// text frames carry JSON control messages. Events are emitted by message type
// (state, transcript, interview_end, error) plus 'audio', 'open', 'close', 'wserror'.

const WS_BASE_URL = import.meta.env.VITE_WS_BASE_URL ?? 'ws://localhost:8000'

let ws = null
let listeners = {}

export function on(event, handler) {
  ;(listeners[event] ||= []).push(handler)
}

function emit(event, payload) {
  ;(listeners[event] || []).forEach((h) => h(payload))
}

export function connect(interviewId) {
  ws = new WebSocket(`${WS_BASE_URL}/interviews/${interviewId}/stream`)
  ws.binaryType = 'arraybuffer'
  ws.onopen = () => emit('open')
  ws.onclose = () => emit('close')
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

export function sendAudioFrame(buffer) {
  if (ws && ws.readyState === WebSocket.OPEN) ws.send(buffer)
}

export function sendControl(obj) {
  if (ws && ws.readyState === WebSocket.OPEN) ws.send(JSON.stringify(obj))
}

export function disconnect() {
  if (ws) {
    ws.onclose = null // avoid emitting close during intentional teardown
    ws.close()
    ws = null
  }
  listeners = {}
}

export { WS_BASE_URL }
