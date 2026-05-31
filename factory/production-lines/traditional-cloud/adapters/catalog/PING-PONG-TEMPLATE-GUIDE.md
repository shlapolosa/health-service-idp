# Ping-Pong Realtime Service Template Guide

This template demonstrates how to build microservices that consume and expose realtime capabilities using the health-service-idp platform. It provides a complete example of the MQTT → Kafka → Stream Processing → WebSocket flow.

## 🎯 Purpose

The ping-pong template serves as a starting point for developers to understand how to:

1. **Integrate with Realtime Platform**: Connect to MQTT, Kafka, and stream processing infrastructure
2. **Handle WebSocket Connections**: Provide real-time data streaming to web clients
3. **Process Streaming Data**: Transform messages using Lenses SQL queries
4. **Follow Best Practices**: Implement proper error handling, health checks, and monitoring

## 🏗️ Architecture Overview

```
┌─────────────────┐    ┌──────────────┐    ┌─────────────────┐    ┌──────────────┐
│  Ping Generator │───▶│ MQTT Broker  │───▶│ Kafka Cluster   │───▶│ Stream       │
│  (Data Source)  │    │ (port 1883)  │    │ (ping_topic)    │    │ Processing   │
└─────────────────┘    └──────────────┘    └─────────────────┘    │ (Lenses SQL) │
                                                                    └──────┬───────┘
                                                                           │
┌─────────────────┐    ┌──────────────┐    ┌─────────────────┐           │
│   Web Clients   │◀───│  WebSocket   │◀───│ Kafka Consumer  │◀──────────┘
│  (Browsers)     │    │  Endpoint    │    │ (pong_topic)    │
└─────────────────┘    └──────────────┘    └─────────────────┘
```

## 📦 Components

### 1. Ping Data Generator (`ping-data-generator`)
- **Purpose**: Generates test ping messages
- **Technology**: FastAPI + MQTT Client
- **Function**: Publishes JSON messages to `ping/messages` MQTT topic every 5 seconds

### 2. Ping-Pong Service (`ping-pong-platform`)
- **Purpose**: Main realtime processing service
- **Technology**: FastAPI + Kafka Consumer + WebSocket
- **Function**: Consumes processed pong messages and streams them to WebSocket clients

### 3. Stream Processing Queries
- **Ping→Pong Transformation**: Converts ping messages to pong responses
- **Analytics Stream**: Tracks processing metrics and message counts

## 🚀 Usage Instructions

### 1. Deploy the Template

```yaml
# Apply the complete template
kubectl apply -f ping-pong-realtime-template.yaml

# Or use as an ApplicationClaim
apiVersion: platform.example.org/v1alpha1
kind: ApplicationClaim
metadata:
  name: my-ping-pong-service
spec:
  name: my-ping-pong
  language: python
  framework: fastapi
  realtime: "my-streaming-platform"  # This creates the realtime infrastructure
  websocket: true
  streaming:
    enabled: true
    topics: ["ping_topic", "pong_topic"]
```

### 2. Access the Service

Once deployed, you can access:

- **Service API**: `https://ping-pong.demo.local/`
- **WebSocket Demo**: `https://ping-pong.demo.local/demo`
- **Health Check**: `https://ping-pong.demo.local/health`
- **Data Generator**: `https://ping-generator.demo.local/`

### 3. Test the Flow

1. **Generate Data**: The data generator automatically starts sending ping messages
2. **View Processing**: Monitor the Lenses UI to see stream processing
3. **See Results**: Open the demo page to see real-time pong messages in your browser

## 🔧 Configuration

### Environment Variables (Auto-injected by Realtime Platform)

```bash
# Kafka Configuration
KAFKA_BOOTSTRAP_SERVERS=ping-pong-streaming-kafka:9092
KAFKA_SCHEMA_REGISTRY_URL=http://ping-pong-streaming-kafka:8081

# MQTT Configuration  
MQTT_HOST=ping-pong-streaming-mqtt
MQTT_PORT=1883
MQTT_USER=realtime-user
MQTT_PASSWORD=realtime-pass

# Service Configuration
PING_MQTT_TOPIC=ping/messages
PONG_WEBSOCKET_ENDPOINT=/ws/pong
MESSAGE_INTERVAL=5
```

### Kafka Topics Created

| Topic | Purpose | Schema |
|-------|---------|--------|
| `ping_topic` | Incoming ping messages from MQTT | `PingMessage` |
| `pong_topic` | Processed pong responses | `PongMessage` |
| `ping_analytics_topic` | Processing metrics | Analytics schema |

### Stream Processing Queries

```sql
-- Transform ping to pong
INSERT INTO pong_topic
SELECT STREAM
    _value.messageId AS _key,
    STRUCT(
      messageId := _value.messageId,
      originalContent := _value.content,
      response := CONCAT('pong: ', _value.content),
      pingTimestamp := _value.timestamp,
      pongTimestamp := UNIX_TIMESTAMP() * 1000,
      processingTimeMs := (UNIX_TIMESTAMP() * 1000) - _value.timestamp
    ) AS _value
FROM ping_topic;
```

## 📊 Monitoring & Observability

### Health Endpoints
- `GET /health` - Service health status
- `GET /` - Service status with connection count

### Metrics Available
- WebSocket connection count
- Message processing latency
- Kafka consumer lag
- MQTT connection status

### Lenses UI Access
- **URL**: Via realtime platform secrets
- **Credentials**: From `{platform-name}-lenses-secret`
- **Features**: Topic monitoring, query management, connector status

## 🛠️ Customization Guide

### 1. Modify Message Schema

Update the Avro schemas in the ConfigMap:

```yaml
apiVersion: v1
kind: ConfigMap
metadata:
  name: my-custom-schemas
data:
  my-message.avsc: |
    {
      "type": "record",
      "name": "MyMessage",
      "fields": [
        {"name": "id", "type": "string"},
        {"name": "data", "type": "string"},
        {"name": "timestamp", "type": "long"}
      ]
    }
```

### 2. Add New Stream Processing

Create additional Lenses SQL queries:

```sql
-- Filter messages by content
INSERT INTO filtered_topic
SELECT STREAM *
FROM ping_topic
WHERE _value.content LIKE '%important%';

-- Aggregate by time window
INSERT INTO hourly_stats
SELECT STREAM
    STRUCT(
      hour := DATE_FORMAT(_value.timestamp, 'yyyy-MM-dd HH'),
      messageCount := COUNT(*),
      avgProcessingTime := AVG(_value.processingTimeMs)
    ) AS _value
FROM pong_topic
GROUP BY DATE_FORMAT(_value.timestamp, 'yyyy-MM-dd HH');
```

### 3. Extend WebSocket Functionality

```python
# Add message filtering
@app.websocket("/ws/filtered")
async def filtered_websocket(websocket: WebSocket, filter: str = ""):
    await manager.connect(websocket)
    # Filter messages based on content
    # Implementation details...

# Add message history
@app.get("/api/history")
async def get_message_history(limit: int = 100):
    # Return recent messages from Kafka
    # Implementation details...
```

## 🔄 Development Workflow

### 1. Local Development

```bash
# 1. Start realtime platform (via ApplicationClaim)
kubectl apply -f my-realtime-platform.yaml

# 2. Get connection secrets
kubectl get secret my-platform-kafka-secret -o yaml

# 3. Set environment variables
export KAFKA_BOOTSTRAP_SERVERS=localhost:9092
export MQTT_HOST=localhost

# 4. Run service locally
pip install -r requirements.txt
uvicorn main:app --reload
```

### 2. Testing

```bash
# Unit tests
pytest tests/

# Integration tests with Docker
docker-compose -f docker-compose.test.yml up

# Load testing
python load_test.py --messages 1000 --rate 10
```

### 3. Deployment

```bash
# Build and push image
docker build -t my-org/my-ping-pong:v1.0.0 .
docker push my-org/my-ping-pong:v1.0.0

# Update ApplicationClaim
kubectl patch applicationclaim my-service \
  --type merge \
  --patch '{"spec":{"image":"my-org/my-ping-pong:v1.0.0"}}'
```

## 📚 Best Practices

### 1. Error Handling
- Always handle Kafka consumer errors gracefully
- Implement retry logic for MQTT connections
- Use circuit breakers for external dependencies

### 2. Performance
- Use connection pooling for Kafka consumers
- Implement proper backpressure handling for WebSocket connections
- Monitor memory usage with large message volumes

### 3. Security
- Never hardcode credentials (use injected secrets)
- Validate all incoming messages
- Implement proper authentication for WebSocket connections

### 4. Observability
- Add structured logging with correlation IDs
- Expose Prometheus metrics
- Include health checks for all dependencies

## 🤝 Contributing

This template can be extended for various use cases:

- **IoT Data Processing**: Replace ping/pong with sensor data
- **Financial Streams**: Process trading data or market feeds
- **Social Media**: Handle real-time social media feeds
- **Gaming**: Process game events and player actions

## 📖 Related Documentation

- [ApplicationClaim Guide](./APPLICATION-CLAIM-GUIDE.md)
- [Realtime Platform Architecture](./REALTIME_SYSTEM.md)
- [Lenses SQL Reference](https://docs.lenses.io/sql/)
- [FastAPI WebSocket Documentation](https://fastapi.tiangolo.com/advanced/websockets/)

---

This template provides a complete foundation for building realtime microservices that integrate with the health-service-idp platform. Use it as a starting point and customize according to your specific requirements.