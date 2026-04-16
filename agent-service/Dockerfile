# Build context must be the repo root (not agent-service/).
# In Railway: set the service's Root Directory to / and Dockerfile Path to agent-service/Dockerfile.
# This allows COPY to access both agent-service/ and .claude/ from the same context.

FROM node:22-alpine

WORKDIR /app

# Install deps first (layer cache)
COPY agent-service/package.json package.json
RUN npm install --omit=dev --ignore-scripts

# Copy service source
COPY agent-service/src src/

# Copy .claude/ so settingSources: ['project'] can find agent definitions at runtime.
# This is the core of the dev-config = prod-config pattern:
# .claude/agents/*.md files drive both Claude Code dev-time tooling and
# production query() calls in this service.
COPY .claude .claude/

# REPO_ROOT tells runner.ts where to find .claude/ (same as /app here).
ENV REPO_ROOT=/app
ENV PORT=3100

EXPOSE 3100

CMD ["node", "--experimental-strip-types", "src/server.ts"]
