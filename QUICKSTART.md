# Email Streamer Quick Start Guide

## 🚀 Cách chạy nhanh

### Option 1: Docker Compose (Recommended)

```bash
# 1. Clone/setup project
cd d:\gma

# 2. Cấu hình .env file
# (Đã có sẵn, chỉ cần update email credentials)

# 3. Chạy toàn bộ stack (Kafka + Email Streamer)
docker-compose up -d

# 4. Check logs
docker-compose logs -f email-streamer

# 5. Test API
curl http://localhost:8000/health
```

### Option 2: Local Development

```bash
# 1. Setup Python environment
python -m venv .venv
.venv\Scripts\activate  # Windows
pip install -r requirements.txt

# 2. Start Kafka (Docker)
docker run -d --name kafka \
  -p 9092:9092 \
  -e KAFKA_ZOOKEEPER_CONNECT=localhost:2181 \
  -e KAFKA_ADVERTISED_LISTENERS=PLAINTEXT://localhost:9092 \
  confluentinc/cp-kafka:latest

# 3. Run email streamer
python api_server.py
```

## 🧪 Testing Commands

```bash
# Test IMAP connection
python test_email_streamer.py imap

# Test Kafka connection
python test_email_streamer.py kafka

# Test full pipeline
python test_email_streamer.py pipeline

# Consume emails from Kafka
python test_email_streamer.py consume
```

## 📋 API Endpoints

- `GET http://localhost:8000/` - Welcome message
- `GET http://localhost:8000/health` - Health check
- `GET http://localhost:8000/status` - Detailed status
- `POST http://localhost:8000/trigger-check` - Manual email check

## ⚙️ Configuration

Update `.env` file:

```env
# IMAP Settings (REQUIRED)
IMAP_USERNAME=your-email@gmail.com
IMAP_PASSWORD=your-app-password

# Kafka Settings (Optional - defaults work for local)
KAFKA_BOOTSTRAP_SERVERS=localhost:9092
KAFKA_TOPIC=email_stream

# App Settings (Optional)
CHECK_INTERVAL_MINUTES=5
```

## 🔍 Monitoring

```bash
# View logs
tail -f logs/email_streamer.log

# Check service status
curl http://localhost:8000/status

# Manual trigger email check
curl -X POST http://localhost:8000/trigger-check
```

## 🛑 Stop Services

```bash
# Docker Compose
docker-compose down

# Local
Ctrl+C (in terminal running the service)
```
