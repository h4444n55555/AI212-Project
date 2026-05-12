# React & Node.js Implementation - Code Snippets

## React Component Structure (`frontend/src/App.jsx`)

```jsx
import { useState, useRef, useCallback, useEffect } from 'react'
import './App.css'

// Main App component with state management
function App() {
  const [theme, setTheme] = useState('dark')
  const [activeTab, setActiveTab] = useState('vision')
  const [statusText, setStatusText] = useState('Ready')
  const [statusColor, setStatusColor] = useState('green')
  
  return (
    <div className={`app ${theme}`}>
      <Topbar 
        theme={theme} 
        onToggleTheme={() => setTheme(theme === 'dark' ? 'light' : 'dark')}
        statusText={statusText}
        statusColor={statusColor}
      />
      <Tabs activeTab={activeTab} onSwitch={setActiveTab} />
      
      {activeTab === 'vision' && <VisionPanel />}
      {activeTab === 'analytics' && <AnalyticsPanel />}
    </div>
  )
}

// Topbar component with theme toggle
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
          {theme === 'dark' ? '☀️ Light' : '🌙 Dark'}
        </button>
      </div>
    </header>
  )
}

// Vision Panel for image upload/webcam
function VisionPanel({ active, onStatusChange, onLogAppend }) {
  const [source, setSource] = useState('upload')
  const [confidence, setConfidence] = useState(0.50)
  const [detections, setDetections] = useState([])
  
  const fileInputRef = useRef(null)
  const previewImgRef = useRef(null)
  const detCanvasRef = useRef(null)

  // Handle image upload
  const handleImageUpload = useCallback(async (event) => {
    const file = event.target.files?.[0]
    if (!file) return
    
    const formData = new FormData()
    formData.append('file', file)
    
    try {
      onStatusChange('Detecting...', 'yellow')
      const response = await fetch('/api/detect', {
        method: 'POST',
        body: formData
      })
      const data = await response.json()
      
      setDetections(data.detections)
      renderBoxes(data.detections, detCanvasRef.current, previewImgRef.current)
      onStatusChange('Complete', 'green')
    } catch (error) {
      onStatusChange('Error', 'red')
    }
  }, [])

  // Render bounding boxes on canvas
  const renderBoxes = useCallback((dets, canvas, mediaEl) => {
    const ctx = canvas.getContext('2d')
    const intrinsicW = mediaEl.naturalWidth || canvas.offsetWidth
    const intrinsicH = mediaEl.naturalHeight || canvas.offsetHeight
    
    canvas.width = intrinsicW
    canvas.height = intrinsicH
    ctx.clearRect(0, 0, canvas.width, canvas.height)
    
    dets.forEach(d => {
      if (d.confidence < confidence) return
      const [x, y, w, h] = d.bbox
      const color = colorFor(d.label)
      
      ctx.strokeStyle = color
      ctx.lineWidth = 3
      ctx.strokeRect(x, y, w, h)
      
      // Draw label
      ctx.fillStyle = color
      ctx.font = '14px bold Arial'
      ctx.fillText(d.label, x, y - 5)
    })
  }, [confidence])

  return (
    <div className="vision-panel">
      <div className="controls">
        <input 
          type="file" 
          ref={fileInputRef} 
          onChange={handleImageUpload}
          accept="image/*"
        />
        <label>
          Confidence: {(confidence * 100).toFixed(0)}%
          <input 
            type="range" 
            min="0" 
            max="1" 
            step="0.01"
            value={confidence}
            onChange={(e) => setConfidence(parseFloat(e.target.value))}
          />
        </label>
      </div>
      
      <div className="preview">
        <img ref={previewImgRef} />
        <canvas ref={detCanvasRef} />
      </div>
    </div>
  )
}
```

## Node.js Build Configuration (`frontend/package.json`)

```json
{
  "name": "my-react-app",
  "private": true,
  "version": "0.0.0",
  "type": "module",
  "scripts": {
    "dev": "vite",
    "build": "vite build",
    "lint": "eslint .",
    "preview": "vite preview"
  },
  "dependencies": {
    "react": "^19.2.4",
    "react-dom": "^19.2.4"
  },
  "devDependencies": {
    "@vitejs/plugin-react": "^6.0.1",
    "vite": "^8.0.4",
    "eslint": "^9.39.4"
  }
}
```

## Vite Configuration (`frontend/vite.config.js`)

```javascript
import { defineConfig } from 'vite'
import react from '@vitejs/plugin-react'

export default defineConfig({
  plugins: [react()],
  server: {
    proxy: {
      '/api': {
        target: 'http://localhost:8000',
        changeOrigin: true
      }
    }
  }
})
```

## Development Commands

```bash
# Install dependencies
npm install

# Start dev server with hot reload (port 5173)
npm run dev

# Build for production
npm run build

# Run linter
npm run lint
```
