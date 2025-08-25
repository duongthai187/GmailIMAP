# 🚀 Quick Start Guide

## 📋 Prerequisites Checklist

- [ ] **Python 3.11+** installed
- [ ] **Docker** installed và running
- [ ] **Gmail account** với 2FA enabled
- [ ] **App Password** tạo trong Google Account

## ⚡ 5-Minute Setup

### Step 1: Gmail App Password
1. Go to [Google Account Security](https://myaccount.google.com/security)
2. Enable **2-Step Verification** (nếu chưa có)
3. Go to **App passwords** → Generate password for "Mail"
4. Copy password (format: `abcd efgh ijkl mnop`)

### Step 2: Project Setup
```bash
# Clone/navigate to project
cd d:/gma

# Create virtual environment
python -m venv .venv

# Activate virtual environment (Windows)
.venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt
```

### Step 3: Configuration
```bash
# Copy environment template
copy .env.example .env

# Edit .env với thông tin của bạn:
# IMAP_USERNAME=your-email@gmail.com  
# IMAP_PASSWORD=your-app-password-here
```

### Step 4: Start Kafka
```bash
# Start Kafka infrastructure
docker-compose up -d zookeeper kafka

# Verify Kafka running
docker-compose ps
```

### Step 5: Run Email Tracker
```bash
# Start email tracking
python email_tracker.py
```

### Step 6: Test
1. **Gửi email** tới Gmail account của bạn
2. **Check terminal** - sẽ thấy log real-time:
   ```
   📧 Real-time email received!
   ✅ Sent to Kafka
   ```

## 🎯 Verification Commands

### Check Kafka Messages
```bash
# View messages in Kafka topic
docker exec kafka kafka-console-consumer \
  --topic email-stream \
  --bootstrap-server localhost:9092 \
  --from-beginning
```

### Check Processing Logs
```bash
# View latest session logs
ls Files/Emails/Logs/Daily/ | tail -5

# View shutdown logs
ls Files/Emails/Logs/ | grep shutdown | tail -3
```

## 🛑 Stop System

```bash
# Graceful shutdown
Ctrl + C

# Stop Kafka infrastructure  
docker-compose down
```

## 🐛 Common Issues

| Issue | Solution |
|-------|----------|
| `IMAP authentication failed` | Check app password format và 2FA enabled |
| `Kafka connection failed` | Run `docker-compose ps` - verify Kafka running |
| `No email notifications` | Send test email, check Gmail INBOX folder |
| `Ctrl+C không work` | Wait 5 seconds (IDLE timeout) |

## 📞 Need Help?

1. **Check logs** trong terminal output
2. **Verify configuration** trong `.env` file  
3. **Test components** riêng lẻ:
   - IMAP: `python -c "from imap_client import *"`
   - Kafka: `docker exec kafka kafka-topics --list --bootstrap-server localhost:9092`

---

## 🎉 Success!

Nếu thấy output như này thì đã success:

```
🔄 Starting real-time email monitoring with IMAP IDLE
📧 Real-time email received!
  UID 12345: Test email subject...
  From: sender@example.com
  ✅ Sent to Kafka
📈 Total: 1 emails, 1 sent, Runtime: 0:00:15
```

**→ System đã sẵn sàng stream emails to Kafka! 🚀**
