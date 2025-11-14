# ---- Stage 1: Build the React client ----
FROM node:20-slim AS builder

WORKDIR /app

# Install pnpm
RUN npm install -g pnpm

# Copy client dependency files and install dependencies to leverage Docker layer caching
COPY client/package.json client/pnpm-lock.yaml* ./client/
RUN cd client && pnpm install

# Copy the theme source code
COPY sources/theme-rev-dark/ ./sources/theme-rev-dark/

# Copy BlockNote source code
# Copy the rest of the client source code and install local theme dependency
COPY client/ ./client/
RUN cd client && pnpm install ../sources/theme-rev-dark
RUN cd client && pnpm build

# ---- Stage 2: Build the final Python application image ----
FROM python:3.10-slim AS base

# ---- Stage 2: Build the final Python application image ----
FROM base AS server_builder


WORKDIR /app

# Argument to receive the version from the build command
ARG APP_VERSION=development

WORKDIR /app

# Argument to receive the version from the build command
ARG APP_VERSION=development

# Set environment variables for non-interactive installs and defaults
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
ENV PORT=3000
ENV APP_ENV=production
ENV RUNTIME_ENV=docker
ENV APP_VERSION=${APP_VERSION}

# Install uv, the Python package manager
RUN pip install uv

# Copy server dependency file and install dependencies
COPY server/requirements.txt ./server/

RUN cd server && uv pip install --system --no-cache-dir -r requirements.txt

# Copy the server source code
COPY server/ ./server/

# Copy the built client application from the 'builder' stage
COPY --from=builder /app/client/dist ./client/dist

# ---- Stage 3: Final runtime image (using a smaller base) ----
FROM base AS final

WORKDIR /app

# Copy runtime environment variables
ARG APP_VERSION=development
ENV PYTHONDONTWRITEBYTECODE 1
ENV PYTHONUNBUFFERED 1
ENV PORT=3000
ENV APP_ENV=production
ENV RUNTIME_ENV=docker
ENV APP_VERSION=${APP_VERSION}

# Copy installed dependencies and source code from server_builder
COPY --from=server_builder /usr/local/lib/python3.10/site-packages /usr/local/lib/python3.10/site-packages
# Copy uv executable to PATH
COPY --from=server_builder /usr/local/bin/uv /usr/local/bin/uv
COPY --from=server_builder /app/server ./server
COPY --from=server_builder /app/client/dist ./client/dist

# Expose the port the app runs on
EXPOSE ${PORT}

# Change to the server directory to run the application
WORKDIR /app/server

# The command to run the application
CMD ["uv", "run", "python", "src/main.py"]