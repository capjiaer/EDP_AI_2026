# Stage 1: Build Vue frontend
FROM node:20-alpine AS frontend-build
WORKDIR /app/frontend
COPY web/frontend/package.json web/frontend/package-lock.json* ./
RUN npm install
COPY web/frontend/ ./
RUN npm run build

# Stage 2: Python runtime
FROM python:3.11-slim
WORKDIR /app

# Install Python deps
COPY web/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy backend
COPY web/backend/ ./backend/

# Copy built frontend from stage 1
COPY --from=frontend-build /app/frontend/dist ./static

# Copy packages (existing Python kits)
COPY packages/ ./packages/

# Flask serves static + API
ENV PYTHONPATH=/app/packages
ENV FLASK_APP=backend.app

EXPOSE 5000

CMD ["python", "-c", \
     "from backend.app import create_app, socketio; \
      app = create_app(); \
      app.static_folder = 'static'; \
      socketio.run(app, host='0.0.0.0', port=5000)"]
