FROM node:20-alpine

WORKDIR /app

# Install dependencies (paths relative to repo root — Docker build context)
COPY backend/package.json ./
RUN npm install

# Copy source files and build
COPY backend/prisma ./prisma
COPY backend/tsconfig.json ./
COPY backend/src ./src

RUN npx prisma generate
RUN npm run build

EXPOSE 3001

CMD ["node", "dist/index.js"]
