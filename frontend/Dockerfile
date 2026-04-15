FROM node:20-slim AS dev

WORKDIR /app
COPY package.json pnpm-lock.yaml* ./
RUN corepack enable && pnpm install
COPY . .
EXPOSE 5173
CMD ["pnpm", "run", "dev", "--host"]
