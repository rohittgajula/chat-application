# Environment Configuration Guide

This project uses a global environment configuration system for better management across different deployment environments.

## Environment Files

### `.env` (Base Configuration)

- **Committed to git**: Contains default values and non-sensitive configuration
- **Purpose**: Base configuration that works for development
- **Usage**: Loaded by all services in Docker Compose

### `.env.local` (Local Development)

- **Not committed**: Personal development overrides
- **Purpose**: Local development customizations
- **Usage**: Copy and modify for your local setup

### `.env.production` (Production)

- **Not committed**: Production-specific configuration
- **Purpose**: Production deployment settings
- **Usage**: Deploy with production values

### `.env.staging` (Staging)

- **Not committed**: Staging environment configuration
- **Purpose**: Staging deployment settings
- **Usage**: Deploy with staging values

## Configuration Categories

### Database Configuration

```bash
POSTGRES_DB=auth_db
POSTGRES_USER=auth_user
POSTGRES_PASSWORD=auth_pass
POSTGRES_HOST=postgres
POSTGRES_PORT=5432
```

### Service Configuration

```bash
AUTH_SERVICE_PORT=8000
CHAT_SERVICE_PORT=8001
AUTH_SERVICE_URL=http://auth_service:8000
CHAT_SERVICE_URL=http://chat_service:8001
```

### Security Configuration

```bash
MICROSERVICE_SECRET_KEY=microservice-secret-key-2024
DJANGO_SECRET_KEY_AUTH=your-auth-secret-key
DJANGO_SECRET_KEY_CHAT=your-chat-secret-key
DJANGO_ALLOWED_HOSTS=*,localhost,127.0.0.1
```

## Usage Instructions

### Development Setup

1. Use the default `.env` file for Docker development
2. Create `.env.local` for personal overrides if needed
3. Run: `docker-compose up`

### Production Deployment

1. Copy `.env.production` to `.env.prod`
2. Update all production values (database, secrets, URLs)
3. Run: `docker-compose --env-file .env.prod up -d`

### Local Development (Outside Docker)

1. Create `.env.local` with local database settings
2. Set `AUTH_SERVICE_URL=http://localhost:8000`
3. Run services individually

## Security Best Practices

1. **Never commit sensitive files**: `.env.local`, `.env.production`, `.env.staging`
2. **Rotate secrets regularly**: Update `MICROSERVICE_SECRET_KEY` and Django secret keys
3. **Use strong passwords**: Generate secure database passwords for production
4. **Limit allowed hosts**: Set specific domains in `DJANGO_ALLOWED_HOSTS` for production
5. **Use environment-specific secrets**: Different keys for each environment

## Environment Variable Priority

Variables are loaded in this order (later overrides earlier):

1. `.env` (base configuration)
2. `.env.local` (local overrides)
3. `.env.${NODE_ENV}` (environment-specific)
4. Docker Compose environment section
5. System environment variables

## Troubleshooting

### Common Issues

- **Service can't connect**: Check `AUTH_SERVICE_URL` matches container name
- **Database connection failed**: Verify `POSTGRES_*` variables match
- **Permission denied**: Ensure Docker has access to volume mounts
- **Port conflicts**: Check if ports are already in use locally

### Debugging

```bash
# Check environment variables in container
docker exec -it auth_service env | grep POSTGRES

# View service logs
docker-compose logs auth_service

# Test service connectivity
docker exec -it chat_service curl http://auth_service:8000/users/profile/
```
