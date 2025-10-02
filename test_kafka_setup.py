#!/usr/bin/env python3
"""
Test script to verify Kafka setup and connectivity
Run this after starting the docker services
"""

import time
import json
from kafka import KafkaProducer, KafkaConsumer
from kafka.errors import KafkaError


def test_kafka_connectivity():
    """Test basic Kafka connectivity"""
    print("Testing Kafka connectivity...")

    try:
        # Test producer
        producer = KafkaProducer(
            bootstrap_servers='localhost:9092',
            value_serializer=lambda v: json.dumps(v).encode('utf-8'),
            request_timeout_ms=10000,
            retries=3,
            retry_backoff_ms=1000
        )

        # Send test message
        test_message = {
            'event_type': 'test.message',
            'message': 'Kafka connectivity test',
            'timestamp': int(time.time() * 1000)
        }

        future = producer.send('test.topic', test_message)
        record_metadata = future.get(timeout=10)

        print(f"✅ Producer test successful!")
        print(f"   Topic: {record_metadata.topic}")
        print(f"   Partition: {record_metadata.partition}")
        print(f"   Offset: {record_metadata.offset}")

        producer.close()

        # Test consumer
        consumer = KafkaConsumer(
            'test.topic',
            bootstrap_servers='localhost:9092',
            value_deserializer=lambda m: json.loads(m.decode('utf-8')),
            consumer_timeout_ms=10000,
            auto_offset_reset='earliest'
        )

        messages_received = 0
        for message in consumer:
            print(f"✅ Consumer test successful!")
            print(f"   Received: {message.value}")
            messages_received += 1
            break

        consumer.close()

        if messages_received > 0:
            print("🎉 Kafka setup is working correctly!")
        else:
            print("⚠️  No messages received by consumer")

    except KafkaError as e:
        print(f"❌ Kafka error: {e}")
        return False
    except Exception as e:
        print(f"❌ Unexpected error: {e}")
        return False

    return True


def test_topics_creation():
    """Test if our application topics exist"""
    print("\nTesting application topics...")

    try:
        from kafka.admin import KafkaAdminClient, NewTopic
        from kafka.admin.config_resource import ConfigResource, ConfigResourceType

        admin_client = KafkaAdminClient(
            bootstrap_servers='localhost:9092',
            request_timeout_ms=5000
        )

        # List existing topics
        metadata = admin_client.describe_cluster()
        existing_topics = admin_client.list_topics()

        print(f"📋 Existing topics: {list(existing_topics)}")

        # Expected topics for our application
        expected_topics = ['user.events', 'auth.events', 'chat.events']

        # Create missing topics
        topics_to_create = []
        for topic_name in expected_topics:
            if topic_name not in existing_topics:
                topics_to_create.append(
                    NewTopic(
                        name=topic_name,
                        num_partitions=3,
                        replication_factor=1
                    )
                )

        if topics_to_create:
            print(f"📝 Creating topics: {[t.name for t in topics_to_create]}")
            fs = admin_client.create_topics(topics_to_create)

            for topic, f in fs.items():
                try:
                    f.result()  # The result itself is None
                    print(f"✅ Topic {topic} created successfully")
                except Exception as e:
                    print(f"❌ Failed to create topic {topic}: {e}")
        else:
            print("✅ All expected topics already exist")

        admin_client.close()

    except Exception as e:
        print(f"❌ Error checking/creating topics: {e}")
        return False

    return True


if __name__ == "__main__":
    print("🚀 Starting Kafka integration test...\n")

    # Test basic connectivity
    connectivity_ok = test_kafka_connectivity()

    # Test topics
    topics_ok = test_topics_creation()

    print(f"\n📊 Test Results:")
    print(f"   Connectivity: {'✅ PASS' if connectivity_ok else '❌ FAIL'}")
    print(f"   Topics: {'✅ PASS' if topics_ok else '❌ FAIL'}")

    if connectivity_ok and topics_ok:
        print(f"\n🎉 All tests passed! Kafka is ready for your chat application.")
        print(f"\n📋 Next steps:")
        print(f"   1. Start your services: docker-compose up")
        print(f"   2. Check Kafka UI at: http://localhost:8080")
        print(f"   3. Monitor logs for Kafka events")
    else:
        print(f"\n⚠️  Some tests failed. Check your Kafka setup:")
        print(f"   1. Make sure Kafka is running: docker-compose ps")
        print(f"   2. Check Kafka logs: docker-compose logs kafka")
        print(f"   3. Verify network connectivity")