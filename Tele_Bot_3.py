import telebot
from youtube_transcript_api import YouTubeTranscriptApi
import re
import os
import csv
from datetime import datetime
import time

# Replace this with your bot token
TOKEN = "7234432071:AAFKNdDZbn9OP_RBEeCDu8jUVzL1OmoDi7U"
bot = telebot.TeleBot(TOKEN)

# Dictionary to store user language preferences
user_languages = {}

# File to store logs
LOG_FILE = "user_logs.csv"

# Function to initialize log file with headers (if it doesn't exist)
def init_log_file():
    if not os.path.exists(LOG_FILE):
        with open(LOG_FILE, "w", newline="") as file:
            writer = csv.writer(file)
            writer.writerow(["User ID", "Username", "First Name", "Last Name", "Action", "YouTube URL", "Timestamp"])

# Function to log user actions (start, YouTube search, etc.)
def log_user_activity(user, action, url=""):
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    with open(LOG_FILE, "a", newline="") as file:
        writer = csv.writer(file)
        writer.writerow([user.id, user.username, user.first_name, user.last_name, action, url, timestamp])

# Ensure the log file is initialized before starting the bot
init_log_file()

# Command Handler: Welcome Messages
@bot.message_handler(commands=['start', 'help'])
def send_welcome(message):
    log_user_activity(message.from_user, "Started Bot")  # Log user details
    bot.reply_to(message, "Hello! Send me a YouTube video link, and I'll fetch its transcript. \n\nUse /language to set your preferred language.")

# List of supported languages
LANGUAGES = {
    "English": "en",
    "Tamil": "ta",
    "Telugu": "te",
    "Malayalam": "ml"
}

# Function to extract YouTube video ID from the URL (Enhanced)
def extract_video_id(url):
    patterns = [
        r"youtube\.com\/watch\?v=([0-9A-Za-z_-]{11})",  # Normal YouTube URL
        r"youtu\.be\/([0-9A-Za-z_-]{11})",  # Short YouTube URL
        r"youtube\.com\/embed\/([0-9A-Za-z_-]{11})",  # Embedded videos
        r"youtube\.com\/v\/([0-9A-Za-z_-]{11})"  # Old format
    ]
    for pattern in patterns:
        match = re.search(pattern, url)
        if match:
            return match.group(1)
    return None

# Command to Set Language
@bot.message_handler(commands=['language'])
def choose_language(message):
    markup = telebot.types.ReplyKeyboardMarkup(one_time_keyboard=True, resize_keyboard=True)
    for lang in LANGUAGES.keys():
        markup.add(lang)
    
    msg = bot.send_message(message.chat.id, "Choose your subtitle language:", reply_markup=markup)
    bot.register_next_step_handler(msg, save_language)

def save_language(message):
    if message.text in LANGUAGES:
        user_languages[message.chat.id] = LANGUAGES[message.text]
        bot.reply_to(message, f"Language set to {message.text}. Now send a YouTube video link!")
    else:
        bot.reply_to(message, "Invalid choice. Please use /language and select a valid language.")

# Message Handler for YouTube Links
@bot.message_handler(func=lambda message: "youtube.com" in message.text or "youtu.be" in message.text)
def fetch_transcript(message):
    video_id = extract_video_id(message.text)
    
    if not video_id:
        bot.reply_to(message, "Invalid YouTube link. Please send a valid video URL.")
        return

    # Log the YouTube link user is searching for
    log_user_activity(message.from_user, "Requested Transcript", message.text)

    # Get user's preferred language, default to English
    lang_code = user_languages.get(message.chat.id, "en")

    try:
        transcript = YouTubeTranscriptApi.get_transcript(video_id, languages=[lang_code])
        transcript_text = "\n".join([entry['text'] for entry in transcript])

        # Send transcript in chunks (Telegram has a character limit)
        for i in range(0, len(transcript_text), 4000):
            bot.send_message(message.chat.id, transcript_text[i:i+4000])

    except Exception as e:
        bot.reply_to(message, f"Error fetching transcript: {e}")

# Graceful bot polling to avoid crashes
print("Bot is running...")

while True:
    try:
        bot.polling(none_stop=True, interval=0.5)
    except Exception as e:
        print(f"Bot crashed due to: {e}")
        time.sleep(5)  # Wait before retrying
