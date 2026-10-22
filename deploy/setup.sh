#!/bin/bash
# Скрипт установки бота на VPS

set -e

echo "=== Установка Telegram бота ==="

# Обновление системы
apt update && apt upgrade -y

# Установка Python и зависимостей
apt install -y python3.11 python3.11-venv python3-pip git

# Создание директории для бота
mkdir -p /opt/telegram-bot
cd /opt/telegram-bot

# Создание виртуального окружения
python3.11 -m venv venv
source venv/bin/activate

# Установка зависимостей
pip install --upgrade pip
pip install -r requirements.txt

echo "=== Установка завершена ==="
echo "Теперь создайте systemd сервис командой:"
echo "sudo cp /opt/telegram-bot/deploy/bot.service /etc/systemd/system/"
echo "sudo systemctl daemon-reload"
echo "sudo systemctl enable telegram-bot"
echo "sudo systemctl start telegram-bot"
