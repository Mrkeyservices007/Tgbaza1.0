#!/bin/bash

# -------------------------------
# Telegram GUI Monitor uchun setup skripti
# -------------------------------

echo "🔹 Virtual muhit yaratilmoqda..."
python3 -m venv sheyxkiller

echo "🔹 Virtual muhit faollashtirilmoqda..."
source sheyxkiller/bin/activate

echo "🔹 Requirements o‘rnatilmoqda..."
pip install --upgrade pip
pip install -r requirements.txt

echo "✅ Setup tugallandi! Virtual muhit faollashtirilgan va talablar o‘rnatilgan."
echo "🔹 Virtual muhitni faollashtirish uchun: source venv/bin/activate"
echo "🔹 Dasturni ishga tushirish: python3 bot2.py"

python3 bot2.py
