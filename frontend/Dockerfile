FROM node:20-alpine AS builder
WORKDIR /app

# vite.config.js reads ../configs/frontend-services.yml at build time
COPY configs/frontend-services.yml configs/frontend-services.yml

WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm ci

COPY frontend/ .
RUN npm run build

FROM nginx:alpine
COPY --from=builder /app/frontend/dist /usr/share/nginx/html
# nginx:alpine runs envsubst over /etc/nginx/templates/*.template at startup and
# writes the result to /etc/nginx/conf.d/. Only BACKEND_ORIGIN is substituted, so
# nginx's own runtime vars ($host, $uri, ...) are left untouched. The default is a
# literal IP so nginx starts even before the backend exists (/api just 502s).
COPY frontend/nginx.conf.template /etc/nginx/templates/default.conf.template
ENV BACKEND_PROXY=http://127.0.0.1:8000 \
    BACKEND_HOST=127.0.0.1 \
    NGINX_ENVSUBST_FILTER=BACKEND_
EXPOSE 8080
CMD ["nginx", "-g", "daemon off;"]
