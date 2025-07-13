# CapitolScope Frontend

A modern React + TypeScript frontend for exploring congressional trading data.

## Features

- **Dashboard**: Overview of key statistics and recent trading activity
- **Trade Browser**: Advanced filtering and search capabilities for congressional trades
- **Member Profiles**: Detailed views of congress members and their trading history
- **Analytics**: Data visualization and trend analysis
- **Data Quality**: Tools for identifying and tracking data quality issues

## Tech Stack

- **React 18** with TypeScript
- **Vite** for fast development and building
- **Tailwind CSS** for styling
- **React Router** for navigation
- **Axios** for API communication
- **Heroicons** for icons
- **date-fns** for date handling

## Getting Started

### Prerequisites

- Node.js 18+ (current version: 18.19.1)
- npm or yarn
- CapitolScope FastAPI backend running on `http://localhost:8000`

### Installation

1. Install dependencies:
```bash
npm install
```

2. Start the development server:
```bash
npm run dev
```

3. Open [http://localhost:5173](http://localhost:5173) in your browser

### Building for Production

```bash
npm run build
```

The built files will be in the `dist/` directory.

## Project Structure

```
src/
├── components/          # React components
│   ├── Layout.tsx      # Main layout with navigation
│   ├── Dashboard.tsx   # Dashboard overview
│   ├── TradeBrowser.tsx # Trade filtering and browsing
│   └── ...
├── services/           # API client and services
│   └── api.ts         # FastAPI backend client
├── types/             # TypeScript type definitions
│   └── index.ts       # Shared types
├── App.tsx            # Main app component with routing
├── main.tsx          # App entry point
└── index.css         # Global styles with Tailwind
```

## API Integration

The frontend communicates with the FastAPI backend through a typed API client (`src/services/api.ts`). Key endpoints:

- `GET /api/v1/congressional/trades` - List trades with filtering
- `GET /api/v1/congressional/members` - List congress members
- `GET /api/v1/congressional/data-quality/stats` - Data quality metrics
- `GET /api/v1/congressional/analytics/*` - Analytics endpoints

## Components

### Dashboard
- Overview statistics
- Recent trades
- Top trading members
- Party distribution

### Trade Browser
- Advanced filtering (party, chamber, date range, ticker, etc.)
- Search functionality
- Pagination
- Responsive table view

### Layout
- Sidebar navigation
- Responsive design
- Consistent header and branding

## Development

### Available Scripts

- `npm run dev` - Start development server
- `npm run build` - Build for production
- `npm run preview` - Preview production build
- `npm run lint` - Run ESLint

### Adding New Components

1. Create component in `src/components/`
2. Add TypeScript types in `src/types/`
3. Update routing in `src/App.tsx`
4. Add API methods in `src/services/api.ts` if needed

### Styling

The project uses Tailwind CSS with custom component classes defined in `src/index.css`:

- `.btn-primary` - Primary button style
- `.btn-secondary` - Secondary button style
- `.card` - Card container style
- `.input-field` - Form input style

## Future Enhancements

- [ ] Member profile pages with detailed trading history
- [ ] Interactive charts and visualizations
- [ ] Export functionality (CSV, PDF)
- [ ] Real-time data updates
- [ ] Advanced analytics (ROI calculations, timing analysis)
- [ ] Network visualization of trading relationships
- [ ] Mobile app version

## Contributing

1. Follow the existing code style and patterns
2. Add TypeScript types for all new data structures
3. Include error handling for API calls
4. Test components with different data states (loading, error, empty)
5. Ensure responsive design works on mobile devices

## License

This project is part of the CapitolScope platform for congressional trading transparency.
