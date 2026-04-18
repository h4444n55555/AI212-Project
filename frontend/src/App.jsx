import { useState, useRef, useCallback, useEffect } from 'react'
import './App.css'

/* ─── constants ─────────────────────────────────────────────── */
const CLASS_COLORS = ['#2E7D55', '#1A5EA8', '#8A5200', '#7B2D8B', '#C0392B', '#17786E']
function colorFor(label) {
  let h = 0
  for (let i = 0; i < label.length; i++) h = (h * 31 + label.charCodeAt(i)) & 0xFFFF
  return CLASS_COLORS[h % CLASS_COLORS.length]
}

/* ─── Topbar ────────────────────────────────────────────────── */
function Topbar({ theme, onToggleTheme, statusText, statusColor }) {
  return (
    <header className="topbar">
      <div className="brand">Detect <span>/ object detection</span></div>
      <div className="topright">
        <div className="status-pill">
          <span className={`dot dot-${statusColor}`} />
          <span>{statusText}</span>
        </div>
        <button className="theme-btn" onClick={onToggleTheme}>
          {/* Sun icon – shown in dark mode */}
          {theme === 'dark' && (
            <svg viewBox="0 0 16 16" fill="none">
              <circle cx="8" cy="8" r="3" stroke="currentColor" strokeWidth="1.4" />
              <path d="M8 1v2M8 13v2M1 8h2M13 8h2M3.22 3.22l1.42 1.42M11.36 11.36l1.42 1.42M3.22 12.78l1.42-1.42M11.36 4.64l1.42-1.42"
                stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" />
            </svg>
          )}
          {/* Moon icon – shown in light mode */}
          {theme === 'light' && (
            <svg viewBox="0 0 16 16" fill="none">
              <path d="M13.5 10A6 6 0 016 2.5a6 6 0 100 11 6 6 0 007.5-3.5z"
                stroke="currentColor" strokeWidth="1.4" strokeLinejoin="round" />
            </svg>
          )}
          <span>{theme === 'light' ? 'Dark' : 'Light'}</span>
        </button>
      </div>
    </header>
  )
}

/* ─── Tabs ──────────────────────────────────────────────────── */
function Tabs({ activeTab, onSwitch }) {
  return (
    <nav className="tabs">
      {['vision', 'analytics'].map(t => (
        <div
          key={t}
          className={`tab${activeTab === t ? ' active' : ''}`}
          onClick={() => onSwitch(t)}
        >
          {t.charAt(0).toUpperCase() + t.slice(1)}
        </div>
      ))}
    </nav>
  )
}

/* ─── VisionPanel ───────────────────────────────────────────── */
function VisionPanel({ active, onStatusChange, onLogAppend, onLatencyRecord, onClassCount }) {
  const [source, setSource]         = useState('upload')
  const [confidence, setConfidence] = useState(0.50)
  const [detections, setDetections] = useState([])
  const [activeToken, setActiveToken] = useState(0)
  const [latencyMs, setLatencyMs]   = useState(null)
  const [hasImage, setHasImage]     = useState(false)
  const [streaming, setStreaming]   = useState(false)

  const fileInputRef    = useRef(null)
  const previewImgRef   = useRef(null)
  const detCanvasRef    = useRef(null)
  const webcamVideoRef  = useRef(null)
  const webcamCanvasRef = useRef(null)
  const camStreamRef    = useRef(null)

  /* ── helpers ── */
  const renderBoxes = useCallback((dets, canvas, mediaEl) => {
    const cvs = canvas
    const ctx = cvs.getContext('2d')
    
    const intrinsicW = mediaEl ? (mediaEl.naturalWidth || mediaEl.videoWidth || cvs.offsetWidth) : cvs.offsetWidth
    const intrinsicH = mediaEl ? (mediaEl.naturalHeight || mediaEl.videoHeight || cvs.offsetHeight) : cvs.offsetHeight

    cvs.width  = intrinsicW
    cvs.height = intrinsicH
    ctx.clearRect(0, 0, cvs.width, cvs.height)

    // YOLO returns coords in intrinsic resolution, and our canvas internal resolution now matches intrinsic resolution.
    // Therefore scale is 1. (CSS will purely handle scaling the canvas visually).
    const scaleX = 1
    const scaleY = 1

    dets.forEach(d => {
      if (d.confidence < confidence) return
      const [x, y, w, h] = d.bbox
      const col = colorFor(d.label)
      ctx.strokeStyle = col
      ctx.lineWidth   = 1.5
      ctx.strokeRect(x * scaleX, y * scaleY, w * scaleX, h * scaleY)
      ctx.fillStyle = col
      const text = `${d.label} ${d.confidence.toFixed(2)}`
      const tw   = ctx.measureText(text).width
      ctx.fillRect(x * scaleX, (y * scaleY) - 18, tw + 10, 16)
      ctx.fillStyle = '#fff'
      ctx.font      = '10px Geist Mono, monospace'
      ctx.fillText(text, x * scaleX + 5, (y * scaleY) - 5)
    })
  }, [confidence])

  /* ── source toggle ── */
  const switchSource = (src) => {
    setSource(src)
    if (src !== 'webcam') {
      stopCamera()
      onStatusChange('model ready', 'green')
    }
  }

  /* ── upload / file ── */
  const triggerUpload = () => fileInputRef.current?.click()

  const handleFile = async (file) => {
    if (!file) return
    const url = URL.createObjectURL(file)
    const img  = previewImgRef.current
    img.src = url
    setHasImage(true)
    onStatusChange('processing…', 'green')
    
    try {
      const formData = new FormData()
      formData.append('file', file)
      const res = await fetch('/api/detect', { method: 'POST', body: formData })
      if (!res.ok) throw new Error(`API returned ${res.status}`)
      
      const data = await res.json()
      setDetections(data.detections || [])
      setLatencyMs(data.latency_ms)
      
      onLogAppend('POST', '/api/detect', res.status, data.latency_ms)
      onLatencyRecord(data.latency_ms)
      if (data.detections) {
        data.detections.forEach(d => {
          if (d.confidence >= confidence) onClassCount(d.label)
        })
      }
      onStatusChange('model ready', 'green')

      // Ensure boxes are drawn after state updates
      requestAnimationFrame(() => {
        if (detCanvasRef.current && previewImgRef.current) {
           renderBoxes(data.detections, detCanvasRef.current, previewImgRef.current)
        }
      })
    } catch (err) {
      console.error(err)
      onLogAppend('POST', '/api/detect', 500)
      onStatusChange('error', 'red')
    }
  }

  const handleDrop = (e) => {
    e.preventDefault()
    const file = e.dataTransfer.files[0]
    if (file && file.type.startsWith('image/')) handleFile(file)
  }

  /* ── confidence ── */
  const handleConf = (v) => {
    const val = parseFloat(v) / 100
    setConfidence(val)
    // re-render boxes with new threshold
    if (detections.length && detCanvasRef.current && previewImgRef.current) {
      renderBoxes(detections, detCanvasRef.current, previewImgRef.current)
    }
  }

  /* ── webcam inference loop ── */
  const sendFrame = useCallback(async () => {
    if (!camStreamRef.current) return
    
    const video = webcamVideoRef.current
    const canvas = webcamCanvasRef.current
    if (!video || !canvas || video.readyState < 2) return

    // Capture frame natively via a detached layout canvas so we don't flash the transparent overlay
    const captureCvs = document.createElement('canvas')
    captureCvs.width = video.videoWidth
    captureCvs.height = video.videoHeight
    captureCvs.getContext('2d').drawImage(video, 0, 0)
    
    try {
      const blob = await new Promise(resolve => captureCvs.toBlob(resolve, 'image/jpeg', 0.8))
      if (!blob) return

      const formData = new FormData()
      formData.append('file', blob, 'frame.jpg')
      
      const res = await fetch('/api/detect', { method: 'POST', body: formData })
      if (res.ok) {
        const data = await res.json()
        setDetections(data.detections || [])
        setLatencyMs(data.latency_ms)
        onLatencyRecord(data.latency_ms)
        
        requestAnimationFrame(() => renderBoxes(data.detections, canvas, video))
      }
    } catch (err) {
      console.error('Frame drop', err)
    }
  }, [renderBoxes, onLatencyRecord])

  /* ── webcam ── */
  const startCamera = async () => {
    try {
      const stream = await navigator.mediaDevices.getUserMedia({ video: true })
      camStreamRef.current = stream
      const video = webcamVideoRef.current
      video.srcObject = stream
      video.dataset.loopActive = "true"
      setStreaming(true)
      onStatusChange('live stream', 'red')
      onLogAppend('GET', '/camera/start', 200)

      // Self-pacing inference loop
      const loop = async () => {
        if (!camStreamRef.current || video.dataset.loopActive !== "true") return
        await sendFrame() // Await the current frame response before moving on
        
        // Wait 100ms before snagging the next frame to yield to the UI thread
        setTimeout(() => {
          requestAnimationFrame(loop)
        }, 100)
      }
      loop()

    } catch (err) {
      onStatusChange('camera error', 'green')
      console.error('Camera error:', err)
    }
  }

  const stopCamera = () => {
    camStreamRef.current?.getTracks().forEach(t => t.stop())
    camStreamRef.current = null
    
    const video = webcamVideoRef.current
    if (video) {
        video.srcObject = null
        video.dataset.loopActive = "false"
    }
    setStreaming(false)
    onStatusChange('model ready', 'green')
  }

  const hudMeta = latencyMs != null
    ? `${detections.length} object${detections.length !== 1 ? 's' : ''} · ${Math.round(latencyMs)} ms`
    : '— objects · — ms'

  const filtered = detections.filter(d => d.confidence >= confidence)

  return (
    <section className={`panel${active ? ' active' : ''}`}>
      {/* Source selector */}
      <div className="src-row">
        {['upload', 'webcam'].map(s => (
          <button
            key={s}
            className={`src-btn${source === s ? ' active' : ''}`}
            data-src={s}
            onClick={() => switchSource(s)}
          >
            {s === 'upload' ? 'Upload image' : 'Webcam'}
          </button>
        ))}
      </div>

      <div className="vision-grid">
        {/* Left: viewport + confidence */}
        <div>
          <div
            className="viewport"
            onDragOver={e => e.preventDefault()}
            onDrop={handleDrop}
          >
            {/* Hidden file input */}
            <input
              ref={fileInputRef}
              type="file"
              accept="image/*"
              style={{ display: 'none' }}
              onChange={e => handleFile(e.target.files[0])}
            />

            {/* Upload area */}
            {source === 'upload' && !hasImage && (
              <div className="upload-area" onClick={triggerUpload}>
                <svg width="28" height="28" viewBox="0 0 24 24" fill="none"
                  stroke="currentColor" strokeWidth="1.2" strokeLinecap="round">
                  <rect x="3" y="3" width="18" height="18" rx="3" />
                  <path d="M12 8v8M8 12l4-4 4 4" />
                </svg>
                <p>click or drag an image to upload</p>
              </div>
            )}

            {/* Preview image */}
            {source === 'upload' && (
              <img
                ref={previewImgRef}
                alt="uploaded preview"
                className="preview-img"
                style={{ display: hasImage ? 'block' : 'none' }}
              />
            )}

            {/* Bounding box canvas */}
            {source === 'upload' && (
              <canvas ref={detCanvasRef} className="detection-canvas" />
            )}

            {/* Webcam area */}
            {source === 'webcam' && (
              <div className="webcam-area" style={{ display: 'flex' }}>
                <video
                  ref={webcamVideoRef}
                  className="webcam-video"
                  autoPlay muted playsInline
                  style={{ display: streaming ? 'block' : 'none' }}
                />
                <canvas ref={webcamCanvasRef} className="webcam-canvas" />
                {!streaming && (
                  <div className="cam-idle">
                    <div className="cam-icon">
                      <svg viewBox="0 0 16 16" fill="none" stroke="currentColor" strokeWidth="1.2">
                        <rect x="1" y="4" width="11" height="8" rx="2" />
                        <path d="M12 7l3-2v6l-3-2V7z" strokeLinejoin="round" />
                      </svg>
                    </div>
                    <p>camera not started</p>
                    <small>click &quot;start camera&quot; below</small>
                  </div>
                )}
              </div>
            )}
          </div>

          {/* Confidence threshold */}
          <div className="conf-row">
            <label htmlFor="conf-slider">Threshold</label>
            <input
              type="range" id="conf-slider"
              min="0" max="100" defaultValue="50" step="1"
              onInput={e => handleConf(e.target.value)}
            />
            <span className="conf-val">{confidence.toFixed(2)}</span>
          </div>
        </div>

        {/* Right: HUD */}
        <div className="hud">
          <div className="hud-label">Detections</div>

          <div className="token-list">
            {filtered.length === 0
              ? <div className="token-empty">no detections yet</div>
              : filtered.map((d, i) => (
                  <div
                    key={i}
                    className={`token${activeToken === i ? ' active' : ''}`}
                    onClick={() => setActiveToken(i)}
                  >
                    <div className="token-dot" style={{ background: colorFor(d.label) }} />
                    <span className="token-name">{d.label}</span>
                    <span className="token-conf">{d.confidence.toFixed(2)}</span>
                  </div>
                ))
            }
          </div>

          <hr className="hud-divider" />
          <div className="hud-meta">{hudMeta}</div>

          {/* Upload shortcut (hidden in webcam mode) */}
          {source === 'upload' && (
            <div className="drop-zone" onClick={triggerUpload}>
              <p>drop file or click to upload</p>
            </div>
          )}

          {/* Webcam controls */}
          {source === 'webcam' && (
            <div style={{ marginTop: '8px' }}>
              {!streaming && (
                <button
                  className="src-btn active"
                  style={{ width: '100%', marginBottom: '6px' }}
                  onClick={startCamera}
                >
                  Start camera
                </button>
              )}
              {streaming && (
                <button className="stop-cam-btn" onClick={stopCamera}>
                  Stop camera
                </button>
              )}
            </div>
          )}
        </div>
      </div>
    </section>
  )
}

/* ─── AnalyticsPanel ────────────────────────────────────────── */
function AnalyticsPanel({ active, latencyHistory, classCounts, metrics, logs = [] }) {
  const sparkRef = useRef(null)
  const donutRef = useRef(null)

  /* draw sparkline whenever history changes */
  useEffect(() => {
    const canvas = sparkRef.current
    if (!canvas || !latencyHistory.length) return
    const data = latencyHistory
    const ctx  = canvas.getContext('2d')
    const W    = canvas.offsetWidth || 200
    const H    = 56
    canvas.width  = W
    canvas.height = H
    ctx.clearRect(0, 0, W, H)
    const min = Math.min(...data)
    const max = Math.max(...data) || 1
    const pts = data.map((v, i) => [
      (i / (data.length - 1 || 1)) * W,
      H - ((v - min) / (max - min + 1)) * (H - 8) - 4
    ])
    ctx.beginPath()
    pts.forEach(([x, y], i) => i === 0 ? ctx.moveTo(x, y) : ctx.lineTo(x, y))
    ctx.strokeStyle = getComputedStyle(document.documentElement).getPropertyValue('--bdr2')
    ctx.lineWidth   = 1.5
    ctx.stroke()
  }, [latencyHistory])

  /* compute donut segments */
  const total   = Object.values(classCounts).reduce((a, b) => a + b, 0)
  const entries = Object.entries(classCounts).sort((a, b) => b[1] - a[1])
  const cx = 36, cy = 36, r = 26, circ = 2 * Math.PI * r
  let offset = 0
  const segments = entries.map(([label, count]) => {
    const frac = count / total
    const dash = frac * circ
    const col  = colorFor(label)
    const seg  = { label, frac, dash, col, offset }
    offset += dash
    return seg
  })


  /* badge helpers */
  const cpuBadge  = metrics.cpu  != null && metrics.cpu  > 80  ? 'badge-warn' : 'badge-ok'
  const memBadge  = metrics.memGb != null && metrics.memGb / (metrics.memMax || 4) > 0.75 ? 'badge-warn' : 'badge-ok'
  const latBadge  = latencyHistory.length && latencyHistory[latencyHistory.length - 1] > 200 ? 'badge-warn' : 'badge-ok'

  return (
    <section className={`panel${active ? ' active' : ''}`}>
      {/* Metric cards */}
      <div className="metrics-grid">
        <div className="metric-card">
          <div className="metric-header">
            <span className="metric-label">Latency</span>
            <span className={`badge ${latBadge}`}>good</span>
          </div>
          <div className="metric-val">
            {latencyHistory.length
              ? Math.round(latencyHistory[latencyHistory.length - 1])
              : '—'}
            <span className="metric-unit"> ms</span>
          </div>
          <div className="metric-sub">avg last 10 inferences</div>
        </div>

        <div className="metric-card">
          <div className="metric-header">
            <span className="metric-label">CPU</span>
            <span className={`badge ${cpuBadge}`}>
              {metrics.cpu != null && metrics.cpu > 80 ? 'high' : 'normal'}
            </span>
          </div>
          <div className="metric-val">
            {metrics.cpu != null ? Math.round(metrics.cpu) : '—'}
            <span className="metric-unit"> %</span>
          </div>
          <div className="metric-sub">inside container</div>
        </div>

        <div className="metric-card">
          <div className="metric-header">
            <span className="metric-label">Memory</span>
            <span className={`badge ${memBadge}`}>
              {metrics.memGb != null && metrics.memGb / (metrics.memMax || 4) > 0.75 ? 'elevated' : 'normal'}
            </span>
          </div>
          <div className="metric-val">
            {metrics.memGb != null ? metrics.memGb.toFixed(1) : '—'}
            <span className="metric-unit"> GB</span>
          </div>
          <div className="metric-sub">of 4 GB allocated</div>
        </div>
      </div>

      {/* Charts row */}
      <div className="charts-row">
        <div className="chart-card">
          <div className="chart-label">Latency trend</div>
          <canvas ref={sparkRef} className="latency-chart" />
        </div>

        <div className="chart-card">
          <div className="chart-label">Class distribution</div>
          <div className="donut-wrap">
            <svg ref={donutRef} className="donut-svg" width="68" height="68" viewBox="0 0 72 72">
              <circle cx="36" cy="36" r="26" fill="none" stroke="var(--bg3)" strokeWidth="10" />
              {segments.map((seg, i) => (
                <circle
                  key={i}
                  cx={cx} cy={cy} r={r}
                  fill="none"
                  stroke={seg.col}
                  strokeWidth="10"
                  strokeDasharray={`${seg.dash} ${circ - seg.dash}`}
                  strokeDashoffset={-seg.offset}
                  transform={`rotate(-90 ${cx} ${cy})`}
                />
              ))}
            </svg>
            <ul className="legend-list">
              {segments.length === 0
                ? <li style={{ color: 'var(--txt3)', fontSize: '11px', fontFamily: 'var(--mono)' }}>no data yet</li>
                : segments.map((seg, i) => (
                    <li key={i}>
                      <div className="legend-dot" style={{ background: seg.col }} />
                      {seg.label} — {Math.round(seg.frac * 100)}%
                    </li>
                  ))
              }
            </ul>
          </div>
        </div>
      </div>

      {/* Request log */}
      <div className="log-label">Request log</div>
      <div className="log-box">
        {logs.length === 0
          ? (
            <div className="log-line">
              <span className="log-ts">—</span>
              <span style={{ color: 'var(--txt3)', fontFamily: 'var(--mono)', fontSize: '11px' }}>
                waiting for requests…
              </span>
            </div>
          )
          : logs.map((l, i) => (
            <div key={i} className="log-line">
              <span className="log-ts">{l.time}</span>
              <span className="log-method">{l.method}</span>
              <span style={{ color: 'var(--txt2)', flex: 1 }}>{l.path}</span>
              <span className={l.ok ? 'log-ok' : 'log-err'}>{l.code}</span>
              {l.ms != null && (
                <span style={{ color: 'var(--txt3)', fontFamily: 'var(--mono)' }}>{Math.round(l.ms)}ms</span>
              )}
            </div>
          ))
        }
      </div>
    </section>
  )
}

/* ─── App ───────────────────────────────────────────────────── */
export default function App() {
  const [theme, setTheme]             = useState('light')
  const [activeTab, setActiveTab]     = useState('vision')
  const [statusText, setStatusText]   = useState('model ready')
  const [statusColor, setStatusColor] = useState('green')
  const [latencyHistory, setLatencyHistory] = useState([])
  const [classCounts, setClassCounts] = useState({})
  const [metrics, setMetrics]         = useState({})
  const [logs, setLogs]               = useState([])

  const toggleTheme = () => {
    const next = theme === 'light' ? 'dark' : 'light'
    setTheme(next)
    document.documentElement.setAttribute('data-theme', next === 'dark' ? 'dark' : '')
  }

  const handleStatusChange = (text, color) => {
    setStatusText(text)
    setStatusColor(color)
  }

  const handleLogAppend = (method, path, code, ms) => {
    const time = new Date().toTimeString().slice(0, 8)
    setLogs(prev => [{ time, method, path, code, ok: code >= 200 && code < 300, ms }, ...prev].slice(0, 50))
  }

  const handleLatencyRecord = (ms) => {
    setLatencyHistory(prev => [...prev.slice(-19), ms])
  }

  const handleClassCount = (label) => {
    setClassCounts(prev => ({ ...prev, [label]: (prev[label] || 0) + 1 }))
  }

  useEffect(() => {
    let iv
    const poll = async () => {
      try {
        const res = await fetch('/api/health')
        if (!res.ok) throw new Error('Network response not ok')
        const data = await res.json()
        setMetrics({ cpu: data.cpu_percent, memGb: data.mem_used_gb, memMax: data.mem_total_gb })
      } catch (err) {
        handleStatusChange('backend offline', 'red')
        console.error('Health poll failed:', err)
      }
    }
    
    // Initial fetch, then periodic
    poll()
    iv = setInterval(poll, 5000)
    
    return () => clearInterval(iv)
  }, [])


  return (
    <div className="app">
      <Topbar
        theme={theme}
        onToggleTheme={toggleTheme}
        statusText={statusText}
        statusColor={statusColor}
      />

      <Tabs activeTab={activeTab} onSwitch={setActiveTab} />

      <VisionPanel
        active={activeTab === 'vision'}
        onStatusChange={handleStatusChange}
        onLogAppend={handleLogAppend}
        onLatencyRecord={handleLatencyRecord}
        onClassCount={handleClassCount}
      />

      <AnalyticsPanel
        active={activeTab === 'analytics'}
        latencyHistory={latencyHistory}
        classCounts={classCounts}
        metrics={metrics}
        logs={logs}
      />
    </div>
  )
}
