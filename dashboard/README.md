# Claude-Nine Dashboard

Next.js frontend for the Claude-Nine AI development teams platform.

## Quick Start

### 1. Install Dependencies

```bash
cd dashboard
npm install
```

### 2. Configure Environment

```bash
cp .env.example .env.local
```

The API URL is already configured for local development.

### 3. Start the Development Server

```bash
npm run dev
```

Visit http://localhost:3000

## Features

- **Home Dashboard**: Overview and quick start guide
- **Teams Management**: Create, view, and manage AI development teams
- **Real-time Status**: Live API health checks and team status
- **Responsive Design**: Works on desktop and mobile

## Project Structure

```
dashboard/
├── app/
│   ├── page.tsx           # Home page
│   ├── teams/
│   │   └── page.tsx       # Teams list page
│   ├── layout.tsx         # Root layout
│   └── globals.css        # Global styles
├── components/            # Reusable components (coming soon)
├── lib/                   # Utilities and API client (coming soon)
└── public/               # Static assets
```

## API Integration

The dashboard connects to the FastAPI backend running on port 8000.

**Make sure the API is running:**
```bash
cd ../api
./run.sh
```

## Development

### Build for Production

```bash
npm run build
npm start
```

### Linting

```bash
npm run lint
```

## Next Steps

- [ ] Add team creation form
- [ ] Add team detail pages
- [ ] Add work items management
- [ ] Add real-time WebSocket updates
- [ ] Add agent status monitoring
- [ ] Add metrics and analytics dashboard

## Tech Stack

- **Framework**: Next.js 14 (App Router)
- **Language**: TypeScript
- **Styling**: Tailwind CSS
- **API**: Fetch API (will add React Query later)
