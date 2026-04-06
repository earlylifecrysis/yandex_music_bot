import os
import logging
import re
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from yandex_music import Client

# Включаем логирование
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Получаем токены из переменных окружения ---
TELEGRAM_TOKEN = os.environ.get("TELEGRAM_BOT_TOKEN")
YANDEX_TOKEN = os.environ.get("YANDEX_MUSIC_TOKEN")

# КОНТАКТЫ ДЛЯ СВЯЗИ (укажите свои)
CONTACT_TELEGRAM = "@hfavngrd"  # Ваш Telegram username (например, @dmitry)
CONTACT_EMAIL = "kira-pest@mail.ru"  # Ваш email

if not TELEGRAM_TOKEN or not YANDEX_TOKEN:
    logger.error("❌ Ошибка: не найдены переменные окружения TELEGRAM_BOT_TOKEN или YANDEX_MUSIC_TOKEN")
    exit(1)


def extract_track_id(url: str) -> str:
    """Извлекает ID трека из URL Яндекс.Музыки"""
    # Ищем паттерн /track/ЧИСЛО
    match = re.search(r'/track/(\d+)', url)
    if match:
        return match.group(1)
    return None


# --- Команда /start ---
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Привет! Я бот для Яндекс Музыки:)\n\n"
        "Что я умею:\n"
        "• Получать информацию о треке по ссылке\n"
        "• Показывать название, исполнителя и длительность\n\n"
        "Как использовать:\n"
        "Просто отправь мне ссылку на трек из Яндекс.Музыки\n\n"
        "Для справки отправь /help"
    )


# --- Команда /help ---
async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    help_text = (
        "🎵 <b>Справка по использованию бота</b> 🎵\n\n"
        "<b>Основные команды:</b>\n"
        "/start - Начать работу с ботом\n"
        "/help - Показать эту справку\n\n"
        "<b>Как получить информацию о треке:</b>\n"
        "1. Откройте Яндекс.Музыку\n"
        "2. Найдите нужный трек\n"
        "3. Нажмите «Поделиться» → «Копировать ссылку»\n"
        "4. Отправьте ссылку в этот чат\n\n"
        "<b>Пример ссылки:</b>\n"
        "<code>https://music.yandex.ru/album/1234567/track/7654321</code>\n\n"
        "<b>Советы:</b>\n"
        "• Бот понимает ссылки на отдельные треки\n"
        "• Можно отправлять ссылки с любыми параметрами (utm-метки и т.д.)\n"
        "• Если бот не отвечает, подождите 10-15 секунд (на холодный старт)\n\n"
        "<b>Связаться с разработчиком:</b>\n"
        f"Telegram: {CONTACT_TELEGRAM}\n"
        f"Email: {CONTACT_EMAIL}\n\n"
        "Пишите ваши предложения по улучшению бота! "
        "Буду рад обратной связи."
    )

    await update.message.reply_text(help_text, parse_mode="HTML")


# --- Обработка ссылок ---
async def handle_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text.strip()
    logger.info(f"Получен URL: {url}")

    # Отправляем уведомление о наборе текста
    await update.message.chat.send_action(action="typing")

    # Извлекаем ID трека из URL
    track_id = extract_track_id(url)
    if not track_id:
        await update.message.reply_text(
            "Не удалось найти ID трека в ссылке.\n\n"
            "Убедитесь, что ссылка содержит /track/число\n"
            "Пример: https://music.yandex.ru/album/1234567/track/7654321\n\n"
            "Отправьте /help для получения справки."
        )
        return

    try:
        # Создаём клиент Яндекс.Музыки
        client = Client(YANDEX_TOKEN).init()

        # Используем метод tracks() (с s на конце), который принимает список ID
        # Метод возвращает список треков
        tracks = client.tracks([track_id])

        if not tracks:
            await update.message.reply_text(
                "Трек не найден.\n\n"
                "Возможно он удалён или не доступен в вашем регионе"
            )
            return

        track = tracks[0]  # Берем первый (и единственный) трек

        # Получаем данные
        title = track.title
        artists = ", ".join([artist.name for artist in track.artists])
        duration_ms = track.duration_ms
        duration_sec = duration_ms // 1000
        minutes = duration_sec // 60
        seconds = duration_sec % 60

        # Формируем ответ
        response = (
            f"<b>Информация о треке</b> 🎉\n\n"
            f"<b>Название:</b> {title}\n"
            f"<b>Исполнитель:</b> {artists}\n"
            f"<b>Длительность:</b> {minutes}:{seconds:02d}\n\n"
            f"<i>Есть предложения по улучшению бота? Напиши /help</i>"
        )

        await update.message.reply_text(response, parse_mode="HTML")
        logger.info(f"Успешно: {title} - {artists}")

    except Exception as e:
        logger.error(f"Ошибка: {e}")
        await update.message.reply_text(
            "Не удалось найти информацию по этой ссылке.\n\n"
            "Возможные причины:\n"
            "• Ссылка ведёт на альбом или плейлист (нужен конкретный трек)\n"
            "• Трек недоступен в вашем регионе\n"
            "• Проблемы с API Яндекс.Музыки\n\n"
            "Отправьте /help для получения справки."
        )


# --- Запуск бота ---
def main():
    # Создаём приложение
    app = Application.builder().token(TELEGRAM_TOKEN).build()

    # Добавляем обработчики команд
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("help", help_command))

    # Добавляем обработчик текстовых сообщений (все остальные сообщения)
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    logger.info("🚀 Бот запущен и готов к работе!")
    logger.info("✅ Доступные команды: /start, /help")
    app.run_polling(allowed_updates=[])


if __name__ == "__main__":
    main()