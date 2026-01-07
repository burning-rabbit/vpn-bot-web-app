#!/bin/bash

# Скрипт для автоматической установки Telegram VPN Bot на сервер

set -e

BOT_DIR="/opt/telegram-vpn-bot"
SERVICE_NAME="telegram-vpn-bot"
CURRENT_USER=$(whoami)

echo "=========================================="
echo "Telegram VPN Bot - Установка"
echo "=========================================="

# Проверка прав root
if [ "$EUID" -eq 0 ]; then 
   echo "Пожалуйста, не запускайте скрипт от root. Используйте обычного пользователя."
   exit 1
fi

# Обновление системы
echo "Обновление системы..."
sudo apt update && sudo apt upgrade -y

# Установка зависимостей
echo "Установка Python и зависимостей..."
sudo apt install -y python3 python3-pip python3-venv

# Создание директории
echo "Создание директории для бота..."
sudo mkdir -p $BOT_DIR
sudo chown $CURRENT_USER:$CURRENT_USER $BOT_DIR

# Копирование файлов (если скрипт запущен из директории бота)
if [ -f "bot.py" ]; then
    echo "Копирование файлов..."
    cp -r * $BOT_DIR/ 2>/dev/null || true
    cp -r .env.example $BOT_DIR/ 2>/dev/null || true
else
    echo "ВНИМАНИЕ: Скрипт должен быть запущен из директории telegram-bot"
    echo "Или скопируйте файлы вручную в $BOT_DIR"
    read -p "Продолжить? (y/n) " -n 1 -r
    echo
    if [[ ! $REPLY =~ ^[Yy]$ ]]; then
        exit 1
    fi
fi

# Создание виртуального окружения
echo "Создание виртуального окружения..."
cd $BOT_DIR
python3 -m venv venv

# Активация и установка зависимостей
echo "Установка зависимостей Python..."
source venv/bin/activate
pip install --upgrade pip
pip install -r requirements.txt

# Создание .env файла если его нет
if [ ! -f "$BOT_DIR/.env" ]; then
    echo "Создание .env файла из примера..."
    cp .env.example .env
    echo ""
    echo "=========================================="
    echo "ВАЖНО: Отредактируйте файл .env:"
    echo "nano $BOT_DIR/.env"
    echo "=========================================="
    read -p "Нажмите Enter после редактирования .env файла..."
fi

# Создание systemd service
echo "Создание systemd service..."
sudo tee /etc/systemd/system/${SERVICE_NAME}.service > /dev/null <<EOF
[Unit]
Description=Telegram VPN Bot
After=network.target

[Service]
Type=simple
User=$CURRENT_USER
WorkingDirectory=$BOT_DIR
Environment="PATH=$BOT_DIR/venv/bin"
ExecStart=$BOT_DIR/venv/bin/python3 $BOT_DIR/bot.py
Restart=always
RestartSec=10
StandardOutput=journal
StandardError=journal

[Install]
WantedBy=multi-user.target
EOF

# Перезагрузка systemd
echo "Перезагрузка systemd..."
sudo systemctl daemon-reload

# Включение автозапуска
echo "Включение автозапуска..."
sudo systemctl enable ${SERVICE_NAME}

# Запуск сервиса
echo "Запуск сервиса..."
sudo systemctl start ${SERVICE_NAME}

# Проверка статуса
sleep 2
if sudo systemctl is-active --quiet ${SERVICE_NAME}; then
    echo ""
    echo "=========================================="
    echo "✅ Бот успешно установлен и запущен!"
    echo "=========================================="
    echo ""
    echo "Полезные команды:"
    echo "  Статус:    sudo systemctl status ${SERVICE_NAME}"
    echo "  Логи:      sudo journalctl -u ${SERVICE_NAME} -f"
    echo "  Остановить: sudo systemctl stop ${SERVICE_NAME}"
    echo "  Запустить:  sudo systemctl start ${SERVICE_NAME}"
    echo "  Перезапуск: sudo systemctl restart ${SERVICE_NAME}"
    echo ""
else
    echo ""
    echo "=========================================="
    echo "❌ Ошибка при запуске сервиса"
    echo "=========================================="
    echo "Проверьте логи: sudo journalctl -u ${SERVICE_NAME} -n 50"
    echo "Проверьте .env файл: nano $BOT_DIR/.env"
    exit 1
fi

