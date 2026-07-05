using System.Text.Json.Serialization;

namespace DotnetApi.DTOs;

public class RegisterRequest
{
    public string Email { get; set; } = string.Empty;
    public string Password { get; set; } = string.Empty;
    
    [JsonPropertyName("first_name")]
    public string FirstName { get; set; } = string.Empty;
    
    [JsonPropertyName("last_name")]
    public string LastName { get; set; } = string.Empty;
}

public class LoginRequest
{
    public string Email { get; set; } = string.Empty;
    public string Password { get; set; } = string.Empty;
}

public class UserWalletDto
{
    public Guid Id { get; set; }
    public string Currency { get; set; } = "NGN";
}

public class UserDto
{
    public Guid Id { get; set; }
    public string Email { get; set; } = string.Empty;
    
    [JsonPropertyName("first_name")]
    public string FirstName { get; set; } = string.Empty;
    
    [JsonPropertyName("last_name")]
    public string LastName { get; set; } = string.Empty;
    
    [JsonPropertyName("date_joined")]
    public DateTime DateJoined { get; set; }
    
    [JsonPropertyName("is_staff")]
    public bool IsStaff { get; set; }
    
    public List<UserWalletDto> Wallets { get; set; } = [];
}

public class TokenDto
{
    public string Refresh { get; set; } = string.Empty;
    public string Access { get; set; } = string.Empty;
}

public class AuthResponse
{
    public UserDto User { get; set; } = null!;
    public TokenDto Tokens { get; set; } = null!;
}
