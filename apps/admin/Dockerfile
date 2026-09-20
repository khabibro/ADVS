FROM node:22-alpine AS deps
WORKDIR /repo
COPY package.json pnpm-workspace.yaml ./
COPY packages ./packages
COPY apps/admin ./apps/admin
RUN corepack enable && pnpm install --filter @advs/admin... --frozen-lockfile=false

FROM node:22-alpine AS builder
WORKDIR /repo
COPY --from=deps /repo ./
RUN corepack enable && pnpm --filter @advs/admin build

FROM node:22-alpine AS runner
WORKDIR /app
ENV NODE_ENV=production
COPY --from=builder /repo/apps/admin/.next/standalone ./
COPY --from=builder /repo/apps/admin/.next/static ./apps/admin/.next/static
COPY --from=builder /repo/apps/admin/public ./apps/admin/public
EXPOSE 3000
CMD ["node", "apps/admin/server.js"]
