# Chat Application Microservice Architecture Documentation

## Table of Contents
1. [Architecture Overview](#architecture-overview)
2. [Service Structure](#service-structure)
3. [Kafka Components & Communication](#kafka-components--communication)
4. [Detailed Request Flows](#detailed-request-flows)
5. [WebSocket Real-time Communication](#websocket-real-time-communication)
6. [Inter-Service Authentication](#inter-service-authentication)
7. [Database Models & Relationships](#database-models--relationships)
8. [Infrastructure & Deployment](#infrastructure--deployment)

---

## Architecture Overview

This chat application follows a **microservices architecture** with event-driven communication using Apache Kafka. The system consists of two main services that communicate through multiple patterns:

```
┌─────────────────┐    ┌─────────────────┐
│   Auth Service  │    │  Chat Service   │
│   (Port 8000)   │    │   (Port 8001)   │
│                 │    │                 │
│ ┌─────────────┐ │    │ ┌─────────────┐ │
│ │ User Mgmt   │ │    │ │ Chat Rooms  │ │
│ │ JWT Auth    │ │    │ │ Messages    │ │
│ │ OTP Verify  │ │    │ │ WebSocket   │ │
│ └─────────────┘ │    │ └─────────────┘ │
└─────────────────┘    └─────────────────┘
         │                       │
         └───────────┬───────────┘
                     │
    ┌─────────────────────────────────┐
    │      Kafka Message Broker       │
    │  ┌─────────┐ ┌─────────────┐   │
    │  │ Topics  │ │ Consumers   │   │
    │  │ Events  │ │ Producers   │   │
    │  └─────────┘ └─────────────┘   │
    └─────────────────────────────────┘
```

**★ Insight ─────────────────────────────────────**
The architecture uses a hybrid communication approach: synchronous HTTP for critical operations requiring immediate responses, and asynchronous Kafka events for scalable, decoupled operations like notifications and analytics.
**─────────────────────────────────────────────────**

---

## Service Structure

### Auth Service ([auth_service/](auth_service/))
**Purpose**: User authentication, authorization, and user management

**Key Files**:
- [auth_service/users/views.py](auth_service/users/views.py) - API endpoints
- [auth_service/auth_service/kafka_utils.py](auth_service/auth_service/kafka_utils.py) - Kafka communication
- [auth_service/users/models.py](auth_service/users/models.py) - User data models
- [auth_service/users/management/commands/start_kafka_consumer.py](auth_service/users/management/commands/start_kafka_consumer.py) - Kafka consumer

### Chat Service ([chat_service/](chat_service/))
**Purpose**: Real-time messaging, chat rooms, and WebSocket communication

**Key Files**:
- [chat_service/chat_app/views.py](chat_service/chat_app/views.py) - API endpoints and inter-service calls
- [chat_service/chat_app/consumers.py](chat_service/chat_app/consumers.py) - WebSocket handlers
- [chat_service/chat_service/kafka_utils.py](chat_service/chat_service/kafka_utils.py) - Kafka communication
- [chat_service/chat_app/models.py](chat_service/chat_app/models.py) - Chat data models
- [chat_service/chat_app/management/commands/start_kafka_consumer.py](chat_service/chat_app/management/commands/start_kafka_consumer.py) - Kafka consumer

---

## Kafka Components & Communication

### Kafka Service Singleton ([kafka_utils.py](auth_service/auth_service/kafka_utils.py))

**KafkaService Class**: Manages all Kafka operations with singleton pattern

**Key Components**:
1. **KafkaProducer**: Publishes events to topics
2. **KafkaConsumer**: Subscribes to topics and processes messages
3. **KafkaJSONEncoder**: Handles UUID and datetime serialization
4. **Event Schemas**: Predefined message structures

**Producer Configuration**:
```python
KafkaProducer(
    bootstrap_servers=kafka:29092,
    acks='all',                    # Wait for all replicas
    retries=3,                     # Retry failed sends
    max_in_flight_requests=1       # Ensure ordering
)
```

**Consumer Configuration**:
```python
KafkaConsumer(
    auto_offset_reset='latest',    # Start from newest messages
    enable_auto_commit=False,      # Manual offset management
    session_timeout_ms=30000       # 30-second heartbeat timeout
)
```

### Topics & Event Types

**1. `user.events` Topic**:
- `user.registered` - New user registration
- `user.verified` - OTP verification completed
- `user.login` - User authentication
- `user.logout` - User session termination
- `user.profile.updated` - Profile modifications

**2. `auth.events` Topic**:
- `auth.user.search.request` - Request user data by username
- `auth.user.search.response` - Response with user information

**3. `chat.events` Topic**:
- `chat.room.created` - New chat room creation
- `chat.message.sent` - Message transmission
- `chat.user.joined` - User joins room
- `chat.user.left` - User leaves room
- `chat.user.typing` - Typing indicators

**★ Insight ─────────────────────────────────────**
Each Kafka event includes metadata like timestamps and service identifiers, enabling distributed tracing and debugging across microservices.
**─────────────────────────────────────────────────**

---

## Detailed Request Flows

### 1. User Registration Flow

**Endpoint**: `POST /users/create-user/`
**File**: [auth_service/users/views.py:24](auth_service/users/views.py#L24)

```
1. Client Request → auth_service/users/views.py:create_user()
2. Validation → users/serializers.py:CreateUpdateSerializer
3. User Creation → users/models.py:CustomUser.objects.create()
4. Celery Task → users/tasks.py:send_otp_via_mail.delay()
5. Kafka Event → kafka_utils.py:publish_event('user.events')
6. Response → User data + OTP confirmation
```

**Detailed Steps**:
1. **Request Processing** ([views.py:24-56](auth_service/users/views.py#L24))
   - Validate input data using `CreateUpdateSerializer`
   - Create user in PostgreSQL database
   - Generate and store OTP

2. **Async Operations**:
   - **Email Task**: `send_otp_via_mail.delay()` - Celery background task
   - **Timer Task**: `otp_timer.apply_async(countdown=600)` - 10-minute expiration
   - **Kafka Event**: Publish `user.registered` event

3. **Event Publishing** ([kafka_utils.py:63-84](auth_service/auth_service/kafka_utils.py#L63)):
```python
user_event = UserEvents.user_registered(serializer.data)
kafka_service.publish_event('user.events', user_event, key=str(user_id))
```

### 2. User Verification Flow

**Endpoint**: `POST /users/verify-user/`
**File**: [auth_service/users/views.py:58](auth_service/users/views.py#L58)

```
1. Client Request → auth_service/users/views.py:verify_otp()
2. OTP Validation → Compare stored OTP with input
3. User Update → Set is_verified=True
4. Kafka Event → Publish user.verified event
5. Response → Verification confirmation
```

### 3. Room Creation Flow

**Endpoint**: `POST /chats/create-room/`
**File**: [chat_service/chat_app/views.py:156](chat_service/chat_app/views.py#L156)

```
1. Client Request → chat_service/chat_app/views.py:CreateRoom.post()
2. Authentication → @require_auth decorator validates JWT
3. User Search → search_user_by_username() - Multi-pattern approach
4. Room Creation → models.py:Room.objects.create()
5. Member Addition → models.py:RoomMembers.objects.create()
6. Kafka Event → Publish chat.room.created event
7. Response → Room data + WebSocket URL
```

**Detailed Steps**:

1. **Authentication** ([views.py:40-62](chat_service/chat_app/views.py#L40)):
   - Extract Bearer token from Authorization header
   - Call auth service: `POST /users/verify-token/`
   - Validate service-to-service communication

2. **User Search** ([views.py:99-147](chat_service/chat_app/views.py#L99)):
   - **Cache Check**: Look for users in local cache
   - **HTTP Fallback**: Direct call to auth service if cache miss
   - **Kafka Async**: Publish search request for future cache population

3. **Room Creation Logic**:
   - **Group Rooms**: Create with multiple members
   - **Direct Rooms**: Use `get_or_create_direct_room()` to prevent duplicates

4. **Event Publishing** ([views.py:225-244](chat_service/chat_app/views.py#L225)):
```python
room_event = ChatEvents.room_created(room_data, creator_id, members)
kafka_service.publish_event('chat.events', room_event, key=str(room.room_id))
```

### 4. Message Sending Flow (WebSocket)

**WebSocket URL**: `ws/chat/{room_id}/`
**File**: [chat_service/chat_app/consumers.py:7](chat_service/chat_app/consumers.py#L7)

```
1. WebSocket Connect → RoomConsumer.connect()
2. JWT Authentication → Custom middleware validates token
3. Room Validation → Check room exists in database
4. Message Receipt → RoomConsumer.receive()
5. Message Processing → handle_chat_message()
6. Database Save → save_message() - async database operation
7. Kafka Event → Publish chat.message.sent event
8. Broadcast → Send to all room members except sender
```

**Message Types Handled**:
- `chat_message`: Send text/media messages
- `typing`: Typing indicators
- `message_status`: Delivery/read receipts
- `ping`: Connection health checks

**Broadcasting Logic** ([consumers.py:261-268](chat_service/chat_app/consumers.py#L261)):
```python
# Exclude sender from broadcast
if event.get('sender_channel') != self.channel_name:
    await self.send(text_data=json.dumps({
        'type': 'new_message',
        'message': event['message']
    }))
```

### 5. User Search Flow (Inter-Service)

**Multiple Communication Patterns**:

**A. Direct HTTP (Synchronous)**:
```
1. Chat Service → HTTP POST /users/search-by-username/
2. Auth Service → Query database for users
3. Auth Service → Return user data immediately
4. Chat Service → Cache results locally
```

**B. Kafka-based (Asynchronous)**:
```
1. Chat Service → Publish auth.user.search.request
2. Auth Service Consumer → Process search request
3. Auth Service → Publish auth.user.search.response
4. Chat Service Consumer → Cache user data
```

**★ Insight ─────────────────────────────────────**
The hybrid user search approach provides both immediate results (HTTP) and eventual consistency (Kafka), optimizing for both user experience and system scalability.
**─────────────────────────────────────────────────**

### 6. Token Verification Flow (Inter-Service)

**Endpoint**: `POST /users/verify-token/`
**File**: [auth_service/users/views.py:111](auth_service/users/views.py#L111)

```
1. Chat Service → HTTP request with X-Service-Key header
2. Auth Service → Validate microservice secret key
3. Auth Service → Parse and validate JWT token
4. Auth Service → Query user from database
5. Auth Service → Return user data or error
6. Chat Service → Store user data in request context
```

**Security Headers**:
- `X-Service-Key`: Microservice authentication
- `Authorization: Bearer <token>`: User JWT token

---

## WebSocket Real-time Communication

### Connection Flow

**File**: [chat_service/chat_app/consumers.py](chat_service/chat_app/consumers.py)

1. **Connection Establishment** ([consumers.py:9-45](chat_service/chat_app/consumers.py#L9)):
   - Extract room_id from URL parameters
   - Validate JWT token through custom middleware
   - Check room existence in database
   - Join Redis channel group for room

2. **Message Processing** ([consumers.py:53-103](chat_service/chat_app/consumers.py#L53)):
   - Parse JSON message types
   - Route to appropriate handlers
   - Handle errors gracefully with error codes

3. **Real-time Features**:
   - **Chat Messages**: Persistent storage + real-time broadcast
   - **Typing Indicators**: Ephemeral real-time updates
   - **Message Status**: Delivery and read receipts
   - **Connection Health**: Ping/pong mechanism

### Channel Layers Configuration

**File**: [chat_service/chat_service/settings.py:85-92](chat_service/chat_service/settings.py#L85)

```python
CHANNEL_LAYERS = {
    "default": {
        "BACKEND": "channels_redis.core.RedisChannelLayer",
        "CONFIG": {
            "hosts": [("redis", 6379)],
        },
    },
}
```

---

## Inter-Service Authentication

### Service-to-Service Communication

**Authentication Method**: Shared secret key approach

**Implementation**: [chat_service/chat_app/views.py:13-38](chat_service/chat_app/views.py#L13)

```python
def check_user(token):
    response = requests.post(
        f"{AUTH_SERVICE_URL}/users/verify-token/",
        headers={
            "X-Service-Key": settings.MICROSERVICE_SECRET_KEY,
            "Content-Type": "application/json"
        },
        json={"token": token}
    )
```

**Security Configuration**:
- **Shared Secret**: `MICROSERVICE_SECRET_KEY` environment variable
- **Network Isolation**: Services communicate via Docker network
- **JWT Validation**: Tokens validated by auth service only

### WebSocket Authentication

**Custom Middleware**: [chat_service/chat_app/middleware.py](chat_service/chat_app/middleware.py)

```python
class JWTAuthMiddleware:
    async def __call__(self, scope, receive, send):
        # Extract JWT from headers
        # Validate with auth service
        # Add user data to scope
```

---

## Database Models & Relationships

### Auth Service Models

**CustomUser** ([auth_service/users/models.py:32](auth_service/users/models.py#L32)):
- `id`: UUID primary key
- `username`: Unique identifier
- `email`: Unique email address
- `is_verified`: OTP verification status
- `otp`: Temporary verification code

**Contact** ([auth_service/users/models.py:73](auth_service/users/models.py#L73)):
- User relationship management
- Status: pending/accepted/blocked

### Chat Service Models

**Room** ([chat_service/chat_app/models.py:6](chat_service/chat_app/models.py#L6)):
- `room_id`: UUID primary key
- `is_group`: Boolean flag for room type
- `created_by`: UUID reference to auth service user

**RoomMembers** ([chat_service/chat_app/models.py:75](chat_service/chat_app/models.py#L75)):
- Many-to-many relationship between rooms and users
- `role`: admin/user permissions

**Message** ([chat_service/chat_app/models.py:94](chat_service/chat_app/models.py#L94)):
- `sender`: UUID reference to auth service user
- `content`: Message text content
- `message_type`: text/image/file
- `mentions`: JSON array of mentioned users

**MessageStatus** ([chat_service/chat_app/models.py:124](chat_service/chat_app/models.py#L124)):
- Per-user message delivery status
- `status`: sent/delivered/seen

**★ Insight ─────────────────────────────────────**
The database design uses UUID foreign keys to reference users across services, maintaining loose coupling while preserving referential integrity through application logic rather than database constraints.
**─────────────────────────────────────────────────**

---

## Infrastructure & Deployment

### Docker Compose Services

**File**: [docker-compose.yml](docker-compose.yml)

**Core Infrastructure**:
- **Redis** (Port 6379): Session storage and WebSocket channel layers
- **Kafka + Zookeeper**: Event streaming platform
- **Kafka UI** (Port 8080): Event monitoring and debugging
- **PostgreSQL**: Separate databases for each service

**Application Services**:
- **auth_service** (Port 8000): User management service
- **chat_service** (Port 8001): Real-time messaging service
- **celery**: Background task processing
- **auth-kafka-consumer**: Dedicated Kafka consumer for auth events
- **chat-kafka-consumer**: Dedicated Kafka consumer for chat events

### Service Dependencies

```
auth_service:
  depends_on:
    - auth_postgres
    - redis
    - kafka

chat_service:
  depends_on:
    - chat_postgres
    - redis
    - kafka
    - auth_service
```

### Environment Configuration

**Key Variables** ([.env](.env)):
- `KAFKA_BOOTSTRAP_SERVERS=kafka:29092`
- `AUTH_SERVICE_URL=http://auth_service:8000`
- `MICROSERVICE_SECRET_KEY=microservice-secret-key-2024`
- Database connection strings for each service

### Background Processes

**Kafka Consumers** run as separate containers:
- **auth-kafka-consumer**: Processes user search requests
- **chat-kafka-consumer**: Handles auth responses and chat events

**Command**: `python3 manage.py start_kafka_consumer`

---

## Summary of Communication Patterns

### 1. **Synchronous HTTP**
- Token verification
- Critical user operations
- Immediate response requirements

### 2. **Asynchronous Kafka Events**
- User lifecycle events
- Chat activity logging
- Inter-service data synchronization
- Analytics and monitoring

### 3. **WebSocket Real-time**
- Live chat messaging
- Typing indicators
- Presence information
- Connection health monitoring

### 4. **Hybrid Approaches**
- User search: Cache → HTTP → Kafka
- Authentication: JWT + Service keys
- Data consistency: Eventual via events

**★ Insight ─────────────────────────────────────**
This architecture demonstrates a mature microservices pattern with multiple communication strategies, providing both immediate responsiveness for user interactions and eventual consistency for system-wide state management.
**─────────────────────────────────────────────────**

---

## Development & Debugging

### Local Development Setup
1. Start infrastructure: `docker-compose up redis kafka zookeeper`
2. Run services locally or in containers
3. Monitor Kafka events via Kafka UI at `localhost:8080`

### Testing Inter-Service Communication
- Use the test endpoints in chat service to verify auth integration
- Monitor Kafka topics for event flow debugging
- Check Redis channel layers for WebSocket communication

### Common Debugging Points
- JWT token validation between services
- Kafka consumer connection and offset management
- WebSocket authentication middleware
- Database connection pooling across services

This documentation provides a comprehensive understanding of how your microservice architecture handles real-time chat functionality with robust inter-service communication patterns.