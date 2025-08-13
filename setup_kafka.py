"""
Setup script for Kafka using Docker
"""
import subprocess
import time
import sys
from loguru import logger


def run_command(cmd, check=True):
    """Run shell command"""
    try:
        result = subprocess.run(cmd, shell=True, capture_output=True, text=True, check=check)
        return result.returncode == 0, result.stdout, result.stderr
    except subprocess.CalledProcessError as e:
        return False, e.stdout, e.stderr


def check_docker():
    """Check if Docker is available"""
    logger.info("Checking Docker availability...")
    success, stdout, stderr = run_command("docker --version", check=False)
    if success:
        logger.info(f"✅ Docker found: {stdout.strip()}")
        return True
    else:
        logger.error("❌ Docker not found. Please install Docker first.")
        return False


def setup_kafka():
    """Setup Kafka using Docker"""
    logger.info("Setting up Kafka with Docker...")
    
    # Stop existing containers
    logger.info("Stopping existing Kafka containers...")
    run_command("docker stop kafka zookeeper", check=False)
    run_command("docker rm kafka zookeeper", check=False)
    
    # Start Zookeeper
    logger.info("Starting Zookeeper...")
    zk_cmd = [
        "docker", "run", "-d", "--name", "zookeeper",
        "-p", "2181:2181",
        "-e", "ZOOKEEPER_CLIENT_PORT=2181",
        "-e", "ZOOKEEPER_TICK_TIME=2000",
        "confluentinc/cp-zookeeper:7.4.0"
    ]
    
    success, stdout, stderr = run_command(" ".join(zk_cmd))
    if not success:
        logger.error(f"Failed to start Zookeeper: {stderr}")
        return False
    
    logger.info("✅ Zookeeper started")
    
    # Wait a bit for Zookeeper to start
    time.sleep(10)
    
    # Start Kafka
    logger.info("Starting Kafka...")
    kafka_cmd = [
        "docker", "run", "-d", "--name", "kafka",
        "-p", "9092:9092",
        "-e", "KAFKA_BROKER_ID=1",
        "-e", "KAFKA_ZOOKEEPER_CONNECT=zookeeper:2181",
        "-e", "KAFKA_LISTENER_SECURITY_PROTOCOL_MAP=PLAINTEXT:PLAINTEXT,PLAINTEXT_HOST:PLAINTEXT",
        "-e", "KAFKA_ADVERTISED_LISTENERS=PLAINTEXT://kafka:29092,PLAINTEXT_HOST://localhost:9092",
        "-e", "KAFKA_OFFSETS_TOPIC_REPLICATION_FACTOR=1",
        "-e", "KAFKA_TRANSACTION_STATE_LOG_MIN_ISR=1",
        "-e", "KAFKA_TRANSACTION_STATE_LOG_REPLICATION_FACTOR=1",
        "--link", "zookeeper",
        "confluentinc/cp-kafka:7.4.0"
    ]
    
    success, stdout, stderr = run_command(" ".join(kafka_cmd))
    if not success:
        logger.error(f"Failed to start Kafka: {stderr}")
        return False
    
    logger.info("✅ Kafka started")
    
    # Wait for Kafka to be ready
    logger.info("Waiting for Kafka to be ready...")
    time.sleep(20)
    
    # Create topic
    logger.info("Creating email_stream topic...")
    topic_cmd = [
        "docker", "exec", "kafka", "kafka-topics", "--create",
        "--topic", "email_stream",
        "--bootstrap-server", "localhost:9092",
        "--partitions", "1",
        "--replication-factor", "1"
    ]
    
    success, stdout, stderr = run_command(" ".join(topic_cmd), check=False)
    if success:
        logger.info("✅ Topic created successfully")
    else:
        logger.warning(f"Topic creation result: {stderr}")
    
    return True


def check_kafka_status():
    """Check Kafka status"""
    logger.info("Checking Kafka status...")
    
    # Check containers
    success, stdout, stderr = run_command("docker ps --filter name=kafka --filter name=zookeeper")
    if success:
        logger.info("Running containers:")
        logger.info(stdout)
    
    # List topics
    success, stdout, stderr = run_command(
        "docker exec kafka kafka-topics --list --bootstrap-server localhost:9092", 
        check=False
    )
    if success:
        logger.info(f"Available topics: {stdout.strip()}")
    else:
        logger.warning("Could not list topics")


def main():
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python setup_kafka.py setup    - Setup Kafka with Docker")
        print("  python setup_kafka.py status   - Check Kafka status")
        print("  python setup_kafka.py stop     - Stop Kafka containers")
        sys.exit(1)
    
    command = sys.argv[1].lower()
    
    if command == "setup":
        if not check_docker():
            sys.exit(1)
        
        if setup_kafka():
            logger.info("🎉 Kafka setup completed successfully!")
            check_kafka_status()
        else:
            logger.error("❌ Kafka setup failed")
            sys.exit(1)
    
    elif command == "status":
        check_kafka_status()
    
    elif command == "stop":
        logger.info("Stopping Kafka containers...")
        run_command("docker stop kafka zookeeper", check=False)
        run_command("docker rm kafka zookeeper", check=False)
        logger.info("✅ Kafka containers stopped")
    
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)


if __name__ == "__main__":
    main()
