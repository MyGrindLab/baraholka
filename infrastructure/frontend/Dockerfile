# Frontend image. Build context: frontend/ (matches CI).
# Stages: deps -> dev (Vite dev server, `make up-frontend`, lint/test)
#              -> builder (static build) -> runtime (nginx, LAST = default target,
#                 so CI's plain build yields the production image).

# stage: deps — cached on package*.json only
FROM node:24-alpine AS deps

WORKDIR /app

COPY package*.json ./
RUN npm ci

# stage: dev — Vite dev server; src/ and public/ are bind-mounted by compose
FROM deps AS dev

COPY . .
EXPOSE 3000
CMD ["npx", "vite"]

# stage: build
FROM deps AS builder

COPY . .
# API calls go to /api on the same origin (services/api.js default) — the
# ingress routes /api to the backend.
RUN npm run build

# stage: runtime
FROM nginx:1.27-alpine

COPY --from=builder /app/dist /usr/share/nginx/html
RUN printf '%s\n' \
  'server {' \
  '    listen 80;' \
  '    server_name _;' \
  '    root /usr/share/nginx/html;' \
  '    index index.html;' \
  '    location / { try_files $uri $uri/ /index.html; }' \
  '}' > /etc/nginx/conf.d/default.conf

EXPOSE 80

CMD ["nginx", "-g", "daemon off;"]
