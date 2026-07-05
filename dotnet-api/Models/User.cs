using System.ComponentModel.DataAnnotations.Schema;

namespace DotnetApi.Models;

[Table("user_user")]
public class User
{
    [Column("id")]
    public Guid Id { get; set; } = Guid.NewGuid();

    [Column("email")]
    public string Email { get; set; } = string.Empty;

    [Column("password")]
    public string Password { get; set; } = string.Empty;

    [Column("first_name")]
    public string FirstName { get; set; } = string.Empty;

    [Column("last_name")]
    public string LastName { get; set; } = string.Empty;

    [Column("is_superuser")]
    public bool IsSuperuser { get; set; } = false;

    [Column("is_staff")]
    public bool IsStaff { get; set; } = false;

    [Column("is_active")]
    public bool IsActive { get; set; } = true;

    [Column("date_joined")]
    public DateTime DateJoined { get; set; } = DateTime.UtcNow;

    // Navigation property
    public List<Wallet> Wallets { get; set; } = [];
}
