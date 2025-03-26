# Japanese Text Translation API

A FastAPI-based service for Japanese text translation and processing, featuring romaji conversion, furigana generation, text slugification, and integration with OpenRouter AI translation services.

## Features

- 🔤 Romaji conversion (Japanese text to Latin alphabet)
- 📝 Furigana generation (reading aids for kanji)
- 🔗 Text slugification for URL-friendly strings
- 🔍 Japanese text tokenization
- 📰 News fetching with translation
- 🌐 AI-powered translation via OpenRouter
- ⚡ Rate limiting and authentication

## Requirements

- Python 3.10 or higher
- Docker (optional, for containerized deployment)

## Installation

### Local Setup

1. Clone the repository
2. Create a virtual environment (recommended):

```bash
python -m venv .venv
source .venv/bin/activate  # For Unix
# or
.venv\Scripts\activate  # For Windows
```

3. Install dependencies:

```bash
pip install -r requirements.txt
python -m unidic download
```

### Docker Setup

Build and run using Docker:

```bash
docker build -t translator .
docker run -p 8000:3097 -e AUTHENTICATION_KEY=your-key -e NEWSAPI_KEY=your-key -e OPENROUTER_API_KEY=your-key translator
```

## Configuration

Create a `.env` file based on `.env.example`:

```env
AUTHENTICATION_KEY=your-authentication-key-here
PORT=8000
NEWSAPI_KEY=your-newsapi-key-here
OPENROUTER_API_KEY=your-openrouter-api-key-here
```

## API Endpoints

### Base URL

`http://localhost:8000`

### Authentication

All endpoints are rate-limited. Some endpoints require authentication via the `AUTHENTICATION_KEY` header.

### Public Endpoints (Rate Limited)

#### 1. Romaji Conversion

```http
POST /romaji
Content-Type: application/json

{
    "str": "こんにちは",
    "html": false
}
```

#### 2. Furigana Generation

```http
POST /furigana
Content-Type: application/json

{
    "str": "日本語",
    "html": true
}
```

#### 3. Slug Generation

```http
POST /slug
Content-Type: application/json

{
    "str": "日本語"
}
```

#### 4. Text Tokenization

```http
POST /tokenizer
Content-Type: application/json

{
    "str": "日本語の文章",
    "with_particle": true
}
```

### Authenticated Endpoints (Requires AUTHENTICATION_KEY)

#### 1. News Fetching

```http
GET /get-news
Authentication: your-auth-key
```

#### 2. Text Transformation

```http
POST /transform-text
Authentication: your-auth-key
Content-Type: application/json

{
    "text": "your-text-here"
}
```

#### 3. Translation

```http
POST /translate
Authentication: your-auth-key
Content-Type: application/json

{
    "text": "こんにちは",
    "target_lang": "EN",
    "source_lang": "JA"  # Optional
}
```

#### 4. Batch Translation

```http
POST /translate-batch
Authentication: your-auth-key
Content-Type: application/json

{
    "texts": ["こんにちは", "さようなら"],
    "target_lang": "EN",
    "source_lang": "JA"  # Optional
}
```

## Rate Limiting

The API includes rate limiting to prevent abuse:

- Public endpoints: Lower rate limits apply
- Authenticated endpoints: Higher rate limits and additional features

## Docker Support

The application can be containerized using the provided Dockerfile. The container runs on port 3097 by default, which can be mapped to any host port.
