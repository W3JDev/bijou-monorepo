# Dockerfile for WhatsApp Bridge (Go Service)
FROM golang:alpine AS builder

# Set working directory
WORKDIR /app

# Install build dependencies
RUN apk add --no-cache git gcc musl-dev sqlite-dev

# Copy go.mod and go.sum
COPY go.mod go.sum ./

# Download dependencies
RUN go mod download

# Copy source code
COPY *.go ./

# Build the application
RUN CGO_ENABLED=1 GOOS=linux go build -a -installsuffix cgo -o whatsapp-bridge .


# Final stage
FROM alpine:latest

# Install runtime dependencies
RUN apk --no-cache add ca-certificates sqlite-libs curl

# Create non-root user
RUN addgroup -S whatsapp && adduser -S whatsapp -G whatsapp

# Set working directory
WORKDIR /app

# Copy binary from builder
COPY --from=builder /app/whatsapp-bridge .

# Create store directory
RUN mkdir -p /app/store && chown -R whatsapp:whatsapp /app

# Switch to non-root user
USER whatsapp

# Expose port
EXPOSE 8080

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=40s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

# Run the application
CMD ["./whatsapp-bridge"]
