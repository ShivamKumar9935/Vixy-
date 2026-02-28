import os
import sys
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
import yt_dlp
import imageio_ffmpeg
from dotenv import load_dotenv

load_dotenv()

BOT_TOKEN = "8727736833:AAEGZy8IiGWtZFW5g6VknX7x6DzFiNm21uo"

if not BOT_TOKEN:
    print("ERROR: BOT_TOKEN not found in .env file")
    sys.exit(1)

DOWNLOAD_DIR = "./downloads"
os.makedirs(DOWNLOAD_DIR, exist_ok=True)


async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "🎵 *YouTube Audio Downloader*\n\n"
        "Send me a YouTube link and I'll send you the audio as an MP3!",
        parse_mode="Markdown"
    )


async def download_audio(update: Update, context: ContextTypes.DEFAULT_TYPE):
    url = update.message.text.strip()

    if "youtube.com" not in url and "youtu.be" not in url:
        await update.message.reply_text("❌ Please send a valid YouTube link.")
        return

    msg = await update.message.reply_text("⏳ Downloading audio, please wait...")

    ydl_opts = {
        "format": "bestaudio/best",
        "outtmpl": f"{DOWNLOAD_DIR}/%(title)s.%(ext)s",
        "postprocessors": [{
            "key": "FFmpegExtractAudio",
            "preferredcodec": "mp3",
            "preferredquality": "192",
        }],
        "ffmpeg_location": imageio_ffmpeg.get_ffmpeg_exe(),
        "quiet": True,
        "noplaylist": True,
    }

    filename = None
    info = None

    try:
        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            info = ydl.extract_info(url, download=True)
            filename = ydl.prepare_filename(info).rsplit(".", 1)[0] + ".mp3"

        if not os.path.exists(filename):
            await msg.edit_text("❌ Failed to process audio.")
            return

        # Telegram limit 50MB
        file_size = os.path.getsize(filename)
        if file_size > 50 * 1024 * 1024:
            await msg.edit_text("❌ File is too large (>50MB). Try a shorter video.")
            os.remove(filename)
            return

        await msg.edit_text("📤 Uploading to Telegram...")

        with open(filename, "rb") as audio_file:
            await update.message.reply_audio(
                audio=audio_file,
                title=info.get("title", "Audio"),
                performer=info.get("uploader", "Unknown"),
            )

        await msg.delete()

    except yt_dlp.utils.DownloadError as e:
        await msg.edit_text(f"❌ Download failed: {str(e)[:200]}")
    except Exception as e:
        await msg.edit_text(f"❌ Error: {str(e)[:200]}")
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