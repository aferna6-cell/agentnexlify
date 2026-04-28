---
name: nodejs-backend-patterns
description: Build production-ready Node.js backend services with Express/Fastify, implementing middleware patterns, error handling, authentication, database integration, and API design best practices. Use when creating Node.js servers, REST APIs, GraphQL backends, or microservices architectures.
---

# Node.js Backend Patterns

Comprehensive guidance for building scalable, maintainable, and production-ready Node.js backend applications with modern frameworks, architectural patterns, and best practices.

## When to Use This Skill

- Building REST APIs or GraphQL servers
- Creating microservices with Node.js
- Implementing authentication and authorization
- Designing scalable backend architectures
- Setting up middleware and error handling
- Integrating databases (SQL and NoSQL)
- Building real-time applications with WebSockets
- Implementing background job processing

## Core Frameworks

### Express.js - Minimalist Framework

**Basic Setup:**

```typescript
import express, { Request, Response, NextFunction } from "express";
import helmet from "helmet";
import cors from "cors";
import compression from "compression";

const app = express();

// Security middleware
app.use(helmet());
app.use(cors({ origin: process.env.ALLOWED_ORIGINS?.split(",") }));
app.use(compression());

// Body parsing
app.use(express.json({ limit: "10mb" }));
app.use(express.urlencoded({ extended: true, limit: "10mb" }));

// Request logging
app.use((req: Request, res: Response, next: NextFunction) => {
  console.log(`${req.method} ${req.path}`);
  next();
});

const PORT = process.env.PORT || 3000;
app.listen(PORT, () => {
  console.log(`Server running on port ${PORT}`);
});
```

### Fastify - High Performance Framework

**Basic Setup:**

```typescript
import Fastify from "fastify";
import helmet from "@fastify/helmet";
import cors from "@fastify/cors";
import compress from "@fastify/compress";

const fastify = Fastify({
  logger: {
    level: process.env.LOG_LEVEL || "info",
    transport: {
      target: "pino-pretty",
      options: { colorize: true },
    },
  },
});

// Plugins
await fastify.register(helmet);
await fastify.register(cors, { origin: true });
await fastify.register(compress);

// Type-safe routes with schema validation
fastify.post<{
  Body: { name: string; email: string };
  Reply: { id: string; name: string };
}>(
  "/users",
  {
    schema: {
      body: {
        type: "object",
        required: ["name", "email"],
        properties: {
          name: { type: "string", minLength: 1 },
          email: { type: "string", format: "email" },
        },
      },
    },
  },
  async (request, reply) => {
    const { name, email } = request.body;
    return { id: "123", name };
  },
);

await fastify.listen({ port: 3000, host: "0.0.0.0" });
```

## Architectural Patterns

### Pattern 1: Layered Architecture

**Structure:**

```
src/
Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ controllers/     # Handle HTTP requests/responses
Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ services/        # Business logic
Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ repositories/    # Data access layer
Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ models/          # Data models
Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ middleware/      # Express/Fastify middleware
Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ routes/          # Route definitions
Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ utils/           # Helper functions
Ã¢â€Å“Ã¢â€â‚¬Ã¢â€â‚¬ config/          # Configuration
Ã¢â€â€Ã¢â€â‚¬Ã¢â€â‚¬ types/           # TypeScript types
```

**Controller Layer:**

```typescript
// controllers/user.controller.ts
import { Request, Response, NextFunction } from "express";
import { UserService } from "../services/user.service";
import { CreateUserDTO, UpdateUserDTO } from "../types/user.types";

export class UserController {
  constructor(private userService: UserService) {}

  async createUser(req: Request, res: Response, next: NextFunction) {
    try {
      const userData: CreateUserDTO = req.body;
      const user = await this.userService.createUser(userData);
      res.status(201).json(user);
    } catch (error) {
      next(error);
    }
  }

  async getUser(req: Request, res: Response, next: NextFunction) {
    try {
      const { id } = req.params;
      const user = await this.userService.getUserById(id);
      res.json(user);
    } catch (error) {
      next(error);
    }
  }

  async updateUser(req: Request, res: Response, next: NextFunction) {
    try {
      const { id } = req.params;
      const updates: UpdateUserDTO = req.body;
      const user = await this.userService.updateUser(id, updates);
      res.json(user);
    } catch (error) {
      next(error);
    }
  }

  async deleteUser(req: Request, res: Response, next: NextFunction) {
    try {
      const { id } = req.params;
      await this.userService.deleteUser(id);
      res.status(204).send();
    } catch (error) {
      next(error);
    }
  }
}
```

**Service Layer:**

```typescript
// services/user.service.ts
import { UserRepository } from "../repositories/user.repository";
import { CreateUserDTO, UpdateUserDTO, User } from "../types/user.types";
import { NotFoundError, ValidationError } from "../utils/errors";
import bcrypt from "bcrypt";

export class UserService {
  constructor(private userRepository: UserRepository) {}

  async createUser(userData: CreateUserDTO): Promise<User> {
    // Validation
    const existingUser = await this.userRepository.findByEmail(userData.email);
    if (existingUser) {
      throw new ValidationError("Email already exists");
    }

    // Hash password
    const hashedPassword = await bcrypt.hash(userData.password, 10);

    // Create user
    const user = await this.userRepository.create({
      ...userData,
      password: hashedPassword,
    });

    // Remove password from response
    const { password, ...userWithoutPassword } = user;
    return userWithoutPassword as User;
  }

  async getUserById(id: string): Promise<User> {
    const user = await this.userRepository.findById(id);
    if (!user) {
      throw new NotFoundError("User not found");
    }
    const { password, ...userWithoutPassword } = user;
    return userWithoutPassword as User;
  }

  async updateUser(id: string, updates: UpdateUserDTO): Promise<User> {
    const user = await this.userRepository.update(id, updates);
    if (!user) {
      throw new NotFoundError("User not found");
    }
    const { password, ...userWithoutPassword } = user;
    return userWithoutPassword as User;
  }

  async deleteUser(id: string): Promise<void> {
    const deleted = await this.userRepository.delete(id);
    if (!deleted) {
      throw new NotFoundError("User not found");
    }
  }
}
```

**Repository Layer:**

```typescript
// repositories/user.repository.ts
import { Pool } from "pg";
import { CreateUserDTO, UpdateUserDTO, UserEntity } from "../types/user.types";

export class UserRepository {
  constructor(private db: Pool) {}

  async create(
    userData: CreateUserDTO & { password: string },
  ): Promise<UserEntity> {
    const query = `
      INSERT INTO users (name, email, password)
      VALUES ($1, $2, $3)
      RETURNING id, name, email, password, created_at, updated_at
    `;
    const { rows } = await this.db.query(query, [
      userData.name,
      userData.email,
      userData.password,
    ]);
    return rows[0];
  }

  async findById(id: string): Promise<UserEntity | null> {
    const query = "SELECT * FROM users WHERE id = $1";
    const { rows } = await this.db.query(query, [id]);
    return rows[0] || null;
  }

  async findByEmail(email: string): Promise<UserEntity | null> {
    const query = "SELECT * FROM users WHERE email = $1";
    const { rows } = await this.db.query(query, [email]);
    return rows[0] || null;
  }

  async update(id: string, updates: UpdateUserDTO): Promise<UserEntity | null> {
    const fields = Object.keys(updates);
    const values = Object.values(updates);

    const setClause = fields
      .map((field, idx) => `${field} = $${idx + 2}`)
      .join(", ");

    const query = `
      UPDATE users
      SET ${setClause}, updated_at = CURRENT_TIMESTAMP
      WHERE id = $1
      RETURNING *
    `;

    const { rows } = await this.db.query(query, [id, ...values]);
    return rows[0] || null;
  }

  async delete(id: string): Promise<boolean> {
    const query = "DELETE FROM users WHERE id = $1";
    const { rowCount } = await this.db.query(query, [id]);
    return rowCount > 0;
  }
}
```

### Pattern 2: Dependency Injection

Use a DI container to wire up repositories, services, and controllers. For a full container implementation, see [references/advanced-patterns.md](references/advanced-patterns.md).


## Middleware And Extended Patterns

Detailed middleware examples live in [Middleware patterns](references/middleware-patterns.md). Error handling, database integration, authentication, caching, API response format, best practices, and testing examples live in [Error, database, and API patterns](references/error-database-and-api.md). Read those references when the task needs code-level examples beyond framework setup or architecture.
