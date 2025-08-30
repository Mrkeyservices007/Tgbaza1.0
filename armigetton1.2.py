#!/usr/bin/env python3
# telegram_private_logger.py

from telethon import TelegramClient, events, functions, types
from gtts import gTTS
import os, subprocess, shutil, platform, json
from zoneinfo import ZoneInfo

# -------------------------------
# Konfiguratsiya
# -------------------------------
api_id = 
api_hash = ''
LOCAL_TZ = ZoneInfo("Asia/Samarkand")

base_dir = os.path.dirname(os.path.abspath(__file__))
image_dir = os.path.join(base_dir, 'images')
log_file = os.path.join(base_dir, 'telegram_bot.log')
state_file = os.path.join(base_dir, 'users_state.json')

os.makedirs(image_dir, exist_ok=True)

# Ranglar
C_RESET = "\033[0m"
C_GREEN = "\033[92m"
C_YELLOW = "\033[93m"
C_CYAN = "\033[96m"
C_MAGENTA = "\033[95m"
C_RED = "\033[91m"
C_BOLD = "\033[1m"

client = TelegramClient('session_name', api_id, api_hash)

# -------------------------------
# Holatni yuklash/saqlash
# -------------------------------
def load_state():
    if os.path.exists(state_file):
        try:
            with open(state_file, "r", encoding="utf-8") as f:
                return json.load(f)
        except:
            return {}
    return {}

def save_state(state: dict):
    try:
        with open(state_file, "w", encoding="utf-8") as f:
            json.dump(state, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"{C_RED}State saqlash xatolik:{C_RESET} {e}")

# -------------------------------
# Status formatlash
# -------------------------------
def format_status(status_obj):
    try:
        if isinstance(status_obj, types.UserStatusOnline):
            return "🟢 Online"
        elif isinstance(status_obj, types.UserStatusOffline):
            return "🔴 Offline"
        elif isinstance(status_obj, types.UserStatusRecently):
            return "🟡 Oxirgi paytlarda online"
        elif isinstance(status_obj, types.UserStatusLastWeek):
            return "🟠 Oxirgi hafta ichida online"
        elif isinstance(status_obj, types.UserStatusLastMonth):
            return "🔵 Oxirgi oy ichida online"
        else:
            return "❔ Status mavjud emas"
    except:
        return "❔ Statusni aniqlash mumkin emas"

# -------------------------------
# Xabar matnini olish (har qanday tip uchun)
# -------------------------------
def get_message_text(event):
    try:
        if event.message.message:
            return event.message.message
        elif event.message.fwd_from:
            return f"[Forwarded message]"
        elif event.message.media:
            return f"[Media: {type(event.message.media).__name__}]"
        else:
            return "[Empty or unsupported message type]"
    except:
        return "[Xabarni olishda xatolik]"

# -------------------------------
# Log yozish
# -------------------------------
def append_log(entry: dict):
    try:
        with open(log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(entry, ensure_ascii=False) + "\n")
    except Exception as e:
        print(f"{C_RED}Log yozishda xatolik:{C_RESET} {e}")

# -------------------------------
# Rangli terminalga chiqarish
# -------------------------------
def print_colored(entry: dict, about_changed: bool):
    header = f"{C_BOLD}{C_GREEN}Time:{C_RESET} {entry.get('time')}\n"
    id_phone = f"{C_YELLOW}ID:{C_RESET} {entry.get('id')}    {C_CYAN}Phone:{C_RESET} {entry.get('phone')}\n"
    username = f"{C_MAGENTA}Username:{C_RESET} {entry.get('username')}\n"
    name = f"{C_CYAN}Name:{C_RESET} {entry.get('first_name')} {entry.get('last_name')}\n"
    about = f"{C_GREEN}About/Bio:{C_RESET} {entry.get('about')}\n"
    status = f"{C_CYAN}Status:{C_RESET} {entry.get('status')}\n"
    photo = f"{C_YELLOW}Profile photo:{C_RESET} {entry.get('photo')}\n"
    last_message = f"{C_MAGENTA}Last message:{C_RESET} {entry.get('last_message')}\n"
    sep = "-----------------------------------------\n"

    if about_changed:
        change_note = f"{C_RED}{C_BOLD}!! ABOUT CHANGED !!{C_RESET}\n"
        print(header + change_note + id_phone + username + name + about + status + photo + last_message + sep)
    else:
        print(header + id_phone + username + name + about + status + photo + last_message + sep)

# -------------------------------
# Ovoz ijro
# -------------------------------
def play_audio(file):
    system = platform.system().lower()
    try:
        if "linux" in system:
            if shutil.which("termux-media-player"):
                subprocess.call(['termux-media-player', 'play', file])
            elif shutil.which("mpv"):
                subprocess.call(['mpv', '--no-terminal', file])
            elif shutil.which("aplay"):
                subprocess.call(['aplay', file])
        elif "windows" in system:
            os.startfile(file)
        elif "darwin" in system:
            subprocess.call(["afplay", file])
    except Exception as e:
        print(f"{C_RED}Ovoz ijro xatolik:{C_RESET} {e}")

# -------------------------------
# Xabar handler (faqat private)
# -------------------------------
@client.on(events.NewMessage)
async def handler(event):
    # Faqat private messages
    if not event.is_private:
        return

    sender = await event.get_sender()
    if sender is None:
        return

    try:
        user_full = await client(functions.users.GetFullUserRequest(id=sender.id))
    except:
        user_full = None

    # Vaqt
    msg_time = event.message.date
    try:
        local_time = msg_time.astimezone(LOCAL_TZ).strftime('%Y-%m-%d %H:%M:%S')
    except:
        local_time = msg_time.strftime('%Y-%m-%d %H:%M:%S')

    # About / bio
    about_text = "Bio mavjud emas"
    try:
        if user_full and getattr(user_full.full_user, 'about', None):
            about_text = user_full.full_user.about
    except: pass

    # Status
    status_text = "Status mavjud emas"
    try:
        if user_full and getattr(user_full.full_user, 'status', None):
            status_text = format_status(user_full.full_user.status)
    except: pass

    # Profil rasmi
    profile_photo_path = "Profil rasmi yo'q"
    try:
        if sender.photo:
            profile_photo_path = os.path.join(image_dir, f"{sender.id}_profile.jpg")
            await client.download_profile_photo(sender, file=profile_photo_path)
    except: pass

    entry = {
        "time": local_time,
        "id": sender.id,
        "phone": sender.phone or "Telefon mavjud emas",
        "username": sender.username or "Username mavjud emas",
        "first_name": sender.first_name or "",
        "last_name": sender.last_name or "",
        "about": about_text,
        "status": status_text,
        "photo": profile_photo_path,
        "last_message": get_message_text(event)
    }

    # Holatni tekshirish
    state = load_state()
    user_key = str(sender.id)
    prev_about = state.get(user_key, {}).get("about")
    about_changed = prev_about != about_text if prev_about else False

    state[user_key] = {
        "about": about_text,
        "last_seen": entry["time"],
        "username": entry["username"]
    }
    save_state(state)

    append_log(entry)
    print_colored(entry, about_changed=about_changed)

    # Ovozli eslatma
    try:
        if about_changed:
            voice_text = f"Foydalanuvchi bio o'zgardi: {entry['username']}"
        else:
            voice_text = f"Yangi xabar: {sender.first_name or sender.username or 'user'}, yozilgan habar: {entry.get('last_message')}"
        tts = gTTS(text=voice_text, lang='ru')
        tts_file = "notify.mp3"
        tts.save(tts_file)
        play_audio(tts_file)
    except: pass

# -------------------------------
# Main
# -------------------------------
async def main():
    await client.start()
    print(f"{C_GREEN}🤖 Bot ishga tushdi. Faqat sizga yuborilgan xabarlar o'qiladi.{C_RESET}")

if __name__ == "__main__":
    with client:
        client.loop.run_until_complete(main())
        client.run_until_disconnected()
