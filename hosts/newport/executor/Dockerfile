# Rebuild the pinned Worker/UI; retain upstream's native host and runtime image.
FROM node:24.22.1-bookworm-slim AS build
COPY --from=oven/bun:1.4.4 /usr/local/bin/bun /usr/local/bin/bun
ENV EXECUTOR_BUILD_VERSION=2.0.0-beta.41-auth-only.1 EXECUTOR_ENVIRONMENT=self-host
RUN apt-get update && apt-get install -y --no-install-recommends git ca-certificates python3 make g++ && rm -rf /var/lib/apt/lists/*
WORKDIR /build
COPY package.json bun.lock .gitignore tsconfig.json ./
COPY patches ./patches
COPY packages ./packages
COPY apps ./apps
COPY playground ./playground
COPY e2e/viewer/package.json ./e2e/viewer/package.json
RUN bun install --frozen-lockfile --filter @executor-js/hosted-self-host --filter @executor-js/hosted-self-host-web --filter @executor-js/telemetry --filter apps --filter @executor-js/app-live-inbox
RUN bun run --cwd packages/telemetry build:motel
RUN bun run --cwd apps/hosted/self-host/web build
RUN bun run --cwd packages/apps build
RUN bun run --cwd apps/hosted/self-host package:runtime

FROM ghcr.io/usefulsoftwareco/executor-selfhost:2.0.0-beta.41@sha256:712dc482432c918d48a84f80cc79b12125e951f9bb6929efc7b4594e5523c576
ENV EXECUTOR_BUILD_VERSION=2.0.0-beta.41-auth-only.1
COPY --from=build --chown=1000:1000 /build/apps/hosted/self-host/dist/workerd/ /app/
