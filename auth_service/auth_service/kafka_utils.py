import json
import logging
import uuid
from typing import Dict, Any, Optional, Callable
from kafka import KafkaProducer, KafkaConsumer
from kafka.errors import KafkaError
from django.conf import settings
from threading import Thread
import time
from decimal import Decimal
from datetime import datetime, date


logger = logging.getLogger(__name__)


class KafkaJSONEncoder(json.JSONEncoder):
    """Custom JSON encoder for Kafka messages that handles UUID and other Django types"""
    def default(self, obj):
        if isinstance(obj, uuid.UUID):
            return str(obj)
        elif isinstance(obj, Decimal):
            return float(obj)
        elif isinstance(obj, (datetime, date)):
            return obj.isoformat()
        return super().default(obj)


class KafkaService:
    _instance = None
    _producer = None
    _consumers = []

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
        return cls._instance

    def __init__(self):
        if not hasattr(self, 'initialized'):
            self.kafka_bootstrap_servers = getattr(settings, 'KAFKA_BOOTSTRAP_SERVERS', 'localhost:9092')
            self._consumers = []
            self.initialized = True

    def get_producer(self) -> KafkaProducer:
        if self._producer is None:
            try:
                self._producer = KafkaProducer(
                    bootstrap_servers=self.kafka_bootstrap_servers,
                    value_serializer=lambda v: json.dumps(v, cls=KafkaJSONEncoder).encode('utf-8'),
                    key_serializer=lambda k: k.encode('utf-8') if k else None,
                    acks='all',
                    retries=3,
                    retry_backoff_ms=1000,
                    max_in_flight_requests_per_connection=1
                )
                logger.info("Kafka producer initialized successfully")
            except Exception as e:
                logger.error(f"Failed to initialize Kafka producer: {e}")
                raise
        return self._producer

    def publish_event(self, topic: str, event_data: Dict[str, Any], key: Optional[str] = None) -> bool:
        try:
            producer = self.get_producer()

            # Add metadata
            event_data.update({
                'timestamp': int(time.time() * 1000),
                'service': 'auth_service'
            })

            future = producer.send(topic, value=event_data, key=key)
            record_metadata = future.get(timeout=10)

            logger.info(f"Event published to {topic}: {record_metadata.topic}[{record_metadata.partition}]@{record_metadata.offset}")
            return True

        except KafkaError as e:
            logger.error(f"Failed to publish event to {topic}: {e}")
            return False
        except Exception as e:
            logger.error(f"Unexpected error publishing to {topic}: {e}")
            return False

    def create_consumer(self, topics: list, group_id: str, handler: Callable[[str, Dict], None]) -> KafkaConsumer:
        try:
            consumer = KafkaConsumer(
                *topics,
                bootstrap_servers=self.kafka_bootstrap_servers,
                group_id=group_id,
                value_deserializer=lambda m: json.loads(m.decode('utf-8')),
                key_deserializer=lambda m: m.decode('utf-8') if m else None,
                auto_offset_reset='latest',
                enable_auto_commit=False,  # Manual commit for better control
                max_poll_records=10,
                consumer_timeout_ms=30000,  # 30 second timeout
                heartbeat_interval_ms=10000,  # 10 second heartbeat
                session_timeout_ms=30000  # 30 second session timeout
            )

            def consume_messages():
                logger.info(f"Starting consumer for topics {topics} in group {group_id}")
                try:
                    while True:
                        message_batch = consumer.poll(timeout_ms=1000, max_records=10)

                        if not message_batch:
                            continue

                        for topic_partition, messages in message_batch.items():
                            for message in messages:
                                try:
                                    logger.info(f"Processing message from {message.topic}:{message.partition}@{message.offset}")
                                    handler(message.topic, message.value)

                                    # Commit offset for this specific message
                                    consumer.commit_async({
                                        topic_partition: message.offset + 1
                                    })

                                except Exception as e:
                                    logger.error(f"Error handling message from {message.topic}:{message.partition}@{message.offset}: {e}")
                                    # Don't commit offset for failed messages - they'll be retried

                except Exception as e:
                    logger.error(f"Consumer loop error: {e}")
                finally:
                    logger.info(f"Closing consumer for topics {topics}")
                    consumer.close()

            # Start consumer in background thread
            consumer_thread = Thread(target=consume_messages, daemon=True)
            consumer_thread.start()

            return consumer

        except Exception as e:
            logger.error(f"Failed to create consumer for {topics}: {e}")
            raise

    def close(self):
        if self._producer:
            self._producer.close()
            self._producer = None
            logger.info("Kafka producer closed")


# Event schemas
class UserEvents:
    USER_REGISTERED = "user.registered"
    USER_VERIFIED = "user.verified"
    USER_LOGIN = "user.login"
    USER_LOGOUT = "user.logout"
    USER_PROFILE_UPDATED = "user.profile.updated"

    @staticmethod
    def user_registered(user_data: Dict[str, Any]) -> Dict[str, Any]:
        return {
            'event_type': UserEvents.USER_REGISTERED,
            'user_id': user_data['id'],
            'username': user_data['username'],
            'email': user_data['email'],
            'data': user_data
        }

    @staticmethod
    def user_verified(user_id: str, username: str) -> Dict[str, Any]:
        return {
            'event_type': UserEvents.USER_VERIFIED,
            'user_id': user_id,
            'username': username
        }

    @staticmethod
    def user_login(user_id: str, username: str, ip_address: str = None) -> Dict[str, Any]:
        return {
            'event_type': UserEvents.USER_LOGIN,
            'user_id': user_id,
            'username': username,
            'ip_address': ip_address
        }


class AuthEvents:
    TOKEN_VERIFIED = "auth.token.verified"
    TOKEN_INVALID = "auth.token.invalid"
    USER_SEARCH_REQUEST = "auth.user.search.request"
    USER_SEARCH_RESPONSE = "auth.user.search.response"

    @staticmethod
    def user_search_response(request_id: str, users: list, requester_service: str) -> Dict[str, Any]:
        return {
            'event_type': AuthEvents.USER_SEARCH_RESPONSE,
            'request_id': request_id,
            'users': users,
            'requester_service': requester_service
        }


# Kafka service instance
kafka_service = KafkaService()