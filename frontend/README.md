# FPL Optimizer Frontend

React frontend application with Mainframe manifesto terminal aesthetic for the FPL Optimizer dashboard.

## Features

- **Terminal Aesthetic**: Monospace typography, minimalist black/white/green design
- **Dashboard Analytics**: Comprehensive FPL analytics visualization
- **News Integration**: Latest FPL news articles
- **Live Tracking**: Real-time gameweek tracking
- **Transfer Recommendations**: AI-powered transfer suggestions
- **Responsive Design**: Works on mobile, tablet, and desktop

## Tech Stack

- React 18+
- Vite (build tool)
- React Router v6
- Axios
- CSS (no CSS-in-JS)

## Setup

1. Install dependencies:
```bash
npm install
```

2. Create `.env` file (optional):
```bash
cp .env.example .env
```

3. Start development server:
```bash
npm run dev
```

The app will be available at `http://localhost:3000`

## Environment Variables

- `VITE_API_BASE_URL`: Base URL for the API (default: `http://localhost:8000/api/v1`)

## Project Structure

```
frontend/
├── src/
│   ├── components/       # Reusable components
│   ├── pages/            # Page components
│   ├── services/         # API service layer
│   ├── hooks/            # Custom React hooks
│   ├── styles/           # CSS files
│   └── utils/            # Utility functions
├── public/               # Static assets
└── package.json
```

## API Integration

The frontend integrates with the FPL Dashboard API running on port 8000. Make sure the backend API is running before using the frontend.

## Build for Production

```bash
npm run build
```

The built files will be in the `dist/` directory.

## Development

- Development server: `npm run dev`
- Build: `npm run build`
- Preview production build: `npm run preview`
