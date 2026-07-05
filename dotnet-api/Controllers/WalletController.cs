using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;
using Microsoft.EntityFrameworkCore;
using DotnetApi.Data;
using DotnetApi.DTOs;
using DotnetApi.Models;

namespace DotnetApi.Controllers;

[ApiController]
[Route("api/wallets")]
[Authorize]
public class WalletController : BaseController
{
    private readonly AppDbContext _context;

    public WalletController(AppDbContext context)
    {
        _context = context;
    }

    [HttpGet]
    public async Task<IActionResult> List()
    {
        var userEmail = User.FindFirst(System.Security.Claims.ClaimTypes.Email)?.Value ?? "";

        var wallets = await _context.Wallets
            .Where(w => w.UserId == CurrentUserId)
            .OrderByDescending(w => w.CreatedAt)
            .Select(w => new WalletDto
            {
                Id = w.Id,
                UserEmail = userEmail,
                Name = w.Name,
                Currency = w.Currency,
                Balance = w.Balance.ToString("F4"),
                CreatedAt = w.CreatedAt,
                UpdatedAt = w.UpdatedAt
            })
            .ToListAsync();

        return Ok(wallets);
    }

    [HttpPost]
    public async Task<IActionResult> Create([FromBody] CreateWalletRequest request)
    {
        var userEmail = User.FindFirst(System.Security.Claims.ClaimTypes.Email)?.Value ?? "";
        var name = string.IsNullOrWhiteSpace(request.Name) ? "Default Wallet" : request.Name.Trim();
        var currency = string.IsNullOrWhiteSpace(request.Currency) ? "NGN" : request.Currency.Trim().ToUpper();

        // Validate unique constraint: user, currency, name
        var exists = await _context.Wallets.AnyAsync(w => w.UserId == CurrentUserId && w.Currency == currency && w.Name == name);
        if (exists)
        {
            return BadRequest(new { non_field_errors = new[] { $"You already have a wallet named '{name}' for currency '{currency}'." } });
        }

        var wallet = new Wallet
        {
            UserId = CurrentUserId,
            Name = name,
            Currency = currency,
            Balance = 0.0000m,
            CreatedAt = DateTime.UtcNow,
            UpdatedAt = DateTime.UtcNow
        };

        _context.Wallets.Add(wallet);
        await _context.SaveChangesAsync();

        var dto = new WalletDto
        {
            Id = wallet.Id,
            UserEmail = userEmail,
            Name = wallet.Name,
            Currency = wallet.Currency,
            Balance = wallet.Balance.ToString("F4"),
            CreatedAt = wallet.CreatedAt,
            UpdatedAt = wallet.UpdatedAt
        };

        return StatusCode(201, dto);
    }

    [HttpGet("{id:guid}")]
    public async Task<IActionResult> Get(Guid id)
    {
        var userEmail = User.FindFirst(System.Security.Claims.ClaimTypes.Email)?.Value ?? "";

        var wallet = await _context.Wallets
            .FirstOrDefaultAsync(w => w.Id == id && w.UserId == CurrentUserId);

        if (wallet == null)
        {
            return NotFound();
        }

        var dto = new WalletDto
        {
            Id = wallet.Id,
            UserEmail = userEmail,
            Name = wallet.Name,
            Currency = wallet.Currency,
            Balance = wallet.Balance.ToString("F4"),
            CreatedAt = wallet.CreatedAt,
            UpdatedAt = wallet.UpdatedAt
        };

        return Ok(dto);
    }
}
