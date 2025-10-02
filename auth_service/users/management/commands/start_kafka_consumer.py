import logging
import signal
import sys
from django.core.management.base import BaseCommand
from auth_service.kafka_utils import kafka_service, UserEvents, AuthEvents
from users.models import CustomUser
from users.serializers import ProfileSerializer


logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = 'Start Kafka consumer for auth service'

    def __init__(self):
        super().__init__()
        self.consumers = []
        self.running = True

    def handle(self, *args, **options):
        # Set up signal handlers for graceful shutdown
        signal.signal(signal.SIGINT, self.signal_handler)
        signal.signal(signal.SIGTERM, self.signal_handler)

        self.stdout.write(
            self.style.SUCCESS('Starting Kafka consumer for auth service...')
        )

        def handle_auth_events(topic: str, message: dict):
            event_type = message.get('event_type')

            try:
                if event_type == AuthEvents.USER_SEARCH_REQUEST:
                    self.handle_user_search_request(message)
                else:
                    logger.info(f"Unhandled event type: {event_type}")
            except Exception as e:
                logger.error(f"Error handling event {event_type}: {e}")

        def handle_user_events(topic: str, message: dict):
            event_type = message.get('event_type')
            logger.info(f"Received user event: {event_type}")

        try:
            # Start consumers
            auth_consumer = kafka_service.create_consumer(
                ['auth.events'],
                'auth-service-group',
                handle_auth_events
            )
            self.consumers.append(auth_consumer)

            user_consumer = kafka_service.create_consumer(
                ['user.events'],
                'auth-service-user-group',
                handle_user_events
            )
            self.consumers.append(user_consumer)

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

    def handle_user_search_request(self, message: dict):
        """Handle user search requests from other services"""
        request_id = message.get('request_id')
        usernames = message.get('usernames', [])
        requester_service = message.get('requester_service')

        logger.info(f"Processing user search request {request_id} for usernames: {usernames}")

        try:
            # Search for users
            users = CustomUser.objects.filter(username__in=usernames)
            serializer = ProfileSerializer(users, many=True)

            # Publish response
            response_event = AuthEvents.user_search_response(
                request_id,
                serializer.data,
                requester_service
            )

            success = kafka_service.publish_event(
                'auth.events',
                response_event,
                key=request_id
            )

            if success:
                logger.info(f"User search response published for request {request_id}")
            else:
                logger.error(f"Failed to publish user search response for request {request_id}")

        except Exception as e:
            logger.error(f"Error processing user search request {request_id}: {e}")