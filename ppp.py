#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os, json, asyncio, ssl, subprocess, hashlib, netifaces, logging
from datetime import datetime
from telethon import TelegramClient, events
from cryptography.fernet import Fernet

# ================= CONFIG =================
api_id = 
api_hash = ''
session_name = 'session'
ROOT_DIR = './data'

TCP_HOST = "0.0.0.0"
TCP_PORT = 9001

MTPROTO_PATH = "/home/lspro/Рабочий стол/2/MTProxy/objs/bin/mtproto-proxy"
MTSECRET = "1234567890abcdef1234567890abcdef"
MTPORT = 8888

# ================= LOGGING =================
os.makedirs(ROOT_DIR, exist_ok=True)
os.makedirs(os.path.join(ROOT_DIR, "logs"), exist_ok=True)
os.makedirs(os.path.join(ROOT_DIR, "media"), exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    handlers=[
        logging.FileHandler(os.path.join(ROOT_DIR, "logs", "bot.log")),
        logging.StreamHandler()
    ]
)

# ================= GLOBALS =================
key = Fernet.generate_key()
cipher = Fernet(key)
client = TelegramClient(session_name, api_id, api_hash)
tcp_clients = []  # TCP mijozlar ro‘yxati

# ================= HELPERS =================
def current_ts():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

def encrypt_text(text):
    return cipher.encrypt(text.encode()).decode()

def calc_hash(data: str):
    return hashlib.sha256(data.encode()).hexdigest()

def save_log(category, filename, data):
    folder = os.path.join(ROOT_DIR, category)
    os.makedirs(folder, exist_ok=True)
    path = os.path.join(folder, filename)
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(data, ensure_ascii=False) + "\n")

def wlan0_active():
    for iface in netifaces.interfaces():
        if iface.startswith(('wlan','eth')):
            addrs = netifaces.ifaddresses(iface)
            if netifaces.AF_INET in addrs:
                return True, iface, addrs[netifaces.AF_INET][0]['addr']
    return False, None, None

def ensure_certificates():
    if not os.path.exists("cert.pem") or not os.path.exists("key.pem"):
        logging.info("[*] SSL sertifikatlari yaratilmoqda...")
        os.system("openssl req -new -x509 -days 365 -nodes -subj '/CN=localhost' -out cert.pem -keyout key.pem")

def ensure_mtproto_files():
    if not os.path.exists("proxy-secret"):
        os.system("curl -s https://core.telegram.org/getProxySecret -o proxy-secret")
    if not os.path.exists("proxy-multi.conf"):
        os.system("curl -s https://core.telegram.org/getProxyConfig -o proxy-multi.conf")

# ================= TCP SERVER =================
async def handle_client(reader, writer):
    addr = writer.get_extra_info('peername')
    logging.info(f"[+] TCP Client connected: {addr}")
    tcp_clients.append(writer)
    try:
        while True:
            data = await reader.readline()
            if not data:
                break
            payload = data.decode().strip()
            traffic_hash = calc_hash(payload)
            traffic_log = {
                "type": "tcp",
                "addr": addr,
                "payload": payload,
                "hash": traffic_hash,
                "timestamp": current_ts()
            }
            logging.info(f"[TCP TRAFFIC] {traffic_log}")
            save_log("logs", "tcp.log", traffic_log)
    except Exception as e:
        logging.error(f"[-] Client error: {e}")
    finally:
        tcp_clients.remove(writer)
        writer.close()
        await writer.wait_closed()

async def run_tcp_server():
    ensure_certificates()
    ssl_ctx = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
    ssl_ctx.load_cert_chain("cert.pem", "key.pem")
    server = await asyncio.start_server(handle_client, TCP_HOST, TCP_PORT, ssl=ssl_ctx)
    logging.info(f"[*] Secure TCP server running on {TCP_HOST}:{TCP_PORT}")
    async with server:
        await server.serve_forever()

async def broadcast(data):
    msg = (json.dumps(data) + "\n").encode()
    for writer in tcp_clients:
        try:
            writer.write(msg)
            await writer.drain()
        except:
            tcp_clients.remove(writer)

# ================= TELEGRAM MONITOR =================
async def monitor_telegram():
    await client.start()
    logging.info("[*] Telegram monitoring started...")
    @client.on(events.NewMessage)
    async def handler(event):
        chat = await event.get_chat()
        sender = await event.get_sender()
        text = event.raw_text or "[MEDIA/EMPTY]"
        timestamp = current_ts()
        photo_flag = bool(event.message.media)
        encrypted_text = encrypt_text(text)
        traffic_hash = calc_hash(text)
        log_data = {
            "username": getattr(sender,'username','[NONE]'),
            "chat": getattr(chat,'title','private'),
            "message": text,
            "telegram_id": sender.id if sender else None,
            "photo": photo_flag,
            "encrypted": encrypted_text,
            "hash": traffic_hash,
            "timestamp": timestamp
        }
        logging.info(f"[TELEGRAM] {log_data}")
        save_log("logs", "telegram.log", log_data)
        await broadcast(log_data)
        if event.message.media:
            filename = os.path.join(ROOT_DIR, "media", f"{timestamp.replace(' ','_')}_{sender.id}.jpg")
            try:
                await client.download_media(event.message, filename)
                logging.info(f"[MEDIA] Saved: {filename}")
            except Exception as e:
                logging.error(f"[-] Media save error: {e}")
    await client.run_until_disconnected()

# ================= MTPROTO =================
def run_mtproto():
    if os.path.exists(MTPROTO_PATH):
        ensure_mtproto_files()
        logging.info("[*] Starting MTProto Proxy...")
        subprocess.Popen([
            MTPROTO_PATH,
            "-u", "nobody",
            "-p", str(MTPORT),
            "-H", "443",
            "-S", MTSECRET,
            "--aes-pwd", "proxy-secret", "proxy-multi.conf",
            "-M", "1"
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    else:
        logging.warning("[-] MTProto binary not found. Skip.")

# ================= DASHBOARD =================
async def dashboard():
    while True:
        active, iface, ip = wlan0_active()
        logging.info(f"[*] WLAN Active: {active}, Interface: {iface}, IP: {ip}, TCP clients: {len(tcp_clients)}")
        await asyncio.sleep(10)

# ================= MAIN =================
async def main():
    run_mtproto()
    await asyncio.gather(
        run_tcp_server(),
        monitor_telegram(),
        dashboard()
    )

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        logging.info("[!] Dastur to‘xtatildi.")
