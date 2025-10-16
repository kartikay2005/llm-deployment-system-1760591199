# LLM Code Deployment System - Render Deployment Guide

## 🚀 Quick Deploy to Render

### Option 1: One-Click Deploy (Recommended)
1. Click the "Deploy to Render" button (if available)
2. Connect your GitHub repository
3. Set the required environment variables (see below)
4. Deploy!

### Option 2: Manual Deployment
1. Fork/clone this repository
2. Sign up for a [Render account](https://render.com)
3. Create a new Web Service
4. Connect your GitHub repository
5. Use the following settings:
   - **Environment**: Docker
   - **Dockerfile Path**: `./Dockerfile`
   - **Region**: Oregon (or your preferred region)
   - **Instance Type**: Starter (or higher for production)

## 🔧 Required Environment Variables

Set these in your Render dashboard under "Environment":

```
OPENAI_API_KEY=your_openai_api_key_here
OPENAI_BASE_URL=https://aipipe.org/openai/v1
GITHUB_TOKEN=your_github_personal_access_token
USER_SECRET=your_user_secret
SECRET_KEY=your_flask_secret_key
FLASK_ENV=production
```

### How to Get These Values:

1. **OPENAI_API_KEY**: Your OpenAI API key from aipipe.org
2. **GITHUB_TOKEN**: Personal Access Token from GitHub with repo permissions
3. **USER_SECRET**: Your authentication secret (e.g., `kartikay@14`)
4. **SECRET_KEY**: Random string for Flask security (auto-generated if not provided)

## 📋 Deployment Configuration

The application is optimized for Render with:

- **Port Binding**: Automatic via `$PORT` environment variable
- **Health Checks**: Available at `/health` endpoint
- **Persistent Storage**: Deployment state saved to mounted disk
- **Production Server**: Gunicorn with optimized settings
- **Docker Support**: Multi-stage build for efficient deployment

## 🏗️ Files for Render Deployment

- `Dockerfile` - Container configuration
- `render.yaml` - Render service configuration
- `start.sh` - Optimized startup script
- `requirements.txt` - Python dependencies

## 🔍 Health Check

The application provides a health endpoint at `/health` that returns:

```json
{
  "status": "healthy",
  "services": {
    "github": "ok",
    "openai": "ok"
  },
  "timestamp": "2025-10-16T14:22:43.938216",
  "version": "1.0.0"
}
```

## 📊 Performance

- **Cold Start**: ~10-15 seconds
- **Warm Response**: <100ms for most endpoints
- **Memory Usage**: ~150-200MB
- **Storage**: Minimal (deployment state only)

## 🔒 Security Features

- Environment variable validation
- Secret-based authentication
- HTTPS-only in production
- Input sanitization and validation
- Rate limiting ready

## 🛠️ Local Development

To run locally:

```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variables
cp .env.template .env
# Edit .env with your values

# Run the application
python app.py
```

## 📚 API Endpoints

- `GET /` - Service information
- `POST /api/deploy` - Deploy code to GitHub
- `POST /api/validate` - Validate deployment request
- `GET /health` - Health check
- `GET /api/status/<deployment_id>` - Deployment status

## 🆘 Troubleshooting

### Common Issues:

1. **Port Binding Errors**: Ensure `PORT` environment variable is set
2. **GitHub Authentication**: Verify `GITHUB_TOKEN` has proper permissions
3. **OpenAI Errors**: Check `OPENAI_API_KEY` and `OPENAI_BASE_URL`
4. **Health Check Failures**: Verify all environment variables are set

### Logs:
Check Render logs for detailed error information and deployment status.

## 📞 Support

For issues related to:
- Render deployment: Check Render documentation
- Application errors: Review application logs
- API issues: Verify environment variables

---

Made with ❤️ for automated code deployment