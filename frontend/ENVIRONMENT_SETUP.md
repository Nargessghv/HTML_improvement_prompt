# Environment Configuration Guide

This guide explains how to configure environment variables for the Ekona Slide Creator frontend application.

## Quick Setup

1. **Copy the template:**
   ```bash
   cp .env.local.example .env.local
   ```

2. **Configure Supabase:**
   - Go to [Supabase Dashboard](https://app.supabase.com)
   - Navigate to your project settings > API
   - Copy the values to your `.env.local` file:
     ```env
     NEXT_PUBLIC_SUPABASE_URL=https://your-project.supabase.co
     NEXT_PUBLIC_SUPABASE_ANON_KEY=your-anon-key
     SUPABASE_SERVICE_ROLE_KEY=your-service-role-key
     ```

3. **Configure Backend API:**
   ```env
   NEXT_PUBLIC_API_URL=http://localhost:8000
   ```

4. **Generate Security Secrets:**
   ```bash
   # Generate NextAuth secret
   openssl rand -base64 32
   
   # Generate JWT secret
   openssl rand -base64 32
   
   # Generate Webhook secret
   openssl rand -base64 32
   ```

5. **Start the development server:**
   ```bash
   npm run dev
   ```

## Environment Variables Reference

### Required Variables

| Variable | Description | Example |
|----------|-------------|---------|
| `NEXT_PUBLIC_SUPABASE_URL` | Supabase project URL | `https://abc123.supabase.co` |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | Supabase anonymous key | `eyJhbGciOiJIUzI1NiIs...` |
| `NEXT_PUBLIC_API_URL` | Backend API base URL | `http://localhost:8000` |

### Security Variables

| Variable | Description | Required |
|----------|-------------|----------|
| `SUPABASE_SERVICE_ROLE_KEY` | Service role key for admin operations | Server-side only |
| `NEXTAUTH_SECRET` | NextAuth session encryption key | Production |
| `JWT_SECRET` | Custom JWT verification key | Production |

### Optional Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `NEXT_PUBLIC_APP_NAME` | Application display name | `Ekona Slide Creator` |
| `NEXT_PUBLIC_STORAGE_BUCKET` | Supabase storage bucket | `presentations` |
| `DEBUG` | Enable debug logging | `false` |
| `VERBOSE_LOGGING` | Enable verbose logging | `false` |

## Feature Flags

Control application features with these environment variables:

| Variable | Description | Default |
|----------|-------------|---------|
| `NEXT_PUBLIC_ENABLE_REALTIME` | Real-time updates | `true` |
| `NEXT_PUBLIC_ENABLE_AI_CHAT` | AI chat features | `true` |
| `NEXT_PUBLIC_ENABLE_EXPORT` | File export features | `true` |
| `NEXT_PUBLIC_ENABLE_COLLABORATION` | Collaboration features | `false` |

## Environment Validation

The application automatically validates environment variables on startup. If required variables are missing, you'll see a helpful error message.

### Health Check

Visit `/health` to check the application configuration:

```json
{
  "status": "healthy",
  "environment": "development",
  "services": {
    "supabase": {
      "configured": true,
      "url": "configured"
    },
    "api": {
      "configured": true,
      "url": "configured"
    }
  },
  "features": {
    "realtime": true,
    "aiChat": true,
    "export": true,
    "collaboration": false
  }
}
```

## Security Best Practices

1. **Never commit secrets** to version control
2. **Use different values** for development, staging, and production
3. **Rotate secrets regularly** in production
4. **Use environment-specific configurations**
5. **Validate all environment variables** at startup

## Deployment Environments

### Development
- Use `.env.local` for local overrides
- Enable debug features
- Use localhost URLs

### Staging
- Use production-like configuration
- Test with real Supabase project
- Enable additional logging

### Production
- Use secure, generated secrets
- Enable all security headers
- Disable debug features
- Use production Supabase project

## Troubleshooting

### Common Issues

1. **Missing environment variables:**
   - Check that `.env.local` exists
   - Verify all required variables are set
   - Restart the development server

2. **Invalid Supabase configuration:**
   - Verify Supabase URL format
   - Check API keys are correct
   - Ensure project is active

3. **Build errors:**
   - Environment variables are validated at build time
   - Use the health check endpoint to debug
   - Check the console for specific error messages

### Debug Commands

```bash
# Check environment validation
npm run build

# Check health endpoint
curl http://localhost:3000/health

# View environment status (development only)
# Check browser console for environment logs
```

## Files Overview

- `.env.example` - Complete reference with all variables
- `.env.local.example` - Development template
- `src/lib/env.ts` - Environment validation and types
- `src/app/api/health/route.ts` - Health check endpoint
- `next.config.ts` - Next.js environment configuration

## Support

If you encounter issues with environment configuration:

1. Check this documentation
2. Verify your `.env.local` file
3. Use the health check endpoint
4. Check the browser console for validation errors