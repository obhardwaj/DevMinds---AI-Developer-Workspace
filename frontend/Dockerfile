# frontend/Dockerfile
# Dev-mode image for the React/TypeScript dashboard (Vite dev server).
# Swap the CMD for a multi-stage nginx build when you're ready for production.

FROM node:20-alpine

WORKDIR /app
COPY package.json package-lock.json* ./
RUN npm install

COPY . .

EXPOSE 5173
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"]
