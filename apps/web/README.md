# Finance Manager Web

React/TypeScript frontend for the Finance Manager application.

## Quick Start

```bash
# Install dependencies
npm install

# Start development server
npm run dev

# Run tests
npm test

# Build for production
npm run build
```

## Project Structure

```
apps/web/
├── src/
│   ├── components/   # Reusable UI components
│   ├── hooks/        # Custom React hooks
│   ├── pages/        # Page components
│   ├── services/     # API clients and services
│   ├── types/        # TypeScript type definitions
│   ├── test/         # Test utilities
│   ├── App.tsx       # Main application component
│   ├── App.css       # Application styles
│   ├── main.tsx      # Entry point
│   └── index.css     # Global styles
├── index.html
├── package.json
├── tsconfig.json
├── vite.config.ts
├── Dockerfile
└── README.md
```

## Scripts

| Script | Description |
|--------|-------------|
| `npm run dev` | Start development server |
| `npm run build` | Build for production |
| `npm run preview` | Preview production build |
| `npm test` | Run tests |
| `npm run test:watch` | Run tests in watch mode |
| `npm run test:coverage` | Run tests with coverage |
| `npm run lint` | Run ESLint |
| `npm run format` | Format code with Prettier |

## Docker

```bash
# Build image
docker build -t finance-manager-web .

# Run container
docker run -p 80:80 finance-manager-web
```

## Environment Variables

Environment variables are embedded at build time. Create a `.env` file:

```
VITE_API_URL=http://localhost:8000
```

## API Proxy

During development, API requests to `/api/*` are proxied to `http://localhost:8000`. See `vite.config.ts` for configuration.
