# React & Node.js

## Overview
React provides the interactive frontend UI, while Node.js powers the build pipeline via Vite and npm.

## How It's Used in the Project

### 1. **React Frontend** (`frontend/src/`)
- Single Page Application (SPA) with tabbed interface
- **Vision Tab** - Upload images or use webcam for real-time detection
- **Analytics Tab** - Monitor system metrics and inference latency
- Dark/Light theme toggle
- Canvas-based bounding box visualization

### 2. **Node.js Build Pipeline** (`frontend/package.json`)
- **Vite** - Ultra-fast frontend build tool and dev server
- **ESLint** - Code linting and quality checks
- Dev server runs on port 5173 with hot reload

## Key Features

- **Component-Based UI** - Modular React components (Topbar, Tabs, VisionPanel, AnalyticsPanel)
- **State Management** - React hooks (`useState`, `useRef`, `useCallback`, `useEffect`)
- **Canvas API** - Direct pixel drawing for bounding box visualization
- **Error Handling** - Graceful error states for failed detections
- **Responsive Design** - Mobile-friendly layout

## Frontend Architecture

```
App.jsx (Main Component)
├── Topbar (Nav + Status)
├── Tabs (Vision / Analytics)
├── VisionPanel
│   ├── Image Upload
│   ├── Webcam Stream
│   └── Canvas Drawing
└── AnalyticsPanel
    ├── Performance Charts
    └── System Metrics
```

## API Integration

Frontend communicates with backend via `fetch()` to:
- POST image to `/api/detect` for inference
- GET `/api/health` for system metrics
