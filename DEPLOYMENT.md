# Deployment Guide

This guide covers different deployment options for the JSON QA Web Application.

## Quick Start

### Local Development
```bash
# 1. Setup environment
python setup.py

# 2. Start application
python -m streamlit run streamlit_app.py

# 3. Access at http://localhost:8501
```

## Production Deployment

### Option 1: Streamlit Cloud (Recommended)

1. **Prepare Repository**
   ```bash
   git init
   git add .
   git commit -m "Initial commit"
   git remote add origin <your-repo-url>
   git push -u origin main
   ```

2. **Deploy to Streamlit Cloud**
   - Visit [share.streamlit.io](https://share.streamlit.io)
   - Connect your GitHub repository
   - Select `streamlit_app.py` as the main file
   - Deploy automatically

3. **Configuration**
   - Streamlit Cloud will use `.streamlit/config.toml`
   - Environment variables can be set in the dashboard
   - Secrets can be managed through the secrets management interface

### Option 2: Docker Deployment

1. **Create Dockerfile**
   ```dockerfile
   FROM python:3.9-slim

   WORKDIR /app

   # Copy requirements and install dependencies
   COPY requirements.txt .
   RUN pip install --no-cache-dir -r requirements.txt

   # Copy application files
   COPY . .

   # Create necessary directories
   RUN python setup.py

   # Expose port
   EXPOSE 8501

   # Health check
   HEALTHCHECK CMD curl --fail http://localhost:8501/_stcore/health

   # Run application
   CMD ["streamlit", "run", "streamlit_app.py", "--server.port=8501", "--server.address=0.0.0.0"]
   ```

2. **Build and Run**
   ```bash
   # Build image
   docker build -t json-qa-app .

   # Run container
   docker run -p 8501:8501 -v $(pwd)/data:/app/json_docs json-qa-app
   ```

3. **Docker Compose (Optional)**
   ```yaml
   version: '3.8'
   services:
     json-qa-app:
       build: .
       ports:
         - "8501:8501"
       volumes:
         - ./data:/app/json_docs
         - ./pdfs:/app/pdf_docs
         - ./schemas:/app/schemas
         - ./corrected:/app/corrected
         - ./audit_logs:/app/audit_logs
       environment:
         - STREAMLIT_SERVER_HEADLESS=true
         - STREAMLIT_BROWSER_GATHER_USAGE_STATS=false
   ```

### Option 3: Traditional Server Deployment

1. **Server Requirements**
   - Python 3.8+
   - 2GB RAM minimum
   - 10GB disk space
   - Network access for users

2. **Installation**
   ```bash
   # Clone repository
   git clone <repository-url>
   cd json-qa-webapp

   # Setup environment
   python -m venv venv
   source venv/bin/activate  # Linux/Mac
   # or
   venv\Scripts\activate     # Windows

   # Install dependencies
   pip install -r requirements.txt

   # Run setup
   python setup.py
   ```

3. **Service Configuration (systemd)**
   ```ini
   # /etc/systemd/system/json-qa-app.service
   [Unit]
   Description=JSON QA Web Application
   After=network.target

   [Service]
   Type=simple
   User=www-data
   WorkingDirectory=/opt/json-qa-webapp
   Environment=PATH=/opt/json-qa-webapp/venv/bin
   ExecStart=/opt/json-qa-webapp/venv/bin/streamlit run streamlit_app.py --server.port=8501 --server.address=0.0.0.0
   Restart=always

   [Install]
   WantedBy=multi-user.target
   ```

4. **Start Service**
   ```bash
   sudo systemctl enable json-qa-app
   sudo systemctl start json-qa-app
   sudo systemctl status json-qa-app
   ```

### Option 4: Reverse Proxy Setup (Nginx)

1. **Nginx Configuration**
   ```nginx
   server {
       listen 80;
       server_name your-domain.com;

       location / {
           proxy_pass http://localhost:8501;
           proxy_http_version 1.1;
           proxy_set_header Upgrade $http_upgrade;
           proxy_set_header Connection "upgrade";
           proxy_set_header Host $host;
           proxy_set_header X-Real-IP $remote_addr;
           proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
           proxy_set_header X-Forwarded-Proto $scheme;
           proxy_cache_bypass $http_upgrade;
       }
   }
   ```

2. **SSL with Let's Encrypt**
   ```bash
   sudo certbot --nginx -d your-domain.com
   ```

## Environment Configuration

### Environment Variables
```bash
# Server configuration
export STREAMLIT_SERVER_PORT=8501
export STREAMLIT_SERVER_ADDRESS=0.0.0.0
export STREAMLIT_SERVER_HEADLESS=true

# Browser settings
export STREAMLIT_BROWSER_GATHER_USAGE_STATS=false

# Application settings
export JSON_QA_DATA_DIR=/path/to/data
export JSON_QA_LOG_LEVEL=INFO
```

### Configuration Files

1. **Streamlit Config** (`.streamlit/config.toml`)
   ```toml
   [server]
   port = 8501
   address = "0.0.0.0"
   headless = true
   
   [browser]
   gatherUsageStats = false
   ```

2. **Application Config** (`config.yaml`)
   ```yaml
   # File paths
   data_directory: "./json_docs"
   pdf_directory: "./pdf_docs"
   schema_directory: "./schemas"
   output_directory: "./corrected"
   audit_directory: "./audit_logs"
   
   # Application settings
   max_file_size_mb: 50
   lock_timeout_minutes: 30
   auto_cleanup_enabled: true
   
   # UI settings
   items_per_page: 20
   enable_pdf_preview: true
   ```

## Security Considerations

### Network Security
- Use HTTPS in production (SSL/TLS certificates)
- Configure firewall to restrict access
- Consider VPN access for sensitive data

### Application Security
- No built-in authentication - add if needed
- File access is limited to configured directories
- Input validation through Pydantic models
- Audit logging for all changes

### Data Security
- Ensure proper file permissions on data directories
- Regular backups of audit logs and corrected files
- Consider encryption for sensitive documents

## Monitoring and Maintenance

### Health Checks
```bash
# Check application status
curl http://localhost:8501/_stcore/health

# Check file system
df -h
du -sh json_docs/ corrected/ audit_logs/

# Check processes
ps aux | grep streamlit
```

### Log Monitoring
```bash
# Application logs
tail -f ~/.streamlit/logs/streamlit.log

# System logs (if using systemd)
journalctl -u json-qa-app -f

# Audit logs
tail -f audit_logs/audit.jsonl
```

### Maintenance Tasks
```bash
# Clean up old locks (automated in app)
find locks/ -name "*.lock" -mmin +30 -delete

# Archive old audit logs
gzip audit_logs/audit-$(date +%Y%m).jsonl

# Backup corrected files
tar -czf backups/corrected-$(date +%Y%m%d).tar.gz corrected/
```

## Scaling Considerations

### Horizontal Scaling
- Use load balancer for multiple instances
- Shared file system (NFS, S3) for data directories
- Database for audit logs (PostgreSQL, MongoDB)

### Performance Optimization
- Use SSD storage for better I/O performance
- Increase memory for large file processing
- Consider CDN for static assets

### High Availability
- Multiple application instances
- Database replication
- Automated failover
- Regular backups

## Troubleshooting

### Common Issues
1. **Port already in use**: Change port in config or kill existing process
2. **Permission denied**: Check file permissions on data directories
3. **Memory issues**: Increase available RAM or optimize file sizes
4. **PDF not loading**: Verify PDF files exist and are readable

### Debug Mode
```bash
# Run with debug logging
streamlit run streamlit_app.py --logger.level=debug

# Check configuration
streamlit config show
```

### Support
- Check application logs for detailed error messages
- Verify all dependencies are installed correctly
- Ensure proper directory structure and permissions
- Test with sample data first