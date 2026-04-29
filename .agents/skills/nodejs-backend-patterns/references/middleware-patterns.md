# Node.js Backend Middleware Patterns

Reference material split out of `../SKILL.md` to keep the loaded skill under 450 lines.

## Middleware Patterns

### Authentication Middleware

```typescript
// middleware/auth.middleware.ts
import { Request, Response, NextFunction } from "express";
import jwt from "jsonwebtoken";
import { UnauthorizedError } from "../utils/errors";

interface JWTPayload {
  userId: string;
  email: string;
}

declare global {
  namespace Express {
    interface Request {
      user?: JWTPayload;
    }
  }
}

export const authenticate = async (
  req: Request,
  res: Response,
  next: NextFunction,
) => {
  try {
    const token = req.headers.authorization?.replace("Bearer ", "");

    if (!token) {
      throw new UnauthorizedError("No token provided");
    }

    const payload = jwt.verify(token, process.env.JWT_SECRET!) as JWTPayload;

    req.user = payload;
    next();
  } catch (error) {
    next(new UnauthorizedError("Invalid token"));
  }
};

export const authorize = (...roles: string[]) => {
  return async (req: Request, res: Response, next: NextFunction) => {
    if (!req.user) {
      return next(new UnauthorizedError("Not authenticated"));
    }

    // Check if user has required role
    const hasRole = roles.some((role) => req.user?.roles?.includes(role));

    if (!hasRole) {
      return next(new UnauthorizedError("Insufficient permissions"));
    }

    next();
  };
};
```

### Validation Middleware

```typescript
// middleware/validation.middleware.ts
import { Request, Response, NextFunction } from "express";
import { AnyZodObject, ZodError } from "zod";
import { ValidationError } from "../utils/errors";

export const validate = (schema: AnyZodObject) => {
  return async (req: Request, res: Response, next: NextFunction) => {
    try {
      await schema.parseAsync({
        body: req.body,
        query: req.query,
        params: req.params,
      });
      next();
    } catch (error) {
      if (error instanceof ZodError) {
        const errors = error.errors.map((err) => ({
          field: err.path.join("."),
          message: err.message,
        }));
        next(new ValidationError("Validation failed", errors));
      } else {
        next(error);
      }
    }
  };
};

// Usage with Zod
import { z } from "zod";

const createUserSchema = z.object({
  body: z.object({
    name: z.string().min(1),
    email: z.string().email(),
    password: z.string().min(8),
  }),
});

router.post("/users", validate(createUserSchema), userController.createUser);
```

### Rate Limiting Middleware

```typescript
// middleware/rate-limit.middleware.ts
import rateLimit from "express-rate-limit";
import RedisStore from "rate-limit-redis";
import Redis from "ioredis";

const redis = new Redis({
  host: process.env.REDIS_HOST,
  port: parseInt(process.env.REDIS_PORT || "6379"),
});

export const apiLimiter = rateLimit({
  store: new RedisStore({
    client: redis,
    prefix: "rl:",
  }),
  windowMs: 15 * 60 * 1000, // 15 minutes
  max: 100, // Limit each IP to 100 requests per windowMs
  message: "Too many requests from this IP, please try again later",
  standardHeaders: true,
  legacyHeaders: false,
});

export const authLimiter = rateLimit({
  store: new RedisStore({
    client: redis,
    prefix: "rl:auth:",
  }),
  windowMs: 15 * 60 * 1000,
  max: 5, // Stricter limit for auth endpoints
  skipSuccessfulRequests: true,
});
```

### Request Logging Middleware

```typescript
// middleware/logger.middleware.ts
import { Request, Response, NextFunction } from "express";
import pino from "pino";

const logger = pino({
  level: process.env.LOG_LEVEL || "info",
  transport: {
    target: "pino-pretty",
    options: { colorize: true },
  },
});

export const requestLogger = (
  req: Request,
  res: Response,
  next: NextFunction,
) => {
  const start = Date.now();

  // Log response when finished
  res.on("finish", () => {
    const duration = Date.now() - start;
    logger.info({
      method: req.method,
      url: req.url,
      status: res.statusCode,
      duration: `${duration}ms`,
      userAgent: req.headers["user-agent"],
      ip: req.ip,
    });
  });

  next();
};

export { logger };
```

