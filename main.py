import sqlite3
import datetime
import logging
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import ParseMode
from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, MessageHandler, filters, ContextTypes

# ==================== КОНФИГ ====================
BOT_TOKEN = "8738766068:AAFbNNQZsfYA6zEf1hhQRHsWcdcSmUlohes"
ADMIN_IDS = [8357585508]
DB_NAME = "vpn_orders.db"


# ==================== БАЗА ДАННЫХ ====================
def init_db():
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute('''CREATE TABLE IF NOT EXISTS orders
                 (
                     id
                     INTEGER
                     PRIMARY
                     KEY
                     AUTOINCREMENT,
                     user_id
                     INTEGER,
                     username
                     TEXT,
                     full_name
                     TEXT,
                     plan
                     TEXT,
                     status
                     TEXT
                     DEFAULT
                     'waiting',
                     created_at
                     TEXT,
                     admin_note
                     TEXT
                 )''')
    conn.commit()
    conn.close()


def add_order(user_id, username, full_name, plan):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("INSERT INTO orders (user_id, username, full_name, plan, status, created_at) VALUES (?,?,?,?,?,?)",
              (user_id, username, full_name, plan, 'waiting', datetime.datetime.now().isoformat()))
    conn.commit()
    order_id = c.lastrowid
    conn.close()
    return order_id


def get_orders(status=None):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    if status:
        c.execute("SELECT * FROM orders WHERE status=? ORDER BY created_at DESC", (status,))
    else:
        c.execute("SELECT * FROM orders ORDER BY created_at DESC")
    rows = c.fetchall()
    conn.close()
    return rows


def get_order(order_id):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("SELECT * FROM orders WHERE id=?", (order_id,))
    row = c.fetchone()
    conn.close()
    return row


def update_order_status(order_id, status, admin_note=''):
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("UPDATE orders SET status=?, admin_note=? WHERE id=?", (status, admin_note, order_id))
    conn.commit()
    conn.close()


# ==================== КЛАВИАТУРЫ ====================
def main_menu():
    kb = [
        [InlineKeyboardButton("🔥 КУПИТЬ VPN", callback_data='buy_vpn')],
        [InlineKeyboardButton("🎁 БЕСПЛАТНЫЙ VPN", callback_data='free_vpn')],
        [InlineKeyboardButton("👤 МОИ ЗАКАЗЫ", callback_data='my_orders')],
        [InlineKeyboardButton("🆘 ПОДДЕРЖКА", callback_data='help')]
    ]
    return InlineKeyboardMarkup(kb)


def plan_buttons():
    kb = [
        [InlineKeyboardButton("🚀 1 МЕСЯЦ — 499 ₽", callback_data='plan_1month')],
        [InlineKeyboardButton("⚡ 3 МЕСЯЦА — 1199 ₽", callback_data='plan_3month')],
        [InlineKeyboardButton("💎 12 МЕСЯЦЕВ — 3999 ₽", callback_data='plan_12month')],
        [InlineKeyboardButton("🔙 НАЗАД", callback_data='back_main')]
    ]
    return InlineKeyboardMarkup(kb)


def admin_orders_buttons(orders):
    kb = []
    for o in orders[:10]:
        kb.append([InlineKeyboardButton(f"🆔 #{o[0]} | {o[3]} | {o[2][:15]}", callback_data=f'admin_view_{o[0]}')])
    kb.append([InlineKeyboardButton("🔄 ОБНОВИТЬ", callback_data='admin_refresh')])
    kb.append([InlineKeyboardButton("📊 СТАТИСТИКА", callback_data='admin_stats')])
    kb.append([InlineKeyboardButton("📋 ВСЕ ЗАКАЗЫ", callback_data='admin_all')])
    return InlineKeyboardMarkup(kb)


def admin_order_actions(order_id):
    kb = [
        [InlineKeyboardButton("✅ ОТПРАВИТЬ ССЫЛКУ", callback_data=f'admin_send_{order_id}')],
        [InlineKeyboardButton("❌ ОТМЕНИТЬ", callback_data=f'admin_cancel_{order_id}')],
        [InlineKeyboardButton("✏️ ПРИМЕЧАНИЕ", callback_data=f'admin_note_{order_id}')],
        [InlineKeyboardButton("🔙 К СПИСКУ", callback_data='admin_orders')]
    ]
    return InlineKeyboardMarkup(kb)


def user_orders_buttons(orders):
    kb = []
    for o in orders:
        status_emoji = "⏳" if o[4] == 'waiting' else "✅" if o[4] == 'done' else "❌"
        kb.append([InlineKeyboardButton(f"{status_emoji} #{o[0]} | {o[3]}", callback_data=f'user_view_{o[0]}')])
    kb.append([InlineKeyboardButton("🔙 НАЗАД", callback_data='back_main')])
    return InlineKeyboardMarkup(kb)


# ==================== ОБРАБОТЧИКИ ====================
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user = update.effective_user
    await update.message.reply_text(
        f"🔥 <b>SWILL VPN</b>\n"
        f"━━━━━━━━━━━━━━━━━━━━━━\n"
        f"👋 Привет, <b>{user.full_name}</b>!\n\n"
        f"⚡ Лучший VPN для интернета без границ\n"
        f"🔒 Полная анонимность и защита данных\n"
        f"🌍 Серверы в 15+ странах\n"
        f"📶 Скорость до 200 Мбит/с\n\n"
        f"💰 <b>Цены:</b>\n"
        f"   🚀 1 месяц — 499 ₽\n"
        f"   ⚡ 3 месяца — 1199 ₽\n"
        f"   💎 12 месяцев — 3999 ₽\n\n"
        f"🎁 <b>Есть бесплатная версия!</b>\n"
        f"   Ограничение: 1 устройство, 10 Мбит/с\n\n"
        f"📌 Выбери действие:",
        reply_markup=main_menu(),
        parse_mode=ParseMode.HTML
    )


async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    data = query.data
    user_id = query.from_user.id
    username = query.from_user.username or 'no_username'
    full_name = query.from_user.full_name

    # ========== ПОКУПКА VPN ==========
    if data == 'buy_vpn':
        await query.edit_message_text(
            "🔥 <b>ВЫБЕРИ ТАРИФ</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "🚀 <b>1 МЕСЯЦ</b> — 499 ₽\n"
            "   • 3 устройства\n"
            "   • Скорость до 100 Мбит/с\n"
            "   • 5 стран\n\n"
            "⚡ <b>3 МЕСЯЦА</b> — 1199 ₽\n"
            "   • 5 устройств\n"
            "   • Скорость до 150 Мбит/с\n"
            "   • 10 стран\n\n"
            "💎 <b>12 МЕСЯЦЕВ</b> — 3999 ₽\n"
            "   • 10 устройств\n"
            "   • Скорость до 200 Мбит/с\n"
            "   • 15+ стран\n"
            "   • VIP-поддержка\n\n"
            "👇 Выбери тариф:",
            reply_markup=plan_buttons(),
            parse_mode=ParseMode.HTML
        )

    elif data.startswith('plan_'):
        plan_map = {
            'plan_1month': '1 месяц — 499 ₽',
            'plan_3month': '3 месяца — 1199 ₽',
            'plan_12month': '12 месяцев — 3999 ₽'
        }
        plan = plan_map.get(data, 'Неизвестно')

        order_id = add_order(user_id, username, full_name, plan)

        admin_text = (
            f"🆕 <b>НОВЫЙ ЗАКАЗ</b>\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"🆔 #{order_id}\n"
            f"👤 {full_name}\n"
            f"📛 @{username}\n"
            f"📋 {plan}\n"
            f"🕒 {datetime.datetime.now().strftime('%d.%m.%Y %H:%M')}"
        )
        for admin_id in ADMIN_IDS:
            await context.bot.send_message(admin_id, admin_text, parse_mode=ParseMode.HTML)
            await context.bot.send_message(
                admin_id,
                f"⚡ ДЕЙСТВИЯ ПО ЗАКАЗУ #{order_id}:",
                reply_markup=admin_order_actions(order_id)
            )

        await query.edit_message_text(
            f"✅ <b>ЗАКАЗ #{order_id} ПРИНЯТ!</b>\n\n"
            f"📋 Тариф: {plan}\n"
            f"⏳ Статус: Ожидает обработки\n\n"
            f"🔔 Администратор скоро отправит ссылку\n"
            f"📩 Ссылка на VPN придёт сюда\n\n"
            f"📧 <b>ВАЖНО:</b> После получения ссылки — введите вашу почту в форме, и инструкция по установке придёт на почту",
            reply_markup=main_menu(),
            parse_mode=ParseMode.HTML
        )

    # ========== БЕСПЛАТНЫЙ VPN ==========
    elif data == 'free_vpn':
        await query.edit_message_text(
            f"🎁 <b>БЕСПЛАТНЫЙ VPN</b>\n"
            f"━━━━━━━━━━━━━━━━━━━━━━\n\n"
            f"🔓 Получи доступ к бесплатной версии!\n\n"
            f"📌 <b>Ограничения:</b>\n"
            f"   • 1 устройство\n"
            f"   • Скорость до 10 Мбит/с\n"
            f"   • 3 страны (Россия, Германия, США)\n"
            f"   • Безлимитный трафик\n\n"
            f"⚡ Чтобы получить доступ, нажми кнопку ниже:",
            reply_markup=InlineKeyboardMarkup([
                [InlineKeyboardButton("🎁 ПОЛУЧИТЬ БЕСПЛАТНО", callback_data='get_free')],
                [InlineKeyboardButton("🔙 НАЗАД", callback_data='back_main')]
            ]),
            parse_mode=ParseMode.HTML
        )

    elif data == 'get_free':
        free_order_id = add_order(user_id, username, full_name, "Бесплатный VPN")

        admin_text = (
            f"🎁 <b>БЕСПЛАТНЫЙ ЗАПРОС</b>\n"
            f"━━━━━━━━━━━━━━━━━━\n"
            f"🆔 #{free_order_id}\n"
            f"👤 {full_name}\n"
            f"📛 @{username}\n"
            f"📋 Бесплатный VPN\n"
            f"🕒 {datetime.datetime.now().strftime('%d.%m.%Y %H:%M')}"
        )
        for admin_id in ADMIN_IDS:
            await context.bot.send_message(admin_id, admin_text, parse_mode=ParseMode.HTML)
            await context.bot.send_message(
                admin_id,
                f"⚡ ДЕЙСТВИЯ ПО БЕСПЛАТНОМУ ЗАКАЗУ #{free_order_id}:",
                reply_markup=admin_order_actions(free_order_id)
            )

        await query.edit_message_text(
            f"✅ <b>ГОТОВО!</b>\n\n"
            f"🎁 Бесплатный VPN активирован!\n"
            f"📩 Администратор отправит ссылку в течение 5 минут\n\n"
            f"📌 Проверь этот чат — ссылка придёт сюда\n"
            f"📧 <b>ВАЖНО:</b> После получения ссылки — введите вашу почту в форме, и инструкция по установке придёт на почту",
            reply_markup=main_menu(),
            parse_mode=ParseMode.HTML
        )

    # ========== МОИ ЗАКАЗЫ ==========
    elif data == 'my_orders':
        orders = get_orders()
        user_orders = [o for o in orders if o[1] == user_id]
        if not user_orders:
            await query.edit_message_text(
                "📭 У тебя пока нет заказов.\n\nНажми «КУПИТЬ VPN» или «БЕСПЛАТНЫЙ VPN»",
                reply_markup=main_menu()
            )
        else:
            text = "📋 <b>ТВОИ ЗАКАЗЫ</b>\n━━━━━━━━━━━━━━━━━\n"
            for o in user_orders[:5]:
                status_emoji = "⏳" if o[4] == 'waiting' else "✅" if o[4] == 'done' else "❌"
                text += f"\n{status_emoji} #{o[0]} | {o[3]}\n   {o[5][:10]}\n"
            await query.edit_message_text(
                text,
                reply_markup=user_orders_buttons(user_orders),
                parse_mode=ParseMode.HTML
            )

    elif data.startswith('user_view_'):
        order_id = int(data.split('_')[2])
        order = get_order(order_id)
        if not order or order[1] != user_id:
            await query.edit_message_text("❌ Заказ не найден", reply_markup=main_menu())
            return
        status_map = {'waiting': '⏳ Ожидает', 'done': '✅ Выполнен', 'cancelled': '❌ Отменён'}
        text = (
            f"🧾 <b>ЗАКАЗ #{order[0]}</b>\n"
            f"━━━━━━━━━━━━━━━━━\n"
            f"📋 {order[3]}\n"
            f"📅 {order[5][:16]}\n"
            f"📌 {status_map.get(order[4], 'Неизвестно')}\n"
            f"✏️ {order[6] or '—'}"
        )
        await query.edit_message_text(text, reply_markup=main_menu(), parse_mode=ParseMode.HTML)

    # ========== ПОДДЕРЖКА ==========
    elif data == 'help':
        await query.edit_message_text(
            "🆘 <b>ПОДДЕРЖКА</b>\n"
            "━━━━━━━━━━━━━━━━━\n\n"
            "🔹 <b>Как купить VPN?</b>\n"
            "   Нажми «КУПИТЬ VPN» → выбери тариф\n\n"
            "🔹 <b>Есть бесплатный?</b>\n"
            "   Да! Нажми «БЕСПЛАТНЫЙ VPN»\n\n"
            "🔹 <b>Как получить доступ?</b>\n"
            "   После заказа админ отправит ссылку\n\n"
            "🔹 <b>Что после получения ссылки?</b>\n"
            "   Перейди по ссылке, введи свою почту — инструкция придёт на почту\n\n"
            "🔹 <b>Связь с админом:</b>\n"
            "   @admin_username",
            reply_markup=main_menu(),
            parse_mode=ParseMode.HTML
        )

    elif data == 'back_main':
        await query.edit_message_text(
            "🏠 <b>ГЛАВНОЕ МЕНЮ</b>\n"
            "━━━━━━━━━━━━━━━━━━━━━━\n\n"
            "🔥 SWILL VPN — твой надёжный защитник в сети",
            reply_markup=main_menu(),
            parse_mode=ParseMode.HTML
        )

    # ========== АДМИНСКИЕ ==========
    elif data.startswith('admin_') and user_id in ADMIN_IDS:
        if data == 'admin_orders':
            orders = get_orders('waiting')
            if not orders:
                await query.edit_message_text("📭 НЕТ АКТИВНЫХ ЗАКАЗОВ", reply_markup=main_menu())
                return
            await query.edit_message_text(
                f"📋 <b>АКТИВНЫЕ ЗАКАЗЫ ({len(orders)})</b>",
                reply_markup=admin_orders_buttons(orders),
                parse_mode=ParseMode.HTML
            )

        elif data == 'admin_refresh':
            orders = get_orders('waiting')
            await query.edit_message_text(
                f"🔄 ОБНОВЛЕНО ({len(orders)})",
                reply_markup=admin_orders_buttons(orders),
                parse_mode=ParseMode.HTML
            )

        elif data == 'admin_all':
            orders = get_orders()
            if not orders:
                await query.edit_message_text("📭 НЕТ ЗАКАЗОВ")
                return
            text = "📋 <b>ВСЕ ЗАКАЗЫ</b>\n━━━━━━━━━━━━━━━━━\n"
            for o in orders[:20]:
                status_emoji = "⏳" if o[4] == 'waiting' else "✅" if o[4] == 'done' else "❌"
                text += f"{status_emoji} #{o[0]} | {o[3]} | {o[2][:10]}\n"
            await query.edit_message_text(text, reply_markup=admin_orders_buttons(orders[:10]),
                                          parse_mode=ParseMode.HTML)

        elif data == 'admin_stats':
            all_orders = get_orders()
            waiting = len([o for o in all_orders if o[4] == 'waiting'])
            done = len([o for o in all_orders if o[4] == 'done'])
            cancelled = len([o for o in all_orders if o[4] == 'cancelled'])
            await query.edit_message_text(
                f"📊 <b>СТАТИСТИКА</b>\n"
                f"━━━━━━━━━━━━━━━━━\n"
                f"📦 Всего: {len(all_orders)}\n"
                f"⏳ Ожидают: {waiting}\n"
                f"✅ Выполнено: {done}\n"
                f"❌ Отменено: {cancelled}",
                reply_markup=admin_orders_buttons(get_orders('waiting')),
                parse_mode=ParseMode.HTML
            )

        elif data.startswith('admin_view_'):
            order_id = int(data.split('_')[2])
            order = get_order(order_id)
            if not order:
                await query.edit_message_text("❌ ЗАКАЗ НЕ НАЙДЕН")
                return
            status_map = {'waiting': '⏳ Ожидает', 'done': '✅ Выполнен', 'cancelled': '❌ Отменён'}
            text = (
                f"🧾 <b>ЗАКАЗ #{order[0]}</b>\n"
                f"━━━━━━━━━━━━━━━━━\n"
                f"👤 {order[2]} (@{order[1]})\n"
                f"📋 {order[3]}\n"
                f"📅 {order[5][:16]}\n"
                f"📌 {status_map.get(order[4], 'Неизвестно')}\n"
                f"✏️ {order[6] or '—'}"
            )
            await query.edit_message_text(text, reply_markup=admin_order_actions(order_id), parse_mode=ParseMode.HTML)

        elif data.startswith('admin_send_'):
            order_id = int(data.split('_')[2])
            context.user_data['pending_order'] = order_id
            await query.edit_message_text(
                f"📤 <b>ОТПРАВКА ССЫЛКИ ДЛЯ ЗАКАЗА #{order_id}</b>\n\n"
                "Введи ссылку на VPN для пользователя:\n\n"
                "🔗 Просто вставь ссылку (на файл .ovpn, на сайт, на архив)\n"
                "📧 Пользователь перейдёт по ссылке, введёт почту и получит инструкцию\n\n"
                "📌 <b>Пример ссылки:</b>\n"
                "<code>https://lk.privatnet.ru/invite?a=Arc</code>\n\n"
                "Вставь свою ссылку вместо примера:",
                parse_mode=ParseMode.HTML
            )

        elif data.startswith('admin_cancel_'):
            order_id = int(data.split('_')[2])
            update_order_status(order_id, 'cancelled')
            await query.edit_message_text(
                f"❌ ЗАКАЗ #{order_id} ОТМЕНЁН",
                reply_markup=admin_orders_buttons(get_orders('waiting'))
            )

        elif data.startswith('admin_note_'):
            order_id = int(data.split('_')[2])
            context.user_data['note_order'] = order_id
            await query.edit_message_text(
                f"✏️ <b>ПРИМЕЧАНИЕ ДЛЯ ЗАКАЗА #{order_id}</b>\n\nВведи текст:",
                parse_mode=ParseMode.HTML
            )


# ==================== ОБРАБОТКА ВВОДА ОТ АДМИНА ====================
async def handle_admin_input(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    if user_id not in ADMIN_IDS:
        await update.message.reply_text("⛔ ДОСТУП ЗАПРЕЩЁН")
        return

    text = update.message.text

    if 'pending_order' in context.user_data:
        order_id = context.user_data.pop('pending_order')
        order = get_order(order_id)
        if not order:
            await update.message.reply_text("❌ ЗАКАЗ НЕ НАЙДЕН")
            return
        try:
            await context.bot.send_message(
                order[1],
                f"🔑 <b>ВАША ССЫЛКА НА VPN:</b>\n\n"
                f"<a href='{text}'>👉 НАЖМИТЕ СЮДА, ЧТОБЫ ПЕРЕЙТИ ПО ССЫЛКЕ</a>\n\n"
                f"📧 <b>ВАЖНО:</b> Перейдите по ссылке, введите вашу почту — и инструкция по установке VPN придёт на почту\n\n"
                f"✅ Ссылка активна!\n"
                f"🌐 SWILL VPN — защита и анонимность в сети",
                parse_mode=ParseMode.HTML,
                disable_web_page_preview=True
            )
            update_order_status(order_id, 'done', f'Отправлена ссылка: {text[:100]}...')
            await update.message.reply_text(f"✅ ССЫЛКА ДЛЯ ЗАКАЗА #{order_id} ОТПРАВЛЕНА ПОЛЬЗОВАТЕЛЮ!")
        except Exception as e:
            await update.message.reply_text(f"❌ ОШИБКА: {e}")

    elif 'note_order' in context.user_data:
        order_id = context.user_data.pop('note_order')
        update_order_status(order_id, 'waiting', text)
        await update.message.reply_text(f"✏️ ПРИМЕЧАНИЕ ДЛЯ ЗАКАЗА #{order_id} СОХРАНЕНО!")

    else:
        await update.message.reply_text(
            "⚡ Используй кнопки в админ-панели.\n"
            "Команды:\n/admin — панель админа\n/start — главное меню"
        )


# ==================== ЗАПУСК ====================
def main():
    logging.basicConfig(level=logging.INFO)
    init_db()

    app = ApplicationBuilder().token(BOT_TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("admin", callback_handler))

    app.add_handler(CallbackQueryHandler(callback_handler))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_admin_input))

    print("🚀 SWILL VPN БОТ ЗАПУЩЕН!")
    print(f"👤 Админ ID: {ADMIN_IDS[0]}")
    print("📌 Нажми /start в боте")

    app.run_polling()


if __name__ == "__main__":
    main()
