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

@dp.message(CommandStart())
async def cmd_start(message: Message):
    await message.answer(
        "👋 **Привет! Я бот для генерации видео через PixVerse.**\n\n"
        "🎬 **Как генерировать:**\n"
        "1. **Только текст:** `/video твой промпт на английском`\n"
        "2. **С картинкой:** прикрепи 1 фото и напиши описание в подписи к нему!",
        parse_mode="Markdown"
    )

@dp.message(Command(commands=["video"]))
async def generate_from_text(message: Message):
    prompt = message.text.replace("/video", "").strip()
    if not prompt:
        await message.answer("⚠️ Напиши описание на английском после команды! Пример:\n`/video Boy running and eating ice cream`", parse_mode="Markdown")
        return

    await process_video_generation(
        message=message, 
        prompt=prompt, 
        endpoint="https://api.pixverse.ai/v1/video/generate", # Обновленный эндпоинт API
        payload_extra={}
    )

@dp.message(F.photo)
async def generate_from_image(message: Message):
    prompt = message.caption
    if not prompt:
        await message.answer("⚠️ Пожалуйста, добавь описание на английском в подпись к фото!")
        return

    photo = message.photo[-1]
    file_info = await bot.get_file(photo.file_id)
    photo_url = f"https://api.telegram.org/file/bot{BOT_TOKEN}/{file_info.file_path}"

    await process_video_generation(
        message=message, 
        prompt=prompt, 
        endpoint="https://api.pixverse.ai/v1/image-to-video/generate",
        payload_extra={"image_url": photo_url}
    )

async def process_video_generation(message: Message, prompt: str, endpoint: str, payload_extra: dict):
    msg = await message.answer("🎬 Отправляю запрос... Жди 1-2 минуты.")

    headers = {
        "Authorization": f"Bearer {PIXVERSE_API_KEY}",
        "Content-Type": "application/json"
    }

    payload = {
        "prompt": prompt,
        "resolution": "480p",
        "duration": 7,
        "model": "v6"
    }
    payload.update(payload_extra)

    async with aiohttp.ClientSession() as session:
        try:
            async with session.post(endpoint, json=payload, headers=headers) as resp:
                if resp.status != 200:
                    text = await resp.text()
                    await msg.edit_text(f"❌ Ошибка API ({resp.status}). Проверь API-ключ или ссылку.")
                    return
                
                data = await resp.json()
                video_id = data.get("video_id") or data.get("data", {}).get("video_id")

            if not video_id:
                await msg.edit_text("❌ Не удалось получить ID видео от сервиса.")
                return

            for _ in range(18):
                await asyncio.sleep(10)
                async with session.get(f"https://api.pixverse.ai/v1/video/result/{video_id}", headers=headers) as check_resp:
                    if check_resp.status == 200:
                        res_data = await check_resp.json()
                        status = res_data.get("status") or res_data.get("data", {}).get("status")
                        
                        if status == "success":
                            video_url = res_data.get("url") or res_data.get("data", {}).get("url")
                            await msg.delete()
                            await message.answer_video(video=video_url, caption=f"✨ **Готово!**\nПромпт: `{prompt}`", parse_mode="Markdown")
                            return
                        elif status == "failed":
                            await msg.edit_text("❌ Ошибка генерации видео.")
                            return

            await msg.edit_text("⏳ Время ожидания истекло.")
        except Exception as e:
            await msg.edit_text(f"⚠️ Произошла ошибка: {str(e)}")

async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
