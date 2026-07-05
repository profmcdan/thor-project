FROM node:20-alpine

WORKDIR /app

# Copy package configurations and install dependencies
COPY package*.json ./
RUN npm install

# Copy application files
COPY . .

# Expose Vite dev server port
EXPOSE 5173

# Run Vite in host mode to allow container networking binds
CMD ["npm", "run", "dev", "--", "--host"]
