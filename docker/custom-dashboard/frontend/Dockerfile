# ── Stage 1: Build ──────────────────────────────────────────
FROM node:18-slim AS builder

WORKDIR /app

# VITE_API_URL must be a build-time ARG, not a runtime ENV
ARG VITE_API_URL=http://localhost:8000
ENV VITE_API_URL=$VITE_API_URL

COPY package*.json ./
RUN npm install

COPY . .
RUN npm run build

# ── Stage 2: Serve ───────────────────────────────────────────
FROM node:18-slim AS runner

WORKDIR /app
RUN npm install -g serve

COPY --from=builder /app/dist ./dist

EXPOSE 5173
CMD ["serve", "-s", "dist", "-l", "5173"]
