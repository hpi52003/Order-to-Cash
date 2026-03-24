# Build frontend
FROM node:18 AS frontend-build
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm install
COPY frontend/ ./
RUN npm run build

# Backend + serve frontend
FROM python:3.11-slim
WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY backend/ ./backend/
COPY data/o2c.db ./data/o2c.db
COPY data/graph_data.json ./data/graph_data.json

# Copy frontend built files from Build frontend stage
COPY --from=frontend-build /app/frontend/dist ./frontend/dist

EXPOSE 10000
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "10000"]
