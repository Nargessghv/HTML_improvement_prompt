# Deployment Guide - ekona Slide Creator

This guide covers deploying the PowerPoint Slide Creator application to Digital Ocean App Platform.

## Overview

The application consists of:
- **Frontend**: Next.js 15 application with TypeScript, Tailwind CSS, and shadcn/ui
- **Backend**: Python FastAPI server with LangGraph AI workflows
- **Database**: Supabase (PostgreSQL with real-time features)
- **Storage**: Supabase Storage for files and presentations
- **Monitoring**: Langfuse for LLM observability

## Prerequisites

### 1. Install Digital Ocean CLI
```bash
# macOS
brew install doctl

# Linux
snap install doctl

# Windows (using scoop)
scoop install doctl
```

### 2. Authenticate with Digital Ocean
```bash
doctl auth init
```

### 3. Set up Supabase Project
1. Go to [supabase.com](https://supabase.com) and create a new project
2. Note your Project URL and API keys
3. Run the database migrations (if any) in your Supabase dashboard

### 4. Set up LLM API Keys
- OpenAI API key for GPT-4 models
- Langfuse account for monitoring (optional but recommended)

## Quick Deployment

### 1. Configure Environment
```bash
# Copy the production environment template
cp .env.production .env

# Edit .env with your actual values
nano .env
```

**Required environment variables:**
```bash
# Supabase
NEXT_PUBLIC_SUPABASE_URL=https://your-project.supabase.co
NEXT_PUBLIC_SUPABASE_ANON_KEY=your-anon-key
SUPABASE_SERVICE_ROLE_KEY=your-service-role-key

# OpenAI
OPENAI_API_KEY=your-openai-api-key

# Security (generate new values for production)
NEXTAUTH_SECRET=$(openssl rand -base64 32)
JWT_SECRET=$(openssl rand -base64 32)
WEBHOOK_SECRET=$(openssl rand -base64 32)

# Langfuse (optional)
LANGFUSE_PUBLIC_KEY=your-langfuse-public-key
LANGFUSE_SECRET_KEY=your-langfuse-secret-key
```

### 2. Update App Configuration
Edit `.do/app.yaml` and update:
- GitHub repository path
- Domain names after deployment

### 3. Deploy
```bash
# Run the deployment script
./deploy.sh
```

## Manual Deployment Steps

If you prefer manual deployment:

### 1. Create App
```bash
doctl apps create --spec .do/app.yaml
```

### 2. Monitor Deployment
```bash
# List apps
doctl apps list

# Get app details
doctl apps get <app-id>

# View logs
doctl apps logs <app-id>
```

### 3. Set Environment Variables
Go to Digital Ocean App Platform dashboard and configure environment variables in the app settings.

## Local Testing with Docker

Before deploying to production, test locally:

### 1. Build and Run
```bash
# Build images
docker-compose build

# Run the application
docker-compose up
```

### 2. Test Endpoints
- Frontend: http://localhost:3000
- Backend API: http://localhost:8000
- Health check: http://localhost:8000/health

## Production Configuration

### Instance Sizing Recommendations

**Frontend (Next.js)**:
- Instance: `basic-xxs` (0.5 vCPU, 0.5GB RAM)
- Suitable for static serving and SSR

**Backend (Python + AI)**:
- Instance: `basic-s` (1 vCPU, 2GB RAM) minimum
- Consider `basic-m` (2 vCPU, 4GB RAM) for high traffic
- AI processing requires more resources

### Scaling Considerations

1. **Horizontal Scaling**: Increase instance count during high traffic
2. **Vertical Scaling**: Use larger instances for complex AI operations
3. **Database**: Supabase handles scaling automatically
4. **File Storage**: Supabase Storage scales with usage

## Security Best Practices

### 1. Environment Variables
- Never commit secrets to git
- Use Digital Ocean's encrypted environment variables
- Rotate API keys regularly

### 2. Network Security
- Enable HTTPS (automatic with Digital Ocean)
- Configure CORS properly
- Use secure headers (already configured in Next.js)

### 3. Database Security
- Use Row Level Security (RLS) in Supabase
- Limit service role key permissions
- Regular security audits

## Monitoring and Maintenance

### 1. Application Monitoring
- Digital Ocean App Platform dashboard
- Langfuse for LLM observability
- Set up alerts for CPU/memory usage

### 2. Health Checks
- Frontend: `/health` endpoint
- Backend: `/health` endpoint
- Automatic restarts on health check failures

### 3. Logging
```bash
# View app logs
doctl apps logs <app-id> --type=run

# Follow live logs
doctl apps logs <app-id> --type=run --follow
```

## Troubleshooting

### Common Issues

1. **Build Failures**
   - Check Dockerfile syntax
   - Verify all dependencies in requirements.txt/package.json
   - Check build logs in Digital Ocean dashboard

2. **Runtime Errors**
   - Verify environment variables
   - Check service connectivity
   - Review application logs

3. **Performance Issues**
   - Monitor resource usage
   - Consider upgrading instance sizes
   - Optimize AI model usage

### Debug Commands
```bash
# Check app status
doctl apps get <app-id>

# View deployment history
doctl apps list-deployments <app-id>

# Get deployment logs
doctl apps logs <app-id> --type=build
```

## Custom Domain Setup

### 1. Add Domain to App
```bash
doctl apps create-domain <app-id> --domain your-domain.com
```

### 2. Configure DNS
Add CNAME record pointing to your Digital Ocean app URL.

### 3. SSL Certificate
Digital Ocean automatically provisions SSL certificates for custom domains.

## Backup and Recovery

### 1. Database Backups
- Supabase provides automatic daily backups
- Manual backups available in Supabase dashboard

### 2. File Storage Backups
- Configure Supabase Storage backup policies
- Consider external backup solutions for critical files

### 3. Application Code
- Ensure code is properly versioned in Git
- Tag releases for easy rollbacks

## Cost Optimization

### 1. Instance Management
- Monitor usage patterns
- Scale down during low traffic
- Use appropriate instance sizes

### 2. Storage Optimization
- Regular cleanup of generated files
- Archive old presentations
- Monitor storage usage

### 3. API Usage
- Monitor OpenAI API costs
- Implement usage limits if needed
- Cache AI responses where appropriate

## Support and Updates

### 1. Application Updates
```bash
# Update app with new code
git push origin main  # Triggers auto-deployment

# Manual update
doctl apps create-deployment <app-id>
```

### 2. Rollback
```bash
# List deployments
doctl apps list-deployments <app-id>

# Rollback to previous deployment
doctl apps create-deployment <app-id> --previous
```

---

For additional support, refer to:
- [Digital Ocean App Platform docs](https://docs.digitalocean.com/products/app-platform/)
- [Supabase documentation](https://supabase.com/docs)
- Project README.md for application-specific information