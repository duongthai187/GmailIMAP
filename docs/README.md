# 📧 Email IMAP to Kafka Streamer

Một hệ thống real-time streaming email từ IMAP server (Gmail) vào Apache Kafka với khả năng phục hồi sau gián đoạn và logging chi tiết.

## 🚀 Tổng Quan

Hệ thống này giám sát email trong Gmail INBOX bằng IMAP IDLE mode (real-time) và stream các email mới vào Kafka topic. Hệ thống được thiết kế để chạy liên tục, có khả năng phục hồi từ gián đoạn và tránh duplicate processing.

### ✨ Tính Năng Chính

- **Real-time Processing**: Sử dụng IMAP IDLE để nhận thông báo ngay khi có email mới
- **State Persistence**: Lưu trạng thái và có thể resume từ điểm ngắt
- **Duplicate Prevention**: Sử dụng UID tracking để tránh xử lý email trùng lặp
- **Lakehouse Logging**: Ghi log chi tiết từng session để audit và debug
- **Graceful Shutdown**: Handle Ctrl+C một cách graceful với cleanup
- **Docker Support**: Container-ready với docker-compose

## 🏗️ Kiến Trúc

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Gmail IMAP    │───▶│  Email Tracker   │───▶│  Apache Kafka   │
│   (IDLE Mode)   │    │                  │    │   (Topic)       │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                │
                                ▼
                       ┌──────────────────┐
                       │  Logging System  │
                       │  (JSON Files)    │
                       └──────────────────┘
```

### 📁 Cấu Trúc Thư Mục

```
d:/gma/
├── email_tracker.py          # Main application - orchestrator
├── imap_client.py            # IMAP connection & email fetching
├── kafka_streamer.py         # Kafka producer & message sending
├── email_logger.py           # Session logging & UID tracking
├── models.py                 # Pydantic data models
├── config.py                 # Configuration management
├── docker-compose.yml        # Infrastructure setup
├── requirements.txt          # Python dependencies
└── Files/
    └── Emails/
        └── Logs/
            ├── Daily/        # Per-session logs
            └── *.json        # Shutdown logs
```

## 📋 Prerequisites

### Hệ Thống
- **Python**: 3.11+
- **Docker**: Để chạy Kafka infrastructure
- **Gmail Account**: Với App Password enabled

### Gmail Setup
1. Bật 2-Factor Authentication
2. Tạo App Password: Google Account → Security → App passwords
3. Sử dụng App Password thay vì password thường

## ⚙️ Cấu Hình

### 1. Environment Variables

Tạo file `.env` từ template:

```env
# IMAP Configuration
IMAP_SERVER=imap.gmail.com
IMAP_PORT=993
IMAP_USERNAME=your-email@gmail.com
IMAP_PASSWORD=your-app-password-here
IMAP_FOLDER=INBOX

# Kafka Configuration
KAFKA_BOOTSTRAP_SERVERS=localhost:9092
KAFKA_TOPIC=email-stream
KAFKA_CLIENT_ID=email_imap_client

# Application Settings (Optional)
CHECK_INTERVAL_MINUTES=0.5
MAX_EMAILS_PER_CHECK=50
LOG_LEVEL=INFO
```

### 2. Cài Đặt Dependencies

```bash
# Tạo virtual environment
python -m venv .venv

# Activate (Windows)
.venv\Scripts\activate

# Activate (Linux/Mac)
source .venv/bin/activate

# Install packages
pip install -r requirements.txt
```

### 3. Infrastructure Setup

```bash
# Start Kafka infrastructure
docker-compose up -d zookeeper kafka

# Verify Kafka is running
docker-compose ps
```

## 🚀 Chạy Hệ Thống

### Option 1: Local Development

```bash
# Navigate to project
cd d:\gma

# Activate virtual environment
.venv\Scripts\activate

# Run email tracker
python email_tracker.py
```

### Option 2: Full Docker

```bash
# Build and run everything
docker-compose up -d

# View logs
docker-compose logs -f email-streamer
```

### Option 3: Kafka Only

```bash
# Chỉ chạy Kafka infrastructure
docker-compose up -d zookeeper kafka

# Run email tracker locally
python email_tracker.py
```

## 📊 Monitoring & Logging

### Real-time Logs
Hệ thống sử dụng `loguru` để logging với format dễ đọc:

```
15:30:45 | INFO | 🔄 Starting real-time email monitoring with IMAP IDLE
15:30:46 | INFO | 📧 Real-time email received!
15:30:46 | INFO | ✅ Sent to Kafka
```

### Session Logs
Mỗi session tạo file log riêng trong `Files/Emails/Logs/Daily/`:

```json
{
  "check_info": {
    "timestamp": "2025-08-26T15:30:45.123456",
    "check_id": "20250826_153045"
  },
  "processing_results": {
    "total_found": 5,
    "processed_uids": [12345, 12346, 12347],
    "emails_sent_to_kafka": 5,
    "errors": 0
  },
  "email_details": [...]
}
```

### Shutdown Logs
Khi shutdown graceful, tạo file log tổng hợp:

```json
{
  "shutdown_info": {
    "timestamp": "2025-08-26T16:00:00.000000",
    "reason": "Graceful shutdown (SIGINT/SIGTERM)",
    "runtime": "0:29:15"
  },
  "session_stats": {
    "total_checks": 15,
    "total_emails_found": 47,
    "total_emails_sent": 47,
    "errors": 0
  }
}
```

## 🔧 Core Components

### 1. EmailTracker (`email_tracker.py`)
- **Main orchestrator** - điều phối toàn bộ workflow
- **State management** - lưu/load trạng thái
- **Signal handling** - xử lý Ctrl+C graceful
- **Statistics tracking** - theo dõi metrics

### 2. ImapEmailClient (`imap_client.py`)
- **IMAP IDLE monitoring** - real-time email notifications
- **Email parsing** - chuyển đổi raw email thành structured data
- **UID-based tracking** - tránh duplicate processing
- **Connection management** - auto-reconnect khi cần

### 3. KafkaEmailStreamer (`kafka_streamer.py`)
- **Kafka producer** - gửi message vào topic
- **Serialization** - JSON encoding với datetime handling
- **Delivery confirmation** - đảm bảo message đã gửi thành công

### 4. EmailProcessingLogger (`email_logger.py`)
- **Session-based logging** - mỗi check tạo log riêng
- **UID deduplication** - load processed UIDs từ logs
- **Daily log management** - tổ chức logs theo ngày

## 🎯 Workflow Chi Tiết

### 1. Startup Process
```
1. Load configuration từ .env
2. Setup logging system
3. Connect to IMAP server
4. Connect to Kafka cluster  
5. Load previous state (nếu có)
6. Load processed UIDs cache
7. Start IMAP IDLE monitoring
```

### 2. Email Processing Flow
```
1. IMAP IDLE notification received
2. Fetch new emails từ server
3. Filter out processed UIDs  
4. Parse email content
5. Send to Kafka topic
6. Log processing session
7. Update UID cache
8. Continue monitoring...
```

### 3. Shutdown Process
```
1. Receive SIGINT/SIGTERM signal
2. Set stop flag
3. Exit IDLE mode
4. Disconnect from services
5. Save current state
6. Save shutdown log
7. Show final statistics
```

## 🧪 Testing & Debugging

### Test Kafka Connection
```bash
# Create test topic
docker exec kafka kafka-topics --create --topic test-topic --bootstrap-server localhost:9092 --partitions 1 --replication-factor 1

# Send test message
docker exec kafka kafka-console-producer --topic test-topic --bootstrap-server localhost:9092

# Consume messages
docker exec kafka kafka-console-consumer --topic test-topic --bootstrap-server localhost:9092 --from-beginning
```

### Test Email Flow
1. Start email tracker
2. Gửi email tới Gmail account
3. Check logs để xác nhận:
   - IDLE notification received
   - Email được parse thành công
   - Message sent to Kafka
   - Session log được tạo

### Debug Common Issues

**IMAP Connection Issues:**
```bash
# Check credentials
python -c "
import imaplib
mail = imaplib.IMAP4_SSL('imap.gmail.com')
mail.login('your-email', 'your-app-password')
print('IMAP OK')
"
```

**Kafka Connection Issues:**
```bash
# Check Kafka status
docker-compose ps
docker exec kafka kafka-topics --list --bootstrap-server localhost:9092
```

## 📈 Performance & Scalability

### Current Limits
- **IMAP Connection**: 1 connection per Gmail account
- **Email Processing**: ~50 emails per check (configurable)
- **Memory Usage**: ~50MB baseline + email content
- **Kafka Throughput**: Limited by network và email size

### Optimization Tips
- **UID Caching**: In-memory cache giảm I/O operations
- **Batch Processing**: Xử lý multiple emails trong 1 session
- **Timeout Tuning**: 5-second IDLE timeout balance performance và responsiveness

## 🛠️ Configuration Reference

### IMAP Settings
| Setting | Default | Description |
|---------|---------|-------------|
| `IMAP_SERVER` | `imap.gmail.com` | IMAP server hostname |
| `IMAP_PORT` | `993` | IMAP SSL port |
| `IMAP_USERNAME` | - | Gmail email address |
| `IMAP_PASSWORD` | - | Gmail app password |
| `IMAP_FOLDER` | `INBOX` | Folder to monitor |

### Kafka Settings
| Setting | Default | Description |
|---------|---------|-------------|
| `KAFKA_BOOTSTRAP_SERVERS` | `localhost:9092` | Kafka cluster endpoints |
| `KAFKA_TOPIC` | `email-stream` | Target topic name |
| `KAFKA_CLIENT_ID` | `email_imap_client` | Producer client ID |

### Application Settings
| Setting | Default | Description |
|---------|---------|-------------|
| `CHECK_INTERVAL_MINUTES` | `0.5` | Fallback polling interval |
| `MAX_EMAILS_PER_CHECK` | `50` | Max emails per processing batch |
| `LOG_LEVEL` | `INFO` | Logging verbosity |

## 🐛 Troubleshooting

### Common Problems

**1. Ctrl+C không hoạt động**
- **Nguyên nhân**: IMAP IDLE timeout quá dài
- **Giải pháp**: Timeout = 5 giây trong `imap_client.py`

**2. Duplicate email processing**
- **Nguyên nhân**: UID cache không work
- **Giải pháp**: Check log files có readable không

**3. Kafka connection failed**
- **Nguyên nhân**: Kafka chưa ready hoặc wrong config
- **Giải pháp**: `docker-compose ps` và check bootstrap servers

**4. IMAP authentication failed**
- **Nguyên nhân**: Sai app password hoặc chưa enable 2FA
- **Giải pháp**: Tạo lại app password trong Google Account

**5. No email notifications**
- **Nguyên nhân**: IDLE không support hoặc firewall block
- **Giải pháp**: Check IMAP logs, test với different timeout

## 🚀 Production Deployment

### Docker Production
```bash
# Production docker-compose
docker-compose -f docker-compose.prod.yml up -d

# Scale processing
docker-compose up -d --scale email-streamer=3
```

### Kubernetes Deployment
```yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: email-streamer
spec:
  replicas: 1  # IMAP connection = single instance only
  selector:
    matchLabels:
      app: email-streamer
  template:
    spec:
      containers:
      - name: email-streamer
        image: your-repo/email-streamer:latest
        env:
        - name: KAFKA_BOOTSTRAP_SERVERS
          value: "kafka-cluster:9092"
```

## 📝 Development Guidelines

### Code Style
- **Type hints**: Sử dụng typing cho tất cả functions
- **Error handling**: Comprehensive exception handling
- **Logging**: Structured logging với context
- **Documentation**: Docstrings cho public methods

### Testing
```bash
# Unit tests
python -m pytest tests/

# Integration tests  
python -m pytest tests/integration/

# Load testing
python -m pytest tests/load/
```

### Contributing
1. Fork repository
2. Create feature branch
3. Add tests cho new functionality
4. Ensure all tests pass
5. Submit pull request

## 📞 Support

### Error Reporting
Khi gặp lỗi, bao gồm:
- Log output relevant 
- Configuration settings (hide credentials)
- Steps to reproduce
- Expected vs actual behavior

### Resources
- **IMAP Protocol**: RFC 3501
- **Kafka Documentation**: https://kafka.apache.org/documentation/
- **IMAPClient Library**: https://imapclient.readthedocs.io/

---

## 📊 Quick Start Checklist

- [ ] Gmail app password created
- [ ] `.env` file configured
- [ ] Virtual environment setup
- [ ] Dependencies installed
- [ ] Kafka infrastructure running
- [ ] First test email sent
- [ ] Logs confirmed working
- [ ] Graceful shutdown tested

**🎉 Ready to stream emails to Kafka!**
