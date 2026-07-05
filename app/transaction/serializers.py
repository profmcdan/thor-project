from rest_framework import serializers
from decimal import Decimal
from wallet.models import Wallet
from transaction.models import Transaction, LedgerEntry

class TransactionSerializer(serializers.ModelSerializer):
    class Meta:
        model = Transaction
        fields = ('id', 'reference', 'transaction_type', 'amount', 'currency', 'status', 'description', 'created_at')
        read_only_fields = fields

class LedgerEntrySerializer(serializers.ModelSerializer):
    transaction = TransactionSerializer(read_only=True)
    class Meta:
        model = LedgerEntry
        fields = ('id', 'transaction', 'wallet', 'amount', 'entry_type', 'balance_after', 'created_at')
        read_only_fields = fields

class DepositSerializer(serializers.Serializer):
    wallet_id = serializers.UUIDField(required=True)
    amount = serializers.DecimalField(max_digits=20, decimal_places=4, required=True, min_value=Decimal('0.0001'))
    description = serializers.CharField(max_length=255, required=False, allow_blank=True)

    def validate_wallet_id(self, value):
        # Ensure the wallet exists and is owned by the request user
        user = self.context['request'].user
        try:
            Wallet.objects.get(id=value, user=user)
        except Wallet.DoesNotExist:
            raise serializers.ValidationError("Wallet not found or does not belong to you.")
        return value

class WithdrawalSerializer(serializers.Serializer):
    wallet_id = serializers.UUIDField(required=True)
    amount = serializers.DecimalField(max_digits=20, decimal_places=4, required=True, min_value=Decimal('0.0001'))
    description = serializers.CharField(max_length=255, required=False, allow_blank=True)

    def validate_wallet_id(self, value):
        # Ensure the wallet exists and is owned by the request user
        user = self.context['request'].user
        try:
            Wallet.objects.get(id=value, user=user)
        except Wallet.DoesNotExist:
            raise serializers.ValidationError("Wallet not found or does not belong to you.")
        return value

class TransferSerializer(serializers.Serializer):
    source_wallet_id = serializers.UUIDField(required=True)
    destination_wallet_id = serializers.UUIDField(required=True)
    amount = serializers.DecimalField(max_digits=20, decimal_places=4, required=True, min_value=Decimal('0.0001'))
    description = serializers.CharField(max_length=255, required=False, allow_blank=True)

    def validate(self, attrs):
        source_id = attrs.get('source_wallet_id')
        dest_id = attrs.get('destination_wallet_id')
        user = self.context['request'].user

        if source_id == dest_id:
            raise serializers.ValidationError("Source and destination wallets must be different.")

        # Ensure source wallet belongs to the user
        try:
            source_wallet = Wallet.objects.get(id=source_id, user=user)
        except Wallet.DoesNotExist:
            raise serializers.ValidationError({"source_wallet_id": "Wallet not found or does not belong to you."})

        # Ensure destination wallet exists
        try:
            dest_wallet = Wallet.objects.get(id=dest_id)
        except Wallet.DoesNotExist:
            raise serializers.ValidationError({"destination_wallet_id": "Destination wallet not found."})

        # Ensure currency match
        if source_wallet.currency != dest_wallet.currency:
            raise serializers.ValidationError("Transfers can only be made between wallets of the same currency.")

        # Ensure sufficient funds
        amount = attrs.get('amount')
        if source_wallet.balance < amount:
            raise serializers.ValidationError({"amount": "Insufficient funds in source wallet."})

        return attrs
