from rest_framework import serializers
from wallet.models import Wallet

class WalletSerializer(serializers.ModelSerializer):
    user = serializers.HiddenField(default=serializers.CurrentUserDefault())
    user_email = serializers.EmailField(source='user.email', read_only=True)

    class Meta:
        model = Wallet
        fields = ('id', 'user', 'user_email', 'name', 'currency', 'balance', 'created_at', 'updated_at')
        read_only_fields = ('id', 'balance', 'created_at', 'updated_at')

    def validate(self, attrs):
        user = attrs.get('user')
        currency = attrs.get('currency', 'NGN').upper()
        name = attrs.get('name', 'Default Wallet')

        # Check for duplicate wallet name/currency combination per user
        if Wallet.objects.filter(user=user, currency=currency, name=name).exists():
            raise serializers.ValidationError(
                f"You already have a wallet named '{name}' for currency '{currency}'."
            )

        attrs['currency'] = currency
        return attrs
