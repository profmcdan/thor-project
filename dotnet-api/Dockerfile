# Build Stage
FROM mcr.microsoft.com/dotnet/sdk:10.0 AS build
WORKDIR /src
COPY ["DotnetApi.csproj", "./"]
RUN dotnet restore "DotnetApi.csproj"
COPY . .
RUN dotnet build "DotnetApi.csproj" -c Release -o /app/build
RUN dotnet publish "DotnetApi.csproj" -c Release -o /app/publish /p:UseAppHost=false

# Runtime Stage
FROM mcr.microsoft.com/dotnet/aspnet:10.0 AS final
WORKDIR /app

# Install curl securely for healthchecks, then clean up
USER root
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Switch to security-hardened non-root user 'app'
USER app

COPY --chown=app:app --from=build /app/publish .
EXPOSE 8000
ENV ASPNETCORE_URLS=http://+:8000
ENTRYPOINT ["dotnet", "DotnetApi.dll"]
