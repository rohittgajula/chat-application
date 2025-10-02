#!/usr/bin/env python3
"""
Test script to verify UUID serialization in Kafka events
"""

import uuid
import sys
import os
import json

# Add the current directory to Python path
sys.path.append('/Users/rohitgajula/Desktop/chat-application/chat_service')
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'chat_service.settings')

import django
django.setup()

from chat_service.kafka_utils import kafka_service, ChatEvents

def test_uuid_serialization():
    """Test that UUID objects can be serialized properly in Kafka events"""
    print("🧪 Testing UUID serialization in Kafka events...")

    try:
        # Create test data with UUID objects
        test_room_id = uuid.uuid4()
        test_creator_id = uuid.uuid4()
        test_member_ids = [uuid.uuid4(), uuid.uuid4()]

        room_data = {
            'room_id': test_room_id,  # This is a UUID object
            'room_name': 'Test Room',
            'is_group': True,
            'description': 'Test room for UUID serialization',
            'created_at': '2025-09-29T18:58:00Z'
        }

        # Test the ChatEvents.room_created method
        room_event = ChatEvents.room_created(
            room_data,
            test_creator_id,  # This is a UUID object
            test_member_ids   # This is a list of UUID objects
        )

        print(f"✅ Event created successfully: {room_event['event_type']}")
        print(f"   Room ID: {room_event['room_id']} (type: {type(room_event['room_id'])})")
        print(f"   Creator ID: {room_event['creator_id']} (type: {type(room_event['creator_id'])})")
        print(f"   Members: {room_event['members']} (types: {[type(m) for m in room_event['members']]})")

        # Test publishing the event to Kafka
        success = kafka_service.publish_event('test.uuid.topic', room_event, key=str(test_room_id))

        if success:
            print("✅ UUID serialization test PASSED!")
            print("   Event successfully published to Kafka with UUID objects")
            return True
        else:
            print("❌ Failed to publish event to Kafka")
            return False

    except Exception as e:
        print(f"❌ UUID serialization test FAILED: {e}")
        return False

if __name__ == "__main__":
    print("🚀 Starting UUID serialization test...\n")

    success = test_uuid_serialization()

    print(f"\n📊 Test Result: {'✅ PASS' if success else '❌ FAIL'}")

    if success:
        print("\n🎉 The UUID serialization fix is working correctly!")
        print("   Your Kafka events can now handle UUID objects without errors.")
    else:
        print("\n⚠️  The UUID serialization fix needs more work.")