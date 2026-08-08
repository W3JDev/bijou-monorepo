# W3J Bijou AI - Production Deployment Guide

**Version**: 2.1.0 (Enterprise Production Ready)  
**Last Updated**: January 19, 2026  
**Status**: Ready for Production

---

## Table of Contents

1. [Prerequisites](#prerequisites)
2. [Pre-Deployment Checklist](#pre-deployment-checklist)
3. [Local Deployment](#local-deployment)
4. [Cloud Deployment](#cloud-deployment)
5. [Configuration](#configuration)
6. [Monitoring & Health Checks](#monitoring--health-checks)
7. [Backup & Recovery](#backup--recovery)
8. [Security Best Practices](#security-best-practices)
9. [Troubleshooting](#troubleshooting)
10. [Scaling & Performance](#scaling--performance)

---

## Prerequisites

### Required:
- Python 3.11+
- Go 1.19+ (for WhatsApp bridge)
- WhatsApp account (personal or business)
- Google Gemini API key ([get free key](https://makersuite.google.com/app/apikey))
- Git & GitHub account

### Optional:
- Google Cloud Project (for Sheets integration)
- PostgreSQL database (for multi-tenant)
- Domain name & SSL certificate (for production)

---

## Pre-Deployment Checklist

### ✅ Code & Configuration

- [ ] All environment variables configured in `.env`
- [ ] Gemini API key validated and working
- [ ] Google OAuth credentials obtained (if using Sheets)
- [ ] WhatsApp bridge compiled and tested
- [ ] All integration tests passing (`python tests/test_integration.py`)
- [ ] Health check passing (`python src/core/health_monitor.py`)
- [ ] Dashboard working (`python dashboard.py`)

### ✅ Security

- [ ] No API keys committed to git
- [ ] `.env` file in `.gitignore`
- [ ] Credentials folder excluded from git
- [ ] GitHub secrets configured (for CI/CD)
- [ ] Database backups configured
- [ ] SSL/TLS certificates ready (if deploying to cloud)

### ✅ Testing

- [ ] Tested with real WhatsApp messages
- [ ] Cost optimization verified (80% reduction)
- [ ] Quality scores acceptable (>4.0/5.0)
- [ ] Auto-recovery tested (simulate failures)
- [ ] Health monitoring tested

---

## Local Deployment

### Step 1: Clone Repository

```bash
# Clone from private GitHub repository
git clone https://github.com/W3JDev/w3j-bijou-ai.git
cd w3j-bijou-ai
```

### Step 2: Install Dependencies

```bash
# Create virtual environment
python -m venv venv

# Activate (Windows)
venv\Scripts\activate

# Activate (Linux/Mac)
source venv/bin/activate

# Install Python dependencies
pip install -r requirements.txt

# Build WhatsApp bridge
cd ../whatsapp-bridge
go build -o bridge.exe main.go  # Windows
go build -o bridge main.go      # Linux/Mac
```

### Step 3: Configure Environment

```bash
# Copy example environment file
cp .env.example .env

# Edit .env with your credentials
nano .env
```

**Required `.env` variables**:
```bash
# Gemini API
GEMINI_API_KEY=AIzaSyB...

# Bridge Configuration
BRIDGE_URL=http://localhost:8080
BRIDGE_DB_PATH=../whatsapp-bridge/store/messages.db

# Bijou Configuration
BIJOU_DB_PATH=data/bijou.db
WHATSAPP_OWNER=+601160600963
POLLING_INTERVAL=2

# Optional: Google Sheets
SHEETS_SPREADSHEET_ID=your_spreadsheet_id_here
```

### Step 4: Initialize Database

```bash
# Create data directory
mkdir -p data

# Database will be created automatically on first run
python src/core/bijou.py --test
```

### Step 5: Run Health Check

```bash
# Verify all components are healthy
python src/core/health_monitor.py

# Expected output:
# Overall Status: HEALTHY
# All components operational
```

### Step 6: Start Services

**Terminal 1 - WhatsApp Bridge**:
```bash
cd whatsapp-bridge
./bridge  # Linux/Mac
bridge.exe  # Windows

# Scan QR code with WhatsApp
```

**Terminal 2 - Bijou AI**:
```bash
cd w3j-bijou-enterprise
python src/core/bijou.py

# Should see:
# [SUCCESS] Bijou AI v2.1.0 initialized successfully!
# Starting message polling loop...
```

**Terminal 3 - Metrics Dashboard** (optional):
```bash
python dashboard.py --live 10

# Live metrics updating every 10 seconds
```

### Step 7: Test the System

Send a WhatsApp message to your connected number:
```
"Hi, I need help with my order"
```

Expected flow:
1. Bridge receives message → stores in `messages.db`
2. Bijou polls database → detects new message
3. TRACE pipeline processes → generates response
4. ML Judge evaluates quality
5. Response sent via bridge → delivered to WhatsApp
6. Metrics updated in dashboard

---

## Cloud Deployment

### Option 1: DigitalOcean Droplet

**1. Create Droplet**:
```bash
# Create Ubuntu 22.04 droplet ($6/month)
# Min specs: 1 GB RAM, 1 vCPU, 25 GB SSD
```

**2. SSH into Server**:
```bash
ssh root@your_droplet_ip
```

**3. Install Dependencies**:
```bash
# Update system
apt update && apt upgrade -y

# Install Python 3.11
apt install python3.11 python3.11-venv python3-pip -y

# Install Go
wget https://go.dev/dl/go1.21.0.linux-amd64.tar.gz
tar -C /usr/local -xzf go1.21.0.linux-amd64.tar.gz
echo 'export PATH=$PATH:/usr/local/go/bin' >> ~/.bashrc
source ~/.bashrc
```

**4. Clone & Setup**:
```bash
# Clone repository (use deploy key)
git clone git@github.com:W3JDev/w3j-bijou-ai.git
cd w3j-bijou-ai

# Setup virtual environment
python3.11 -m venv venv
source venv/bin/activate
pip install -r requirements.txt

# Build bridge
cd ../whatsapp-bridge
go build -o bridge main.go
```

**5. Create Systemd Services**:

**`/etc/systemd/system/whatsapp-bridge.service`**:
```ini
[Unit]
Description=WhatsApp Bridge Service
After=network.target

[Service]
Type=simple
User=root
WorkingDirectory=/root/whatsapp-bridge
ExecStart=/root/whatsapp-bridge/bridge
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

**`/etc/systemd/system/bijou-ai.service`**:
```ini
[Unit]
Description=Bijou AI Service
After=network.target whatsapp-bridge.service

[Service]
Type=simple
User=root
WorkingDirectory=/root/w3j-bijou-ai
Environment="PATH=/root/w3j-bijou-ai/venv/bin:/usr/bin"
ExecStart=/root/w3j-bijou-ai/venv/bin/python src/core/bijou.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

**6. Enable & Start Services**:
```bash
systemctl daemon-reload
systemctl enable whatsapp-bridge bijou-ai
systemctl start whatsapp-bridge bijou-ai

# Check status
systemctl status bijou-ai
```

**7. Setup Monitoring Cron Job**:
```bash
# Add to crontab (every 5 minutes)
crontab -e

# Add line:
*/5 * * * * cd /root/w3j-bijou-ai && /root/w3j-bijou-ai/venv/bin/python src/core/health_monitor.py >> /var/log/bijou-health.log 2>&1
```

### Option 2: Docker Deployment

**1. Create `Dockerfile`**:
```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application
COPY src/ ./src/
COPY data/ ./data/
COPY .env .

# Expose ports (if needed)
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s \
  CMD python src/core/health_monitor.py || exit 1

# Run application
CMD ["python", "src/core/bijou.py"]
```

**2. Create `docker-compose.yml`**:
```yaml
version: '3.8'

services:
  whatsapp-bridge:
    build: ../whatsapp-bridge
    ports:
      - "8080:8080"
    volumes:
      - ./whatsapp-bridge/store:/app/store
    restart: unless-stopped

  bijou-ai:
    build: .
    depends_on:
      - whatsapp-bridge
    environment:
      - BRIDGE_URL=http://whatsapp-bridge:8080
      - GEMINI_API_KEY=${GEMINI_API_KEY}
    volumes:
      - ./data:/app/data
      - ./credentials:/app/credentials
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "python", "src/core/health_monitor.py"]
      interval: 30s
      timeout: 10s
      retries: 3
```

**3. Deploy**:
```bash
# Build and start
docker-compose up -d

# View logs
docker-compose logs -f bijou-ai

# Check health
docker-compose ps
```

---

## Monitoring & Health Checks

### Automated Health Monitoring

**1. Setup Cron Job** (Linux):
```bash
# Check health every 5 minutes
*/5 * * * * cd /path/to/w3j-bijou-ai && python src/core/health_monitor.py --alert

# Daily health report (email)
0 9 * * * cd /path/to/w3j-bijou-ai && python src/core/health_monitor.py --json | mail -s "Bijou AI Daily Report" your@email.com
```

**2. Setup Windows Task Scheduler**:
- Create task: Run every 5 minutes
- Action: `python C:\path\to\src\core\health_monitor.py`

### Metrics Dashboard

**Run continuously**:
```bash
# Keep dashboard running in tmux/screen
tmux new -s dashboard
python dashboard.py --live 10
# Ctrl+B, D to detach
```

**Export metrics for external monitoring**:
```bash
# Export to JSON every hour
0 * * * * cd /path/to/w3j-bijou-ai && python dashboard.py --json > /var/www/html/metrics.json
```

---

## Backup & Recovery

### Database Backups

**Automated Daily Backup**:
```bash
#!/bin/bash
# backup.sh

BACKUP_DIR="/backup/bijou"
DATE=$(date +%Y%m%d_%H%M%S)

# Create backup directory
mkdir -p $BACKUP_DIR

# Backup Bijou database
cp data/bijou.db $BACKUP_DIR/bijou_$DATE.db

# Backup Bridge database
cp ../whatsapp-bridge/store/messages.db $BACKUP_DIR/messages_$DATE.db

# Keep only last 7 days
find $BACKUP_DIR -name "*.db" -mtime +7 -delete

echo "Backup completed: $DATE"
```

**Setup cron**:
```bash
# Daily backup at 2 AM
0 2 * * * /path/to/backup.sh >> /var/log/bijou-backup.log 2>&1
```

### Google Sheets Backup

If using Google Sheets integration, conversations are automatically logged.

To export:
```bash
# Export to CSV
python -c "from integrations.sheets import GoogleSheetsRAG; s = GoogleSheetsRAG(); s.export_to_csv('backup.csv')"
```

### Recovery Procedure

**From backup**:
```bash
# Stop services
systemctl stop bijou-ai

# Restore database
cp /backup/bijou/bijou_20260119.db data/bijou.db

# Restart service
systemctl start bijou-ai

# Verify health
python src/core/health_monitor.py
```

---

## Security Best Practices

### 1. Environment Variables

Never commit sensitive data:
```bash
# .gitignore
.env
credentials/
*.db
__pycache__/
venv/
```

### 2. API Key Rotation

Rotate Gemini API key quarterly:
```bash
# 1. Generate new key in Google AI Studio
# 2. Update .env
# 3. Test with health check
python src/core/health_monitor.py
# 4. Restart service
systemctl restart bijou-ai
```

### 3. Database Encryption (Optional)

For sensitive deployments, encrypt SQLite:
```python
# Use SQLCipher
pip install sqlcipher3

# In code:
import sqlcipher3 as sqlite3
conn = sqlite3.connect('data/bijou.db')
conn.execute(f"PRAGMA key='{encryption_key}'")
```

### 4. Firewall Configuration

```bash
# Allow only necessary ports
ufw allow 22   # SSH
ufw allow 8080 # Bridge (if external access needed)
ufw enable
```

---

## Troubleshooting

### Issue: Bridge Not Connecting

**Symptoms**: No messages being received

**Solution**:
```bash
# Check bridge status
systemctl status whatsapp-bridge

# Check bridge logs
journalctl -u whatsapp-bridge -f

# Restart bridge
systemctl restart whatsapp-bridge

# Re-scan QR code if needed
```

### Issue: High API Costs

**Symptoms**: Cost optimizer not working (>20% API calls)

**Solution**:
```bash
# Check cache hit rate
python -c "from core.cost_optimizer import CostOptimizer; c = CostOptimizer(); print(c.get_optimization_stats())"

# Clear cache and restart
rm -rf data/cache/*
systemctl restart bijou-ai
```

### Issue: Low Quality Scores

**Symptoms**: Average quality < 3.5/5.0

**Solution**:
```bash
# Review ML Judge insights
python -c "from core.ml_judge import MLJudge; j = MLJudge(); print(j.get_learning_insights())"

# Common fixes:
# - Update FAQ in Google Sheets
# - Adjust humanizer intensity
# - Review failed responses in logs
```

### Issue: System Unhealthy

**Symptoms**: Health check shows UNHEALTHY

**Solution**:
```bash
# Run detailed health check
python src/core/health_monitor.py --verbose

# Check individual components:
# 1. Bridge: curl http://localhost:8080/api/health
# 2. Database: sqlite3 data/bijou.db "SELECT COUNT(*) FROM conversations"
# 3. Gemini: python -c "import google.generativeai as genai; genai.configure(api_key='your_key'); print('OK')"

# Restart if needed
systemctl restart bijou-ai
```

---

## Scaling & Performance

### Horizontal Scaling

For high-volume deployments (>100K messages/day):

**1. Load Balancer Setup**:
```
                     ┌─────────────┐
  WhatsApp ──────>   │Load Balancer│
                     └──────┬──────┘
                            │
              ┌─────────────┼─────────────┐
              │             │             │
         ┌────▼───┐    ┌───▼────┐   ┌───▼────┐
         │Bijou 1 │    │Bijou 2 │   │Bijou 3 │
         └────┬───┘    └───┬────┘   └───┬────┘
              │            │            │
              └────────────┼────────────┘
                           │
                   ┌───────▼────────┐
                   │  PostgreSQL    │
                   │  (Shared DB)   │
                   └────────────────┘
```

**2. Database Migration**:
```bash
# Migrate SQLite → PostgreSQL
pip install psycopg2-binary

# Update .env
DATABASE_URL=postgresql://user:pass@host:5432/bijou

# Migrate data
python scripts/migrate_to_postgres.py
```

### Performance Tuning

**1. Increase Polling Interval** (if low traffic):
```bash
# .env
POLLING_INTERVAL=5  # Check every 5s instead of 2s
```

**2. Batch Processing**:
```python
# In bijou.py, process multiple messages at once
messages = fetch_new_messages(limit=10)
responses = [process_message(msg) for msg in messages]
batch_send(responses)
```

**3. Redis Caching** (for distributed setup):
```bash
pip install redis

# Update cost_optimizer.py to use Redis
```

---

## Production Checklist

Before going live:

- [ ] All tests passing
- [ ] Health checks green
- [ ] Backups configured
- [ ] Monitoring setup
- [ ] Documentation updated
- [ ] Team trained on operations
- [ ] Incident response plan ready
- [ ] Scaling strategy defined
- [ ] Cost projections validated
- [ ] Security audit completed

---

## Support & Resources

- **GitHub Issues**: [Report bugs](https://github.com/W3JDev/w3j-bijou-ai/issues)
- **Email Support**: w3j.btc@gmail.com
- **Documentation**: See `docs/` directory
- **Health Check**: `python src/core/health_monitor.py`
- **Dashboard**: `python dashboard.py --live 10`

---

**Version 2.1.0 - Enterprise Production Ready**  
**Built with ❤️ by W3J**
