# Kafka Integration for Chat Application

This document describes the Kafka integration implemented to replace tight coupling with async message-driven communication.

## Architecture Changes

### Before (Tight Coupling)
- Chat service made direct HTTP calls to auth service
- Synchronous blocking requests
- Single point of failure
- No fault tolerance

### After (Event-Driven)
- Services communicate via Kafka events
- Asynchronous message processing
- Fault tolerance with retries
- Better scalability and reliability

## Kafka Setup

### Services Added
- **Zookeeper**: Kafka coordination service
- **Kafka**: Message broker
- **Kafka UI**: Web interface for monitoring (http://localhost:8080)
- **Auth Kafka Consumer**: Processes auth-related events
- **Chat Kafka Consumer**: Processes chat-related events

### Topics Created
- `user.events` - User registration, verification, profile updates
- `auth.events` - Authentication events, user searches
- `chat.events` - Room creation, messages, typing indicators

## Event Schemas

### User Events
```json
{
  "event_type": "user.registered",
  "user_id": "uuid",
  "username": "string",
  "email": "string",
  "timestamp": 1640995200000,
  "service": "auth_service"
}
```

### Auth Events
```json
{
  "event_type": "auth.user.search.response",
  "request_id": "uuid",
  "users": [{"id": "uuid", "username": "string", "email": "string"}],
  "timestamp": 1640995200000,
  "service": "auth_service"
}
```

### Chat Events
```json
{
  "event_type": "chat.room.created",
  "room_id": "uuid",
  "room_name": "string",
  "creator_id": "uuid",
  "members": ["uuid1", "uuid2"],
  "timestamp": 1640995200000,
  "service": "chat_service"
}
```

## Key Changes Made

### 1. Docker Compose Updates
- Added Kafka and Zookeeper services
- Added dedicated Kafka consumer containers
- Updated service dependencies

### 2. Dependencies
- Added `kafka-python==2.0.2` to both services
- Updated requirements.txt files

### 3. Kafka Utilities
- `auth_service/auth_service/kafka_utils.py` - Producer/consumer for auth service
- `chat_service/chat_service/kafka_utils.py` - Producer/consumer for chat service

### 4. Event Publishing
- User registration → `user.events` topic
- User verification → `user.events` topic
- Room creation → `chat.events` topic
- Message sent → `chat.events` topic

### 5. Event Consumption
- Auth service: Handles user search requests
- Chat service: Caches user search responses

### 6. Management Commands
- `python manage.py start_kafka_consumer` - Starts Kafka consumers for each service

## Testing the Integration

### 1. Start Services
```bash
docker-compose up -d
```

### 2. Test Kafka Connectivity
```bash
python test_kafka_setup.py
```

### 3. Monitor Topics
Visit Kafka UI at http://localhost:8080 to see:
- Topics and partitions
- Message flow
- Consumer groups
- Lag monitoring

### 4. Check Logs
```bash
# Auth service Kafka consumer
docker-compose logs auth-kafka-consumer

# Chat service Kafka consumer
docker-compose logs chat-kafka-consumer

# Kafka broker
docker-compose logs kafka
```

## Gradual Migration Strategy

The implementation includes a **gradual migration approach**:

1. **Fallback mechanism**: Chat service still tries HTTP calls if cache misses
2. **Dual publishing**: Events are published to both Kafka and processed synchronously
3. **Cache warming**: Kafka responses populate cache for future requests

This ensures:
- ✅ No breaking changes during deployment
- ✅ Graceful degradation if Kafka is unavailable
- ✅ Smooth transition from tight coupling to event-driven

## Benefits Achieved

### Reliability
- **Fault tolerance**: Services can operate independently
- **Retry mechanisms**: Built-in Kafka delivery guarantees
- **Circuit breaker**: Cache prevents cascading failures

### Scalability
- **Horizontal scaling**: Multiple consumer instances
- **Load distribution**: Kafka partitioning
- **Async processing**: Non-blocking operations

### Monitoring
- **Event tracking**: All inter-service communication is visible
- **Debugging**: Message history in Kafka
- **Metrics**: Consumer lag and throughput monitoring

## Future Enhancements

### 1. Complete HTTP Removal
Once Kafka is stable, remove HTTP fallbacks:
```python
# Remove this after migration
if AUTH_SERVICE_URL and missing_usernames:
    # Fallback HTTP logic
```

### 2. Dead Letter Queues
Add error handling topics:
- `user.events.dlq`
- `auth.events.dlq`
- `chat.events.dlq`

### 3. Event Sourcing
Store all events for audit trails and replay capabilities

### 4. Schema Registry
Add Confluent Schema Registry for event schema validation

### 5. Kafka Streams
Implement real-time event processing and aggregations

## Troubleshooting

### Common Issues

1. **Kafka not starting**
   ```bash
   docker-compose logs zookeeper
   docker-compose logs kafka
   ```

2. **Consumer not receiving messages**
   - Check consumer group in Kafka UI
   - Verify topic creation
   - Check network connectivity

3. **Message serialization errors**
   - Verify JSON schema compatibility
   - Check encoding/decoding logic

4. **Performance issues**
   - Monitor consumer lag
   - Adjust batch sizes
   - Scale consumer instances

### Configuration Files
- `docker-compose.yml` - Service definitions
- `.env` - Environment variables
- `**/kafka_utils.py` - Kafka configurations

This integration transforms your chat application from tightly-coupled services to a modern, event-driven microservices architecture.