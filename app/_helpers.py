import os
from fastapi import FastAPI, HTTPException, Request
from html.parser import HTMLParser
from app.rate_limiter import authenticated

app = FastAPI()


def free_limit_not_exceeded(request: Request, limit=350):
    length = request.headers.get("Content-Length")
    return int(length) < limit


def request_allowed(request: Request):
    if authenticated(request):
        return True
    elif free_limit_not_exceeded(request):
        return True
    else:
        raise HTTPException(status_code=413, detail="Payload too large for free user")


def process_html(html_string, callback):
    class CallbackParser(HTMLParser):
        def __init__(self, callback):
            super().__init__()
            self.callback = callback
            self.result = ""
            self.name_stack = []

        def handle_starttag(self, name, attrs):
            if name in ["img", "input", "br", "hr", "meta"]:
                self.result += "<" + name + " "
                for attr in attrs:
                    self.result += attr[0] + '="' + attr[1] + '" '
                self.result += ">"
            else:
                self.result += "<" + name
                for attr in attrs:
                    self.result += " " + attr[0] + '="' + attr[1] + '"'
                self.result += ">"
            self.name_stack.append(name)

        def handle_endtag(self, name):
            current_name = self.name_stack.pop()
            if self.name_stack and self.name_stack[-1] != current_name:
                self.result += " "
            self.result += "</" + name + ">"

        def handle_data(self, data):
            data = self.callback(data)
            if data:
                # Append leading and trailing whitespace to match the original string
                self.result += data.strip() + " "
                if self.name_stack:
                    self.result = self.result.rstrip() + " "

        def handle_startendtag(self, tag, attrs):
            if tag in ["img", "input", "br", "hr", "meta"]:
                self.result += "<" + tag
                for attr in attrs:
                    self.result += " " + attr[0] + '="' + attr[1] + '"'
                self.result += ">"
            else:
                raise Exception("Start-end tags should be handled in handle_starttag")

        def get_result(self):
            return self.result

    parser = CallbackParser(callback)
    parser.feed(html_string)
    parser.close()
    return parser.get_result()


import worldnewsapi
from worldnewsapi.models.retrieve_newspaper_front_page200_response import (
    RetrieveNewspaperFrontPage200Response,
)
from worldnewsapi.rest import ApiException
from dotenv import load_dotenv

load_dotenv()


def fetch_news():
    configuration = worldnewsapi.Configuration()
    configuration.api_key["apiKey"] = os.environ["NEWSAPI_KEY"]
    # Configure API key authorization: headerApiKey
    configuration.api_key["headerApiKey"] = os.environ["NEWSAPI_KEY"]
    # Enter a context with an instance of the API client
    with worldnewsapi.ApiClient(configuration) as api_client:
        # Create an instance of the API class
        api_instance = worldnewsapi.NewsApi(api_client)
        source_country = "jp"
        language = "ja"
        categories = ",".join(
            [
                "business",
                "technology",
                "entertainment",
                "science",
                "education",
            ]
        )
    try:
        # Retrieve Newspaper Front Page
        api_response = api_instance.search_news(
            source_country=source_country, language=language, categories=categories
        )
        return api_response.news
    except Exception as e:
        raise "Exception when calling NewsApi->retrieve_newspaper_front_page: %s\n" % e


# ================================== #


# ================================== #
# OpenRouter Translation
# ================================== #


import json
from typing import Optional, Dict, List
from openai import OpenAI

# ISO 639-1 language codes (common subset)
LANGUAGE_CODES: Dict[str, str] = {
    "ar": "Arabic",
    "zh": "Chinese",
    "en": "English",
    "fr": "French",
    "de": "German",
    "hi": "Hindi",
    "id": "Indonesian",
    "it": "Italian",
    "ja": "Japanese",
    "ko": "Korean",
    "pt": "Portuguese",
    "ru": "Russian",
    "es": "Spanish",
    "tr": "Turkish",
    "vi": "Vietnamese",
}


class TranslationError(Exception):
    """Custom exception for translation errors"""

    pass


def split_text_into_chunks(text: str, max_size: int = 120000) -> List[str]:
    """
    Split text into chunks based on newlines, then by size if needed.

    Args:
        text: The text to split
        max_size: Maximum size of each chunk in characters

    Returns:
        List of text chunks
    """
    # If text is smaller than max size, return as single chunk
    if len(text) <= max_size:
        return [text]

    # Split text by newlines first
    lines = text.split("\n")

    chunks = []
    current_chunk = []
    current_size = 0

    for line in lines:
        line = line.strip()
        if not line:
            continue

        # If this line alone exceeds max size, split it further
        if len(line) > max_size:
            # Add current chunk if it exists
            if current_chunk:
                chunks.append("\n".join(current_chunk))
                current_chunk = []
                current_size = 0

            # Split long line by spaces
            words = line.split()
            temp_line = []
            temp_size = 0

            for word in words:
                if temp_size + len(word) + 1 > max_size:
                    if temp_line:
                        chunks.append(" ".join(temp_line))
                        temp_line = []
                        temp_size = 0
                temp_line.append(word)
                temp_size += len(word) + 1

            if temp_line:
                chunks.append(" ".join(temp_line))

        # If adding this line would exceed max size, start new chunk
        elif current_size + len(line) + 1 > max_size:
            if current_chunk:
                chunks.append("\n".join(current_chunk))
            current_chunk = [line]
            current_size = len(line)
        else:
            current_chunk.append(line)
            current_size += len(line) + 1

    # Add the last chunk if there's anything left
    if current_chunk:
        chunks.append("\n".join(current_chunk))

    return chunks


def translate_text(
    text: str, target_lang: str, source_lang: Optional[str] = None, chunk_size=50000
) -> str | None:
    """
    Translate text using OpenAI's API via OpenRouter.
    Handles large texts by splitting into chunks.

    Args:
        text: The text to translate
        target_lang: The target language code (e.g., 'es' for Spanish)
        source_lang: Optional source language code (e.g., 'en' for English)
                    If not provided, the model will attempt to detect the language.
        chunk_size: Maximum size of each chunk in characters

    Returns:
        str|None : translated text

    """
    # Validate inputs
    if not text or not text.strip():
        return None

    # Validate target language code
    target_lang = target_lang.lower()
    if target_lang not in LANGUAGE_CODES:
        target_lang = "en"

    # Validate source language code if provided
    if source_lang:
        source_lang = source_lang.lower()
        if source_lang not in LANGUAGE_CODES:
            source_lang = None

    # Get API key from environment variable
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        return None

    # Initialize OpenAI client with OpenRouter base URL
    client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=api_key,
        default_headers={
            "HTTP-Referer": "https://github.com/OpenRouterAI/openrouter-python"
        },
    )

    # Split text into chunks if necessary
    chunks = split_text_into_chunks(text, chunk_size)
    translated_chunks = []

    for i, chunk in enumerate(chunks, 1):
        # Prepare the prompt using full language names for better model understanding
        instruction = f"Translate the following text to {LANGUAGE_CODES[target_lang]}"
        if source_lang:
            instruction += f" from {LANGUAGE_CODES[source_lang]}"
        instruction += ":"
        try:

            # Make the API request using the OpenAI SDK
            response = client.chat.completions.create(
                model="deepseek/deepseek-chat:free",
                messages=[
                    {
                        "role": "system",
                        "content": "You are a highly accurate translation assistant. Respond with only the translated text, no explanations.",
                    },
                    {"role": "user", "content": f"{instruction}\n\n{chunk}"},
                ],
            )

            # Extract the translated text
            translated_chunk = response.choices[0].message.content.strip()
            translated_chunks.append(translated_chunk)

        except Exception as e:
            # Join all translated chunks with appropriate spacing
            translated_text = "\n".join(translated_chunks)
            return translated_text + "\n\n===TRANSLATION DID NOT COMPLETE==="

    # Join all translated chunks with appropriate spacing
    translated_text = "\n".join(translated_chunks)
    return translated_text


def translate_array(
    texts: list[str],
    target_lang: str,
    source_lang: Optional[str] = None,
    chunk_size=50000,
) -> list[str | None]:
    """
    Translate an array of texts using OpenAI's API via OpenRouter.
    Joins texts into a single request and splits into chunks if necessary.

    Args:
        texts: List of texts to translate
        target_lang: The target language code (e.g., 'es' for Spanish)
        source_lang: Optional source language code (e.g., 'en' for English)
                    If not provided, the model will attempt to detect the language.
        chunk_size: Maximum size of each chunk in characters

    Returns:
        list[str|None]: A list of translated texts.
                                The order of translations matches the input array order.

    """
    if not texts:
        return []

    if not isinstance(texts, list):
        return []

    # Validate target language code
    target_lang = target_lang.lower()
    if target_lang not in LANGUAGE_CODES:
        target_lang = "en"

    # Validate source language code if provided
    if source_lang:
        source_lang = source_lang.lower()
        if source_lang not in LANGUAGE_CODES:
            source_lang = None

    # Get API key from environment variable
    api_key = os.getenv("OPENROUTER_API_KEY")
    if not api_key:
        return []

    # Initialize OpenAI client with OpenRouter base URL
    client = OpenAI(
        base_url="https://openrouter.ai/api/v1",
        api_key=api_key,
        default_headers={
            "HTTP-Referer": "https://github.com/OpenRouterAI/openrouter-python"
        },
    )

    # for text in texts:

    # Split texts into smaller groups to avoid overwhelming the model
    text_groups = []
    current_group = []
    current_size = 0
    # try:

    for text in texts:
        text = str(text)
        text_size = len(text)
        if current_size + text_size > chunk_size // 2:  # Use half max size for safety
            if current_group:
                text_groups.append(current_group)
            current_group = [text]
            current_size = text_size
        else:
            current_group.append(text)
            current_size += text_size
        #
    if current_group:
        text_groups.append(current_group)

    all_translations = []

    for group_idx, text_group in enumerate(text_groups, 1):
        # Format texts in this group as a numbered list
        formatted_texts = "\n".join(
            f"{i+1}. {text}" for i, text in enumerate(text_group)
        )

        # Prepare the prompt using full language names for better model understanding
        instruction = f"Translate each of the following numbered texts to {LANGUAGE_CODES[target_lang]}"
        if source_lang:
            instruction += f" from {LANGUAGE_CODES[source_lang]}"
        instruction += (
            ". Return only the translations as a JSON array in the exact same order:"
        )

        try:
            # Make the API request using the OpenAI SDK
            response = client.chat.completions.create(
                model="deepseek/deepseek-chat:free",
                messages=[
                    {
                        "role": "system",
                        "content": 'You are a highly accurate translation assistant. Return ONLY a JSON array containing the translated texts in order, with no additional text or explanations. Example format: ["translation1", "translation2"]',
                    },
                    {"role": "user", "content": f"{instruction}\n\n{formatted_texts}"},
                ],
                response_format={"type": "json_object"},
                temperature=0.1,  # Lower temperature for more consistent JSON formatting
            )

            # Extract and parse the JSON response
            response_content = response.choices[0].message.content.strip()

            # Try to parse the raw JSON response
            translations = json.loads(response_content)

            # Handle different response formats
            if isinstance(translations, dict):
                # If it's a dictionary, look for translations in known fields
                translations = translations.get(
                    "translations",
                    translations.get("results", translations.get("text", [])),
                )
            elif not isinstance(translations, list):
                # If it's not a list or dict, try to convert to list
                translations = [translations] if translations else []

            # Ensure all elements are strings
            translations = [str(t).strip() for t in translations]

            if len(translations) != len(text_group):
                return [
                    f"ERR: Expected {len(text_group)} translations in group {group_idx}, got {len(translations)}"
                ]

            all_translations.extend(translations)

        except json.JSONDecodeError as e:
            return [
                f"Invalid JSON response in group {group_idx}: {str(e)}\nResponse content: {response_content}"
            ]
        except Exception as e:
            return [f"ERR: {str(e)}"]

    # Verify final number of translations
    if len(all_translations) != len(texts):
        return [
            f"ERR: Expected {len(texts)} total translations, got {len(all_translations)}"
        ]

    return all_translations


# ================================== #
# Line transformation
# ================================== #

import cutlet
import jaconv
from cutlet.cutlet import has_foreign_lemma


def is_kanji(char):
    """Check if a character is a kanji (CJK Unified Ideographs)."""
    return 0x4E00 <= ord(char) <= 0x9FFF


def transform_line(line: str):
    """Transform a Japanese sentence into structured data with original text and word-level furigana.

    Args:
        line: Japanese text to process

    Returns:
        Dictionary with structure:
        {
            "origin": original text,
            "translation": translation or null,
            "words": [
                {"text": surface text, "furigana": kana or null},
                ...
            ]
        }
    """
    katsu = cutlet.Cutlet()
    words = katsu.tagger(line)

    result = {"origin": line, "translation": None, "words": []}

    for word in words:
        # Only provide furigana for words containing kanji
        has_kanji = any(is_kanji(char) for char in word.surface)

        # Handle special cases that should have no furigana
        if (
            not has_kanji  # No kanji characters
            or word.feature.pos1 == "補助記号"  # Punctuation
            or word.feature.pos1 == "助詞"  # Particles
            or has_foreign_lemma(word)  # Foreign words like "cutlet"
            or word.surface.isascii()
        ):  # ASCII text
            furigana = None
        else:
            # Get furigana for kanji words
            furigana = (
                jaconv.kata2hira(word.feature.kana) if word.feature.kana else None
            )

        result["words"].append({"text": word.surface, "furigana": furigana})

    return result
