import json

from openai import AsyncOpenAI
from pycommontools.configs.logging import setup_logger

from src.core.categories import CATEGORIES
from src.core.settings import settings

logger = setup_logger("chatgpt")

client = AsyncOpenAI(api_key=settings.openai_api_key)


async def classify_ad(text: str, base64_images: list[str]) -> tuple[dict, int, int]:
    messages = [
        {
            "role": "system",
            "content": (
                "Ты модель для классификации объявлений. "
                "На вход ты получаешь текст объявления и изображения. "
                "Нужно подобрать максимально точные категории и подкатегории, "
                "ты можешь вернуть несколько категорий или подкатегорий, "
                "если видишь в этом смысл, "
                "главное надо постараться максимально точно подобрать их. "
                "Если ты понимаешь, что тут явное преобладание 1 категории "
                "и 1 подкатегории, то не стоит указывать несколько "
                "(будь более строгим в определении категорий, "
                "лучше иметь один супер точный вариант, "
                "чем 1 супер точный и 1 не совсем точный). "
                "Я передам тебе список доступных категорий и подкатегорий: "
                f"{CATEGORIES}. Верни ответ в формате: "
                '{"<category_name1>": [<sub1>, ...], "<category_name2>": [...], ...}'
                "Если ты понимаешь, что данное объявление содержит спам или "
                "продвигает запрещённые товары или услуги, верни пустой "
                "список категорий в формате: {}."
            ),
        },
        {
            "role": "user",
            "content": [
                {"type": "text", "text": text},
                *[
                    {"type": "image_url", "image_url": {"url": img}}
                    for img in base64_images
                ],
            ],
        },
    ]

    response = await client.chat.completions.create(
        model="gpt-4.1-mini", messages=messages
    )

    response_content = response.choices[0].message.content or "{}"

    logger.debug(f"ChatGPT response: {response_content}")

    try:
        parsed_response = json.loads(response_content)
    except json.JSONDecodeError:
        logger.error(f"Failed to parse JSON response: {response_content}")
        parsed_response = {"categories": [], "subcategories": []}

    if not response.usage:
        logger.warning("Response usage information is missing")
        return parsed_response, 0, 0

    return (
        parsed_response,
        response.usage.prompt_tokens,
        response.usage.completion_tokens,
    )
