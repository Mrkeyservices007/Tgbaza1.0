#!/usr/bin/env python3
# telegram_full_monitor_expanded_v2.py

from telethon import TelegramClient, events, types, functions
from telethon.tl.types import Channel, Chat, User
import os, json
from zoneinfo import ZoneInfo

# -------------------------------
# Konfiguratsiya
# -------------------------------
api_id = 
api_hash = ''
LOCAL_TZ = ZoneInfo("Asia/Samarkand")

base_dir = os.path.dirname(os.path.abspath(__file__))
log_dir = os.path.join(base_dir, 'logs')
os.makedirs(log_dir, exist_ok=True)

client = TelegramClient('session_name', api_id, api_hash)

# Ranglar
C_RESET = "\033[0m"
C_GREEN = "\033[92m"
C_YELLOW = "\033[93m"
C_CYAN = "\033[96m"
C_MAGENTA = "\033[95m"
C_RED = "\033[91m"
C_BOLD = "\033[1m"

# -------------------------------
# Helper: faylga yozish
# -------------------------------
def append_log(file_path, entry):
    os.makedirs(os.path.dirname(file_path), exist_ok=True)
    with open(file_path, "a", encoding="utf-8") as f:
        f.write(json.dumps(entry, ensure_ascii=False) + "\n")

# -------------------------------
# Status formatlash
# -------------------------------
def format_status(status_obj):
    try:
        if isinstance(status_obj, types.UserStatusOnline):
            return "🟢 Online"
        elif isinstance(status_obj, types.UserStatusOffline):
            return f"🔴 Offline, last seen {status_obj.was_online}"
        elif isinstance(status_obj, types.UserStatusRecently):
            return "🟡 Recently Online"
        elif isinstance(status_obj, types.UserStatusLastWeek):
            return "🟠 Last week online"
        elif isinstance(status_obj, types.UserStatusLastMonth):
            return "🔵 Last month online"
        else:
            return "❔ Unknown"
    except:
        return "❔ Unknown"

# -------------------------------
# Foydalanuvchi malumotlarini olish
# -------------------------------
async def get_user_info(user):
    if isinstance(user, User):
        info = {
            "id": user.id,
            "username": user.username or "",
            "first_name": user.first_name or "",
            "last_name": user.last_name or "",
            "phone": getattr(user, 'phone', "") or "",
            "bio": "",
            "status": ""
        }
        try:
            full_user = await client(functions.users.GetFullUserRequest(id=user.id))
            info["bio"] = getattr(full_user.full_user, 'about', "")
            info["status"] = format_status(getattr(full_user.full_user, 'status', None))
        except:
            pass
        return info
    elif isinstance(user, Channel):
        return {
            "id": user.id,
            "title": getattr(user, 'title', ""),
            "type": "channel"
        }
    elif isinstance(user, Chat):
        return {
            "id": user.id,
            "title": getattr(user, 'title', ""),
            "type": "chat"
        }
    else:
        return {"id": None}

# -------------------------------
# Foydalanuvchi profilini saqlash
# -------------------------------
async def save_user_profile(user_info, folder_path):
    if not user_info:
        return
    user_folder = os.path.join(folder_path, str(user_info.get("username") or user_info.get("id")))
    os.makedirs(user_folder, exist_ok=True)
    json_file = os.path.join(user_folder, "info.json")
    with open(json_file, "w", encoding="utf-8") as f:
        json.dump(user_info, f, ensure_ascii=False, indent=2)
    # Profil rasmini yuklash
    if "id" in user_info and "type" not in user_info:
        try:
            profile_file = os.path.join(user_folder, "profile.jpg")
            await client.download_profile_photo(user_info["id"], file=profile_file)
        except:
            pass

# -------------------------------
# Gruppadagi foydalanuvchilarni olish
# -------------------------------
async def fetch_group_members(group):
    try:
        group_title = getattr(group, 'title', f"group_{group.id}")
        folder_path = os.path.join(log_dir, "groups", group_title)
        os.makedirs(folder_path, exist_ok=True)
        members = await client.get_participants(group)
        for user in members:
            info = await get_user_info(user)
            await save_user_profile(info, folder_path)
    except Exception as e:
        print(f"{C_RED}Foydalanuvchilarni olishda xatolik:{C_RESET} {e}")

# -------------------------------
# Private xabarlar
# -------------------------------
@client.on(events.NewMessage)
async def private_handler(event):
    if not event.is_private:
        return
    sender = await event.get_sender()
    text = event.raw_text
    info = await get_user_info(sender)
    entry = {
        "user": info,
        "message": text
    }
    file_path = os.path.join(log_dir, "private", "private_messages.log")
    append_log(file_path, entry)
    folder_path = os.path.join(log_dir, "private", "users")
    await save_user_profile(info, folder_path)
    print(f"{C_GREEN}[PRIVATE]{C_RESET} {info.get('first_name','')} ({info.get('username','')}): {text}")

# -------------------------------
# Kanal postlari
# -------------------------------
@client.on(events.NewMessage)
async def channel_handler(event):
    if getattr(event.chat, 'broadcast', False):
        sender = await event.get_sender()
        text = event.raw_text
        channel_title = getattr(event.chat, 'title', "UnknownChannel")
        file_path = os.path.join(log_dir, "channels", f"{channel_title}.log")
        info = await get_user_info(sender) if sender else {}
        entry = {
            "channel": channel_title,
            "post_by": info,
            "message": text
        }
        append_log(file_path, entry)
        print(f"{C_CYAN}[CHANNEL:{channel_title}]{C_RESET} {text}")

# -------------------------------
# Gruppadagi yangi xabarlar
# -------------------------------
@client.on(events.NewMessage)
async def group_handler(event):
    if getattr(event.chat, 'megagroup', False):
        group_title = getattr(event.chat, 'title', f"group_{event.chat_id}")
        folder_path = os.path.join(log_dir, "groups", group_title)
        os.makedirs(folder_path, exist_ok=True)
        msg_file = os.path.join(folder_path, "messages.log")

        sender = await event.get_sender()
        user_info = await get_user_info(sender)
        entry_msg = {
            "group": group_title,
            "user": user_info,
            "message": event.raw_text
        }
        append_log(msg_file, entry_msg)
        await save_user_profile(user_info, folder_path)
        print(f"{C_YELLOW}[GROUP:{group_title}]{C_RESET} {user_info.get('first_name','')}: {event.raw_text}")

# -------------------------------
# Foydalanuvchi qo‘shildi/chiqdi
# -------------------------------
@client.on(events.ChatAction)
async def user_action(event):
    if getattr(event.chat, 'megagroup', False):
        group_title = getattr(event.chat, 'title', f"group_{event.chat_id}")
        folder_path = os.path.join(log_dir, "groups", group_title)
        os.makedirs(folder_path, exist_ok=True)

        action = ""
        if event.user_added:
            action = "added"
        elif event.user_left:
            action = "left"
        elif event.user_kicked:
            action = "kicked"

        user = await event.get_user()
        user_info = await get_user_info(user)
        entry = {
            "user": user_info,
            "action": action
        }
        members_file = os.path.join(folder_path, "members.log")
        append_log(members_file, entry)
        await save_user_profile(user_info, folder_path)
        print(f"{C_MAGENTA}[GROUP:{group_title}] {user_info.get('first_name','')} {action}")

# -------------------------------
# Main
# -------------------------------
async def main():
    await client.start()
    print(f"{C_GREEN}🤖 Bot ishga tushdi. Gruppalar, kanallar va private xabarlar real vaqtda loglanadi.{C_RESET}")

    dialogs = await client.get_dialogs()
    for dialog in dialogs:
        entity = dialog.entity
        if isinstance(entity, Channel) and getattr(entity, 'megagroup', False):
            await fetch_group_members(entity)
        elif isinstance(entity, Chat):
            await fetch_group_members(entity)

    await client.run_until_disconnected()

if __name__ == "__main__":
    with client:
        client.loop.run_until_complete(main())

