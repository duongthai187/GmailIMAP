# Email IMAP to Kafka Streamer

Một service đơn giản để monitor IMAP email và stream vào Kafka server.

## 🚀 Tính năng

- ✅ Kết nối IMAP để đọc email mới
- ✅ Stream email data vào Kafka topic
- ✅ REST API để monitor và control service
- ✅ Auto retry và error handling
- ✅ Logging và monitoring
- ✅ Configurable qua file .env

## 📋 Yêu cầu hệ thống

- Python 3.8+
- Kafka server (có thể dùng Docker)
- IMAP email account (Gmail, Outlook, etc.)

## 🛠️ Cài đặt

### 1. Setup Python environment

```bash
# Tạo virtual environment
python -m venv .venv

# Activate virtual environment
# Windows:
.venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Setup Kafka (Docker)

```bash
# Download và chạy Kafka bằng Docker
docker run -d --name kafka-server \
  -p 9092:9092 \
  -e KAFKA_ZOOKEEPER_CONNECT=localhost:2181 \
  -e KAFKA_ADVERTISED_LISTENERS=PLAINTEXT://localhost:9092 \
  -e KAFKA_OFFSETS_TOPIC_REPLICATION_FACTOR=1 \
  confluentinc/cp-kafka:latest
```

Hoặc cài đặt Kafka local theo hướng dẫn official.

### 3. Cấu hình

Copy file `.env.example` thành `.env` và cập nhật thông tin:

```bash
cp .env.example .env
```

Chỉnh sửa file `.env`:

```env
# IMAP Configuration
IMAP_SERVER=imap.gmail.com
IMAP_PORT=993
IMAP_USERNAME=your-email@gmail.com
IMAP_PASSWORD=your-app-password
IMAP_FOLDER=INBOX

# Application Settings
CHECK_INTERVAL_MINUTES=5
MAX_EMAILS_PER_CHECK=50
LOG_LEVEL=INFO

# API Server Settings
API_HOST=0.0.0.0
API_PORT=8000

# Kafka Configuration
KAFKA_BOOTSTRAP_SERVERS=localhost:9092
KAFKA_TOPIC=email_stream
KAFKA_CLIENT_ID=email_imap_client
```

**Lưu ý cho Gmail:**
- Bật 2FA
- Tạo App Password: https://myaccount.google.com/apppasswords
- Dùng App Password thay vì password thường

## 🏃‍♂️ Cách chạy

### Chạy với API Server (Recommended)

```bash
# Chạy FastAPI server
python api_server.py
```

Server sẽ chạy tại: http://localhost:8000

### Chạy CLI mode

```bash
# Chạy service trực tiếp
python main.py
```

### API Endpoints

- `GET /` - Root endpoint
- `GET /health` - Health check
- `GET /status` - Detailed status
- `GET /config` - Current config
- `POST /trigger-check` - Manual email check

## 🧪 Testing

### Test connections

```bash
# Test IMAP connection
python test_email_streamer.py imap

# Test Kafka connection  
python test_email_streamer.py kafka

# Test full pipeline
python test_email_streamer.py pipeline
```

### Test Kafka consumer

```bash
# Consumer emails từ Kafka
python test_email_streamer.py consume
```

## 📊 Monitoring

### Logs

Logs được lưu tại `logs/email_streamer.log` với rotation hàng ngày.

### Status API

```bash
# Check service status
curl http://localhost:8000/status

# Health check
curl http://localhost:8000/health
```

## 🚀 Deployment

### Docker Deployment

Tạo `Dockerfile`:

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

EXPOSE 8000

CMD ["python", "api_server.py"]
```

Build và run:

```bash
# Build image
docker build -t email-streamer .

# Run container
docker run -d \
  --name email-streamer \
  -p 8000:8000 \
  --env-file .env \
  email-streamer
```

### Production Deployment

1. **Use process manager** (PM2, Supervisor, systemd)
2. **Setup reverse proxy** (Nginx)
3. **Setup monitoring** (Prometheus + Grafana)
4. **Setup log aggregation** (ELK stack)

### Systemd Service

Tạo `/etc/systemd/system/email-streamer.service`:

```ini
[Unit]
Description=Email IMAP to Kafka Streamer
After=network.target

[Service]
Type=simple
User=your-user
WorkingDirectory=/path/to/your/app
Environment=PATH=/path/to/your/venv/bin
ExecStart=/path/to/your/venv/bin/python api_server.py
Restart=always
RestartSec=3

[Install]
WantedBy=multi-user.target
```

Enable và start:

```bash
sudo systemctl enable email-streamer
sudo systemctl start email-streamer
sudo systemctl status email-streamer
```

## 🔧 Configuration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `IMAP_SERVER` | IMAP server hostname | `imap.gmail.com` |
| `IMAP_PORT` | IMAP server port | `993` |
| `IMAP_USERNAME` | Email username | - |
| `IMAP_PASSWORD` | Email password/app password | - |
| `IMAP_FOLDER` | Email folder to monitor | `INBOX` |
| `CHECK_INTERVAL_MINUTES` | Check interval in minutes | `5` |
| `MAX_EMAILS_PER_CHECK` | Max emails per check | `50` |
| `KAFKA_BOOTSTRAP_SERVERS` | Kafka servers | `localhost:9092` |
| `KAFKA_TOPIC` | Kafka topic name | `email_stream` |
| `API_PORT` | API server port | `8000` |

## 📝 Email Data Structure

Email data được stream vào Kafka với format:

```json
{
  "timestamp": "2024-01-15T10:30:00Z",
  "source": "imap_client",
  "email": {
    "message_id": "unique-message-id",
    "subject": "Email Subject",
    "sender": "sender@example.com",
    "recipients": ["recipient@example.com"],
    "cc": ["cc@example.com"],
    "bcc": ["bcc@example.com"],
    "date": "2024-01-15T10:25:00Z",
    "body_text": "Plain text content",
    "body_html": "<html>HTML content</html>",
    "attachments": [
      {
        "filename": "document.pdf",
        "content_type": "application/pdf",
        "size": 1024
      }
    ],
    "flags": [],
    "folder": "INBOX"
  }
}
```

## ⚠️ Troubleshooting

### Common Issues

1. **IMAP Connection Failed**
   - Check email credentials
   - Enable 2FA và tạo App Password (Gmail)
   - Check firewall/network connectivity

2. **Kafka Connection Failed**
   - Check Kafka server is running
   - Verify bootstrap servers config
   - Check network connectivity

3. **No emails processed**
   - Check IMAP folder exists
   - Verify email account has new emails
   - Check logs for errors

### Debug Mode

Set `LOG_LEVEL=DEBUG` trong `.env` để có thêm log chi tiết.

## 🤝 Contributing

1. Fork the repo
2. Create feature branch
3. Make changes
4. Add tests
5. Submit pull request

## 📄 License

MIT License - see LICENSE file for details.
