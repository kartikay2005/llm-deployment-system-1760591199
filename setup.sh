#!/bin/bash

# LLM Code Deployment Project - Automated Setup Script
# This script sets up the complete development environment

set -e  # Exit on any error

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
BLUE='\033[0;34m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Functions
print_header() {
    echo ""
    echo -e "${BLUE}================================${NC}"
    echo -e "${BLUE}$1${NC}"
    echo -e "${BLUE}================================${NC}"
}

print_step() {
    echo -e "${GREEN}✓${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠️${NC} $1"
}

print_error() {
    echo -e "${RED}❌${NC} $1"
}

check_command() {
    if command -v $1 &> /dev/null; then
        print_step "$1 is installed"
        return 0
    else
        print_error "$1 is not installed"
        return 1
    fi
}

print_header "🚀 LLM Code Deployment Project Setup"

echo "This script will set up your complete development environment."
echo "Please make sure you have the following ready:"
echo "- OpenAI API key (https://platform.openai.com/api-keys)"
echo "- GitHub Personal Access Token (https://github.com/settings/tokens)"
echo "- Your unique secret from the Google Form submission"
echo ""
read -p "Press Enter to continue or Ctrl+C to abort..."

# Check system requirements
print_header "🔍 Checking System Requirements"

PYTHON_REQUIRED=true
PIP_REQUIRED=true
NODE_REQUIRED=true
GIT_REQUIRED=true

check_command python3 || PYTHON_REQUIRED=false
check_command pip || check_command pip3 || PIP_REQUIRED=false
check_command node || NODE_REQUIRED=false
check_command git || GIT_REQUIRED=false

if [ "$PYTHON_REQUIRED" = false ] || [ "$PIP_REQUIRED" = false ]; then
    print_error "Python 3 and pip are required. Please install them first."
    echo "Ubuntu/Debian: sudo apt update && sudo apt install python3 python3-pip"
    echo "macOS: brew install python3"
    echo "Windows: Download from https://python.org"
    exit 1
fi

if [ "$NODE_REQUIRED" = false ]; then
    print_warning "Node.js not found. Playwright may require it."
    echo "Install from: https://nodejs.org"
fi

# Check Python version
PYTHON_VERSION=$(python3 --version | cut -d' ' -f2)
PYTHON_MAJOR=$(echo $PYTHON_VERSION | cut -d'.' -f1)
PYTHON_MINOR=$(echo $PYTHON_VERSION | cut -d'.' -f2)

if [ "$PYTHON_MAJOR" -eq 3 ] && [ "$PYTHON_MINOR" -ge 9 ]; then
    print_step "Python $PYTHON_VERSION (compatible)"
else
    print_error "Python 3.9+ required, found $PYTHON_VERSION"
    exit 1
fi

# Create virtual environment
print_header "📦 Setting Up Python Environment"

if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
    print_step "Virtual environment created"
else
    print_step "Virtual environment already exists"
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate || {
    print_error "Failed to activate virtual environment"
    exit 1
}
print_step "Virtual environment activated"

# Upgrade pip
echo "Upgrading pip..."
pip install --upgrade pip
print_step "pip upgraded"

# Install Python dependencies
print_header "📚 Installing Python Dependencies"

if [ -f "requirements.txt" ]; then
    echo "Installing requirements from requirements.txt..."
    pip install -r requirements.txt
    print_step "Python dependencies installed"
else
    print_error "requirements.txt not found"
    exit 1
fi

# Install Playwright browsers
print_header "🎭 Setting Up Playwright Browsers"

echo "Installing Playwright browsers..."
python -m playwright install chromium
print_step "Playwright chromium browser installed"

# Install system dependencies for Playwright (Linux)
if [[ "$OSTYPE" == "linux-gnu"* ]]; then
    echo "Installing Playwright system dependencies..."
    python -m playwright install-deps chromium || {
        print_warning "Could not install system dependencies automatically"
        echo "You may need to run: sudo playwright install-deps chromium"
    }
fi

# Set up environment configuration
print_header "⚙️ Setting Up Environment Configuration"

if [ ! -f ".env" ]; then
    if [ -f ".env.template" ]; then
        echo "Creating .env file from template..."
        cp .env.template .env
        print_step "Environment file created"

        echo ""
        echo -e "${YELLOW}IMPORTANT: You need to edit .env with your actual API keys!${NC}"
        echo ""
        echo "Required configuration:"
        echo "1. OPENAI_API_KEY - Get from https://platform.openai.com/api-keys"
        echo "2. GITHUB_TOKEN - Get from https://github.com/settings/tokens"
        echo "3. USER_SECRET - Your unique secret from Google Form"
        echo ""

        # Generate Flask secret key
        SECRET_KEY=$(python -c "import secrets; print(secrets.token_hex(32))" 2>/dev/null || echo "your-secure-secret-key-here")

        # Update .env with generated secret key
        if [ "$SECRET_KEY" != "your-secure-secret-key-here" ]; then
            sed -i.bak "s/your-secure-random-secret-key-here/$SECRET_KEY/" .env
            print_step "Flask secret key generated and set"
        fi

    else
        print_error ".env.template not found"
        exit 1
    fi
else
    print_step "Environment file already exists"
fi

# Create necessary directories
print_header "📁 Creating Directory Structure"

mkdir -p logs
mkdir -p uploads
mkdir -p screenshots
print_step "Directories created"

# Set up database
print_header "🗄️ Setting Up Database"

echo "Initializing database..."
python -c "
try:
    from evaluation_system import DatabaseManager
    db = DatabaseManager()
    print('✅ Database initialized successfully')
except ImportError:
    print('⚠️ evaluation_system.py not found - database will be created on first run')
except Exception as e:
    print(f'❌ Database setup error: {e}')
" || print_warning "Database setup had issues - will be created on first run"

# Create sample request file
print_header "📄 Creating Sample Files"

cat > sample_request.json << 'EOF'
{
  "email": "student@example.com",
  "secret": "your-secret-here",
  "task": "sample-task",
  "round": 1,
  "nonce": "sample-nonce-123",
  "brief": "Create a simple HTML page with a button that displays 'Hello World' when clicked. Include Bootstrap for styling.",
  "checks": [
    "Repo has MIT license",
    "README.md is professional",
    "Page displays a button",
    "js: document.querySelector('button') !== null",
    "js: document.title.length > 0"
  ],
  "evaluation_url": "https://httpbin.org/post",
  "attachments": []
}
EOF
print_step "Sample request file created (sample_request.json)"

# Create test script for manual testing
cat > manual_test.sh << 'EOF'
#!/bin/bash
echo "🧪 Manual Test - Deployment Request"
echo "=================================="

# Check if server is running
if curl -s http://localhost:5000/health > /dev/null; then
    echo "✅ Server is running"

    echo "📤 Sending sample deployment request..."
    curl -X POST http://localhost:5000/api/deploy          -H "Content-Type: application/json"          -d @sample_request.json          | python -m json.tool
else
    echo "❌ Server is not running"
    echo "Start with: python app.py"
fi
EOF

chmod +x manual_test.sh
print_step "Manual test script created (manual_test.sh)"

# Run comprehensive tests
print_header "🧪 Running System Tests"

if [ -f "test_suite.py" ]; then
    echo "Running comprehensive test suite..."
    python test_suite.py || {
        print_warning "Some tests failed - check output above"
        echo "You can still proceed, but may need to fix configuration issues"
    }
else
    print_warning "test_suite.py not found - skipping comprehensive tests"
fi

# Final instructions
print_header "🎉 Setup Complete!"

echo ""
echo -e "${GREEN}Your LLM Code Deployment system is ready!${NC}"
echo ""
echo "📝 Next steps:"
echo "1. Edit .env file with your API keys:"
echo "   - OPENAI_API_KEY (required)"
echo "   - GITHUB_TOKEN (required)"  
echo "   - USER_SECRET (required)"
echo ""
echo "2. Test your configuration:"
echo "   python test_suite.py"
echo ""
echo "3. Start the development server:"
echo "   python app.py"
echo ""
echo "4. Test the API (in another terminal):"
echo "   curl http://localhost:5000/health"
echo "   ./manual_test.sh"
echo ""
echo "5. Deploy to production:"
echo "   - Heroku: git push heroku main"
echo "   - Railway: railway up"
echo "   - Docker: docker build -t llm-deploy ."
echo ""

# Check if API keys are set
if grep -q "your-openai-api-key-here" .env 2>/dev/null; then
    print_warning "Remember to set your OPENAI_API_KEY in .env"
fi

if grep -q "your-github-personal-access-token-here" .env 2>/dev/null; then
    print_warning "Remember to set your GITHUB_TOKEN in .env"
fi

if grep -q "your-unique-secret-from-google-form" .env 2>/dev/null; then
    print_warning "Remember to set your USER_SECRET in .env"
fi

echo ""
echo -e "${BLUE}Happy coding! 🚀${NC}"
echo ""

# Deactivate virtual environment message
echo "Note: Virtual environment is activated for this session."
echo "To activate it later, run: source venv/bin/activate"
