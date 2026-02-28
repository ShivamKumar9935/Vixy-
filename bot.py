import os
import sys
import asyncio
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import yt_dlp
import imageio_ffmpeg
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = os.getenv("BOT_TOKEN")

if not BOT_TOKEN:
    print("ERROR: BOT_TOKEN not found in .env file")
    sys.exit(1)

DOWNLOAD_DIR = "./downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.message:
        await update.message.reply_text(
            "🎵 *YouTube Audio Downloader*\n\n"
            "Send me a YouTube link and I'll send you the audio as an MP3!",
            parse_mode="Markdown"
        )


async def download_audio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return

    url = update.message.text.strip()

    if "youtube.com" not in url and "youtu.be" not in url:
        await update.message.reply_text("❌ Please send a valid YouTube link.")
        return

    msg = await update.message.reply_text("⏳ Downloading audio, please wait...")

    ydl_opts = {
        "format": "bestaudio/best",
        "outtmpl": f"{DOWNLOAD_DIR}/%(title).80s.%(ext)s",
        "postprocessors": [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
            "preferredquality": "192",
        }],
        "ffmpeg_location": imageio_ffmpeg.get_ffmpeg_exe(),
        "quiet": True,
        "noplaylist": True,
        "extractor_args": {  # Helps bypass some bot detection
            "youtube": {
                "player_client": ["android", "web"]
            }
        }
    }

    filename = None
    info = None

    try:
        loop = asyncio.get_event_loop()

        # Run blocking yt-dlp in thread
        def download():
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                return ydl.extract_info(url, download=True)

        info = await loop.run_in_executor(None, download)

        # Construct mp3 filename safely
        base = yt_dlp.YoutubeDL(ydl_opts).prepare_filename(info)
        filename = os.path.splitext(base)[0] + ".mp3"

        if not os.path.exists(filename):
            await msg.edit_text("❌ Failed to process audio.")
            return

        file_size = os.path.getsize(filename)

        # Telegram bot limit 50MB
        if file_size > 50 * 1024 * 1024:
            await msg.edit_text("❌ File is too large (>50MB). Try a shorter video.")
            os.remove(filename)
            return

        await msg.edit_text("📤 Uploading to Telegram...")

        with open(filename, "rb") as audio_file:
            await update.message.reply_document(
                document=audio_file,
                filename=os.path.basename(filename),
            )

        await msg.delete()

    except yt_dlp.utils.DownloadError:
        await msg.edit_text("❌ Download failed. Video may require login or is restricted.")
    except Exception as e:
        await msg.edit_text(f"❌ Unexpected error: {str(e)[:150]}")
    finally:
        if filename and os.path.exists(filename):
            os.remove(filename)


def main():
    app = (
        Application.builder()
        .token(BOT_TOKEN)
        .read_timeout(120)
        .write_timeout(120)
        .connect_timeout(60)
        .pool_timeout(60)
        .build()
    )

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, download_audio))

    print("Bot is running...")
    app.run_polling(drop_pending_updates=True)


if __name__ == "__main__":
    main()
