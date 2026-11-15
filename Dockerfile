FROM node:22-bookworm-slim AS frontend
WORKDIR /app
COPY package.json package-lock.json ./
RUN npm ci
COPY frontend ./frontend
RUN mkdir web && npm run build

FROM python:3.12-slim-bookworm
WORKDIR /app
COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
COPY . .
COPY --from=frontend /app/web/app.js ./web/app.js
ENV HOST=0.0.0.0 PYTHONUNBUFFERED=1
CMD ["python", "-m", "ragent_openfire.web"]
