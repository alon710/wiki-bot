# WikiBot - Wikipedia Facts WhatsApp Bot

A cost-optimized WhatsApp bot that sends daily Wikipedia facts in English and Hebrew using AI summarization.

## Features

- 🤖 **AI-Powered Summarization**: Uses OpenRouter to create engaging daily facts from Wikipedia articles
- 🌍 **Multi-Language Support**: English and Hebrew Wikipedia articles
- 💰 **Cost-Optimized**: Generates one fact per language per day and broadcasts to all users
- 📅 **Scheduled Distribution**: Daily facts sent at configurable time using APScheduler
- 🗄️ **PostgreSQL Database**: SQLModel-based data persistence with proper indexing
- 🔒 **Secure**: Structured logging, environment-based configuration, and security headers
- 📊 **Admin Dashboard**: Health checks, statistics, and manual controls

## Architecture

### Layered Structure
- **API Layer** (`src/api/`): FastAPI routes and middleware
- **Service Layer** (`src/services/`): Business logic (Wikipedia, AI, WhatsApp, Scheduler)
- **Data Access Layer** (`src/data_access/`): Database client and repositories
- **Models** (`src/models/`): SQLModel/Pydantic data models

### Key Components
- **Wikipedia Service**: Fetches random articles with content filtering
- **AI Service**: OpenRouter integration for fact summarization
- **WhatsApp Service**: Twilio WhatsApp API integration for message delivery
- **Scheduler Service**: APScheduler with PostgreSQL job store
- **Database Client**: SQLModel with PostgreSQL backend

## Prerequisites

- Python 3.9+
- PostgreSQL 12+
- OpenRouter API key
- Twilio Account SID and Auth Token

## Installation

### Option 1: Docker (Recommended)

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd wiki-bot
   ```

2. **Set up environment variables**:
   ```bash
   cp .env.example .env
   # Edit .env with your configuration (especially API keys)
   ```

3. **Build and run with Docker**:
   ```bash
   # Build the image
   docker build -t wikibot .
   
   # Run the container
   docker run -p 80:80 --env-file .env wikibot
   ```

### Option 2: Local Installation

1. **Clone the repository**:
   ```bash
   git clone <repository-url>
   cd wiki-bot
   ```

2. **Install dependencies with uv**:
   ```bash
   uv sync
   ```

3. **Set up environment variables**:
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

4. **Configure PostgreSQL**:
   ```bash
   # Create database
   createdb wikibot
   ```

5. **Initialize database**:
   ```bash
   python scripts/setup_database.py
   ```

## Configuration

Edit `.env` file with your settings:

```env
# Environment
ENV_ID=local

# Database (PostgreSQL)
DATABASE_URL=postgresql://username:password@localhost:5432/wikibot

# Twilio WhatsApp API
TWILIO_ACCOUNT_SID=your-twilio-account-sid
TWILIO_AUTH_TOKEN=your-twilio-auth-token
TWILIO_WHATSAPP_FROM=whatsapp:+14155238886

# OpenRouter
OPENROUTER_API_KEY=your-openrouter-api-key
OPENROUTER_MODEL=openai/gpt-4o-mini

# Scheduler (UTC time)
SCHEDULER_FACT_GENERATION_HOUR=9
SCHEDULER_FACT_GENERATION_MINUTE=0

# Server
SERVER_HOST=0.0.0.0
SERVER_PORT=80
```

## Usage

### Start the Application

```bash
python main.py
```

Or with uvicorn directly:
```bash
uvicorn main:app --host 0.0.0.0 --port 80 --reload
```

### WhatsApp Commands

Users can interact with the bot using these commands:
- `/start` or `/subscribe` - Subscribe to daily facts
- `/stop` or `/unsubscribe` - Unsubscribe from daily facts  
- `/english` or `/en` - Switch to English facts
- `/hebrew` or `/he` or `/עברית` - Switch to Hebrew facts
- `/help` or `/h` - Show help message

### Admin Endpoints

- `GET /` - Basic application info
- `GET /health` - Simple health check
- `GET /admin/health` - Comprehensive health check with all service status
- `GET /admin/stats` - System statistics (users, facts, scheduler status)

### Webhook Setup

Configure your Twilio WhatsApp webhook to send messages to:
- `POST /webhook/whatsapp` - Handle incoming WhatsApp messages
- `GET /webhook/whatsapp` - Webhook verification (optional for Twilio)

In your Twilio Console, set the webhook URL to: `https://yourdomain.com/webhook/whatsapp`

## Development

### Project Structure

```
wiki-bot/
├── src/
│   ├── api/
│   │   ├── routes/          # API endpoints
│   │   └── middleware.py    # Request middleware
│   ├── services/            # Business logic
│   ├── data_access/         # Database layer
│   ├── models/              # SQLModel definitions
│   ├── config/              # Configuration
│   └── utils/               # Utilities
├── scripts/                 # Setup and maintenance scripts
├── tests/                   # Test files
├── main.py                  # Application entry point
├── requirements.txt         # Dependencies
└── README.md               # This file
```

### Database Schema

#### Users Table
- `id` (Primary Key)
- `phone` (Unique, Indexed)
- `language` (en/he)
- `subscribed` (Boolean)
- `created_at`, `updated_at`

#### Daily Facts Table
- `id` (Primary Key)
- `date` (Indexed)
- `language` (Indexed)
- `original_title`, `original_url`
- `summary` (AI-generated)
- `created_at`
- Unique constraint on (date, language)

#### Message Logs Table
- `id` (Primary Key)
- `to` (Phone number, Indexed)
- `content`, `message_type`, `status`
- `external_id`, `metadata`
- `created_at`, `updated_at`

### Logging

The application uses structured logging with no string interpolation:

```python
# Good ✅
logger.info("User created", phone=user.phone, language=user.language)

# Bad ❌ 
logger.info(f"User {user.phone} created with language {user.language}")
```

### Cost Optimization Strategy

1. **Single Daily Generation**: One fact per language per day
2. **Batch Distribution**: Send to all users simultaneously
3. **Smart Caching**: Store generated facts to avoid re-generation
4. **Efficient Scheduling**: Off-peak generation times
5. **API Rate Limiting**: Respectful API usage patterns

## Testing

```bash
# Run tests
pytest

# Run with coverage
pytest --cov=src tests/

# Test specific service
python -m pytest tests/test_wikipedia_service.py
```

## Deployment

### Docker

The application includes a production-ready Dockerfile:

```bash
# Build the image
docker build -t wikibot .

# Run with environment variables
docker run -p 80:80 --env-file .env wikibot

# Or run with individual environment variables
docker run -p 80:80 \
  -e DATABASE_URL="postgresql://user:pass@host:5432/wikibot" \
  -e TWILIO_ACCOUNT_SID="your-account-sid" \
  -e TWILIO_AUTH_TOKEN="your-auth-token" \
  -e OPENROUTER_API_KEY="your-api-key" \
  wikibot
```

**Docker Features:**
- Multi-stage build for optimized image size
- Non-root user for security
- Health checks included
- Uses uv for faster dependency installation

### Environment Variables for Production

```env
ENV_ID=production
DATABASE_URL=postgresql://user:pass@host:5432/wikibot
TWILIO_ACCOUNT_SID=your-production-account-sid
TWILIO_AUTH_TOKEN=your-production-auth-token
TWILIO_WHATSAPP_FROM=whatsapp:+14155238886
OPENROUTER_API_KEY=your-production-key
SERVER_HOST=0.0.0.0
SERVER_PORT=80
LOG_LEVEL=INFO
```

## Monitoring

- Health checks: `/health` and `/admin/health`
- Structured logs for monitoring systems
- Scheduler job monitoring via `/admin/jobs`
- Database connection monitoring
- API service health checks

## Troubleshooting

### Common Issues

1. **Database Connection Failed**
   - Check PostgreSQL is running
   - Verify DATABASE_URL format
   - Ensure database exists

2. **Scheduler Not Starting**
   - Check database connectivity
   - Verify APScheduler table permissions

3. **WhatsApp Messages Not Sending**
   - Verify Twilio Account SID and Auth Token
   - Check Twilio WhatsApp sandbox configuration
   - Ensure phone numbers are in correct format (with country codes)
   - Check webhook configuration in Twilio Console
   - Review message logs and Twilio error codes

4. **AI Summarization Failing**
   - Verify OpenRouter API key
   - Check model availability and pricing
   - Review OpenRouter error logs
   - Ensure sufficient credits in OpenRouter account

5. **Docker Container Issues**
   - Check that all required environment variables are set
   - Ensure PostgreSQL is accessible from the container
   - View container logs: `docker logs <container-name>`
   - Test health endpoint: `curl http://localhost:80/health`
   - For database connectivity, ensure DATABASE_URL points to accessible host

### Logs

Check application logs for detailed error information:
```bash
tail -f logs/wikibot.log
```

## OpenRouter Models

The bot supports various AI models through OpenRouter:

### Recommended Models
- `openai/gpt-4o-mini` - Cost-effective, good quality
- `anthropic/claude-3-haiku` - Fast, multilingual support
- `google/gemini-pro` - Competitive pricing
- `meta-llama/llama-3.1-8b-instruct` - Open source option

### Model Selection Considerations
- **Cost**: Compare pricing per token across models
- **Quality**: Test summarization quality for your use case
- **Speed**: Consider response time for user experience
- **Language Support**: Ensure Hebrew language support

## License

This project is licensed under the MIT License.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make changes with proper tests
4. Ensure all tests pass
5. Submit a pull request

## Support

For issues and questions:
- Check the troubleshooting section
- Review logs for error details
- Open an issue on GitHub# wiki-bot
