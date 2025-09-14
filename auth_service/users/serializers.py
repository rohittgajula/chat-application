from rest_framework import serializers
from .models import CustomUser, Contact
from django.db import transaction

class ProfileSerializer(serializers.ModelSerializer):
    class Meta:
        model = CustomUser
        fields = ['id', 'email', 'first_name', 'username', 'last_name', 'is_verified']

class CreateUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        age = serializers.ReadOnlyField()
        
        model = CustomUser
        fields = ['first_name', 'last_name', 'username', 'email', 'password', 'date_of_birth', 'age']

    def create(self, validated_data):
        password = validated_data.pop('password', None)
        user = CustomUser(**validated_data)
        if password:
            user.set_password(password)
        user.save()
        return user

    def update(self, instance, validated_data):
        password = validated_data.pop('password', None)
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        if password:
            instance.set_password(password)
        instance.save()
        return instance
    
class VerifyAcountSerializer(serializers.Serializer):
  
  email = serializers.EmailField()
  otp = serializers.CharField()