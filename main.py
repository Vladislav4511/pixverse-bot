import os
import asyncio
import aiohttp
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message
from aiogram.filters import CommandStart, Command

BOT_TOKEN = os.getenv("BOT_TOKEN")
PIXVERSE_API_KEY = os.getenv("PIXVERSE_API_KEY")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

# Команда /start
@dp.message(CommandStart())
async def cmd_start(message: Message):
    await message.answer(
        "👋 **Привет! Я бот для генерации видео через PixVerse V6 (480p, 7 сек).**\n\n"
        "🎬 **Как генерировать:**\n"
        "1. **Только текст:** отправь команду `/video твой промпт`\n"
        "2. **С картинкой:** прикрепи 1 фото и напиши описание в подписи к нему!",
        parse_mode="Markdown"
    )

# 1. РЕЖИМ: Только текст (/video)
@dp.message(Command(commands=["video"]))
async def generate_from_text(message: Message):
    prompt = message.text.replace("/video", "").strip()
    if not prompt:
        await message.answer("⚠️ Напиши описание после команды! Пример:\n`/video Cyberpunk neon city, 4k`", parse_mode="Markdown")
        return

    await process_video_generation(
        message=message, 
        prompt=prompt, 
        endpoint="https://app-api.pixverse.ai/openapi/v2/video/text_to_video", 
        payload_extra={}
    )

# 2. РЕЖИМ: Оживление картинки (1 фото с подписью)
@dp.message(F.photo)
async def generate_from_image(message: Message):
    prompt = message.caption
    if not prompt:
        await message.answer("⚠️ Пожалуйста, добавь описание прямо в подпись к фото!")
        return

    # Получаем прямую ссылку на прикреплённое фото
    photo = message.photo[-1]
    file_info = await bot.get_file(photo.file_id)
    photo_url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_info.file_path}"

    await process_video_generation(
        message=message, 
        prompt=prompt, 
        endpoint="https://app-api.pixverse.ai/openapi/v2/video/img_to_video", 
        payload_extra={"img_url": photo_url}
    )

# Вспомогательная функция для генерации и ожидания
async def process_video_generation(message: Message, prompt: str, endpoint: str, payload_extra: dict):
    msg = await message.answer("🎬 Запрос отправлен в PixVerse V6! Рендерю 480p (7 сек). Жди 1-2 минуты...")

    headers = {
        "API-KEY": PIXVERSE_API_KEY,
        "Content-Type": "application/json"
    }

    # Базовые параметры: 480p, 7 секунд
    payload = {
        "prompt": prompt,
        "resolution": "480p",
        "duration": 7,
        "model_version": "v6"
    }
    payload.update(payload_extra)

    async with aiohttp.ClientSession() as session:
        # Отправляем задачу на сервер
        async with session.post(endpoint, json=payload, headers=headers) as resp:
            data = await resp.json()
            if data.get("code") != 0 or "data" not in data:
                await msg.edit_text("❌ Ошибка при отправке запроса в PixVerse.")
                return
            video_id = data["data"]["video_id"]

        # Цикл ожидания готовности (проверка каждые 10 секунд, до 3 минут)
        for _ in range(18):
            await asyncio.sleep(10)
            async with session.get(f"https://app-api.pixverse.ai/openapi/v2/video/result/{video_id}", headers=headers) as check_resp:
                res_data = await check_resp.json()
                status = res_data.get("data", {}).get("status")
                
                if status == "success":
                    video_url = res_data["data"]["url"]
                    await msg.delete()
                    await message.answer_video(video=video_url, caption=f"✨ **Готово!**\nПромпт: `{prompt}`", parse_mode="Markdown")
                    return
                elif status == "failed":
                    await msg.edit_text("❌ Нейросеть не смогла сгенерировать видео.")
                    return

        await msg.edit_text("⏳ Время ожидания истекло. Попробуй еще раз.")

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
