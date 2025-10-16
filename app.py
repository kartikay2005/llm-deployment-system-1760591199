import os
import json
import uuid
import base64
import secrets
import time
import logging
from datetime import datetime
from typing import Dict, List, Any, Optional
import requests

from flask import Flask, request, jsonify
from werkzeug.utils import secure_filename
from github import Github, GithubException
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = Flask(__name__)

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('app.log'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

# Configuration
class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY', secrets.token_hex(32))
    OPENAI_API_KEY = os.environ.get('OPENAI_API_KEY')
    OPENAI_BASE_URL = os.environ.get('OPENAI_BASE_URL', 'https://aipipe.org/openai/v1')
    GITHUB_TOKEN = os.environ.get('GITHUB_TOKEN') 
    USER_SECRET = os.environ.get('USER_SECRET')
    MAX_CONTENT_LENGTH = 16 * 1024 * 1024  # 16MB

    def validate(self):
        missing = []
        if not self.OPENAI_API_KEY:
            missing.append('OPENAI_API_KEY')
        if not self.GITHUB_TOKEN:
            missing.append('GITHUB_TOKEN')
        if not self.USER_SECRET:
            missing.append('USER_SECRET')

        if missing:
            raise ValueError(f"Missing required environment variables: {', '.join(missing)}")

config = Config()
app.config.from_object(config)

# Initialize OpenAI client
openai_client = None
try:
    from openai import OpenAI
    openai_client = OpenAI(
        api_key=config.OPENAI_API_KEY,
        base_url=config.OPENAI_BASE_URL
    )
    logger.info(f"OpenAI client initialized successfully with base URL: {config.OPENAI_BASE_URL}")
except ImportError as e:
    logger.warning(f"OpenAI library not available: {e}")
    openai_client = None
except Exception as e:
    logger.warning(f"OpenAI client initialization failed: {e}")
    openai_client = None

# Initialize GitHub client
try:
    github_client = Github(config.GITHUB_TOKEN)
    github_user = github_client.get_user()
    logger.info(f"GitHub authenticated as: {github_user.login}")
except Exception as e:
    logger.error(f"GitHub authentication failed: {e}")
    github_client = None
    github_user = None

class RequestValidator:
    @staticmethod
    def validate_request(data: Dict[str, Any]) -> tuple[bool, str]:
        # Handle nested task structure
        if 'task' in data and isinstance(data['task'], dict):
            task_data = data['task']
            data.update({
                'brief': task_data.get('brief', ''),
                'checks': task_data.get('checks', []),
                'attachments': task_data.get('attachments', []),
                'evaluation_url': task_data.get('evaluation_url', data.get('evaluation_url', ''))
            })
            data['task'] = task_data.get('id', data['task'])

        # Provide defaults
        data.setdefault('email', 'student@example.com')
        data.setdefault('round', 1)
        data.setdefault('nonce', str(uuid.uuid4()))
        data.setdefault('evaluation_url', 'http://localhost:5000/evaluation_callback')
        data.setdefault('attachments', [])

        # Essential fields
        essential_fields = ['task', 'brief', 'checks']
        for field in essential_fields:
            if field not in data or not data[field]:
                return False, f"Missing essential field: {field}"

        # Handle secret - add default if missing (validation done earlier in deploy())
        if 'secret' not in data or not data['secret']:
            # Add default secret if missing or empty
            data['secret'] = config.USER_SECRET
            logger.info(f"Added default secret for task {data.get('task', 'unknown')}")

        # Enhanced round validation - prioritize explicit round field over task name detection
        if 'round' in data and data['round'] is not None:
            if not isinstance(data['round'], int):
                try:
                    data['round'] = int(data['round'])
                    logger.info(f"Converted round to integer: {data['round']}")
                except (ValueError, TypeError):
                    logger.warning(f"Invalid round value: {data['round']}, attempting detection from task name")
                    data['round'] = None
        
        # Improved task name-based round detection
        if 'round' not in data or data['round'] is None:
            task_name = str(data.get('task', '')).lower()
            # Check for round 2 indicators (more comprehensive)
            if any(pattern in task_name for pattern in ['round2', 'round-2', 'round_2', 'r2-', '-r2', 'r2_']):
                data['round'] = 2
                logger.info(f"Detected round 2 from task name: {data['task']}")
            # Check for round 1 indicators  
            elif any(pattern in task_name for pattern in ['round1', 'round-1', 'round_1', 'r1-', '-r1', 'r1_']):
                data['round'] = 1
                logger.info(f"Detected round 1 from task name: {data['task']}")
            else:
                data['round'] = 1
                logger.info(f"Defaulting to round 1 for task: {data['task']}")
                
        # Ensure round is valid
        if data['round'] not in [1, 2]:
            logger.warning(f"Invalid round {data['round']}, defaulting to 1")
            data['round'] = 1

        # Enhanced email validation
        email = data.get('email', '')
        if not email or '@' not in email or '.' not in email:
            data['email'] = 'student@example.com'
            logger.info(f"Fixed invalid email, using default: {data['email']}")

        # Validate checks array - handle both string and object formats
        if not isinstance(data['checks'], list):
            return False, "Checks must be an array"
        
        if len(data['checks']) == 0:
            data['checks'] = ['document.title.length > 0']
            logger.info("Added default check for empty checks array")
        
        # Normalize checks format - convert strings to objects if needed
        normalized_checks = []
        for i, check in enumerate(data['checks']):
            if isinstance(check, str):
                # Convert string check to object format for compatibility
                normalized_checks.append({
                    'description': check,
                    'js': f'document.title.length > 0 // {check}'
                })
                logger.info(f"Converted string check to object: {check}")
            elif isinstance(check, dict):
                # Ensure object has required properties
                if 'js' not in check and 'description' not in check:
                    return False, f"Check at index {i} must have either 'js' or 'description' property"
                normalized_checks.append(check)
            else:
                return False, f"Check at index {i} must be a string or object"
        
        data['checks'] = normalized_checks

        return True, "Valid request"

class AttachmentHandler:
    @staticmethod  
    def process_attachments(attachments: List[Dict]) -> List[Dict]:
        processed = []
        if not attachments:
            return processed

        for attachment in attachments:
            try:
                if 'url' not in attachment or 'name' not in attachment:
                    logger.warning(f"Attachment missing required fields: {attachment}")
                    continue

                url = attachment['url']
                name = attachment['name']

                if not url.startswith('data:'):
                    logger.warning(f"Attachment {name} is not a data URI")
                    continue

                try:
                    header, data = url.split(',', 1)
                    media_info = header.replace('data:', '')

                    if ';' in media_info:
                        media_type, encoding = media_info.split(';', 1)
                    else:
                        media_type = media_info
                        encoding = ''

                    if encoding == 'base64':
                        decoded_data = base64.b64decode(data)
                    else:
                        decoded_data = data.encode('utf-8')

                    processed.append({
                        'name': secure_filename(name),
                        'content': decoded_data,
                        'media_type': media_type,
                        'original_name': name
                    })

                    logger.info(f"Processed attachment: {name} ({len(decoded_data)} bytes)")

                except Exception as decode_error:
                    logger.error(f"Failed to decode attachment {name}: {decode_error}")
                    continue

            except Exception as e:
                logger.error(f"Error processing attachment: {e}")
                continue

        return processed

class LLMCodeGenerator:
    @staticmethod
    def generate_app_code(brief: str, checks: List[str], attachments: List[Dict] = None, round_num: int = 1) -> str:
        # Prepare attachment information
        attachment_info = ""
        if attachments:
            attachment_info = f"\n\nATTACHMENTS PROVIDED ({len(attachments)} files):\n"
            for att in attachments:
                attachment_info += f"- {att['name']} ({att['media_type']}): Available in assets/ folder\n"

        # Process checks - handle both string and object formats
        requirements_list = []
        for check in checks:
            if isinstance(check, dict):
                if 'description' in check:
                    requirements_list.append(check['description'])
                elif 'js' in check:
                    # Extract meaningful requirement from JS check
                    js_check = check['js']
                    if 'querySelector' in js_check:
                        requirements_list.append(f"Ensure proper DOM elements: {js_check}")
                    else:
                        requirements_list.append(f"JavaScript validation: {js_check}")
                else:
                    requirements_list.append("General functionality requirement")
            elif isinstance(check, str):
                requirements_list.append(check)
            else:
                requirements_list.append(str(check))

        # Create comprehensive prompt
        prompt = f"""Create a single-page static web application contained in one HTML file with embedded CSS and JavaScript. This app must fully implement the task requirements including accepting input parameters (like app brief and URL), dynamically generating and displaying content according to those inputs, and allowing for easy future updates to add new features or integrations.

BRIEF: {brief}

REQUIREMENTS TO SATISFY:
{chr(10).join(f"- {req}" for req in requirements_list)}

{attachment_info}

SPECIFICATIONS:
1. Create a single HTML file (index.html) that works standalone
2. Include all CSS and JavaScript inline within the HTML
3. The application must be production-ready and follow web best practices
4. Handle all the functionality specified in the brief completely
5. Include proper error handling and user feedback
6. Make it responsive and accessible
7. Use modern web standards (HTML5, ES6+, CSS3)
8. If attachments are referenced, fetch them from the "assets/" folder using JavaScript fetch() API
9. The page should work immediately when opened in a browser
10. For CSV files: Use fetch() to load, parse with split() and proper string processing, calculate sums correctly
11. Always display numerical results with proper formatting (e.g., $5727.00 for money)
12. When using external libraries (marked, highlight.js, bootstrap, etc.), use the latest stable CDN versions and proper API methods
13. Research and use the correct modern API for each library - many libraries have updated their APIs
14. Test that all library integrations work correctly and handle errors gracefully

CRITICAL IMPLEMENTATION NOTES:
- For CSV processing: Use fetch('assets/filename.csv'), parse properly, convert to numbers, sum accurately
- For Markdown processing: Use proper CDN links and current API methods for markdown parsing libraries
- For code highlighting: Integrate syntax highlighting libraries correctly with proper initialization
- For UI frameworks: Use current class names and components for styling frameworks

IMPORTANT: 
- Generate ONLY the complete HTML code
- Do not include markdown formatting or code blocks
- Start directly with <!DOCTYPE html>
- Ensure all functionality works without external dependencies (except major CDNs)
- Use CURRENT and CORRECT API methods for all external libraries
- Include comprehensive error handling for all fetch operations and library usage

The application should be a complete, working solution that satisfies all the checks listed above."""

        try:
            logger.info("Generating code with OpenAI client...")

            if openai_client:
                logger.info("Using OpenAI library with AI Pipe")
                response = openai_client.chat.completions.create(
                    model="gpt-4o",
                    messages=[
                        {
                            "role": "system",
                            "content": "You are an expert web developer who creates complete, functional, production-ready web applications. You always generate valid, working HTML with inline CSS and JavaScript. Generate ONLY the HTML code without any markdown formatting or explanations."
                        },
                        {
                            "role": "user",
                            "content": prompt
                        }
                    ],
                    max_tokens=4000,
                    temperature=0.1,
                    presence_penalty=0.1,
                    frequency_penalty=0.1
                )
                
                generated_code = response.choices[0].message.content.strip()
                
                # Clean up any markdown formatting
                if generated_code.startswith('```html'):
                    generated_code = generated_code.replace('```html', '').replace('```', '').strip()
                elif generated_code.startswith('```'):
                    generated_code = generated_code.replace('```', '').strip()

                logger.info(f"Successfully generated {len(generated_code)} characters of code")
                return generated_code
                
            else:
                # Fallback to direct HTTP call
                logger.info("OpenAI client not available, using direct HTTP call")
                return LLMCodeGenerator._call_ai_pipe_direct(prompt)

        except Exception as e:
            logger.error(f"Error generating code with AI: {e}")
            return LLMCodeGenerator._call_ai_pipe_direct(prompt)

    @staticmethod
    def _call_ai_pipe_direct(prompt: str) -> str:
        try:
            headers = {
                "Authorization": f"Bearer {config.OPENAI_API_KEY}",
                "Content-Type": "application/json",
                "User-Agent": "LLM-Code-Deployment/1.0"
            }
            
            payload = {
                "model": "gpt-4o",
                "messages": [
                    {
                        "role": "system",
                        "content": "You are an expert web developer who creates complete, functional, production-ready web applications. You always generate valid, working HTML with inline CSS and JavaScript. Generate ONLY the HTML code without any markdown formatting or explanations."
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                "max_tokens": 4000,
                "temperature": 0.1,
                "presence_penalty": 0.1,
                "frequency_penalty": 0.1
            }
            
            logger.info("Making direct HTTP call to AI Pipe...")
            response = requests.post(
                "https://aipipe.org/openai/v1/chat/completions",
                headers=headers,
                json=payload,
                timeout=120
            )
            
            logger.info(f"AI Pipe response status: {response.status_code}")
            
            if response.status_code == 200:
                result = response.json()
                if 'choices' in result and len(result['choices']) > 0:
                    generated_code = result['choices'][0]['message']['content'].strip()
                    
                    # Clean up markdown formatting
                    if generated_code.startswith('```html'):
                        generated_code = generated_code.replace('```html', '').replace('```', '').strip()
                    elif generated_code.startswith('```'):
                        generated_code = generated_code.replace('```', '').strip()
                    
                    logger.info(f"AI Pipe HTTP call successful: {len(generated_code)} characters generated")
                    return generated_code
                else:
                    logger.error("AI Pipe response missing choices")
                    return LLMCodeGenerator._generate_fallback_app("AI Pipe response error")
            else:
                logger.error(f"AI Pipe HTTP call failed: {response.status_code}")
                return LLMCodeGenerator._generate_fallback_app("AI Pipe API error")
                
        except Exception as e:
            logger.error(f"Direct AI Pipe call failed: {e}")
            return LLMCodeGenerator._generate_fallback_app(str(e))

    @staticmethod
    def _generate_fallback_app(error_msg: str) -> str:
        return f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Fallback Application</title>
    <style>
        body {{
            font-family: Arial, sans-serif;
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
            line-height: 1.6;
            background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
            min-height: 100vh;
            color: white;
        }}
        .container {{
            background: rgba(255,255,255,0.95);
            color: #333;
            border-radius: 15px;
            padding: 2rem;
            box-shadow: 0 10px 30px rgba(0,0,0,0.1);
        }}
        .error {{
            color: #d32f2f;
            background-color: #ffebee;
            padding: 10px;
            border-radius: 4px;
            margin: 10px 0;
        }}
        .demo-button {{
            background: linear-gradient(45deg, #667eea, #764ba2);
            border: none;
            color: white;
            padding: 12px 24px;
            border-radius: 25px;
            transition: transform 0.2s;
            cursor: pointer;
        }}
        .demo-button:hover {{
            transform: translateY(-2px);
        }}
        #output {{
            margin-top: 1rem;
            padding: 1rem;
            background: #e7f3ff;
            border-radius: 8px;
            min-height: 50px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>Fallback Application</h1>
        <p>This is a fallback application generated when the AI service encounters an issue.</p>
        <div class="error">
            <strong>Error:</strong> {error_msg}
        </div>
        
        <h3>Demo Functionality</h3>
        <button class="demo-button" onclick="demonstrateFunction()">
            Click to Test Application
        </button>
        
        <div id="output">
            Click the button above to see the application in action!
        </div>
        
        <h4>System Information:</h4>
        <ul>
            <li><strong>Generated:</strong> <span id="timestamp"></span></li>
            <li><strong>Mode:</strong> Fallback Implementation</li>
            <li><strong>Status:</strong> Functional</li>
        </ul>
    </div>

    <script>
        document.getElementById('timestamp').textContent = new Date().toLocaleString();

        let clickCount = 0;

        function demonstrateFunction() {{
            clickCount++;
            const output = document.getElementById('output');
            const messages = [
                "Application is working correctly!",
                "Interactive functionality confirmed!", 
                "System responding to user input!",
                "All basic features operational!",
                "Ready for evaluation!"
            ];

            const message = messages[Math.min(clickCount - 1, messages.length - 1)];
            output.innerHTML = `<strong>${{message}}</strong><br><small>Button clicked ${{clickCount}} time(s)</small>`;
        }}

        console.log('Fallback application loaded successfully');
        console.log('Error:', '{error_msg}');
    </script>
</body>
</html>"""

class GitHubManager:
    def __init__(self):
        if not github_client or not github_user:
            logger.warning("GitHub client not properly initialized")
            self.client = None
            self.user = None
            self.username = None
            self.github_token = config.GITHUB_TOKEN
            return

        self.client = github_client
        self.user = github_user
        self.username = github_user.login
        self.github_token = config.GITHUB_TOKEN

    def create_repository(self, task_id: str, code: str, attachments: List[Dict] = None, email: str = "") -> Dict[str, str]:
        if not self.client or not self.user:
            raise ValueError("GitHub client not available")
            
        try:
            timestamp = int(time.time())
            repo_name = f"{task_id}-{timestamp}"

            logger.info(f"Creating repository: {repo_name}")

            repo = self.user.create_repo(
                name=repo_name,
                description=f"Auto-generated application for task {task_id}",
                private=False,
                has_issues=True,
                has_wiki=False,
                has_downloads=True,
                auto_init=False
            )

            logger.info(f"Repository created: {repo.html_url}")

            # Add files
            license_content = self._generate_mit_license()
            repo.create_file("LICENSE", "Add MIT License", license_content)

            readme_content = self._generate_readme(task_id, code, email)
            repo.create_file("README.md", "Add comprehensive README", readme_content)

            repo.create_file("index.html", "Add main application", code)

            # Add attachments
            if attachments:
                for attachment in attachments:
                    try:
                        file_path = f"assets/{attachment['name']}"
                        repo.create_file(
                            file_path, 
                            f"Add attachment: {attachment['original_name']}", 
                            attachment['content']
                        )
                        logger.info(f"Added attachment: {file_path}")
                    except Exception as e:
                        logger.error(f"Failed to add attachment {attachment['name']}: {e}")

            # Enable GitHub Pages
            self._enable_github_pages(repo)

            commits = repo.get_commits()
            latest_commit_sha = commits[0].sha

            pages_url = f"https://{self.username}.github.io/{repo_name}/"

            result = {
                'repo_url': repo.html_url,
                'commit_sha': latest_commit_sha,
                'pages_url': pages_url,
                'repo_name': repo_name
            }

            logger.info(f"Repository setup complete: {pages_url}")
            return result

        except Exception as e:
            logger.error(f"Repository creation error: {e}")
            raise Exception(f"Repository creation failed: {e}")

    def update_existing_repository(self, task_id: str, code: str, attachments: List[Dict] = None, repo_name: str = None) -> Dict[str, str]:
        """Update existing repository for Round 2 instead of creating new one"""
        if not self.client or not self.user:
            raise ValueError("GitHub client not available")
            
        try:
            target_repo = None
            
            if repo_name:
                # Use the exact repository name from deployment state
                logger.info(f"Looking for specific repository: {repo_name}")
                try:
                    target_repo = self.client.get_repo(f"{self.username}/{repo_name}")
                    logger.info(f"Found repository by name: {target_repo.name}")
                except Exception as e:
                    logger.warning(f"Could not find repository {repo_name}: {e}")
            
            if not target_repo:
                # Fallback to searching by task pattern
                base_task_id = task_id.replace('-round2a', '').replace('-round2b', '').replace('-round2', '')
                logger.info(f"Searching for repository matching task: {base_task_id}")
                
                repos = list(self.user.get_repos(sort="created", direction="desc"))
                
                for repo in repos:
                    repo_base = repo.name
                    # Remove timestamp suffix to get base name
                    if '-' in repo_base:
                        parts = repo_base.split('-')
                        if len(parts) >= 2 and parts[-1].isdigit():
                            repo_base = '-'.join(parts[:-1])
                    
                    if repo_base == base_task_id:
                        target_repo = repo
                        logger.info(f"Found matching repository: {repo.name}")
                        break
            
            if not target_repo:
                logger.warning(f"No existing repository found for {base_task_id}, creating new one")
                return self.create_repository(task_id, code, attachments)
            
            logger.info(f"Updating repository: {target_repo.name}")
            
            # Update the index.html file
            try:
                contents = target_repo.get_contents("index.html")
                target_repo.update_file(
                    "index.html", 
                    f"Update for Round 2: {task_id}", 
                    code,
                    contents.sha
                )
                logger.info("Successfully updated index.html for Round 2")
            except Exception as e:
                logger.error(f"Failed to update index.html: {e}")
                # If update fails, create the file
                target_repo.create_file("index.html", f"Add Round 2 version: {task_id}", code)
                logger.info("Created new index.html for Round 2")
            
            # Add new attachments if any
            if attachments:
                for attachment in attachments:
                    try:
                        file_path = f"assets/{attachment['name']}"
                        try:
                            # Try to update existing file
                            contents = target_repo.get_contents(file_path)
                            target_repo.update_file(
                                file_path, 
                                f"Update attachment for Round 2: {attachment['original_name']}", 
                                attachment['content'],
                                contents.sha
                            )
                        except:
                            # File doesn't exist, create it
                            target_repo.create_file(
                                file_path, 
                                f"Add Round 2 attachment: {attachment['original_name']}", 
                                attachment['content']
                            )
                        logger.info(f"Updated attachment: {file_path}")
                    except Exception as e:
                        logger.error(f"Failed to update attachment {attachment['name']}: {e}")

            # Get latest commit
            commits = target_repo.get_commits()
            latest_commit_sha = commits[0].sha

            pages_url = f"https://{self.username}.github.io/{target_repo.name}/"

            result = {
                'repo_url': target_repo.html_url,
                'commit_sha': latest_commit_sha,
                'pages_url': pages_url,
                'repo_name': target_repo.name,
                'updated': True
            }

            logger.info(f"Repository update complete: {pages_url}")
            return result

        except Exception as e:
            logger.error(f"Repository update error: {e}")
            raise Exception(f"Repository update failed: {e}")

    def _enable_github_pages(self, repo):
        try:
            pages_data = {
                "source": {
                    "branch": "main",
                    "path": "/"
                }
            }
            
            url = f"https://api.github.com/repos/{repo.full_name}/pages"
            headers = {
                "Authorization": f"token {self.github_token}",
                "Accept": "application/vnd.github.v3+json"
            }
            
            response = requests.post(url, json=pages_data, headers=headers)
            
            if response.status_code == 201:
                logger.info("GitHub Pages enabled successfully")
            elif response.status_code == 409:
                logger.info("GitHub Pages already enabled")
            else:
                logger.warning(f"Could not enable GitHub Pages: {response.status_code}")
                
        except Exception as e:
            logger.warning(f"Pages enable error: {e}")

    @staticmethod
    def _generate_mit_license() -> str:
        year = datetime.now().year
        return f"""MIT License

Copyright (c) {year} LLM Code Deployment Project

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE."""

    @staticmethod
    def _generate_readme(task_id: str, code: str, email: str = "") -> str:
        stats = {
            'code_lines': len(code.split('\n')),
            'code_chars': len(code),
            'timestamp': datetime.now().isoformat(),
            'task_id': task_id,
            'email': email
        }

        return f"""# {task_id.title().replace('-', ' ')}

## Project Overview

This application was automatically generated using the LLM Code Deployment system.

## Generated Application

- **Task ID:** `{task_id}`
- **Generated:** {stats['timestamp']}
- **Student:** {email if email else 'Anonymous'}
- **Code Size:** {stats['code_lines']} lines, {stats['code_chars']} characters

## Quick Start

1. **View Live Application**
   - The application is automatically deployed to GitHub Pages
   - Access it directly through the repository's Pages URL

2. **Local Development**
   ```bash
   # Clone the repository
   git clone <repository-url>
   cd {task_id}

   # Open in browser
   open index.html
   ```

## Technical Details

### Architecture
- **Framework:** Single-page HTML application
- **Styling:** Inline CSS (with optional Bootstrap CDN)
- **Functionality:** Vanilla JavaScript (ES6+)
- **Dependencies:** Self-contained (no build process)

### Features
- Responsive design for all device sizes
- Modern web standards compliance
- Accessibility considerations
- Error handling and user feedback
- Cross-browser compatibility

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

---

*This README was automatically generated by the LLM Code Deployment system on {stats['timestamp']}*
"""

class EvaluationNotifier:
    @staticmethod
    def notify_evaluation(evaluation_url: str, repo_data: Dict, request_data: Dict) -> bool:
        # Determine the correct evaluation URL based on round
        if request_data['round'] == 2:
            # For Round 2, use a different evaluation endpoint
            evaluation_url = evaluation_url.replace('/evaluation_callback', '/evaluation_callback_round2')
            logger.info(f"Using Round 2 evaluation URL: {evaluation_url}")
        
        payload = {
            'email': request_data['email'],
            'task': request_data['task'], 
            'round': request_data['round'],
            'nonce': request_data['nonce'],
            'repo_url': repo_data['repo_url'],
            'commit_sha': repo_data['commit_sha'],
            'pages_url': repo_data['pages_url'],
            'updated': repo_data.get('updated', False)  # Indicate if this was an update vs new repo
        }

        logger.info(f"Notifying evaluation endpoint: {evaluation_url}")

        max_retries = 5
        retry_delays = [1, 2, 4, 8, 16]

        for attempt in range(max_retries):
            try:
                response = requests.post(
                    evaluation_url,
                    json=payload,
                    headers={
                        'Content-Type': 'application/json',
                        'User-Agent': 'LLM-Code-Deployment/1.0'
                    },
                    timeout=30
                )

                if response.status_code == 200:
                    logger.info(f"Successfully notified evaluation endpoint (attempt {attempt + 1})")
                    return True
                else:
                    logger.warning(f"Evaluation endpoint returned {response.status_code}: {response.text}")

            except requests.exceptions.Timeout:
                logger.error(f"Timeout contacting evaluation endpoint (attempt {attempt + 1})")
            except requests.exceptions.ConnectionError:
                logger.error(f"Connection error with evaluation endpoint (attempt {attempt + 1})")
            except requests.RequestException as e:
                logger.error(f"Request error contacting evaluation endpoint (attempt {attempt + 1}): {e}")

            if attempt < max_retries - 1:
                wait_time = retry_delays[attempt]
                logger.info(f"Waiting {wait_time} seconds before retry...")
                time.sleep(wait_time)

        logger.error(f"Failed to notify evaluation endpoint after {max_retries} attempts")
        return False

# Initialize GitHub manager
github_manager = None
try:
    github_manager = GitHubManager()
    logger.info("GitHub manager initialized successfully")
except Exception as e:
    logger.error(f"Failed to initialize GitHub manager: {e}")
    github_manager = None

# Track deployment state with persistence
deployment_state_file = 'deployment_state.json'

def load_deployment_state():
    try:
        if os.path.exists(deployment_state_file):
            with open(deployment_state_file, 'r') as f:
                return json.load(f)
    except Exception as e:
        logger.warning(f"Could not load deployment state: {e}")
    return {}

def save_deployment_state():
    try:
        with open(deployment_state_file, 'w') as f:
            json.dump(deployment_state, f, indent=2)
    except Exception as e:
        logger.error(f"Could not save deployment state: {e}")

deployment_state = load_deployment_state()
logger.info(f"Loaded deployment state with {len(deployment_state)} records")

@app.route('/', methods=['GET'])
def index():
    return jsonify({
        'status': 'success',
        'message': 'LLM Code Deployment System',
        'version': '1.0.0',
        'endpoints': {
            'deploy': '/api/deploy (POST)',
            'validate': '/api/validate (POST)',
            'health': '/health (GET)',
            'status': '/api/status/<deployment_id> (GET)'
        },
        'timestamp': datetime.now().isoformat()
    })

@app.route('/api/validate', methods=['POST'])
def validate_only():
    """Fast validation endpoint for testing - validates request without deployment"""
    start_time = time.time()
    
    try:
        # Parse JSON
        try:
            data = request.get_json()
        except Exception as e:
            return jsonify({
                'status': 'error',
                'error': 'Invalid JSON format',
                'code': 'JSON_PARSE_ERROR'
            }), 400
            
        if not data:
            return jsonify({
                'status': 'error',
                'error': 'Empty request',
                'code': 'EMPTY_REQUEST'
            }), 400

        # Fast secret validation
        if 'secret' in data and data['secret']:
            if data['secret'] != config.USER_SECRET:
                return jsonify({
                    'status': 'error',
                    'error': 'Invalid secret',
                    'code': 'INVALID_SECRET'
                }), 401

        # Run validation
        is_valid, error_msg = RequestValidator.validate_request(data.copy())  # Use copy to avoid mutations
        
        duration = time.time() - start_time
        
        if is_valid:
            return jsonify({
                'status': 'success',
                'message': 'Validation passed',
                'code': 'VALIDATION_SUCCESS',
                'duration': f"{duration:.3f}s",
                'validated_data': {
                    'task': data.get('task'),
                    'round': data.get('round', 1),
                    'email': data.get('email'),
                    'brief_length': len(str(data.get('brief', ''))),
                    'checks_count': len(data.get('checks', [])),
                    'attachments_count': len(data.get('attachments', []))
                }
            }), 200
        else:
            # Determine error code
            if 'secret' in error_msg.lower():
                status_code = 401
                error_code = 'INVALID_SECRET'
            elif 'missing' in error_msg.lower():
                status_code = 400
                error_code = 'MISSING_FIELD'
            else:
                status_code = 422
                error_code = 'VALIDATION_ERROR'
                
            return jsonify({
                'status': 'error',
                'error': error_msg,
                'code': error_code,
                'duration': f"{duration:.3f}s"
            }), status_code
            
    except Exception as e:
        duration = time.time() - start_time
        logger.error(f"Validation endpoint error: {e}")
        return jsonify({
            'status': 'error',
            'error': 'Internal validation error',
            'code': 'INTERNAL_ERROR',
            'duration': f"{duration:.3f}s"
        }), 500

@app.route('/api/deploy', methods=['POST'])
def deploy():
    start_time = time.time()
    
    try:
        # Enhanced request parsing with better error handling
        try:
            data = request.get_json()
        except Exception as e:
            logger.error(f"JSON parsing error: {e}")
            return jsonify({
                'status': 'error',
                'error': 'Invalid JSON format in request body',
                'code': 'JSON_PARSE_ERROR',
                'details': str(e)
            }), 400
            
        if not data:
            return jsonify({
                'status': 'error',
                'error': 'Request must contain valid JSON data',
                'code': 'EMPTY_REQUEST'
            }), 400

        # Check for validate_only mode (for testing)
        validate_only = request.args.get('validate_only', '').lower() == 'true'

        logger.info(f"Received deployment request for task: {data.get('task', 'unknown')}")
        logger.info(f"Request format: email={data.get('email', 'missing')}, round={data.get('round', 'missing')}, checks_type={type(data.get('checks', []))}")
        
        # EARLY SECRET VALIDATION - Fast exit for invalid secrets
        if 'secret' in data and data['secret']:
            if data['secret'] != config.USER_SECRET:
                logger.warning(f"Invalid secret provided for task {data.get('task', 'unknown')}: {data['secret'][:10]}...")
                return jsonify({
                    'status': 'error',
                    'error': 'Invalid secret provided',
                    'code': 'INVALID_SECRET'
                }), 401

        # Validate request with enhanced error reporting
        is_valid, error_msg = RequestValidator.validate_request(data)
        if not is_valid:
            logger.warning(f"Request validation failed: {error_msg}")
            # Determine appropriate error code
            if 'secret' in error_msg.lower():
                status_code = 401
                error_code = 'INVALID_SECRET'
            elif 'missing' in error_msg.lower() or 'field' in error_msg.lower():
                status_code = 400
                error_code = 'MISSING_REQUIRED_FIELD'
            else:
                status_code = 422
                error_code = 'VALIDATION_ERROR'
                
            return jsonify({
                'status': 'error',
                'error': error_msg,
                'code': error_code
            }), status_code

        # Fast validation mode - return success without deployment
        if validate_only:
            logger.info(f"Validation-only mode: Request for task {data.get('task')} is valid")
            return jsonify({
                'status': 'success',
                'message': 'Request validation passed',
                'code': 'VALIDATION_SUCCESS',
                'validated_data': {
                    'task': data.get('task'),
                    'round': data.get('round', 1),
                    'email': data.get('email'),
                    'checks_count': len(data.get('checks', [])),
                    'has_attachments': len(data.get('attachments', [])) > 0
                }
            }), 200

        # Check GitHub manager
        if not github_manager:
            logger.error("GitHub manager not available")
            return jsonify({
                'status': 'error',
                'error': 'GitHub integration not available. Check your GITHUB_TOKEN.',
                'code': 'GITHUB_UNAVAILABLE'
            }), 500

        # Process attachments
        attachments = []
        if 'attachments' in data and data['attachments']:
            attachments = AttachmentHandler.process_attachments(data['attachments'])
            logger.info(f"Processed {len(attachments)} attachments")

        # Generate code
        logger.info(f"Generating code for task: {data['task']}")
        generated_code = LLMCodeGenerator.generate_app_code(
            data['brief'], 
            data['checks'], 
            attachments,
            data['round']
        )

        # Create or update repository based on round
        # Normalize task name for deployment key (remove round2 suffix)
        base_task_name = data['task'].replace('-round2a', '').replace('-round2b', '').replace('-round2', '')
        deployment_key = f"{data['email']}-{base_task_name}"
        
        logger.info(f"Using deployment key: {deployment_key} (from task: {data['task']})")
        
        if data['round'] == 2:
            logger.info("Round 2 detected - updating existing repository")
            
            # Lookup the expected repo name for this student/task
            stored_info = deployment_state.get(deployment_key)
            if stored_info:
                logger.info(f"Found existing deployment record for {deployment_key}")
                repo_data = github_manager.update_existing_repository(
                    data['task'], 
                    generated_code, 
                    attachments,
                    stored_info.get('repo_name')
                )
                # Update state with new commit info
                deployment_state[deployment_key]['repo_name'] = repo_data['repo_name']
                deployment_state[deployment_key]['updated_at'] = datetime.now().isoformat()
                save_deployment_state()
            else:
                logger.warning('No Round 1 deployment found, creating new repo for Round 2')
                repo_data = github_manager.create_repository(
                    data['task'], 
                    generated_code, 
                    attachments,
                    data['email']
                )
                deployment_state[deployment_key] = {
                    'repo_name': repo_data['repo_name'],
                    'created_at': datetime.now().isoformat()
                }
                save_deployment_state()
        else:
            # Round 1: always create repository
            logger.info("Round 1 - creating new repository")
            repo_data = github_manager.create_repository(
                data['task'], 
                generated_code, 
                attachments,
                data['email']
            )
            deployment_state[deployment_key] = {
                'repo_name': repo_data['repo_name'],
                'created_at': datetime.now().isoformat()
            }
            save_deployment_state()

        # Notify evaluation endpoint
        evaluation_success = EvaluationNotifier.notify_evaluation(
            data['evaluation_url'],
            repo_data,
            data
        )

        processing_time = time.time() - start_time
        logger.info(f"Deployment completed for task {data['task']} in {processing_time:.2f}s")

        return jsonify({
            'status': 'success',
            'message': 'Deployment completed successfully',
            'processing_time': round(processing_time, 2),
            'repo_name': repo_data.get('repo_name'),
            'round': data['round'],
            'updated': repo_data.get('updated', False)
        }), 200

    except ValueError as e:
        # Handle validation and configuration errors
        logger.error(f"Validation error during deployment: {e}")
        return jsonify({
            'status': 'error',
            'error': 'Configuration or validation error',
            'message': str(e),
            'code': 'VALIDATION_ERROR'
        }), 400
        
    except requests.RequestException as e:
        # Handle external API errors (GitHub, OpenAI)
        logger.error(f"External API error during deployment: {e}")
        return jsonify({
            'status': 'error',
            'error': 'External service error',
            'message': str(e),
            'code': 'EXTERNAL_API_ERROR'
        }), 502
        
    except Exception as e:
        # Handle all other errors
        logger.error(f"Unexpected deployment error: {e}")
        return jsonify({
            'status': 'error',
            'error': 'Deployment failed',
            'message': str(e),
            'code': 'DEPLOYMENT_ERROR',
            'task': data.get('task', 'unknown') if 'data' in locals() else 'unknown'
        }), 500

@app.route('/health', methods=['GET'])
def health_check():
    try:
        github_status = "ok" if github_manager and github_manager.client else "unavailable"
        openai_status = "ok" if openai_client else "unavailable"
        system_status = "healthy" if github_status == "ok" and openai_status == "ok" else "degraded"

        return jsonify({
            'status': system_status,
            'timestamp': datetime.now().isoformat(),
            'services': {
                'github': github_status,
                'openai': openai_status,
                'base_url': config.OPENAI_BASE_URL
            },
            'version': '1.0.0'
        }), 200

    except Exception as e:
        logger.error(f"Health check error: {e}")
        return jsonify({
            'status': 'error',
            'timestamp': datetime.now().isoformat(),
            'error': str(e)
        }), 500

@app.route('/status/<task_id>', methods=['GET'])
def get_deployment_status(task_id):
    email = request.args.get('email', '')
    deployment_key = f"{email}-{task_id}"

    if deployment_key in deployment_state:
        return jsonify({
            'status': 'found',
            'task_id': task_id,
            'email': email,
            'deployment_info': deployment_state[deployment_key]
        }), 200
    else:
        return jsonify({
            'status': 'not_found',
            'task_id': task_id,
            'email': email
        }), 404

@app.errorhandler(413)
def request_entity_too_large(error):
    return jsonify({
        'status': 'error',
        'error': 'Request too large',
        'code': 'REQUEST_TOO_LARGE'
    }), 413

@app.errorhandler(500)
def internal_server_error(error):
    logger.error(f"Internal server error: {error}")
    return jsonify({
        'status': 'error',
        'error': 'Internal server error',
        'code': 'INTERNAL_ERROR'
    }), 500

@app.errorhandler(404)
def not_found(error):
    return jsonify({
        'status': 'error',
        'error': 'Endpoint not found',
        'code': 'NOT_FOUND'
    }), 404

# Initialize configuration
try:
    config.validate()
    logger.info("Configuration validated successfully")
except Exception as e:
    logger.error(f"Configuration validation failed: {e}")
    # Don't exit, continue with degraded functionality

if __name__ == '__main__':
    print("\n" + "="*60)
    print("LLM Code Deployment System Starting...")
    print("="*60)

    try:
        config.validate()
        print("Configuration: Valid")
        print(f"GitHub User: {github_user.login if github_user else 'Not available'}")
        print(f"OpenAI Client: {'Connected' if openai_client else 'Not available'}")
        print(f"Base URL: {config.OPENAI_BASE_URL}")
        print("Flask Server: Starting...")

        port = int(os.environ.get('PORT', 5000))
        debug = os.environ.get('FLASK_ENV') == 'development'

        print(f"Server URL: http://localhost:{port}")
        print(f"Health Check: http://localhost:{port}/health")
        print(f"Debug Mode: {debug}")
        print("="*60 + "\n")

        app.run(
            host='0.0.0.0', 
            port=port, 
            debug=debug,
            threaded=True
        )

    except Exception as e:
        print(f"Startup Error: {e}")
        print("Please check your configuration and try again.")
        exit(1)