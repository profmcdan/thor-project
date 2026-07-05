using System.Text.Json.Serialization;

namespace DotnetApi.DTOs;

public class CreateWalletRequest
{
    public string Name { get; set; } = "Primary Wallet";
    public string Currency { get; set; } = "NGN";
}

public class WalletDto
{
    public Guid Id { get; set; }
    
    [JsonPropertyName("user_email")]
    public string UserEmail { get; set; } = string.Empty;
    
    public string Name { get; set; } = string.Empty;
    public string Currency { get; set; } = string.Empty;
    public string Balance { get; set; } = "0.0000";
    
    [JsonPropertyName("created_at")]
    public DateTime CreatedAt { get; set; }
    
    [JsonPropertyName("updated_at")]
    public DateTime UpdatedAt { get; set; }
}
