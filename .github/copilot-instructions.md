# AI Agent Instructions for rev-lorecard

## Project Overview

This is a web application for generating structured "lorebooks" and "character cards" from web sources using LLMs. It consists of:

- **Frontend** (`/client`): React/TypeScript SPA built with Vite
- **Backend** (`/server`): Python API using Litestar, with support for SQLite and PostgreSQL

## Key Architecture Points

### Backend Architecture

- **No ORM**: Raw SQL is used for database operations (`/server/db/`)
- **Background Jobs**: Uses a worker system for async processing (`/server/src/worker.py`)
- **Provider System**: Modular LLM provider integration (`/server/providers/`)
- **Template-based Generation**: Uses Jinja templates for LLM prompts

### Data Flow

1. User creates a Project (lorebook/character)
2. System extracts content from web sources
3. LLM processes content into structured entries
4. Results stored in database and served via API

## Development Workflow

### Backend Setup
```bash
uv venv --python 3.10
uv pip install -r requirements.txt
python src/main.py  # Start server
```

### Frontend Setup
```bash
pnpm install
pnpm dev  # Starts on http://localhost:5173
```

## Project-Specific Patterns

### State Management
- SSE (Server-Sent Events) used for real-time updates (`/client/src/hooks/useSse.ts`)
- Global state managed via React hooks in `/client/src/hooks/`

### Database Operations
- All SQL in dedicated `/server/db/` modules
- Use parameterized queries to prevent injection
- Example: See `/server/db/projects.py` for patterns

### API Structure
- RESTful endpoints in `/server/controllers/`
- Background jobs for long-running tasks
- Request logging and analytics built-in

## Testing and Quality

### Backend Tests
- Uses pytest (`python -m pytest`)
- Test fixtures in `/server/tests/conftest.py`
- Test background jobs with `test_background_jobs.py`

### Frontend Development
- TypeScript for type safety
- ESLint + Prettier for code style
- Vite for fast development experience

## Common Operations

### Adding a New Provider
1. Create provider class in `/server/providers/`
2. Implement required interface methods
3. Register in provider system
4. Add credentials management UI support

### Adding a New Template
1. Define template in project's templates JSON
2. Update template validation in `schemas.py`
3. Add UI support in template management components

## Important Files
- `/server/docs/design.md`: Detailed system architecture
- `/server/src/schemas.py`: Data models and validation
- `/client/src/types/index.ts`: TypeScript type definitions
- `/server/src/worker.py`: Background job processing