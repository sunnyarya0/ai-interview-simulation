// Runs on the audio thread. Input is already 16kHz mono float32 (the AudioContext
// is created at sampleRate:16000), so we only convert to int16 and post ~100ms frames.
class PCMWorklet extends AudioWorkletProcessor {
  constructor() {
    super()
    this._target = 1600 // 100ms at 16kHz
    this._buf = new Int16Array(this._target)
    this._n = 0
  }

  process(inputs) {
    const input = inputs[0]
    if (input && input[0]) {
      const ch = input[0] // Float32Array, 128 samples per quantum
      for (let i = 0; i < ch.length; i++) {
        const s = Math.max(-1, Math.min(1, ch[i]))
        this._buf[this._n++] = s < 0 ? s * 0x8000 : s * 0x7fff
        if (this._n >= this._target) {
          const out = this._buf.slice(0, this._n)
          this.port.postMessage(out.buffer, [out.buffer])
          this._n = 0
        }
      }
    }
    return true
  }
}

registerProcessor('pcm-worklet', PCMWorklet)
