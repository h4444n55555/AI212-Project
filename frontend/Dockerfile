# Stage 1: Build Image
FROM node:20-alpine AS builder

WORKDIR /app

# Install dependencies
COPY package*.json ./
RUN npm install

# Build static assets via Vite
COPY . .
RUN npm run build

# Stage 2: Serve Image
FROM nginx:alpine

# Copy built artifacts from Stage 1 into Nginx default public directory
COPY --from=builder /app/dist /usr/share/nginx/html

# Replace default Nginx configuration with our custom setup (React Router + Backend Proxy)
COPY nginx.conf /etc/nginx/conf.d/default.conf

# Expose Nginx internal port
EXPOSE 80

# Keep Nginx running in the foreground natively
CMD ["nginx", "-g", "daemon off;"]
