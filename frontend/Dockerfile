# ---------- Stage 1: build the React app ----------
FROM node:20-alpine AS builder
WORKDIR /app
COPY package.json ./
RUN npm install --no-audit --no-fund
COPY . ./
RUN npm run build

# ---------- Stage 2: serve the static build with nginx ----------
FROM nginx:alpine
# Render sets PORT at runtime; default to 80 for local Docker runs.
ENV PORT=80
# nginx's stock entrypoint expands templates in /etc/nginx/templates
# (using $PORT) and runs scripts in /docker-entrypoint.d before starting.
COPY --from=builder /app/dist /usr/share/nginx/html
COPY nginx.conf.template /etc/nginx/templates/default.conf.template
COPY write-config.sh /docker-entrypoint.d/15-write-config.sh
RUN chmod +x /docker-entrypoint.d/15-write-config.sh
EXPOSE 80
