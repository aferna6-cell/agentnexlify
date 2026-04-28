# Node.js Backend Extended Patterns

Reference material split out of `../SKILL.md` to keep the loaded skill under 500 lines.

## Error Handling

### Custom Error Classes

```typescript
// utils/errors.ts
export class AppError extends Error {
  constructor(
    public message: string,
    public statusCode: number = 500,
    public isOperational: boolean = true,
  ) {
    super(message);
    Object.setPrototypeOf(this, AppError.prototype);
    Error.captureStackTrace(this, this.constructor);
  }
}

export class ValidationError extends AppError {
  constructor(
    message: string,
    public errors?: any[],
  ) {
    super(message, 400);
  }
}

export class NotFoundError extends AppError {
  constructor(message: string = "Resource not found") {
    super(message, 404);
  }
}

export class UnauthorizedError extends AppError {
  constructor(message: string = "Unauthorized") {
    super(message, 401);
  }
}

export class ForbiddenError extends AppError {
  constructor(message: string = "Forbidden") {
    super(message, 403);
  }
}

export class ConflictError extends AppError {
  constructor(message: string) {
    super(message, 409);
  }
}
```

### Global Error Handler

```typescript
// middleware/error-handler.ts
import { Request, Response, NextFunction } from "express";
import { AppError } from "../utils/errors";
import { logger } from "./logger.middleware";

export const errorHandler = (
  err: Error,
  req: Request,
  res: Response,
  next: NextFunction,
) => {
  if (err instanceof AppError) {
    return res.status(err.statusCode).json({
      status: "error",
      message: err.message,
      ...(err instanceof ValidationError && { errors: err.errors }),
    });
  }

  // Log unexpected errors
  logger.error({
    error: err.message,
    stack: err.stack,
    url: req.url,
    method: req.method,
  });

  // Don't leak error details in production
  const message =
    process.env.NODE_ENV === "production"
      ? "Internal server error"
      : err.message;

  res.status(500).json({
    status: "error",
    message,
  });
};

// Async error wrapper
export const asyncHandler = (
  fn: (req: Request, res: Response, next: NextFunction) => Promise<any>,
) => {
  return (req: Request, res: Response, next: NextFunction) => {
    Promise.resolve(fn(req, res, next)).catch(next);
  };
};
```

## Database Patterns

Node.js supports both SQL and NoSQL databases. Use connection pooling for all production databases.

Key patterns covered in [references/advanced-patterns.md](references/advanced-patterns.md):
- **PostgreSQL with connection pool** â€” `pg` Pool configuration and graceful shutdown
- **MongoDB with Mongoose** â€” connection management and schema definition
- **Transaction pattern** â€” `BEGIN`/`COMMIT`/`ROLLBACK` with `pg` client

## Authentication & Authorization

JWT-based auth with access tokens (short-lived, 15m) and refresh tokens (7d). Full `AuthService` implementation with `bcrypt` password comparison in [references/advanced-patterns.md](references/advanced-patterns.md).

## Caching Strategies

Redis-backed `CacheService` with get/set/delete/invalidatePattern, plus a `@Cacheable` decorator for method-level caching. See [references/advanced-patterns.md](references/advanced-patterns.md).

## API Response Format

Standardized `ApiResponse` helper with `success`, `error`, and `paginated` static methods. See [references/advanced-patterns.md](references/advanced-patterns.md).

## Best Practices

1. **Use TypeScript**: Type safety prevents runtime errors
2. **Implement proper error handling**: Use custom error classes
3. **Validate input**: Use libraries like Zod or Joi
4. **Use environment variables**: Never hardcode secrets
5. **Implement logging**: Use structured logging (Pino, Winston)
6. **Add rate limiting**: Prevent abuse
7. **Use HTTPS**: Always in production
8. **Implement CORS properly**: Don't use `*` in production
9. **Use dependency injection**: Easier testing and maintenance
10. **Write tests**: Unit, integration, and E2E tests
11. **Handle graceful shutdown**: Clean up resources
12. **Use connection pooling**: For databases
13. **Implement health checks**: For monitoring
14. **Use compression**: Reduce response size
15. **Monitor performance**: Use APM tools

## Testing Patterns

See `javascript-testing-patterns` skill for comprehensive testing guidance.
