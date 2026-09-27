import os
import asyncio
import aiohttp
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message
from aiogram.filters import CommandStart, Command

BOT_TOKEN = os.getenv("BOT_TOKEN")
FAL_KEY = os.getenv("PIXVERSE_API_KEY")

bot = Bot(token=BOT_TOKEN)
dp = Dispatcher()

@dp.message(CommandStart())
async def cmd_start(message: Message):
    await message.answer(
        "👋 **Привет! Я бот для генерации видео через Fal.ai (PixVerse).**\n\n"
        "🎬 **Как генерировать:**\n"
        "1. **Только текст:** `/video твой промпт на английском`\n"
        "2. **С картинкой:** прикрепи photo и напиши описание в подписи!",
        parse_mode="Markdown"
    )

@dp.message(Command(commands=["video"]))
async def generate_from_text(message: Message):
    prompt = message.text.replace("/video", "").strip()
    if not prompt:
        await message.answer("⚠️ Напиши описание на английском! Пример:\n`/video Boy running and eating ice cream`", parse_mode="Markdown")
        return

    await process_fal_generation(
        message=message, 
        endpoint="https://fal.run/fal-ai/pixverse/v3/text-to-video",
        payload={"prompt": prompt, "resolution": "480p", "duration": 7}
    )

@dp.message(F.photo)
async def generate_from_image(message: Message):
    prompt = message.caption
    if not prompt:
        await message.answer("⚠️ Добавь описание на английском в подпись к фото!")
        return

    photo = message.photo[-1]
    file_info = await bot.get_file(photo.file_id)
    photo_url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_info.file_path}"

    await process_fal_generation(
        message=message, 
        endpoint="https://fal.run/fal-ai/pixverse/v3/image-to-video",
        payload={"prompt": prompt, "image_url": photo_url, "resolution": "480p", "duration": 7}
    )

async def process_fal_generation(message: Message, endpoint: str, payload: dict):
    msg = await message.answer("🎬 Запрос отправлен! Генерирую видео. Жди 1-2 минуты...")

    headers = {
        "Authorization": f"Key {FAL_KEY}",
        "Content-Type": "application/json"
    }

    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(endpoint, json=payload, headers=headers) as resp:
                if resp.status != 200:
                    err_text = await resp.text()
                    await msg.edit_text(f"❌ Ошибка API ({resp.status}). Проверь ключ Fal.ai.")
                    return
                
                data = await resp.json()
                video_url = data.get("video", {}).get("url") or data.get("video_url")
                
                if video_url:
                    await msg.delete()
                    await message.answer_video(video=video_url, caption="✨ **Готово!**")
                else:
                    await msg.edit_text("❌ Ошибка: Не удалось получить видео.")

        except Exception as e:
            await msg.edit_text(f"⚠️ Ошибка: {str(e)}")

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
