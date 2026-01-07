"""Command handlers for Telegram bot."""
import logging
import re
from urllib.parse import quote
from typing import Dict, Any
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup, WebAppInfo
from telegram.ext import ContextTypes
from services.xui_service import XUIService
from config import WEB_APP_URL

logger = logging.getLogger(__name__)
xui_service = XUIService()


async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /start command."""
    try:
        user = update.effective_user
        telegram_user_id = user.id if user else None
        
        # Check if user has subscriptions
        has_subscriptions = False
        if telegram_user_id and user.username:
            try:
                all_subscriptions = xui_service.get_all_user_subscriptions(telegram_user_id, user.username)
                has_subscriptions = len(all_subscriptions) > 0
            except Exception as e:
                logger.error(f"Error checking subscriptions in start_command: {str(e)}")
                has_subscriptions = False
        
        welcome_message = (
            f"Привет, {user.first_name if user else 'пользователь'}! 👋\n\n"
            "Я бот для получения доступа к SANI_VPN.\n\n"
        )
        
        if has_subscriptions:
            welcome_message += "Выберите действие:"
            keyboard = [
                [InlineKeyboardButton("📋 Активные подписки", callback_data="get_subscription_link")],
                [InlineKeyboardButton("➕ Добавить устройство", callback_data="add_device")],
                [InlineKeyboardButton("💬 Для получения помощи нажми сюда", url="https://t.me/sanya_na_svyazi")]
            ]
        else:
            welcome_message += "Нажмите кнопку ниже, чтобы настроить подключение."
            keyboard = [
                [InlineKeyboardButton("🔗 Получить доступ к SANI_VPN", callback_data="get_vpn")],
                [InlineKeyboardButton("💬 Для получения помощи нажми сюда", url="https://t.me/sanya_na_svyazi")]
            ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        if update.message:
            await update.message.reply_text(
                welcome_message,
                reply_markup=reply_markup
            )
        elif update.callback_query:
            await update.callback_query.message.reply_text(
                welcome_message,
                reply_markup=reply_markup
            )
    except Exception as e:
        logger.error(f"Error in start_command: {str(e)}")
        if update.message:
            await update.message.reply_text("❌ Произошла ошибка. Попробуйте позже.")


async def help_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /help command."""
    try:
        user = update.effective_user
        telegram_user_id = user.id if user else None
        
        # Check if user has subscriptions
        has_subscriptions = False
        if telegram_user_id and user.username:
            try:
                all_subscriptions = xui_service.get_all_user_subscriptions(telegram_user_id, user.username)
                has_subscriptions = len(all_subscriptions) > 0
            except Exception as e:
                logger.error(f"Error checking subscriptions in help_command: {str(e)}")
                has_subscriptions = False
        
        help_message = (
            "📖 Справка по использованию бота:\n\n"
            "• /start - Начать работу с ботом\n"
            "• /help - Показать эту справку\n"
            "• /get_vpn - Получить ссылку на VPN подписку\n"
            "• /devices - Показать список ваших устройств\n\n"
        )
        
        if has_subscriptions:
            help_message += "Используйте кнопки ниже для управления подписками."
            keyboard = [
                [InlineKeyboardButton("📋 Активные подписки", callback_data="get_subscription_link")],
                [InlineKeyboardButton("➕ Добавить устройство", callback_data="add_device")],
                [InlineKeyboardButton("💬 Для получения помощи нажми сюда", url="https://t.me/sanya_na_svyazi")]
            ]
        else:
            help_message += "Просто нажмите кнопку 'Получить VPN доступ' для создания вашей подписки."
            keyboard = [
                [InlineKeyboardButton("🔗 Получить доступ к SANI_VPN", callback_data="get_vpn")],
                [InlineKeyboardButton("💬 Для получения помощи нажми сюда", url="https://t.me/sanya_na_svyazi")]
            ]
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        if update.message:
            await update.message.reply_text(
                help_message,
                reply_markup=reply_markup
            )
        elif update.callback_query:
            await update.callback_query.message.reply_text(
                help_message,
                reply_markup=reply_markup
            )
    except Exception as e:
        logger.error(f"Error in help_command: {str(e)}")
        if update.message:
            await update.message.reply_text("❌ Произошла ошибка. Попробуйте позже.")


async def get_vpn_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /get_vpn command."""
    await handle_device_selection(update, context)


async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle button callbacks."""
    query = update.callback_query
    await query.answer()
    
    if query.data == "get_vpn":
        await handle_device_selection(update, context)
    elif query.data == "setup_iphone_mac":
        await handle_setup_iphone_mac(update, context)
    elif query.data == "setup_android":
        await handle_setup_android(update, context)
    elif query.data == "setup_windows_linux":
        await handle_setup_windows_linux(update, context)
    elif query.data == "app_downloaded":
        await handle_app_downloaded(update, context)
    elif query.data == "generate_subscription":
        # This callback is kept for backward compatibility, but now app_downloaded directly calls generation
        await handle_generate_subscription(update, context)
    elif query.data == "get_subscription_link":
        await handle_get_subscription_link(update, context)
    elif query.data == "add_device":
        await handle_add_device(update, context)
    elif query.data.startswith("select_subscription_"):
        # Handle subscription selection: select_subscription_{sub_id}
        sub_id = query.data.replace("select_subscription_", "")
        await handle_select_subscription(update, context, sub_id)
    elif query.data.startswith("device_name_"):
        # Handle device name selection from buttons: device_name_{name}
        device_name = query.data.replace("device_name_", "")
        await handle_device_name_selected(update, context, device_name)
    elif query.data == "enter_custom_device_name":
        await handle_enter_custom_device_name(update, context)


async def handle_device_selection(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle device selection - first step after clicking 'Get VPN'."""
    query = update.callback_query
    if query:
        await query.answer()
        reply_to_message = query.message
    else:
        reply_to_message = update.message
    
    device_message = "📱 Выберите ваше устройство для скачивания приложения:"
    
    device_keyboard = [
        [InlineKeyboardButton("🍎 iPhone / Mac", callback_data="setup_iphone_mac")],
        [InlineKeyboardButton("🤖 Android", callback_data="setup_android")],
        [InlineKeyboardButton("💻 Windows / Linux", callback_data="setup_windows_linux")],
        [InlineKeyboardButton("💬 Для получения помощи нажми сюда", url="https://t.me/sanya_na_svyazi")]
    ]
    device_reply_markup = InlineKeyboardMarkup(device_keyboard)
    
    if query:
        await query.message.reply_text(
            device_message,
            reply_markup=device_reply_markup
        )
    else:
        await reply_to_message.reply_text(
            device_message,
            reply_markup=device_reply_markup
        )


async def handle_generate_subscription(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle subscription generation after app is downloaded."""
    query = update.callback_query
    await query.answer()
    
    user = update.effective_user
    telegram_user_id = user.id
    
    # Step 1: Send "processing" message (NEW MESSAGE)
    processing_msg = await query.message.reply_text("⏳ Создаю вашу подписку...")
    
    try:
        # Check if user has username set
        if not user.username:
            error_message = (
                "❌ У вас не установлен username в Telegram.\n\n"
                "Для получения VPN доступа необходимо:\n"
                "1. Открыть настройки Telegram\n"
                "2. Установить username (имя пользователя)\n"
                "3. Попробовать снова\n\n"
                "Username должен быть уникальным и не должен повторяться."
            )
            
            await processing_msg.edit_text(error_message)
            return
        
        # Get device_name from context (for additional devices)
        device_name = context.user_data.get("device_name")
        
        # Check if user already exists by username (only for first device)
        existing_subscription = None
        if not device_name:
            # For first device, check if base username exists
            try:
                existing_subscription = xui_service.get_user_subscription(telegram_user_id, user.username)
            except Exception as e:
                logger.error(f"Error checking existing subscription: {str(e)}")
                existing_subscription = None
        
        result = None
        subscription_url_to_store = None
        is_new_subscription = False
        
        if existing_subscription and not device_name:
            # User already has first subscription
            subscription_url_to_store = existing_subscription
            is_new_subscription = False
        else:
            # Create new user (first device or additional device)
            try:
                result = xui_service.create_user(telegram_user_id, user.username, device_name)
            except Exception as e:
                logger.error(f"Error creating user: {str(e)}")
                import traceback
                traceback.print_exc()
                result = None
            
            if result:
                if result.get("success"):
                    subscription_url_to_store = result.get("subscription_url")
                    is_new_subscription = True
                elif result.get("error") == "username_exists":
                    existing_url = result.get("subscription_url")
                    if existing_url:
                        subscription_url_to_store = existing_url
                        is_new_subscription = False
                    else:
                        error_message = (
                            f"⚠️ Пользователь с именем '{user.username}' уже существует в системе.\n\n"
                            "Пожалуйста, свяжитесь с администратором."
                        )
                        await processing_msg.edit_text(error_message)
                        return
                elif result.get("error") == "username_required":
                    error_message = result.get("message", "Имя пользователя не указано.")
                    await processing_msg.edit_text(error_message)
                    return
                else:
                    error_message = (
                        "❌ Ошибка при создании подписки.\n\n"
                        "Пожалуйста, попробуйте позже или свяжитесь с администратором."
                    )
                    await processing_msg.edit_text(error_message)
                    return
            else:
                error_message = (
                    "❌ Ошибка при создании подписки.\n\n"
                    "Пожалуйста, попробуйте позже или свяжитесь с администратором."
                )
                await processing_msg.edit_text(error_message)
                return
        
        if not subscription_url_to_store:
            error_message = (
                "❌ Не удалось получить ссылку на подписку.\n\n"
                "Пожалуйста, попробуйте позже или свяжитесь с администратором."
            )
            await processing_msg.edit_text(error_message)
            return
        
        # Store subscription URL in context for later use
        context.user_data["subscription_url"] = subscription_url_to_store
        
        # Step 2: Edit processing message to show result with copy button
        if is_new_subscription:
            result_message = (
                "✅ Ваша подписка успешно создана!\n\n"
                "Для настройки VPN приложения выполните следующие шаги:\n\n"
                "1️⃣ Нажмите кнопку \"📋 Скопировать ссылку\" ниже - ссылка будет скопирована в буфер обмена\n\n"
                "2️⃣ Откройте ваше VPN приложение (HAPP Proxy Utility Plus / v2rayNG / v2rayN)\n\n"
                "3️⃣ Нажмите на ➕ в правом верхнем углу экрана\n\n"
                "4️⃣ Нажмите «Вставить из буфера обмена» (Paste from Clipboard)\n\n"
                "5️⃣ Подключитесь к VPN"
            )
        else:
            result_message = (
                "✅ У вас уже есть активная подписка!\n\n"
                "Для настройки VPN приложения выполните следующие шаги:\n\n"
                "1️⃣ Нажмите кнопку \"📋 Скопировать ссылку\" ниже - ссылка будет скопирована в буфер обмена\n\n"
                "2️⃣ Откройте ваше VPN приложение (HAPP Proxy Utility Plus / v2rayNG / v2rayN)\n\n"
                "3️⃣ Нажмите на ➕ в правом верхнем углу экрана\n\n"
                "4️⃣ Нажмите «Вставить из буфера обмена» (Paste from Clipboard)\n\n"
                "5️⃣ Подключитесь к VPN"
            )
        
        # Add copy button if WEB_APP_URL is configured
        result_keyboard = []
        if WEB_APP_URL:
            copy_url = f"{WEB_APP_URL}?url={quote(subscription_url_to_store)}"
            result_keyboard.append([
                InlineKeyboardButton("📋 Скопировать ссылку", web_app=WebAppInfo(url=copy_url))
            ])
        
        # Add navigation buttons
        # Check if user has multiple subscriptions
        try:
            all_subscriptions = xui_service.get_all_user_subscriptions(telegram_user_id, user.username)
            has_multiple = len(all_subscriptions) > 1
        except Exception as e:
            logger.error(f"Error checking subscriptions for navigation: {str(e)}")
            has_multiple = False
        
        # Add navigation buttons
        nav_buttons = []
        if has_multiple:
            nav_buttons.append(InlineKeyboardButton("📱 Мои устройства", callback_data="get_subscription_link"))
        nav_buttons.append(InlineKeyboardButton("➕ Добавить устройство", callback_data="add_device"))
        
        if nav_buttons:
            result_keyboard.append(nav_buttons)
        
        # Add help button in separate row
        result_keyboard.append([
            InlineKeyboardButton("💬 Для получения помощи нажми сюда", url="https://t.me/sanya_na_svyazi")
        ])
        
        result_reply_markup = InlineKeyboardMarkup(result_keyboard)
        
        await processing_msg.edit_text(
            result_message,
            reply_markup=result_reply_markup
        )
            
    except Exception as e:
        logger.error(f"Error handling VPN request: {str(e)}")
        import traceback
        traceback.print_exc()
        error_message = (
            "❌ Произошла ошибка при обработке запроса.\n\n"
            "Пожалуйста, попробуйте позже."
        )
        
        try:
            await processing_msg.edit_text(error_message)
        except:
            await query.message.reply_text(error_message)


async def handle_setup_iphone_mac(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle iPhone/Mac device selection - show app download link."""
    query = update.callback_query
    await query.answer()
    
    # Store selected device in context
    context.user_data["selected_device"] = "iphone_mac"
    
    # Send app download message
    download_message = (
        "🍎 **iPhone / Mac**\n\n"
        "Скачайте приложение для вашего устройства:\n\n"
        "[HAPP Proxy Utility Plus](https://apps.apple.com/ru/app/happ-proxy-utility-plus/id6746188973)\n\n"
        "После скачивания нажмите кнопку ниже"
    )
    
    keyboard = [
        [InlineKeyboardButton("✅ Я скачал приложение", callback_data="app_downloaded")],
        [InlineKeyboardButton("💬 Для получения помощи нажми сюда", url="https://t.me/sanya_na_svyazi")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.message.reply_text(
        download_message,
        parse_mode="Markdown",
        reply_markup=reply_markup
    )


async def handle_setup_android(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle Android device selection - show app download link."""
    query = update.callback_query
    await query.answer()
    
    # Store selected device in context
    context.user_data["selected_device"] = "android"
    
    # Send app download message
    download_message = (
        "🤖 **Android**\n\n"
        "Скачайте приложение для вашего устройства:\n\n"
        "[v2rayNG](https://github.com/2dust/v2rayNG)\n\n"
        "После скачивания нажмите кнопку ниже"
    )
    
    keyboard = [
        [InlineKeyboardButton("✅ Я скачал приложение", callback_data="app_downloaded")],
        [InlineKeyboardButton("💬 Для получения помощи нажми сюда", url="https://t.me/sanya_na_svyazi")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.message.reply_text(
        download_message,
        parse_mode="Markdown",
        reply_markup=reply_markup
    )


async def handle_setup_windows_linux(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle Windows/Linux device selection - show app download link."""
    query = update.callback_query
    await query.answer()
    
    # Store selected device in context
    context.user_data["selected_device"] = "windows_linux"
    
    # Send app download message
    download_message = (
        "💻 **Windows / Linux**\n\n"
        "Скачайте приложение для вашего устройства:\n\n"
        "[v2rayN](https://github.com/2dust/v2rayN)\n\n"
        "После скачивания нажмите кнопку ниже"
    )
    
    keyboard = [
        [InlineKeyboardButton("✅ Я скачал приложение", callback_data="app_downloaded")],
        [InlineKeyboardButton("💬 Для получения помощи нажми сюда", url="https://t.me/sanya_na_svyazi")]
    ]
    reply_markup = InlineKeyboardMarkup(keyboard)
    
    await query.message.reply_text(
        download_message,
        parse_mode="Markdown",
        reply_markup=reply_markup
    )


async def handle_app_downloaded(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle 'app downloaded' button - start subscription generation immediately."""
    query = update.callback_query
    await query.answer()
    
    # Immediately start subscription generation
    await handle_generate_subscription(update, context)


async def handle_get_subscription_link(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle 'Get subscription link' button - show menu to select subscription."""
    query = update.callback_query
    await query.answer()
    
    user = update.effective_user
    telegram_user_id = user.id if user else None
    
    if not telegram_user_id or not user.username:
        await query.message.reply_text(
            "❌ Не удалось определить ваш аккаунт. Пожалуйста, используйте команду /start."
        )
        return
    
    try:
        all_subscriptions = xui_service.get_all_user_subscriptions(telegram_user_id, user.username)
        
        if not all_subscriptions:
            await query.message.reply_text(
                "❌ У вас нет активных подписок. Используйте кнопку 'Получить доступ к SANI_VPN' для создания первой подписки."
            )
            return
        
        if len(all_subscriptions) == 1:
            # Only one subscription - show it directly
            subscription = all_subscriptions[0]
            await show_subscription_details(update, context, subscription)
        else:
            # Multiple subscriptions - show selection menu
            message_text = "📋 Выберите устройство для получения ссылки:\n\n"
            
            keyboard = []
            for i, sub in enumerate(all_subscriptions, 1):
                device_name = sub.get("device_name", f"Устройство {i}")
                sub_id = sub.get("sub_id", "")
                keyboard.append([
                    InlineKeyboardButton(
                        device_name,
                        callback_data=f"select_subscription_{sub_id}"
                    )
                ])
            
            keyboard.append([
                InlineKeyboardButton("💬 Для получения помощи нажми сюда", url="https://t.me/sanya_na_svyazi")
            ])
            
            reply_markup = InlineKeyboardMarkup(keyboard)
            await query.message.reply_text(message_text, reply_markup=reply_markup)
            
    except Exception as e:
        logger.error(f"Error getting subscriptions: {str(e)}")
        await query.message.reply_text(
            "❌ Произошла ошибка при получении подписок. Попробуйте позже."
        )


async def handle_select_subscription(update: Update, context: ContextTypes.DEFAULT_TYPE, sub_id: str):
    """Handle subscription selection from menu."""
    query = update.callback_query
    await query.answer()
    
    user = update.effective_user
    telegram_user_id = user.id if user else None
    
    if not telegram_user_id or not user.username:
        await query.message.reply_text(
            "❌ Не удалось определить ваш аккаунт."
        )
        return
    
    try:
        all_subscriptions = xui_service.get_all_user_subscriptions(telegram_user_id, user.username)
        
        # Find subscription by sub_id
        selected_subscription = None
        for sub in all_subscriptions:
            if sub.get("sub_id") == sub_id:
                selected_subscription = sub
                break
        
        if not selected_subscription:
            await query.message.reply_text(
                "❌ Подписка не найдена."
            )
            return
        
        await show_subscription_details(update, context, selected_subscription)
        
    except Exception as e:
        logger.error(f"Error selecting subscription: {str(e)}")
        await query.message.reply_text(
            "❌ Произошла ошибка. Попробуйте позже."
        )


async def show_subscription_details(update: Update, context: ContextTypes.DEFAULT_TYPE, subscription: Dict[str, Any]):
    """Show subscription details with copy button."""
    query = update.callback_query if hasattr(update, 'callback_query') and update.callback_query else None
    message = query.message if query else update.message
    
    subscription_url = subscription.get("subscription_url")
    device_name = subscription.get("device_name", "Устройство")
    
    if not subscription_url:
        error_msg = "❌ Не удалось получить ссылку на подписку."
        if query:
            await query.message.reply_text(error_msg)
        else:
            await message.reply_text(error_msg)
        return
    
    # Store subscription URL in context
    context.user_data["subscription_url"] = subscription_url
    
    # Format device name for proper case
    if device_name == "Основное устройство":
        device_text = "основного устройства"
    else:
        device_text = device_name
    
    result_message = (
        f"✅ Подписка для {device_text}\n\n"
        "Для настройки VPN приложения выполните следующие шаги:\n\n"
        "1️⃣ Нажмите кнопку \"📋 Скопировать ссылку\" ниже - ссылка будет скопирована в буфер обмена\n\n"
        "2️⃣ Откройте ваше VPN приложение (HAPP Proxy Utility Plus / v2rayNG / v2rayN)\n\n"
        "3️⃣ Нажмите на ➕ в правом верхнем углу экрана\n\n"
        "4️⃣ Нажмите «Вставить из буфера обмена» (Paste from Clipboard)\n\n"
        "5️⃣ Подключитесь к VPN"
    )
    
    result_keyboard = []
    if WEB_APP_URL:
        copy_url = f"{WEB_APP_URL}?url={quote(subscription_url)}"
        result_keyboard.append([
            InlineKeyboardButton("📋 Скопировать ссылку", web_app=WebAppInfo(url=copy_url))
        ])
    
    # Add navigation buttons
    # Get user info to check subscriptions
    user = update.effective_user if hasattr(update, 'effective_user') else None
    telegram_user_id = user.id if user else None
    
    if telegram_user_id and user and user.username:
        try:
            all_subscriptions = xui_service.get_all_user_subscriptions(telegram_user_id, user.username)
            has_multiple = len(all_subscriptions) > 1
        except Exception as e:
            logger.error(f"Error checking subscriptions for navigation: {str(e)}")
            has_multiple = False
        
        # Add navigation buttons
        nav_buttons = []
        if has_multiple:
            nav_buttons.append(InlineKeyboardButton("📱 Мои устройства", callback_data="get_subscription_link"))
        nav_buttons.append(InlineKeyboardButton("➕ Добавить устройство", callback_data="add_device"))
        
        if nav_buttons:
            result_keyboard.append(nav_buttons)
    
    # Add help button in separate row
    result_keyboard.append([
        InlineKeyboardButton("💬 Для получения помощи нажми сюда", url="https://t.me/sanya_na_svyazi")
    ])
    
    result_reply_markup = InlineKeyboardMarkup(result_keyboard)
    
    if query:
        await query.message.reply_text(
            result_message,
            reply_markup=result_reply_markup
        )
    else:
        await message.reply_text(
            result_message,
            reply_markup=result_reply_markup
        )


async def handle_add_device(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle 'Add device' button - start flow for adding new device."""
    query = update.callback_query
    await query.answer()
    
    user = update.effective_user
    if not user.username:
        await query.message.reply_text(
            "❌ У вас не установлен username в Telegram.\n\n"
            "Для добавления устройства необходимо установить username в настройках Telegram."
        )
        return
    
    # Clear any previous device_name from context
    context.user_data.pop("device_name", None)
    
    # Show device name selection
    message_text = (
        "➕ **Добавление нового устройства**\n\n"
        "Выберите имя для вашего устройства или введите своё:"
    )
    
    # Predefined device name buttons
    keyboard = [
        [
            InlineKeyboardButton("📱 iPhone", callback_data="device_name_iphone"),
            InlineKeyboardButton("💻 Mac", callback_data="device_name_mac")
        ],
        [
            InlineKeyboardButton("📱 Android", callback_data="device_name_android"),
            InlineKeyboardButton("💻 Windows", callback_data="device_name_windows")
        ],
        [
            InlineKeyboardButton("💻 Linux", callback_data="device_name_linux"),
            InlineKeyboardButton("📱 iPad", callback_data="device_name_ipad")
        ],
        [InlineKeyboardButton("✏️ Ввести своё имя", callback_data="enter_custom_device_name")],
        [InlineKeyboardButton("💬 Для получения помощи нажми сюда", url="https://t.me/sanya_na_svyazi")]
    ]
    
    reply_markup = InlineKeyboardMarkup(keyboard)
    await query.message.reply_text(message_text, parse_mode="Markdown", reply_markup=reply_markup)


async def handle_device_name_selected(update: Update, context: ContextTypes.DEFAULT_TYPE, device_name: str):
    """Handle device name selection from buttons."""
    query = update.callback_query
    await query.answer()
    
    # Store device name in context
    context.user_data["device_name"] = device_name
    
    # Determine device type from name and show appropriate setup instructions
    device_name_lower = device_name.lower()
    
    if device_name_lower in ["iphone", "ipad", "mac"]:
        # iPhone, iPad, or Mac - show iPhone/Mac setup
        context.user_data["selected_device"] = "iphone_mac"
        download_message = (
            f"✅ Имя устройства: **{device_name}**\n\n"
            "🍎 **iPhone / Mac**\n\n"
            "Скачайте приложение для вашего устройства:\n\n"
            "[HAPP Proxy Utility Plus](https://apps.apple.com/ru/app/happ-proxy-utility-plus/id6746188973)\n\n"
            "После скачивания нажмите кнопку ниже"
        )
        
        keyboard = [
            [InlineKeyboardButton("✅ Я скачал приложение", callback_data="app_downloaded")],
            [InlineKeyboardButton("💬 Для получения помощи нажми сюда", url="https://t.me/sanya_na_svyazi")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.message.reply_text(
            download_message,
            parse_mode="Markdown",
            reply_markup=reply_markup
        )
    elif device_name_lower == "android":
        # Android - show Android setup
        context.user_data["selected_device"] = "android"
        download_message = (
            f"✅ Имя устройства: **{device_name}**\n\n"
            "🤖 **Android**\n\n"
            "Скачайте приложение для вашего устройства:\n\n"
            "[v2rayNG](https://github.com/2dust/v2rayNG)\n\n"
            "После скачивания нажмите кнопку ниже"
        )
        
        keyboard = [
            [InlineKeyboardButton("✅ Я скачал приложение", callback_data="app_downloaded")],
            [InlineKeyboardButton("💬 Для получения помощи нажми сюда", url="https://t.me/sanya_na_svyazi")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.message.reply_text(
            download_message,
            parse_mode="Markdown",
            reply_markup=reply_markup
        )
    elif device_name_lower in ["windows", "linux"]:
        # Windows or Linux - show Windows/Linux setup
        context.user_data["selected_device"] = "windows_linux"
        download_message = (
            f"✅ Имя устройства: **{device_name}**\n\n"
            "💻 **Windows / Linux**\n\n"
            "Скачайте приложение для вашего устройства:\n\n"
            "[v2rayN](https://github.com/2dust/v2rayN)\n\n"
            "После скачивания нажмите кнопку ниже"
        )
        
        keyboard = [
            [InlineKeyboardButton("✅ Я скачал приложение", callback_data="app_downloaded")],
            [InlineKeyboardButton("💬 Для получения помощи нажми сюда", url="https://t.me/sanya_na_svyazi")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await query.message.reply_text(
            download_message,
            parse_mode="Markdown",
            reply_markup=reply_markup
        )
    else:
        # Custom device name - show device type selection
        device_keyboard = [
            [InlineKeyboardButton("🍎 iPhone / Mac", callback_data="setup_iphone_mac")],
            [InlineKeyboardButton("🤖 Android", callback_data="setup_android")],
            [InlineKeyboardButton("💻 Windows / Linux", callback_data="setup_windows_linux")],
            [InlineKeyboardButton("💬 Для получения помощи нажми сюда", url="https://t.me/sanya_na_svyazi")]
        ]
        device_reply_markup = InlineKeyboardMarkup(device_keyboard)
        
        await query.message.reply_text(
            f"✅ Имя устройства: **{device_name}**\n\n"
            "Теперь выберите тип устройства для скачивания приложения:",
            parse_mode="Markdown",
            reply_markup=device_reply_markup
        )


async def handle_enter_custom_device_name(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle request to enter custom device name."""
    query = update.callback_query
    await query.answer()
    
    # Set flag in context to wait for text input
    context.user_data["waiting_for_device_name"] = True
    
    await query.message.reply_text(
        "✏️ Введите имя для вашего устройства:"
    )


async def devices_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle /devices command - show list of all user devices."""
    user = update.effective_user
    telegram_user_id = user.id if user else None
    
    if not telegram_user_id or not user.username:
        await update.message.reply_text(
            "❌ Не удалось определить ваш аккаунт."
        )
        return
    
    try:
        all_subscriptions = xui_service.get_all_user_subscriptions(telegram_user_id, user.username)
        
        if not all_subscriptions:
            await update.message.reply_text(
                "📱 У вас пока нет устройств.\n\n"
                "Используйте кнопку 'Получить доступ к SANI_VPN' для создания первой подписки."
            )
            return
        
        message_text = f"📱 **Ваши устройства ({len(all_subscriptions)}):**\n\n"
        
        keyboard = []
        for i, sub in enumerate(all_subscriptions, 1):
            device_name = sub.get("device_name", f"Устройство {i}")
            sub_id = sub.get("sub_id", "")
            message_text += f"{i}. {device_name}\n"
            keyboard.append([
                InlineKeyboardButton(
                    device_name,
                    callback_data=f"select_subscription_{sub_id}"
                )
            ])
        
        keyboard.append([
            InlineKeyboardButton("💬 Для получения помощи нажми сюда", url="https://t.me/sanya_na_svyazi")
        ])
        
        reply_markup = InlineKeyboardMarkup(keyboard)
        await update.message.reply_text(message_text, parse_mode="Markdown", reply_markup=reply_markup)
        
    except Exception as e:
        logger.error(f"Error in devices_command: {str(e)}")
        await update.message.reply_text(
            "❌ Произошла ошибка при получении списка устройств. Попробуйте позже."
        )


async def handle_text_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handle text messages - for custom device name input."""
    if not update.message or not update.message.text:
        return
    
    # Check if we're waiting for device name
    if not context.user_data.get("waiting_for_device_name"):
        return
    
    device_name = update.message.text.strip()
    
    # Validate device name (minimal validation - only check for empty and very long names)
    if len(device_name) == 0:
        await update.message.reply_text(
            "❌ Имя устройства не может быть пустым. Попробуйте снова."
        )
        return
    
    # Allow up to 50 characters (reasonable limit for safety)
    if len(device_name) > 50:
        await update.message.reply_text(
            "❌ Имя устройства слишком длинное. Максимум 50 символов. Попробуйте снова."
        )
        return
    
    # Clear waiting flag
    context.user_data.pop("waiting_for_device_name", None)
    
    # Store device name in context
    context.user_data["device_name"] = device_name
    
    # Determine device type from name and show appropriate setup instructions
    device_name_lower = device_name.lower()
    
    if device_name_lower in ["iphone", "ipad", "mac", "айфон", "айпад", "мак"]:
        # iPhone, iPad, or Mac - show iPhone/Mac setup
        context.user_data["selected_device"] = "iphone_mac"
        download_message = (
            f"✅ Имя устройства: **{device_name}**\n\n"
            "🍎 **iPhone / Mac**\n\n"
            "Скачайте приложение для вашего устройства:\n\n"
            "[HAPP Proxy Utility Plus](https://apps.apple.com/ru/app/happ-proxy-utility-plus/id6746188973)\n\n"
            "После скачивания нажмите кнопку ниже"
        )
        
        keyboard = [
            [InlineKeyboardButton("✅ Я скачал приложение", callback_data="app_downloaded")],
            [InlineKeyboardButton("💬 Для получения помощи нажми сюда", url="https://t.me/sanya_na_svyazi")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            download_message,
            parse_mode="Markdown",
            reply_markup=reply_markup
        )
    elif device_name_lower in ["android", "андроид"]:
        # Android - show Android setup
        context.user_data["selected_device"] = "android"
        download_message = (
            f"✅ Имя устройства: **{device_name}**\n\n"
            "🤖 **Android**\n\n"
            "Скачайте приложение для вашего устройства:\n\n"
            "[v2rayNG](https://github.com/2dust/v2rayNG)\n\n"
            "После скачивания нажмите кнопку ниже"
        )
        
        keyboard = [
            [InlineKeyboardButton("✅ Я скачал приложение", callback_data="app_downloaded")],
            [InlineKeyboardButton("💬 Для получения помощи нажми сюда", url="https://t.me/sanya_na_svyazi")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            download_message,
            parse_mode="Markdown",
            reply_markup=reply_markup
        )
    elif device_name_lower in ["windows", "linux", "виндовс", "виндоус", "линукс"]:
        # Windows or Linux - show Windows/Linux setup
        context.user_data["selected_device"] = "windows_linux"
        download_message = (
            f"✅ Имя устройства: **{device_name}**\n\n"
            "💻 **Windows / Linux**\n\n"
            "Скачайте приложение для вашего устройства:\n\n"
            "[v2rayN](https://github.com/2dust/v2rayN)\n\n"
            "После скачивания нажмите кнопку ниже"
        )
        
        keyboard = [
            [InlineKeyboardButton("✅ Я скачал приложение", callback_data="app_downloaded")],
            [InlineKeyboardButton("💬 Для получения помощи нажми сюда", url="https://t.me/sanya_na_svyazi")]
        ]
        reply_markup = InlineKeyboardMarkup(keyboard)
        
        await update.message.reply_text(
            download_message,
            parse_mode="Markdown",
            reply_markup=reply_markup
        )
    else:
        # Custom device name - show device type selection
        device_keyboard = [
            [InlineKeyboardButton("🍎 iPhone / Mac", callback_data="setup_iphone_mac")],
            [InlineKeyboardButton("🤖 Android", callback_data="setup_android")],
            [InlineKeyboardButton("💻 Windows / Linux", callback_data="setup_windows_linux")],
            [InlineKeyboardButton("💬 Для получения помощи нажми сюда", url="https://t.me/sanya_na_svyazi")]
        ]
        device_reply_markup = InlineKeyboardMarkup(device_keyboard)
        
        await update.message.reply_text(
            f"✅ Имя устройства: **{device_name}**\n\n"
            "Теперь выберите тип устройства для скачивания приложения:",
            parse_mode="Markdown",
            reply_markup=device_reply_markup
        )

