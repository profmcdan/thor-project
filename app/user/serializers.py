from rest_framework import serializers
from django.contrib.auth import get_user_model
from wallet.models import Wallet

User = get_user_model()

class UserWalletSerializer(serializers.ModelSerializer):
    class Meta:
        model = Wallet
        fields = ('id', 'currency')

class UserSerializer(serializers.ModelSerializer):
    wallets = UserWalletSerializer(many=True, read_only=True)
    
    class Meta:
        model = User
        fields = ('id', 'email', 'first_name', 'last_name', 'date_joined', 'is_staff', 'wallets')
        read_only_fields = ('id', 'date_joined', 'is_staff')

class UserRegistrationSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, required=True, style={'input_type': 'password'})

    class Meta:
        model = User
        fields = ('email', 'password', 'first_name', 'last_name')

    def create(self, validated_data):
        user = User.objects.create_user(
            email=validated_data['email'],
            password=validated_data['password'],
            first_name=validated_data.get('first_name', ''),
            last_name=validated_data.get('last_name', '')
        )
        return user
