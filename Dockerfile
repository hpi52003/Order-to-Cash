# Build frontend
FROM node:22 AS frontend-build
WORKDIR /app/frontend
COPY frontend/package*.json ./
RUN npm install
COPY frontend/ ./
RUN npm run build

# Backend
FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY backend/ ./backend/
COPY data/ ./data/

# Generate o2c.db from CSV files
RUN python -m backend.ingest

# Copy frontend built files
COPY --from=frontend-build /app/frontend/dist ./frontend/dist

EXPOSE 10000
CMD ["uvicorn", "backend.main:app", "--host", "0.0.0.0", "--port", "10000"]

