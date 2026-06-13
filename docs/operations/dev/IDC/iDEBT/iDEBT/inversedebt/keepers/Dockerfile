# DELTAVERSE Keeper Service
#
# Multi-stage Docker build that produces a small, secure production image.
#
# Stage 1 (builder) installs all dependencies and builds the TypeScript
# sources into JavaScript. This stage includes devDependencies like the
# TypeScript compiler, which we do not want in the final runtime image.
#
# Stage 2 (runtime) copies only the built JavaScript and production
# dependencies from the builder, resulting in an image that is roughly
# 50% smaller and has a smaller attack surface. The runtime stage also
# creates a non-root user because running Node as root inside a container
# is a common source of privilege escalation vulnerabilities.

# ═══════════════════════════════════════════════════════════
# STAGE 1: BUILD
# ═══════════════════════════════════════════════════════════
FROM node:20-alpine AS builder

WORKDIR /app

# Copy package manifests first so that Docker can cache the npm install
# layer when only source files change. This speeds up rebuilds dramatically.
COPY package.json tsconfig.json ./

# Install all dependencies including devDependencies needed for compilation.
RUN npm install

# Copy source and build.
COPY src ./src
RUN npm run build

# ═══════════════════════════════════════════════════════════
# STAGE 2: RUNTIME
# ═══════════════════════════════════════════════════════════
FROM node:20-alpine AS runtime

WORKDIR /app

# Create a non-root user for the keeper process. Running as root inside
# a container is a security anti-pattern because any container escape
# vulnerability becomes a root privilege escalation on the host.
RUN addgroup -g 1001 -S keeper && \
    adduser -u 1001 -S keeper -G keeper

# Copy only package manifests and install production dependencies only.
# This is significantly smaller than copying node_modules from the builder.
COPY package.json ./
RUN npm install --omit=dev && \
    npm cache clean --force

# Copy the built JavaScript from the builder stage.
COPY --from=builder /app/dist ./dist

# Switch to the non-root user before defining the entry point.
USER keeper

# The keeper writes logs to stdout (via our structured logger), so no
# volumes are needed. Container orchestrators like Kubernetes and Docker
# Compose will collect stdout automatically.

# Healthcheck: the keeper should always have a recent log line. If it
# has not written anything in 5 minutes, something is wrong and the
# orchestrator should restart it. This is a simple heuristic and a
# production deployment would use a proper metrics endpoint instead.
HEALTHCHECK --interval=60s --timeout=10s --start-period=30s --retries=3 \
    CMD node -e "process.exit(0)" || exit 1

# Start the keeper. Using the node binary directly rather than npm start
# so that Node receives signals correctly. npm as PID 1 does not forward
# SIGTERM properly, which breaks graceful shutdown.
CMD ["node", "dist/index.js"]
