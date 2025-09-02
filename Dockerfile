# ---- Stage 1: Build the React client ----
FROM node:20-slim AS builder

WORKDIR /app

# Install pnpm
RUN npm install -g pnpm

# Copy client dependency files and install dependencies to leverage Docker layer caching
COPY client/package.json client/pnpm-lock.yaml* ./client/
RUN cd client && pnpm install --frozen-lockfile

# Copy the rest of the client source code and build the application
COPY client/ ./client/
RUN cd client && pnpm build

# ---- Stage 2: Build the final Python application image ----
FROM python:3.10-slim

WORKDIR /app

# Set environment variables for non-interactive installs and defaults
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
ENV PORT=3000
ENV DATABASE_TYPE=sqlite
ENV DATABASE_URL=lorebook_creator.db

# Install uv, the Python package manager
RUN pip install uv

# Copy server dependency file and install dependencies
COPY server/requirements.txt ./server/
RUN cd server && uv pip install --system --no-cache-dir -r requirements.txt

# Copy the server source code
COPY server/ ./server/

# Copy the built client application from the 'builder' stage
COPY --from=builder /app/client/dist ./client/dist

# Expose the port the app runs on
EXPOSE ${PORT}

# Change to the server directory to run the application
WORKDIR /app/server

# The command to run the application
CMD ["uv", "run", "python", "src/main.py"]