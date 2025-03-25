import os
from fastapi import FastAPI, HTTPException, Request
from html.parser import HTMLParser
from rate_limiter import authenticated

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


import deepl


def translate_text(text, target_lang="EN-US"):
    try:
        target_lang = target_lang.upper()
        auth_key = os.environ["DEEPL_KEY"]
        translator = deepl.Translator(auth_key)
        res = translator.translate_text(text, target_lang=target_lang)
        return res.text
    except:
        return None


def get_deepl_usage():
    try:
        auth_key = os.environ["DEEPL_KEY"]
        translator = deepl.Translator(auth_key)
        res = translator.get_usage()
        return res
    except Exception as e:
        return None


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

    result = {"origin": line, "translation": translate_text(line), "words": []}

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
