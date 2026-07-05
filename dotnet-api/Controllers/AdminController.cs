using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Mvc;
using Microsoft.EntityFrameworkCore;
using DotnetApi.Data;
using DotnetApi.DTOs;
using DotnetApi.Models;

namespace DotnetApi.Controllers;

[ApiController]
[Route("api/admin")]
[Authorize(Roles = "Admin")]
public class AdminController : BaseController
{
    private readonly AppDbContext _context;

    public AdminController(AppDbContext context)
    {
        _context = context;
    }

    [HttpGet("dashboard")]
    public async Task<IActionResult> GetDashboardStats()
    {
        var usersCount = await _context.Users.CountAsync();
        var walletsCount = await _context.Wallets.CountAsync();
        
        var totalNgnBalance = await _context.Wallets
            .Where(w => w.Currency == "NGN")
            .SumAsync(w => (decimal?)w.Balance) ?? 0.0000m;
            
        var totalUsdBalance = await _context.Wallets
            .Where(w => w.Currency == "USD")
            .SumAsync(w => (decimal?)w.Balance) ?? 0.0000m;

        var totalTransactions = await _context.Transactions.CountAsync();

        var stats = new AdminStatsDto
        {
            UsersCount = usersCount,
            WalletsCount = walletsCount,
            TotalNgnBalance = totalNgnBalance.ToString("F4"),
            TotalUsdBalance = totalUsdBalance.ToString("F4"),
            TotalTransactions = totalTransactions
        };

        return Ok(stats);
    }

    [HttpGet("transactions")]
    public async Task<IActionResult> ListTransactions([FromQuery] string? search, [FromQuery] int page = 1, [FromQuery] int page_size = 10, [FromQuery] string? ordering = null)
    {
        var query = _context.Transactions.AsQueryable();

        // 1. Search Filter
        if (!string.IsNullOrWhiteSpace(search))
        {
            search = search.Trim().ToLower();
            query = query.Where(t => t.Reference.ToLower().Contains(search) || 
                                     (t.Description != null && t.Description.ToLower().Contains(search)) || 
                                     t.TransactionType.ToLower().Contains(search) || 
                                     t.Status.ToLower().Contains(search) || 
                                     t.Currency.ToLower().Contains(search));
        }

        // 2. Ordering
        if (!string.IsNullOrWhiteSpace(ordering))
        {
            var isDescending = ordering.StartsWith("-");
            var propertyName = isDescending ? ordering[1..] : ordering;

            query = propertyName.ToLower() switch
            {
                "amount" => isDescending ? query.OrderByDescending(t => t.Amount) : query.OrderBy(t => t.Amount),
                "created_at" or _ => isDescending ? query.OrderByDescending(t => t.CreatedAt) : query.OrderBy(t => t.CreatedAt),
            };
        }
        else
        {
            query = query.OrderByDescending(t => t.CreatedAt);
        }

        // 3. Pagination
        var count = await query.CountAsync();
        var results = await query
            .Skip((page - 1) * page_size)
            .Take(page_size)
            .Select(t => new TransactionDto
            {
                Id = t.Id,
                Reference = t.Reference,
                TransactionType = t.TransactionType,
                Amount = t.Amount.ToString("F4"),
                Currency = t.Currency,
                Status = t.Status,
                Description = t.Description,
                CreatedAt = t.CreatedAt
            })
            .ToListAsync();

        var scheme = Request.Scheme;
        var host = Request.Host;
        var path = Request.Path;

        var nextUrl = page * page_size < count ? $"{scheme}://{host}{path}?page={page + 1}&page_size={page_size}" : null;
        var prevUrl = page > 1 ? $"{scheme}://{host}{path}?page={page - 1}&page_size={page_size}" : null;

        var response = new PaginatedListDto<TransactionDto>
        {
            Count = count,
            Next = nextUrl,
            Previous = prevUrl,
            Results = results
        };

        return Ok(response);
    }

    [HttpGet("wallets")]
    public async Task<IActionResult> ListWallets([FromQuery] string? search, [FromQuery] int page = 1, [FromQuery] int page_size = 10, [FromQuery] string? ordering = null)
    {
        var query = _context.Wallets
            .Include(w => w.User)
            .AsQueryable();

        // 1. Search Filter
        if (!string.IsNullOrWhiteSpace(search))
        {
            search = search.Trim().ToLower();
            query = query.Where(w => w.User!.Email.ToLower().Contains(search) || 
                                     w.Name.ToLower().Contains(search) || 
                                     w.Currency.ToLower().Contains(search));
        }

        // 2. Ordering
        if (!string.IsNullOrWhiteSpace(ordering))
        {
            var isDescending = ordering.StartsWith("-");
            var propertyName = isDescending ? ordering[1..] : ordering;

            query = propertyName.ToLower() switch
            {
                "balance" => isDescending ? query.OrderByDescending(w => w.Balance) : query.OrderBy(w => w.Balance),
                "created_at" or _ => isDescending ? query.OrderByDescending(w => w.CreatedAt) : query.OrderBy(w => w.CreatedAt),
            };
        }
        else
        {
            query = query.OrderByDescending(w => w.CreatedAt);
        }

        // 3. Pagination
        var count = await query.CountAsync();
        var results = await query
            .Skip((page - 1) * page_size)
            .Take(page_size)
            .Select(w => new WalletDto
            {
                Id = w.Id,
                UserEmail = w.User!.Email,
                Name = w.Name,
                Currency = w.Currency,
                Balance = w.Balance.ToString("F4"),
                CreatedAt = w.CreatedAt,
                UpdatedAt = w.UpdatedAt
            })
            .ToListAsync();

        var scheme = Request.Scheme;
        var host = Request.Host;
        var path = Request.Path;

        var nextUrl = page * page_size < count ? $"{scheme}://{host}{path}?page={page + 1}&page_size={page_size}" : null;
        var prevUrl = page > 1 ? $"{scheme}://{host}{path}?page={page - 1}&page_size={page_size}" : null;

        var response = new PaginatedListDto<WalletDto>
        {
            Count = count,
            Next = nextUrl,
            Previous = prevUrl,
            Results = results
        };

        return Ok(response);
    }
}
