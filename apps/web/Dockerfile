FROM node:22-alpine AS deps
WORKDIR /repo
COPY package.json pnpm-workspace.yaml ./
COPY packages ./packages
COPY apps/web ./apps/web
RUN corepack enable && pnpm install --filter @advs/web... --frozen-lockfile=false

FROM node:22-alpine AS builder
WORKDIR /repo
COPY --from=deps /repo ./
RUN corepack enable && pnpm --filter @advs/web build

FROM node:22-alpine AS runner
WORKDIR /app
ENV NODE_ENV=production
COPY --from=builder /repo/apps/web/.next/standalone ./
COPY --from=builder /repo/apps/web/.next/static ./.next/static
EXPOSE 3000
CMD ["node", "server.js"]
