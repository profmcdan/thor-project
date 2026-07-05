using System.Text;
using Microsoft.AspNetCore.Authentication.JwtBearer;
using Microsoft.EntityFrameworkCore;
using Microsoft.IdentityModel.Tokens;
using Microsoft.OpenApi;
using StackExchange.Redis;
using DotnetApi.Data;
using DotnetApi.Services;

var builder = WebApplication.CreateBuilder(args);

// 1. Configure PostgreSQL DbContext
var pgHost = Environment.GetEnvironmentVariable("POSTGRES_HOST") ?? "db";
var pgPort = Environment.GetEnvironmentVariable("POSTGRES_PORT") ?? "5432";
var pgDb = Environment.GetEnvironmentVariable("POSTGRES_DB") ?? "thor001db";
var pgUser = Environment.GetEnvironmentVariable("POSTGRES_USER") ?? "thoro1";
var pgPassword = Environment.GetEnvironmentVariable("MAIN_POSTGRES_PASSWORD") ?? "password";

var connectionString = $"Host={pgHost};Port={pgPort};Database={pgDb};Username={pgUser};Password={pgPassword};";
builder.Services.AddDbContext<AppDbContext>(options =>
    options.UseNpgsql(connectionString));

// 2. Configure Redis
var redisUrl = Environment.GetEnvironmentVariable("REDIS_URL") ?? "redis:6379/1";
if (redisUrl.StartsWith("redis://"))
{
    redisUrl = redisUrl[8..];
}
var slashIndex = redisUrl.IndexOf('/');
if (slashIndex != -1)
{
    redisUrl = redisUrl[..slashIndex];
}
var redisConfig = new ConfigurationOptions
{
    EndPoints = { redisUrl },
    AbortOnConnectFail = false,
    ConnectRetry = 5,
    ConnectTimeout = 5000
};
builder.Services.AddSingleton<IConnectionMultiplexer>(sp => ConnectionMultiplexer.Connect(redisConfig));

// 3. Register Custom Services
builder.Services.AddScoped<IWalletService, WalletService>();
builder.Services.AddScoped<ITokenService, TokenService>();

// 4. Configure JWT Authentication
var secret = builder.Configuration["JWT_SECRET"] ?? "django-insecure-prod-key-for-high-performance-wallet-service-12345";
if (secret.Length < 32)
{
    secret = secret.PadRight(32, 'a');
}
var key = Encoding.UTF8.GetBytes(secret);

builder.Services.AddAuthentication(options =>
{
    options.DefaultAuthenticateScheme = JwtBearerDefaults.AuthenticationScheme;
    options.DefaultChallengeScheme = JwtBearerDefaults.AuthenticationScheme;
})
.AddJwtBearer(options =>
{
    options.RequireHttpsMetadata = false;
    options.SaveToken = true;
    options.TokenValidationParameters = new TokenValidationParameters
    {
        ValidateIssuerSigningKey = true,
        IssuerSigningKey = new SymmetricSecurityKey(key),
        ValidateIssuer = false,
        ValidateAudience = false,
        ValidateLifetime = true,
        ClockSkew = TimeSpan.Zero
    };
});

builder.Services.AddControllers();

// 5. Configure Swagger / OpenAPI
builder.Services.AddEndpointsApiExplorer();
builder.Services.AddSwaggerGen(options =>
{
    options.SwaggerDoc("v1", new OpenApiInfo { Title = "Thor Digital Wallet API (.NET)", Version = "v1" });
    
    // Add JWT support in Swagger UI
    options.AddSecurityDefinition("Bearer", new OpenApiSecurityScheme
    {
        Name = "Authorization",
        Type = SecuritySchemeType.ApiKey,
        Scheme = "Bearer",
        BearerFormat = "JWT",
        In = ParameterLocation.Header,
        Description = "JWT Authorization header using the Bearer scheme. Example: \"Bearer {token}\""
    });
    
    options.AddSecurityRequirement(document => new OpenApiSecurityRequirement
    {
        {
            new OpenApiSecuritySchemeReference("Bearer", document),
            new List<string>()
        }
    });
});

// 6. Configure CORS
builder.Services.AddCors(options =>
{
    options.AddDefaultPolicy(policy =>
    {
        policy.AllowAnyOrigin().AllowAnyHeader().AllowAnyMethod();
    });
});

var app = builder.Build();

// Configure the HTTP request pipeline.
if (app.Environment.IsDevelopment() || true) // Enable Swagger in all environments for comparison
{
    app.UseSwagger();
    app.UseSwaggerUI(c =>
    {
        c.SwaggerEndpoint("/swagger/v1/swagger.json", "Thor API v1");
        c.RoutePrefix = "docs"; // Serve Swagger UI on /docs matching Django
    });
}

app.UseCors();

app.UseAuthentication();
app.UseAuthorization();

app.MapControllers();

app.Run();
