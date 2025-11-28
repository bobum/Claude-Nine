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

Visit http://localhost:3001

## Features

- **Home Dashboard**: Overview and quick start guide
- **Teams Management**: Create, view, and manage AI development teams
- **Work Items Management**: Manage work from Azure DevOps, Jira, GitHub, and more
- **Bulk Assignment**: Select multiple work items and assign them to teams at once
- **Real-time Updates**: WebSocket connection for live status updates
- **Search & Filtering**: Quickly find teams and work items
- **Dark Mode**: Toggle between light and dark themes
- **Toast Notifications**: Non-blocking user feedback
- **Responsive Design**: Works on desktop and mobile

## Project Structure

```
dashboard/
├── app/
│   ├── page.tsx                 # Home page
│   ├── teams/
│   │   ├── page.tsx             # Teams list page
│   │   ├── new/page.tsx         # Create team page
│   │   └── [id]/page.tsx        # Team detail page
│   ├── work-items/
│   │   └── page.tsx             # Work items page with bulk assignment
│   ├── dashboard/
│   │   └── page.tsx             # Metrics dashboard
│   ├── layout.tsx               # Root layout
│   └── globals.css              # Global styles with dark mode
├── components/
│   ├── ThemeToggle.tsx          # Dark mode toggle
│   └── Toast.tsx                # Notification component
├── lib/
│   ├── api.ts                   # API client with all endpoints
│   └── hooks.ts                 # Custom React hooks (WebSocket, Toast, etc.)
└── public/                      # Static assets
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

## Key Features Documentation

### Bulk Assignment

The bulk assignment feature allows you to select multiple work items and assign them to a team's queue at once. Perfect for sprint planning and work distribution.

**📚 [Read the Complete Bulk Assignment Guide](../docs/bulk-assignment-guide.md)**

Quick example:
1. Navigate to Work Items page
2. Select items using checkboxes
3. Click "Assign X Items" button
4. Choose target team
5. Confirm assignment

### Other Features

- **WebSocket Integration**: Real-time updates for team and agent status
- **Dark Mode**: Persistent theme toggle with localStorage
- **Search**: Instant filtering on teams page
- **Toast Notifications**: Non-blocking user feedback system

## Next Steps

- [x] ~~Add team creation form~~
- [x] ~~Add team detail pages~~
- [x] ~~Add work items management~~
- [x] ~~Add real-time WebSocket updates~~
- [x] ~~Add bulk assignment feature~~
- [ ] Add Azure DevOps integration
- [ ] Add Jira integration
- [ ] Add GitHub issues sync
- [ ] Add agent status monitoring dashboard
- [ ] Add metrics and analytics charts
- [ ] Add activity feed/logs viewer

## Tech Stack

- **Framework**: Next.js 14 (App Router)
- **Language**: TypeScript
- **Styling**: Tailwind CSS
- **API**: Fetch API (will add React Query later)
