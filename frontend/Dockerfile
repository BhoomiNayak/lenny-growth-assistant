FROM node:20-alpine

WORKDIR /app

# Install dependencies
COPY package.json package-lock.json* ./
RUN npm install

# Copy source
COPY . .

# Expose dev server port
EXPOSE 3000

# Start dev server
CMD ["npm", "run", "dev"]
