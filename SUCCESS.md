# 🎉 Email IMAP to Kafka Streamer - HOÀN THÀNH!

## ✅ Hệ thống đã hoạt động thành công!

Bạn vừa tạo thành công một server để monitor IMAP email và stream vào Kafka. Hệ thống đã test thành công với:
- **✅ IMAP Connection**: Kết nối Gmail thành công
- **✅ Kafka Streaming**: Đã gửi 50 emails vào Kafka topic
- **✅ API Server**: FastAPI server hoạt động tốt
- **✅ Auto Monitor**: Tự động check email mỗi 5 phút

## 🚀 Cách chạy hệ thống

### 1. Start Kafka (Chỉ cần làm 1 lần)

```bash
# Xóa containers cũ (nếu có)
docker stop kafka zookeeper 2>NUL
docker rm kafka zookeeper 2>NUL

# Start Zookeeper
docker run -d --name zookeeper -p 2181:2181 -e ZOOKEEPER_CLIENT_PORT=2181 -e ZOOKEEPER_TICK_TIME=2000 confluentinc/cp-zookeeper:7.4.0

# Đợi 10 giây
timeout /t 10 /nobreak > NUL

# Start Kafka
docker run -d --name kafka -p 9092:9092 -e KAFKA_BROKER_ID=1 -e KAFKA_ZOOKEEPER_CONNECT=zookeeper:2181 -e KAFKA_ADVERTISED_LISTENERS=PLAINTEXT://localhost:9092 -e KAFKA_OFFSETS_TOPIC_REPLICATION_FACTOR=1 -e KAFKA_AUTO_CREATE_TOPICS_ENABLE=true --link zookeeper confluentinc/cp-kafka:7.4.0
```

### 2. Start Email Streamer

```bash
cd d:\gma
.venv\Scripts\activate
python api_server.py
```

### 3. Truy cập API

- **API Server**: http://localhost:8000
- **Health Check**: http://localhost:8000/health  
- **Status**: http://localhost:8000/status
- **Config**: http://localhost:8000/config

## 🧪 Test hệ thống

```bash
# Test IMAP connection
python test_email_streamer.py imap

# Test Kafka connection  
python test_email_streamer.py kafka

# Test full pipeline
python test_email_streamer.py pipeline

# Consumer emails từ Kafka (để xem emails đã được stream)
python test_email_streamer.py consume
```

## 📊 Monitor hệ thống

### API Endpoints

```bash
# Check status
curl http://localhost:8000/status

# Manual trigger check emails
curl -X POST http://localhost:8000/trigger-check

# Health check
curl http://localhost:8000/health
```

### Logs

```bash
# Xem logs realtime
Get-Content logs\email_streamer.log -Wait -Tail 50

# Hoặc
tail -f logs/email_streamer.log
```

## 🐳 Deploy với Docker

### Build image

```bash
docker build -t email-streamer .
```

### Run với Docker Compose

```bash
# Chạy toàn bộ stack (Kafka + Email Streamer)
docker-compose up -d

# Xem logs
docker-compose logs -f email-streamer

# Stop
docker-compose down
```

## 📈 Kết quả hiện tại

Hệ thống đã test thành công:

```
✅ IMAP Connection: Connected to imap.gmail.com  
✅ Kafka Connection: Connected to localhost:9092
✅ Email Processing: Processed 50 emails successfully
✅ Kafka Streaming: Sent 50 emails to topic 'email-stream'
✅ API Server: Running on http://localhost:8000
✅ Auto Monitoring: Check every 5 minutes
```

## 🔧 Cấu hình

File `.env` hiện tại:

```env
# IMAP Configuration
IMAP_SERVER=imap.gmail.com
IMAP_PORT=993
IMAP_USERNAME=thaiduong18796@gmail.com
IMAP_PASSWORD=uflj rven bwsg kwft
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
KAFKA_TOPIC=email-stream
KAFKA_CLIENT_ID=email_imap_client
```

## 📝 Email Data Format

Mỗi email được stream vào Kafka với format JSON:

```json
{
  "timestamp": "2025-08-14T00:16:06.331Z",
  "source": "imap_client", 
  "email": {
    "message_id": "<unique-id@example.com>",
    "subject": "Email Subject",
    "sender": "sender@example.com",
    "recipients": ["recipient@example.com"],
    "date": "2025-08-14T00:15:00Z", 
    "body_text": "Plain text content",
    "body_html": "<html>HTML content</html>",
    "attachments": [],
    "folder": "INBOX"
  }
}
```

## 🎯 Tính năng chính

1. **Real-time Email Monitoring**: Tự động check IMAP mỗi 5 phút
2. **Kafka Streaming**: Stream email data vào Kafka topic
3. **REST API**: Control và monitor qua HTTP API
4. **Auto Retry**: Tự động reconnect khi mất kết nối
5. **Logging**: Log chi tiết vào file và console
6. **Configurable**: Dễ dàng config qua file .env

## 🚀 Sẵn sàng Production

Hệ thống đã sẵn sàng cho production với:
- Docker deployment
- Health check endpoints
- Proper logging  
- Error handling
- Auto recovery

## 🤝 Hỗ trợ

Nếu cần hỗ trợ, check:
1. Logs trong `logs/email_streamer.log`
2. API status tại `/status` endpoint
3. Test connections với script `test_email_streamer.py`

**🎊 Chúc mừng! Hệ thống Email to Kafka Streamer đã hoạt động hoàn hảo!**
