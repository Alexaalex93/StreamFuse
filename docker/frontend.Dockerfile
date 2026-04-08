FROM node:22-alpine AS deps

WORKDIR /app
COPY frontend/package.json frontend/package-lock.json* ./
RUN npm install

FROM deps AS dev
COPY frontend /app
EXPOSE 5173
CMD ["npm", "run", "dev", "--", "--host", "0.0.0.0", "--port", "5173"]

FROM deps AS build
COPY frontend /app
RUN npm run build

FROM nginx:1.27-alpine AS prod
COPY docker/nginx.conf /etc/nginx/conf.d/default.conf
COPY --from=build /app/dist /usr/share/nginx/html
EXPOSE 80
CMD ["nginx", "-g", "daemon off;"]