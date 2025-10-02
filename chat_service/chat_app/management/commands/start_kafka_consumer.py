import logging
import signal
import sys
from django.core.management.base import BaseCommand
from chat_service.kafka_utils import kafka_service, ChatEvents, UserSearchEvents


logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Start Kafka consumer for chat service'

    def __init__(self):
        super().__init__()
        self.consumers = []
        self.running = True

    def handle(self, *args, **options):
        # Set up signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)

        self.stdout.write(
            self.style.SUCCESS('Starting Kafka consumer for chat service...')
        )

        def handle_auth_events(topic: str, message: dict):
            event_type = message.get('event_type')

            try:
                if event_type == UserSearchEvents.USER_SEARCH_RESPONSE:
                    self.handle_user_search_response(message)
                else:
                    logger.info(f"Unhandled auth event type: {event_type}")
            except Exception as e:
                logger.error(f"Error handling auth event {event_type}: {e}")

        def handle_user_events(topic: str, message: dict):
            event_type = message.get('event_type')
            logger.info(f"Received user event: {event_type}")

        def handle_chat_events(topic: str, message: dict):
            event_type = message.get('event_type')
            logger.info(f"Received chat event: {event_type}")

            try:
                if event_type == ChatEvents.ROOM_CREATED:
                    self.handle_room_created_event(message)
                elif event_type == ChatEvents.MESSAGE_SENT:
                    self.handle_message_sent_event(message)
                elif event_type == ChatEvents.USER_JOINED_ROOM:
                    self.handle_user_joined_event(message)
                elif event_type == ChatEvents.USER_LEFT_ROOM:
                    self.handle_user_left_event(message)
                else:
                    logger.info(f"Unhandled chat event type: {event_type}")
            except Exception as e:
                logger.error(f"Error handling chat event {event_type}: {e}")
                logger.error(f"Message data: {message}")

        try:
            # Start consumers
            auth_consumer = kafka_service.create_consumer(
                ['auth.events'],
                'chat-service-auth-group',
                handle_auth_events
            )
            self.consumers.append(auth_consumer)

            user_consumer = kafka_service.create_consumer(
                ['user.events'],
                'chat-service-user-group',
                handle_user_events
            )
            self.consumers.append(user_consumer)

            chat_consumer = kafka_service.create_consumer(
                ['chat.events'],
                'chat-service-group',
                handle_chat_events
            )
            self.consumers.append(chat_consumer)

            self.stdout.write(
                self.style.SUCCESS('Kafka consumers started successfully!')
            )

            # Keep the command running until signal received
            try:
                while self.running:
                    signal.pause()
            except KeyboardInterrupt:
                pass

            self.stdout.write(
                self.style.WARNING('Stopping Kafka consumers...')
            )
            self.shutdown()

        except Exception as e:
            self.stdout.write(
                self.style.ERROR(f'Failed to start Kafka consumers: {e}')
            )

    def signal_handler(self, signum, frame):
        """Handle shutdown signals"""
        self.stdout.write(
            self.style.WARNING(f'Received signal {signum}, shutting down gracefully...')
        )
        self.running = False

    def shutdown(self):
        """Gracefully shutdown consumers"""
        for consumer in self.consumers:
            try:
                consumer.close()
            except Exception as e:
                logger.error(f"Error closing consumer: {e}")

        kafka_service.close()
        self.stdout.write(
            self.style.SUCCESS('Kafka consumers stopped successfully!')
        )

    def handle_user_search_response(self, message: dict):
        """Handle user search responses from auth service"""
        request_id = message.get('request_id')
        users = message.get('users', [])
        requester_service = message.get('requester_service')

        logger.info(f"Received user search response for request {request_id}: {len(users)} users found")

        # Cache the users for future use
        kafka_service.cache_users(users)

        # Here you could implement a callback system or update a waiting request
        # For now, we just cache the users

    def handle_room_created_event(self, message: dict):
        """Handle room creation events"""
        room_id = message.get('room_id')
        room_name = message.get('room_name')
        creator_id = message.get('creator_id')
        members = message.get('members', [])

        logger.info(f"Room created: {room_name} (ID: {room_id}) by user {creator_id}")
        logger.info(f"Members: {members}")

        # Here you could implement additional logic like:
        # - Sending notifications to members
        # - Updating analytics
        # - Triggering other services

    def handle_message_sent_event(self, message: dict):
        """Handle message sent events"""
        message_id = message.get('message_id')
        room_id = message.get('room_id')
        sender_id = message.get('sender_id')
        content = message.get('content', '')

        logger.info(f"Message sent in room {room_id} by user {sender_id}: {content[:50]}...")

        # Here you could implement additional logic like:
        # - Content moderation
        # - Analytics tracking
        # - Push notifications to offline users

    def handle_user_joined_event(self, message: dict):
        """Handle user joined room events"""
        room_id = message.get('room_id')
        user_id = message.get('user_id')

        logger.info(f"User {user_id} joined room {room_id}")

    def handle_user_left_event(self, message: dict):
        """Handle user left room events"""
        room_id = message.get('room_id')
        user_id = message.get('user_id')

        logger.info(f"User {user_id} left room {room_id}")