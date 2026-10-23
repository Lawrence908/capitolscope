# Use official Node.js image
FROM node:20-alpine

WORKDIR /app

# Install wget for healthcheck
RUN apk add --no-cache wget

# Copy package files first for better caching
COPY package.json package-lock.json* ./
RUN npm install

# Copy the rest of the frontend code
COPY . .

EXPOSE 5173

# Run the development server with host binding for Docker
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0"] 