import cutlet
from fastapi import APIRouter, Request, HTTPException

from cutlet import Cutlet

from app.__exceptions import ExceptionList
from app._helpers import (
    fetch_news,
    request_allowed,
    process_html,
    transform_line,
    translate_array,
    translate_text,
)
from app.rate_limiter import authenticated, limiter, get_rate_limit
from app._info import __version__
from pydantic import BaseModel, Field


class RomajiRequest(BaseModel):
    str: str
    html: bool = False


class SlugRequest(BaseModel):
    str: str


class TransformRequest(BaseModel):
    text: str
    target: str = "en"


class TransformNewsRequest(BaseModel):
    title: str
    content: str


class TranslateTextRequest(BaseModel):
    text: str
    target_lang: str = "en"
    source_lang: str | None = None


class TranslateBatchRequest(BaseModel):
    texts: list[str]
    target_lang: str = "en"
    source_lang: str | None = None


class TokenizerRequest(BaseModel):
    str: str
    with_particle: bool = True


router = APIRouter()


@limiter.limit(get_rate_limit)
@router.get("/")
async def home(request: Request):
    return {"version": __version__}


@limiter.limit(get_rate_limit)
@router.post("/romaji")
def romaji(request: Request, validated_request: RomajiRequest):
    auth = authenticated(request)
    if not request_allowed(request):
        raise HTTPException(
            status_code=422,
            detail="Not authenticated or allowed string length exceeded.",
        )

    translator = Cutlet()
    for ex in ExceptionList:
        translator.add_exception(ex["from"], ex["to"])
    if validated_request.html:
        try:
            translated_html = process_html(
                validated_request.str, lambda x: translator.romaji(x)
            )

            return {"auth": auth, "result": translated_html}
        except Exception:
            raise HTTPException(
                status_code=422, detail="HTML not clean and can't be processed."
            )
    else:
        return {"auth": auth, "result": translator.romaji(validated_request.str)}


@limiter.limit(get_rate_limit)
@router.post("/furigana")
def furigana(request: Request, validated_request: RomajiRequest):
    auth = authenticated(request)
    if not request_allowed(request):
        raise HTTPException(
            status_code=422,
            detail="Not authenticated or allowed string length exceeded.",
        )

    translator = Cutlet()
    for ex in ExceptionList:
        translator.add_exception(ex["from"], ex["to"])
    if validated_request.html:
        try:
            translated_html = process_html(
                validated_request.str,
                lambda x: f"<ruby>{x}<rt>{translator.romaji(x)}<rt></ruby>",
            )
            return {"auth": auth, "result": translated_html}
        except Exception:
            raise HTTPException(
                status_code=422, detail="HTML not clean and can't be processed."
            )
    else:
        raise HTTPException(status_code=400, detail="html params must be true")


@limiter.limit(get_rate_limit)
@router.post("/slug")
def slug(request: Request, validated_request: SlugRequest):
    auth = authenticated(request)
    if not request_allowed(request):
        raise HTTPException(
            status_code=422,
            detail="Not authenticated or allowed string length exceeded.",
        )
    translator = Cutlet()

    for ex in ExceptionList:
        translator.add_exception(ex["from"], ex["to"])
    return {"auth": auth, "result": translator.slug(validated_request.str)}


@limiter.limit(get_rate_limit)
@router.post("/tokenizer")
def tokenizer(request: Request, validated_request: TokenizerRequest):
    auth = authenticated(request)
    if not request_allowed(request):
        raise HTTPException(
            status_code=422,
            detail="Not authenticated or allowed string length exceeded.",
        )
    words = Cutlet().tagger(validated_request.str)
    out = []
    # def cleaning_word(word):

    for wi, word in enumerate(words):
        po = out[-1] if out else None
        pw = words[wi - 1] if wi > 0 else None
        nw = words[wi + 1] if wi < len(words) - 1 else None
        # handle possessive apostrophe as a special case
        if (
            word.surface == "'"
            and (nw and nw.char_type == cutlet.CHAR_ALPHA and not nw.white_space)
            and not word.white_space
        ):
            # remove preceeding space
            if po:
                po.space = False
            out.append(cutlet.Token(word.surface, False))
            continue

        # ########
        # if self.ensure_ascii:
        #         out = '?' * len(word.surface)
        #         return out
        #     else:
        #         return word.surface

        if word.is_unk:
            # print(word.surface)
            roma = ""
        elif word.feature.pos1 == "補助記号":
            roma = ""
        elif word.feature.pos1 == "助詞" and not validated_request.with_particle:
            roma = ""
        else:
            roma = word.surface
        if roma and po and po.surface and po.surface[-1] == "っ":
            po.surface = po.surface[:-1] + roma[0]
        foreign = Cutlet().use_foreign_spelling and cutlet.has_foreign_lemma(word)
        tok = cutlet.Token(roma, False, foreign)
        # handle punctuation with atypical spacing
        if word.surface in "「『":
            if po:
                po.space = True
            out.append(tok)
            continue
        if roma in "([":
            if po:
                po.space = True
            out.append(tok)
            continue
        if roma == "/":
            out.append(tok)
            continue

        # preserve spaces between ascii tokens
        if word.surface.isascii() and nw and nw.surface.isascii():
            use_space = bool(nw.white_space)
            out.append(cutlet.Token(word.surface, use_space))
            continue

        out.append(tok)
        # no space sometimes
        # お酒 -> osake
        if word.feature.pos1 == "接頭辞":
            continue
        # 今日、 -> kyou, ; 図書館 -> toshokan
        if nw and nw.feature.pos1 in ("補助記号", "接尾辞"):
            continue
        # special case for half-width commas
        if nw and nw.surface == ",":
            continue
        # special case for prefixes
        if foreign and roma[-1] == "-":
            continue

        # 思えば -> omoeba
        if nw and nw.feature.pos2 in ("接続助詞"):
            continue
        # 333 -> 333 ; this should probably be handled in mecab
        if word.surface.isdigit() and nw and nw.surface.isdigit():
            continue
        # そうでした -> sou deshita
        if (
            nw
            and word.feature.pos1 in ("動詞", "助動詞", "形容詞")
            and nw.feature.pos1 == "助動詞"
            and nw.surface != "です"
        ):
            continue
        # if we get here, it does need a space
        tok.space = True

    # remove any leftover っ
    for tok in out:
        tok.surface = tok.surface.replace("っ", "")
    # strr = [str(tok) for tok in out]
    strr = "".join([str(tok) for tok in out]).strip()
    return {"auth": auth, "result": strr.split(" ")}


@limiter.limit(get_rate_limit)
@router.get("/get-news")
def get_news(request: Request, target: str = "en"):
    auth = authenticated(request)
    if not auth:
        raise HTTPException(
            status_code=401, detail="Only authenticated user can access this endpoint."
        )
    news = fetch_news()

    structured_news = []
    for article in news:
        result = {
            "title": article.title,
            "content": article.text,
            "category": article.category,
            "source": article.url,
            "published_date": article.publish_date,
        }
        structured_news.append(result)
    return {"auth": auth, "news": structured_news}


@limiter.limit(get_rate_limit)
@router.post("/transform-text")
def transform_text(request: Request, validated_request: TransformRequest):
    auth = authenticated(request)
    if not auth:
        raise HTTPException(
            status_code=401, detail="Only authenticated user can access this endpoint."
        )

    splitted_content = [
        line for line in validated_request.text.split("\n") if line != ""
    ]
    translated_content = translate_array(splitted_content, validated_request.target)
    transformed_line = [transform_line(line) for line in splitted_content]
    if len(transformed_line) == len(translated_content):
        for i in range(len(transformed_line)):
            transformed_line[i]["translation"] = str(translated_content[i])
    elif len(transformed_line == 1):
        transformed_line[0]["translation"] = str(translated_content[0])

    return {"auth": auth, "result": transformed_line}


@limiter.limit(get_rate_limit)
@router.post("/translate-text")
def translate(request: Request, validated_request: TranslateTextRequest):
    auth = authenticated(request)
    if not auth:
        raise HTTPException(
            status_code=401, detail="Only authenticated users can access this endpoint."
        )
    return {
        "auth": auth,
        "result": translate_text(
            validated_request.text,
            validated_request.target_lang,
            validated_request.source_lang,
        ),
    }


@limiter.limit(get_rate_limit)
@router.post("/translate-batch")
def translate_batch(
    request: Request,
    validated_request: TranslateBatchRequest,
):
    auth = authenticated(request)
    if not auth:
        raise HTTPException(
            status_code=401, detail="Only authenticated users can access this endpoint."
        )
    return {
        "auth": auth,
        "results": translate_array(
            validated_request.texts,
            validated_request.target_lang,
            validated_request.source_lang,
        ),
    }
