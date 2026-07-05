using Microsoft.AspNetCore.Authorization;
using Microsoft.AspNetCore.Identity;
using Microsoft.AspNetCore.Mvc;
using Microsoft.EntityFrameworkCore;
using DotnetApi.Data;
using DotnetApi.DTOs;
using DotnetApi.Models;
using DotnetApi.Services;

namespace DotnetApi.Controllers;

[ApiController]
[Route("api")]
public class AuthController : BaseController
{
    private readonly AppDbContext _context;
    private readonly ITokenService _tokenService;
    private readonly PasswordHasher<User> _passwordHasher;

    public AuthController(AppDbContext context, ITokenService tokenService)
    {
        _context = context;
        _tokenService = tokenService;
        _passwordHasher = new PasswordHasher<User>();
    }

    [HttpPost("auth/register")]
    [AllowAnonymous]
    public async Task<IActionResult> Register([FromBody] RegisterRequest request)
    {
        if (string.IsNullOrWhiteSpace(request.Email) || string.IsNullOrWhiteSpace(request.Password))
        {
            return BadRequest(new { error = "Email and password are required." });
        }

        var existingUser = await _context.Users.AnyAsync(u => u.Email == request.Email);
        if (existingUser)
        {
            return BadRequest(new { error = "User with this email already exists." });
        }

        var user = new User
        {
            Email = request.Email,
            FirstName = request.FirstName,
            LastName = request.LastName,
            DateJoined = DateTime.UtcNow
        };

        user.Password = _passwordHasher.HashPassword(user, request.Password);

        _context.Users.Add(user);
        await _context.SaveChangesAsync();

        var accessToken = _tokenService.GenerateAccessToken(user);
        var refreshToken = _tokenService.GenerateRefreshToken(user);

        var responseDto = new AuthResponse
        {
            User = new UserDto
            {
                Id = user.Id,
                Email = user.Email,
                FirstName = user.FirstName,
                LastName = user.LastName,
                DateJoined = user.DateJoined,
                IsStaff = user.IsStaff,
                Wallets = []
            },
            Tokens = new TokenDto
            {
                Access = accessToken,
                Refresh = refreshToken
            }
        };

        return StatusCode(201, responseDto);
    }

    [HttpPost("auth/login")]
    [AllowAnonymous]
    public async Task<IActionResult> Login([FromBody] LoginRequest request)
    {
        var user = await _context.Users
            .Include(u => u.Wallets)
            .FirstOrDefaultAsync(u => u.Email == request.Email);

        if (user == null)
        {
            return Unauthorized(new { detail = "No active account found with the given credentials" });
        }

        var verificationResult = _passwordHasher.VerifyHashedPassword(user, user.Password, request.Password);
        if (verificationResult == PasswordVerificationResult.Failed)
        {
            return Unauthorized(new { detail = "No active account found with the given credentials" });
        }

        var accessToken = _tokenService.GenerateAccessToken(user);
        var refreshToken = _tokenService.GenerateRefreshToken(user);

        var responseDto = new AuthResponse
        {
            User = new UserDto
            {
                Id = user.Id,
                Email = user.Email,
                FirstName = user.FirstName,
                LastName = user.LastName,
                DateJoined = user.DateJoined,
                IsStaff = user.IsStaff,
                Wallets = user.Wallets.Select(w => new UserWalletDto
                {
                    Id = w.Id,
                    Currency = w.Currency
                }).ToList()
            },
            Tokens = new TokenDto
            {
                Access = accessToken,
                Refresh = refreshToken
            }
        };

        return Ok(responseDto);
    }

    [HttpPost("auth/token/refresh")]
    [AllowAnonymous]
    public async Task<IActionResult> RefreshToken([FromBody] TokenDto request)
    {
        if (string.IsNullOrEmpty(request.Refresh))
        {
            return BadRequest(new { error = "Refresh token is required." });
        }

        try
        {
            var principal = _tokenService.GetPrincipalFromExpiredToken(request.Refresh);
            if (principal == null)
            {
                return BadRequest(new { error = "Invalid refresh token." });
            }

            var userIdClaim = principal.FindFirst(System.Security.Claims.ClaimTypes.NameIdentifier)?.Value;
            if (string.IsNullOrEmpty(userIdClaim) || !Guid.TryParse(userIdClaim, out var userId))
            {
                return BadRequest(new { error = "Invalid token claims." });
            }

            var user = await _context.Users.FindAsync(userId);
            if (user == null)
            {
                return NotFound(new { error = "User not found." });
            }

            var newAccessToken = _tokenService.GenerateAccessToken(user);
            return Ok(new { access = newAccessToken });
        }
        catch (Exception)
        {
            return BadRequest(new { error = "Invalid or expired token." });
        }
    }

    [HttpGet("auth/me")]
    [Authorize]
    public async Task<IActionResult> Me()
    {
        var user = await _context.Users
            .Include(u => u.Wallets)
            .FirstOrDefaultAsync(u => u.Id == CurrentUserId);

        if (user == null)
        {
            return NotFound();
        }

        var userDto = new UserDto
        {
            Id = user.Id,
            Email = user.Email,
            FirstName = user.FirstName,
            LastName = user.LastName,
            DateJoined = user.DateJoined,
            IsStaff = user.IsStaff,
            Wallets = user.Wallets.Select(w => new UserWalletDto
            {
                Id = w.Id,
                Currency = w.Currency
            }).ToList()
        };

        return Ok(userDto);
    }

    [HttpGet("users")]
    [Authorize]
    public async Task<IActionResult> ListUsers([FromQuery] string? search)
    {
        var query = _context.Users
            .Where(u => u.Id != CurrentUserId);

        if (!string.IsNullOrWhiteSpace(search))
        {
            query = query.Where(u => u.Email.Contains(search));
        }

        var users = await query
            .OrderBy(u => u.Email)
            .Select(u => new UserDto
            {
                Id = u.Id,
                Email = u.Email,
                FirstName = u.FirstName,
                LastName = u.LastName,
                DateJoined = u.DateJoined,
                IsStaff = u.IsStaff
            })
            .ToListAsync();

        return Ok(users);
    }
}
