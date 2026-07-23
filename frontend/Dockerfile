FROM node:20-alpine

WORKDIR /app

COPY package*.json ./
# Upgrade npm first: the 10.8.2 shipped with node:20-alpine hits an arborist
# bug ("Cannot read properties of null (reading 'edgesOut')") resolving the
# Nuxt 4 tree. No committed lockfile yet, so `npm install` (not `npm ci`);
# node_modules is preserved across the bind mount by the anonymous volume in
# docker-compose.
RUN npm install -g npm@11 && npm install --no-audit --no-fund

COPY . .

EXPOSE 3000

CMD ["npm", "run", "dev"]