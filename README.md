# LLM Code Deployment System# Student API - LLM Code Deployment



A production-ready Flask application that receives project briefs, generates complete web applications using LLMs, and automatically deploys them to GitHub Pages with full evaluation support.🚀 **AI-powered code generation and deployment API for students**



## 🚀 FeaturesThis is a Flask API that receives task specifications, uses OpenAI's GPT models to generate code, and automatically deploys the generated applications to GitHub Pages.



- **🤖 LLM Code Generation**: Uses OpenAI API to generate complete, functional web applications## 🎯 Overview

- **📂 GitHub Integration**: Automatically creates repositories, uploads files, and enables Pages

- **🔄 Round Support**: Handles initial deployment (Round 1) and feature updates (Round 2) As a student, you will:

- **📎 Attachment Processing**: Supports file attachments with base64 encoding (images, data files, etc.)1. **Receive Tasks**: Your API receives JSON requests with coding task specifications

- **🔐 Secure Validation**: Comprehensive input validation and secret-based authentication2. **Generate Code**: OpenAI GPT models create the required code based on the task

- **📞 Evaluation Callbacks**: Notifies evaluation endpoints with deployment details and retry logic3. **Deploy Automatically**: Code is committed to GitHub and deployed via GitHub Pages

- **⚡ High Performance**: Optimized request processing with fast validation paths4. **Get Evaluated**: Instructors can access your deployed applications for grading



## 📋 Requirements## 🏗️ How It Works



- Python 3.8+```

- OpenAI API access┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐

- GitHub Personal Access Token│   Instructor    │───▶│   Your Flask API │───▶│  GitHub Pages   │

- Internet connection for API calls│  (Task Request) │    │ (GPT Generation) │    │   (Deployed)    │

└─────────────────┘    └──────────────────┘    └─────────────────┘

## 🛠️ Quick Setup```



1. **Install dependencies:**## 📦 Your Files

   ```bash

   pip install -r requirements.txt### Core Application

   ```- **`app.py`** - Your main Flask API server with OpenAI integration

- **`requirements.txt`** - Required Python packages  

2. **Configure environment variables:**- **`.env`** - Your API keys and configuration (keep this secret!)

   ```bash

   set OPENAI_API_KEY=your_openai_api_key### Setup & Examples

   set GITHUB_TOKEN=your_github_personal_access_token  - **`setup.sh`** - Automated setup script

   set USER_SECRET=your_authentication_secret- **`test-solution/`** - Example of generated code structure

   ```- **`.env.template`** - Template showing what environment variables you need



3. **Start the server:**## 🚀 Quick Start

   ```bash

   python app.py### 1. Setup Environment

   ```

```bash

4. **Server will be available at:** `http://localhost:5000`# Clone and setup

git clone <repository>

## 🔌 API Usagecd llm-code-deployment



### POST /api/deploy# Run automated setup

Main deployment endpoint that creates/updates applications.chmod +x setup.sh

./setup.sh

**Request:**```

```json

{### 2. Configure API Keys

  "email": "student@university.edu",

  "secret": "your_authentication_secret",Edit `.env` file with your credentials:

  "task": "markdown-to-html-converter", 

  "round": 1,```env

  "nonce": "unique_identifier_123",OPENAI_API_KEY=sk-your-openai-key-here

  "brief": "Create a web app that converts markdown to HTML with syntax highlighting",GITHUB_TOKEN=ghp-your-github-token-here  

  "checks": [USER_SECRET=your-unique-secret

    "Page loads successfully",```

    "Markdown converts to HTML", 

    "Code blocks have syntax highlighting"### 3. Test Installation

  ],

  "evaluation_url": "https://evaluation.system.com/callback",```bash

  "attachments": [python test_suite.py

    {```

      "name": "sample.md",

      "url": "data:text/markdown;base64,SGVsbG8gV29ybGQ="### 4. Start Server

    }

  ]```bash

}python app.py

``````



**Response:**### 5. Test Deployment

```json

{```bash

  "status": "success",curl -X POST http://localhost:5000/api/deploy      -H "Content-Type: application/json"      -d @sample_request.json

  "message": "Deployment completed successfully", ```

  "processing_time": 45.2,

  "repo_name": "markdown-to-html-converter-1234567890",## 📋 API Specification

  "round": 1,

  "updated": false### Deployment Endpoint

}

```**POST** `/api/deploy`



### POST /api/validate  ```json

Validates requests without deploying (for testing).{

  "email": "student@example.com",

## 🎯 How It Works  "secret": "your-secret",

  "task": "captcha-solver-demo",

1. **Request Validation**: Validates all required fields and authentication  "round": 1,

2. **LLM Generation**: Creates complete HTML/CSS/JS application based on brief  "nonce": "unique-nonce-123",

3. **GitHub Deployment**:   "brief": "Create a captcha solver app",

   - Round 1: Creates new public repository  "checks": [

   - Round 2: Updates existing repository    "Repo has MIT license",

4. **File Upload**: Uploads generated code, README, LICENSE, and attachments    "README.md is professional",

5. **Pages Activation**: Enables GitHub Pages for instant web hosting    "js: document.querySelector('button') !== null"

6. **Evaluation Callback**: Notifies provided URL with repository details  ],

  "evaluation_url": "https://example.com/notify",

## 📁 Generated Repository Structure  "attachments": [...]

}

``````

repository-name/

├── index.html          # Main application (generated by LLM)**Response:**

├── README.md           # Professional documentation```json

├── LICENSE             # MIT License{

└── assets/             # Uploaded attachments (if any)  "status": "success",

    └── filename.ext  "data": {

```    "repo_url": "https://github.com/user/repo",

    "pages_url": "https://user.github.io/repo/",

## 🔄 Round System    "commit_sha": "abc123"

  }

- **Round 1**: Creates new repository with initial implementation}

- **Round 2**: Updates existing repository with enhanced features```

- **Round 3+**: Further updates to the same repository

## 🧪 Testing

## 🔐 Security Features

### Automated Testing

- Secret-based request authentication

- Input validation and sanitization  ```bash

- No sensitive data in git history# Run full test suite

- Environment variable configurationpython test_suite.py

- Rate limiting and error handling

# Run specific tests

## 🌐 Deployment Supportpython -m pytest tests/

```

- **GitHub Pages**: Automatic hosting with custom domains

- **Static Sites**: Self-contained HTML applications### Manual Testing

- **Mobile Responsive**: Generated apps work on all devices

- **Fast Loading**: Optimized code generation```bash

# Start test evaluation endpoint

## 📊 Monitoringpython test_evaluation_endpoint.py



- Deployment state tracking in `deployment_state.json`# Test deployment (in another terminal)

- Comprehensive logging for debugging./manual_test.sh

- Performance metrics and timing```

- Error reporting and recovery

### Browser Testing

## 🏆 Production Ready

```bash

This system is battle-tested and ready for:# Start Playwright evaluation

- Student project evaluation systemspython evaluation_system.py

- Automated code generation pipelines  ```

- Educational technology platforms

- Rapid prototyping workflows## 🔧 Configuration



---### Required Environment Variables



**Built with ❤️ for automated code deployment and evaluation**| Variable | Description | Example |
|----------|-------------|---------|
| `OPENAI_API_KEY` | OpenAI API key | `sk-...` |
| `GITHUB_TOKEN` | GitHub Personal Access Token | `ghp_...` |
| `USER_SECRET` | Unique authentication secret | `my-secret-123` |

### Optional Configuration

| Variable | Default | Description |
|----------|---------|-------------|
| `PORT` | `5000` | Server port |
| `FLASK_ENV` | `development` | Environment |
| `LOG_LEVEL` | `INFO` | Logging level |

## 📊 Evaluation System

### Repository Checks

- ✅ MIT License present
- ✅ Professional README.md
- ✅ Proper file structure
- ✅ Recent creation time

### Application Checks

- ✅ Page loads successfully
- ✅ JavaScript functionality
- ✅ Content display verification
- ✅ Framework integration (Bootstrap, etc.)

### Check Types

```javascript
// JavaScript-based checks
"js: document.querySelector('button') !== null"
"js: document.title.includes('Sales Summary')"

// Content checks  
"Page displays captcha image"
"README.md is professional"
"Repo has MIT license"
```

## 🚀 Deployment Options

### Heroku

```bash
# Setup
heroku create your-app-name
heroku config:set OPENAI_API_KEY=sk-...
heroku config:set GITHUB_TOKEN=ghp-...

# Deploy
git push heroku main
```

### Railway

```bash
railway new
railway up
```

### Docker

```bash
docker build -t llm-deploy .
docker run -p 5000:5000 --env-file .env llm-deploy
```

## 📁 Project Structure

```
llm-code-deployment/
├── app.py                          # Main Flask API
├── evaluation_system.py            # Testing & evaluation
├── requirements.txt                # Dependencies
├── .env.template                   # Config template
├── setup.sh                       # Setup script
├── test_suite.py                   # Test suite
├── sample_request.json             # Example request
├── test_evaluation_endpoint.py     # Mock endpoint
├── Dockerfile                      # Container config
├── .github/workflows/deploy.yml    # CI/CD
├── logs/                          # Application logs
├── uploads/                       # File uploads
└── venv/                          # Python environment
```

## 🔒 Security

### API Security

- Request validation and sanitization
- Secret-based authentication
- Rate limiting support
- HTTPS enforcement

### Code Generation Safety

- Prompt injection prevention
- Output validation
- Resource usage limits
- Security scanning integration

## 📈 Monitoring & Logging

### Health Checks

```bash
curl http://localhost:5000/health
```

### Log Files

- `app.log` - Application logs
- `evaluation.log` - Evaluation results

### Metrics

- Deployment success rate
- Evaluation scores
- Performance metrics
- Error tracking

## 🤝 Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests: `python test_suite.py`
5. Submit a pull request

## 📚 Educational Value

This project demonstrates:

- **Modern Web Development**: Flask, REST APIs, microservices
- **AI Integration**: LLM prompt engineering, code generation
- **DevOps Practices**: CI/CD, containerization, automated deployment
- **Testing Automation**: Browser automation, integration testing
- **Cloud Services**: GitHub API, OpenAI API, deployment platforms

## 🆘 Troubleshooting

### Common Issues

**OpenAI Rate Limits**
```bash
# Check your usage at https://platform.openai.com/usage
# Implement retry logic (already included)
```

**GitHub Pages Not Deploying**
```bash
# Check repository is public
# Ensure index.html is in root
# Wait up to 10 minutes for first deployment
```

**Playwright Browser Issues**
```bash
playwright install chromium
playwright install-deps chromium
```

### Support

- 📖 [Full Documentation](IMPLEMENTATION_GUIDE.md)
- 🐛 [Issue Tracker](https://github.com/your-repo/issues)
- 💬 [Discussions](https://github.com/your-repo/discussions)

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🏆 Acknowledgments

- OpenAI for GPT API
- GitHub for Pages hosting
- Playwright team for browser automation
- Flask community for web framework

---

**Built with ❤️ for educational purposes**

*This system demonstrates the power of combining AI with automated deployment for educational applications.*
