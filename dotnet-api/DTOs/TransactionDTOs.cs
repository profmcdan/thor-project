using System.Text.Json.Serialization;

namespace DotnetApi.DTOs;

public class DepositRequest
{
    [JsonPropertyName("wallet_id")]
    public Guid WalletId { get; set; }
    
    public decimal Amount { get; set; }
    public string? Description { get; set; }
}

public class WithdrawRequest
{
    [JsonPropertyName("wallet_id")]
    public Guid WalletId { get; set; }
    
    public decimal Amount { get; set; }
    public string? Description { get; set; }
}

public class TransferRequest
{
    [JsonPropertyName("source_wallet_id")]
    public Guid SourceWalletId { get; set; }
    
    [JsonPropertyName("destination_wallet_id")]
    public Guid DestinationWalletId { get; set; }
    
    public decimal Amount { get; set; }
    public string? Description { get; set; }
}

public class TransactionDto
{
    public Guid Id { get; set; }
    public string Reference { get; set; } = string.Empty;
    
    [JsonPropertyName("transaction_type")]
    public string TransactionType { get; set; } = string.Empty;
    
    public string Amount { get; set; } = "0.0000";
    public string Currency { get; set; } = "NGN";
    public string Status { get; set; } = "PENDING";
    public string? Description { get; set; }
    
    [JsonPropertyName("created_at")]
    public DateTime CreatedAt { get; set; }
}

public class LedgerEntryDto
{
    public Guid Id { get; set; }
    public TransactionDto Transaction { get; set; } = null!;
    public Guid Wallet { get; set; }
    public string Amount { get; set; } = "0.0000";
    
    [JsonPropertyName("entry_type")]
    public string EntryType { get; set; } = string.Empty;
    
    [JsonPropertyName("balance_after")]
    public string BalanceAfter { get; set; } = "0.0000";
    
    [JsonPropertyName("created_at")]
    public DateTime CreatedAt { get; set; }
}

public class AdminStatsDto
{
    [JsonPropertyName("users_count")]
    public int UsersCount { get; set; }
    
    [JsonPropertyName("wallets_count")]
    public int WalletsCount { get; set; }
    
    [JsonPropertyName("total_ngn_balance")]
    public string TotalNgnBalance { get; set; } = "0.0000";
    
    [JsonPropertyName("total_usd_balance")]
    public string TotalUsdBalance { get; set; } = "0.0000";
    
    [JsonPropertyName("total_transactions")]
    public int TotalTransactions { get; set; }
}

public class PaginatedListDto<T>
{
    public int Count { get; set; }
    public string? Next { get; set; }
    public string? Previous { get; set; }
    public List<T> Results { get; set; } = [];
}
