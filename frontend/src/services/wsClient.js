const WS_BASE_URL = import.meta.env.VITE_WS_BASE_URL ?? 'ws://localhost:8000'

export function connect(_interviewId) {
  throw new Error('not implemented')
}

export function disconnect() {
  throw new Error('not implemented')
}

export function sendAudioFrame(_buffer) {
  throw new Error('not implemented')
}

export function on(_event, _handler) {
  throw new Error('not implemented')
}

export { WS_BASE_URL }
