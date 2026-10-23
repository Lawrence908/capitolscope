# Production image: build the Vite bundle, serve it as static files.
# (Dockerfile.dev runs the Vite dev server with hot reload for local work.)
FROM node:20-alpine AS build
WORKDIR /app
COPY package.json package-lock.json* ./
RUN npm ci
COPY . .
# Vite inlines VITE_* at build time, so the API origin is a build arg.
ARG VITE_API_URL=https://capitolscope.chrislawrence.ca
ENV VITE_API_URL=$VITE_API_URL
RUN npm run build

FROM nginxinc/nginx-unprivileged:1.27-alpine
COPY nginx.homelab.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 5173
