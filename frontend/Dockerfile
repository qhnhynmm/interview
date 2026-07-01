# Next.js Dockerfile for Aurelia (App Router)
# Produces a lean production image using standalone output.
#
# Build (from repo root):
#   docker compose build frontend
#
# Runtime: port 8080, proxies /api → BACKEND_URL (default http://127.0.0.1:8000)

FROM node:20-alpine AS deps
WORKDIR /app

COPY frontend/package*.json ./
RUN npm ci

FROM node:20-alpine AS builder
WORKDIR /app

ARG BACKEND_URL=http://127.0.0.1:8000
ARG NEXT_PUBLIC_SITE_URL=http://localhost:8080
ENV BACKEND_URL=$BACKEND_URL
ENV NEXT_PUBLIC_SITE_URL=$NEXT_PUBLIC_SITE_URL
ENV NEXT_TELEMETRY_DISABLED=1

COPY --from=deps /app/node_modules ./node_modules
COPY frontend/ .

RUN npm run build

FROM node:20-alpine AS runner
WORKDIR /app

ARG BACKEND_URL=http://127.0.0.1:8000
ENV BACKEND_URL=$BACKEND_URL
ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1
ENV PORT=8080
ENV HOSTNAME=0.0.0.0

RUN addgroup --system --gid 1001 nodejs \
    && adduser --system --uid 1001 nextjs

COPY --from=builder /app/public ./public
COPY --from=builder --chown=nextjs:nodejs /app/.next/standalone ./
COPY --from=builder --chown=nextjs:nodejs /app/.next/static ./.next/static

USER nextjs

EXPOSE 8080

CMD ["node", "server.js"]