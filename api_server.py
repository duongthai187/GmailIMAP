"""
FastAPI server for Email IMAP to Kafka Streamer
"""
import asyncio
from contextlib import asynccontextmanager
from fastapi import FastAPI, HTTPException
from fastapi.responses import JSONResponse
from loguru import logger

from email_monitor import EmailMonitorService
from config import settings

# Global service instance
email_service: EmailMonitorService = None
monitor_task: asyncio.Task = None


@asynccontextmanager
async def lifespan(app: FastAPI):
    """FastAPI lifespan manager"""
    global email_service, monitor_task
    
    # Startup
    logger.info("Starting Email IMAP to Kafka Streamer API")
    email_service = EmailMonitorService()
    
    # Start monitoring task in background
    monitor_task = asyncio.create_task(email_service.start())
    
    yield
    
    # Shutdown
    logger.info("Shutting down Email IMAP to Kafka Streamer API")
    if email_service:
        await email_service.stop()
    
    if monitor_task and not monitor_task.done():
        monitor_task.cancel()
        try:
            await monitor_task
        except asyncio.CancelledError:
            pass


# Create FastAPI app
app = FastAPI(
    title="Email IMAP to Kafka Streamer",
    description="A service that monitors IMAP for new emails and streams them to Kafka",
    version="1.0.0",
    lifespan=lifespan
)


@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Email IMAP to Kafka Streamer API",
        "version": "1.0.0",
        "status": "running"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    if not email_service:
        raise HTTPException(status_code=503, detail="Service not initialized")
    
    status = email_service.get_status()
    
    # Check if service is healthy
    is_healthy = (
        status["imap"]["connected"] and 
        status["kafka"]["connected"] and
        status["service"]["running"]
    )
    
    if is_healthy:
        return JSONResponse(
            status_code=200,
            content={
                "status": "healthy",
                "timestamp": status["service"]["last_check"],
                "details": status
            }
        )
    else:
        return JSONResponse(
            status_code=503,
            content={
                "status": "unhealthy",
                "details": status
            }
        )


@app.get("/status")
async def get_status():
    """Get detailed service status"""
    if not email_service:
        raise HTTPException(status_code=503, detail="Service not initialized")
    
    return email_service.get_status()


@app.post("/trigger-check")
async def trigger_manual_check():
    """Trigger a manual email check"""
    if not email_service:
        raise HTTPException(status_code=503, detail="Service not initialized")
    
    try:
        await email_service._check_and_process_emails()
        return {"message": "Manual email check completed", "status": "success"}
    except Exception as e:
        logger.error(f"Error in manual check: {e}")
        raise HTTPException(status_code=500, detail=f"Manual check failed: {str(e)}")


@app.get("/config")
async def get_config():
    """Get current configuration (without sensitive data)"""
    return {
        "imap": {
            "server": settings.imap_server,
            "port": settings.imap_port,
            "username": settings.imap_username,
            "folder": settings.imap_folder
        },
        "kafka": {
            "bootstrap_servers": settings.kafka_bootstrap_servers,
            "topic": settings.kafka_topic,
            "client_id": settings.kafka_client_id
        },
        "app": {
            "check_interval_minutes": settings.check_interval_minutes,
            "max_emails_per_check": settings.max_emails_per_check,
            "log_level": settings.log_level
        }
    }


if __name__ == "__main__":
    import uvicorn
    
    # Configure logging
    logger.add("logs/email_streamer.log", rotation="1 day", retention="7 days")
    
    # Run server
    uvicorn.run(
        "api_server:app",
        host=settings.api_host,
        port=settings.api_port,
        reload=False,
        log_level=settings.log_level.lower()
    )
