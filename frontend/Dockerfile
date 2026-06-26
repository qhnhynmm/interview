# Next.js Dockerfile for Aurelia (App Router)
# Produces a lean production image using standalone output.

FROM node:20-alpine AS deps
WORKDIR /app

# Copy package files
COPY frontend/package*.json ./
RUN npm ci

FROM node:20-alpine AS builder
WORKDIR /app

COPY --from=deps /app/node_modules ./node_modules
COPY frontend/ .
# Copy root configs/ (proctoring + backend urls) if still referenced at build
COPY configs/ ../configs/

# Build
ENV NEXT_TELEMETRY_DISABLED=1
RUN npm run build

# Production image
FROM node:20-alpine AS runner
WORKDIR /app

ENV NODE_ENV=production
ENV NEXT_TELEMETRY_DISABLED=1
ENV PORT=8080

# Copy standalone output (enabled in next.config)
COPY --from=builder /app/.next/standalone ./
COPY --from=builder /app/.next/static ./.next/static
COPY --from=builder /app/public ./public

# If you still need the yml for anything at runtime, copy it
# COPY --from=builder /app/../configs ./configs

EXPOSE 8080

CMD ["node", "server.js"]
