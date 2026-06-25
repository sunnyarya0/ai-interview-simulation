// Browser audio engine: mic capture -> 16kHz int16 PCM frames (+ client VAD),
// and gapless playback of the AI's WAV clips. Decoupled from the WebSocket:
// startCapture() takes onFrame/onUtteranceEnd callbacks (wired to wsClient in S25).

const FRAME_MS = 100
const SILENCE_LIMIT_MS = 800
const RMS_THRESHOLD = 0.015 // normalized [-1,1]; tune for your mic/room

let ctx = null
let stream = null
let sourceNode = null
let workletNode = null
let sinkGain = null

let handlers = {}
let listening = false
let muted = false

// VAD state
let speaking = false
let silenceMs = 0

// playback
let playCtx = null
let playHead = 0

function _rms(int16Buffer) {
  const view = new Int16Array(int16Buffer)
  let sum = 0
  for (let i = 0; i < view.length; i++) {
    const v = view[i] / 32768
    sum += v * v
  }
  return Math.sqrt(sum / view.length)
}

function _onFrame(arrayBuffer) {
  if (!listening || muted) return
  handlers.onFrame?.(arrayBuffer)

  const isSpeech = _rms(arrayBuffer) > RMS_THRESHOLD
  if (isSpeech) {
    speaking = true
    silenceMs = 0
  } else if (speaking) {
    silenceMs += FRAME_MS
    if (silenceMs >= SILENCE_LIMIT_MS) {
      speaking = false
      silenceMs = 0
      handlers.onUtteranceEnd?.()
    }
  }
}

export async function startCapture({ onFrame, onUtteranceEnd } = {}) {
  handlers = { onFrame, onUtteranceEnd }
  stream = await navigator.mediaDevices.getUserMedia({
    audio: { echoCancellation: true, noiseSuppression: true, autoGainControl: true, channelCount: 1 },
  })
  ctx = new AudioContext({ sampleRate: 16000 })
  await ctx.audioWorklet.addModule('/pcm-worklet.js')
  sourceNode = ctx.createMediaStreamSource(stream)
  workletNode = new AudioWorkletNode(ctx, 'pcm-worklet')
  workletNode.port.onmessage = (e) => _onFrame(e.data)

  // Route through a muted gain so the worklet's process() runs without audible passthrough.
  sinkGain = ctx.createGain()
  sinkGain.gain.value = 0
  sourceNode.connect(workletNode)
  workletNode.connect(sinkGain)
  sinkGain.connect(ctx.destination)
}

export function setListening(value) {
  listening = value
  if (value) {
    speaking = false
    silenceMs = 0
  }
}

export function setMuted(value) {
  muted = value
}

export async function stopCapture() {
  try {
    stream?.getTracks().forEach((t) => t.stop())
    sourceNode?.disconnect()
    workletNode?.disconnect()
    sinkGain?.disconnect()
    await ctx?.close()
  } finally {
    ctx = stream = sourceNode = workletNode = sinkGain = null
    listening = false
    speaking = false
    silenceMs = 0
  }
}

export async function playAudioChunk(arrayBuffer) {
  if (!playCtx) playCtx = new AudioContext()
  if (playCtx.state === 'suspended') await playCtx.resume()
  // decodeAudioData detaches the buffer — copy so callers keep theirs.
  const audioBuf = await playCtx.decodeAudioData(arrayBuffer.slice(0))
  const src = playCtx.createBufferSource()
  src.buffer = audioBuf
  src.connect(playCtx.destination)
  const startAt = Math.max(playCtx.currentTime, playHead)
  src.start(startAt)
  playHead = startAt + audioBuf.duration
}

export function resetPlayback() {
  playHead = 0
}
