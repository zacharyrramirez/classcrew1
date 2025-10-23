streamll# Fly.io Deployment Guide for AI Grader v2

This guide will help you deploy the AI Grader application to Fly.io.

## Prerequisites

1. **Fly.io CLI**: Install from [fly.io/docs/getting-started/installing-flyctl](https://fly.io/docs/getting-started/installing-flyctl/)
2. **Fly.io Account**: Sign up at [fly.io](https://fly.io)
3. **Docker**: Ensure Docker is installed and running locally

## Environment Variables

Set these environment variables in your Fly.io app:

```bash
# Your AI Service API Keys (you provide these)
OPENAI_API_KEY=your-openai-api-key
GEMINI_API_KEY=your-google-gemini-api-key

# Optional
DEBUG_MODE=0
```

**Note:** Teachers will now configure their own Canvas settings through the web interface. You only need to provide the AI service API keys.

## Deployment Steps

### 1. Login to Fly.io

```bash
fly auth login
```

### 2. Create the App

```bash
fly launch
```

When prompted:
- **App name**: Choose a unique name (e.g., `ai-grader-v2-yourname`)
- **Region**: Choose closest to your users (e.g., `sjc` for San Jose)
- **Use existing fly.toml**: Yes (we've already created it)

### 3. Create Persistent Volume

```bash
fly volumes create data_volume --region sjc --size 10
```

This creates a 10GB persistent volume for storing student submissions and grading data.

### 4. Set Environment Variables

```bash
fly secrets set OPENAI_API_KEY=your-openai-api-key
fly secrets set GEMINI_API_KEY=your-google-gemini-api-key
```

**Note:** Teachers will configure their Canvas settings through the web interface after creating their accounts.

### 5. Deploy the Application

```bash
fly deploy
```

### 6. Check Deployment Status

```bash
fly status
fly logs
```

## Accessing Your Application

After successful deployment, your app will be available at:
```
https://your-app-name.fly.dev
```

## Teacher Onboarding

Teachers can now create accounts and configure their Canvas settings:

1. **Visit the app** → Login page appears
2. **Click "Create Account"** → Registration form
3. **Fill in details:**
   - Username and password
   - Email address
   - Canvas URL (e.g., `https://school.instructure.com`)
   - Canvas API Token (from Account → Settings → Approved Integrations)
   - Course ID (from course URL)
4. **Account created** → Redirected to login
5. **Login** → Access grading dashboard
6. **Update settings** → Use sidebar "Account Settings" anytime

## File Storage

The application uses a persistent volume mounted at `/app/data` to store:
- **User accounts** (`users.json`) - Teacher credentials and Canvas settings
- **Student submissions** - Downloaded assignment files
- **Generated PDFs** - Merged and processed documents
- **Grading results** - CSV exports and logs
- **Debug outputs** - Temporary processing files

This ensures data persists across deployments and restarts.

## Scaling and Performance

### Auto-scaling Configuration

The `fly.toml` is configured with:
- `auto_stop_machines = true` - Stops machines when idle
- `auto_start_machines = true` - Starts machines when needed
- `min_machines_running = 0` - No machines running when idle

### Resource Allocation

- **CPU**: 1 shared CPU
- **Memory**: 2GB RAM
- **Storage**: 10GB persistent volume

## Monitoring and Logs

### View Logs
```bash
fly logs
```

### Monitor Status
```bash
fly status
fly dashboard
```

### SSH into Container
```bash
fly ssh console
```

## Updates and Maintenance

### Deploy Updates
```bash
git add .
git commit -m "Update application"
fly deploy
```

### Scale Resources
```bash
# Scale memory
fly scale memory 4096

# Scale CPU
fly scale vm shared-cpu-2x
```

## Troubleshooting

### Common Issues

1. **Build Failures**: Check Dockerfile and requirements.txt
2. **Memory Issues**: Increase memory allocation
3. **File Permission Errors**: Check volume mount permissions
4. **API Key Issues**: Verify environment variables are set

### Debug Commands

```bash
# Check app logs
fly logs --app your-app-name

# SSH into running container
fly ssh console --app your-app-name

# Check volume status
fly volumes list --app your-app-name
```

## Security Considerations

1. **API Keys**: Never commit API keys to version control
2. **HTTPS**: Fly.io automatically provides HTTPS
3. **File Access**: Persistent volume is only accessible to your app
4. **Environment Variables**: Use Fly.io secrets for sensitive data
5. **User Authentication**: Passwords are hashed using SHA-256
6. **Session Management**: 2-hour session timeout for security
7. **Canvas Tokens**: Stored securely per user account

## Cost Optimization

- The app auto-stops when idle, minimizing costs
- Persistent volume costs ~$0.15/GB/month
- Compute costs only when the app is active

## Support

For Fly.io specific issues:
- [Fly.io Documentation](https://fly.io/docs/)
- [Fly.io Community](https://community.fly.io/)

For application issues:
- Check the application logs
- Review the README_ai_grader_v2.md file
