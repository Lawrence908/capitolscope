# CapitolScope

Congressional trading transparency and analysis platform.

## Overview

CapitolScope is a FastAPI-based platform for tracking and analyzing congressional trading activities, providing transparency and insights into stock transactions by members of Congress.

## Features

- **Congressional Trading Data**: Track trades by members of Congress
- **Member Profiles**: Detailed information about congressional members
- **Portfolio Analysis**: Analyze trading patterns and portfolio performance
- **API Access**: RESTful API with comprehensive documentation
- **Real-time Data**: Up-to-date trading information

## Quick Start

### Using Docker Compose

```bash
# Start the application
docker-compose -p capitolscope-dev up --build

# Access the API
curl http://localhost:8000/
```

### Local Development

```bash
# Install dependencies
uv pip install -e .

# Run the application
cd app/src
python -m uvicorn main:app --reload
```

## API Documentation

When running in development mode, access the interactive API documentation at:

- **Swagger UI**: http://localhost:8000/docs
- **ReDoc**: http://localhost:8000/redoc

## Environment Setup

Copy the `.env.example` file to `.env` and configure your environment variables:

```bash
cp .env.example .env
```

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Submit a pull request

## License

MIT License - see LICENSE file for details.
