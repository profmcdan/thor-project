using System.Security.Claims;
using Microsoft.AspNetCore.Mvc;

namespace DotnetApi.Controllers;

public class BaseController : ControllerBase
{
    protected Guid CurrentUserId
    {
        get
        {
            var userIdStr = User.FindFirst(ClaimTypes.NameIdentifier)?.Value;
            return Guid.TryParse(userIdStr, out var id) ? id : Guid.Empty;
        }
    }
}
