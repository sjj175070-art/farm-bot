import os
import json
import time
import random
import logging

# Налаштування логування
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

# Отримуємо токен з оточення
TOKEN = os.environ.get("TOKEN")
DATA_FILE = "farm_users.json"

if not TOKEN:
    logger.error("❌ TOKEN не знайдено! Бот не запуститься.")
    # Не виходимо, щоб контейнер не перезапускався циклічно, але лог видно

# ---------------------- ДАНІ ----------------------
VEGS = {
    "tomato": {"name":"Помидор","emoji":"🍅","seed_price":30,"harvest":5,"grass":10,"price":[5,8],  "base_time":1800},
    "carrot": {"name":"Морковь","emoji":"🥕","seed_price":50,"harvest":8,"grass":8, "price":[8,12], "base_time":3600},
    "cucumber":{"name":"Огурец","emoji":"🥒","seed_price":60,"harvest":4,"grass":12,"price":[10,15],"base_time":3600},
    "corn":   {"name":"Кукуруза","emoji":"🌽","seed_price":80,"harvest":6,"grass":15,"price":[20,30],"base_time":5400},
    "broccoli":{"name":"Брокколи","emoji":"🥦","seed_price":120,"harvest":5,"grass":20,"price":[30,50],"base_time":7200},
    "pepper": {"name":"Перец","emoji":"🌶","seed_price":200,"harvest":4,"grass":25,"price":[60,90], "base_time":10800},
    "eggplant":{"name":"Баклажан","emoji":"🍆","seed_price":350,"harvest":6,"grass":30,"price":[80,120],"base_time":14400},
    "garlic":  {"name":"Чеснок","emoji":"🧄","seed_price":500,"harvest":10,"grass":35,"price":[100,150],"base_time":21600},
    "strawberry":{"name":"Клубника","emoji":"🍓","seed_price":800,"harvest":15,"grass":40,"price":[150,200],"base_time":28800},
    "ginseng": {"name":"Женьшень","emoji":"🌿","seed_price":2000,"harvest":5,"grass":50,"price":[500,800],"base_time":43200},
}

WELL_LEVELS = {
    1: {"water_per_hour": 20, "upgrade_price": 0,    "upgrade_water": 0},
    2: {"water_per_hour": 50, "upgrade_price": 1000, "upgrade_water": 100},
    3: {"water_per_hour": 100, "upgrade_price": 5000, "upgrade_water": 300},
    4: {"water_per_hour": 200, "upgrade_price": 15000, "upgrade_water": 800},
    5: {"water_per_hour": 500, "upgrade_price": 50000, "upgrade_water": 2000},
}

GREENHOUSE_LEVELS = {
    1: {"beds": 1, "upgrade_price": 0,    "upgrade_seeds": 0,   "upgrade_water": 0},
    2: {"beds": 3, "upgrade_price": 1000, "upgrade_seeds": 50,  "upgrade_water": 100},
    3: {"beds": 8, "upgrade_price": 5000, "upgrade_seeds": 200, "upgrade_water": 300},
    4: {"beds": 15, "upgrade_price": 15000, "upgrade_seeds": 500, "upgrade_water": 800},
    5: {"beds": 30, "upgrade_price": 50000, "upgrade_seeds": 1500, "upgrade_water": 2000},
}

# ---------------------- РОБОТА З ДАНИМИ ----------------------
def load_db():
    try:
        with open(DATA_FILE, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

def save_db(data):
    with open(DATA_FILE, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def get_user(uid):
    db = load_db()
    if uid not in db:
        db[uid] = {
            "usd": 1000.0,
            "water": 0,
            "grass": 0,
            "fertilizer": 0,
            "seeds": {},
            "harvest": {},
            "well": 0,
            "greenhouse": 0,
            "factory": False,
            "last_water": time.time(),
            "growing": None,
            "market_offers": [],
        }
        save_db(db)
    return db[uid]

def save_user(uid, user_data):
    db = load_db()
    db[uid] = user_data
    save_db(db)

# ---------------------- ІГРОВА ЛОГІКА ----------------------
def collect_water(user):
    if user["well"] == 0:
        return user
    now = time.time()
    hours = (now - user["last_water"]) / 3600
    wph = WELL_LEVELS[user["well"]]["water_per_hour"]
    user["water"] = min(user["water"] + int(wph * hours), 9999)
    user["last_water"] = now
    return user

def grow_time(veg_id, amount):
    base = VEGS[veg_id]["base_time"]
    if amount <= 5:
        return base
    elif amount <= 15:
        return base * 2
    elif amount <= 30:
        return base * 3
    elif amount <= 50:
        return base * 5
    else:
        return base * 8

def main_menu_text(user):
    user = collect_water(user)
    beds = GREENHOUSE_LEVELS[user["greenhouse"]]["beds"] if user["greenhouse"] > 0 else 0
    growing = ""
    if user["growing"]:
        left = int(user["growing"]["finish"] - time.time())
        if left > 0:
            mins = left // 60
            growing = f"\n🌱 Растёт: {mins} мин осталось"
        else:
            growing = "\n✅ Урожай готов!"

    text = (
        "🌾 ФЕРМА\n\n"
        f"💰 ${int(user['usd'])}\n"
        f"💧 Вода: {int(user['water'])}\n"
        f"🌿 Трава: {user['grass']}\n"
        f"🧪 Удобрения: {user['fertilizer']} мешков\n"
        f"🌱 Теплица: {'Ур.' + str(user['greenhouse']) + ' (' + str(beds) + ' грядок)' if user['greenhouse'] > 0 else 'нет'}\n"
        f"🪣 Колодец: {'Ур.' + str(user['well']) if user['well'] > 0 else 'нет'}"
        + growing
    )
    keyboard = [
        [InlineKeyboardButton("🪣 Колодец", callback_data="well"),
         InlineKeyboardButton("🌱 Теплица", callback_data="greenhouse")],
        [InlineKeyboardButton("🏭 Завод", callback_data="factory"),
         InlineKeyboardButton("🏪 Базар", callback_data="market")],
        [InlineKeyboardButton("🛒 Магазин", callback_data="shop"),
         InlineKeyboardButton("📦 Склад", callback_data="warehouse")],
    ]
    return text, InlineKeyboardMarkup(keyboard)

# ---------------------- ОБРОБНИКИ КОМАНД ----------------------
async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = str(update.effective_user.id)
    get_user(uid)  # створюємо, якщо немає
    name = update.effective_user.first_name
    await update.message.reply_text(
        f"🌾 Привет {name}!\n\n"
        "Добро пожаловать на ферму!\n"
        "Ты переехал в деревню с $1000.\n"
        "Стань богатым фермером!\n\n"
        "Напиши /farm чтобы открыть ферму!"
    )

async def farm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = str(update.effective_user.id)
    user = get_user(uid)
    user = collect_water(user)
    save_user(uid, user)
    text, kb = main_menu_text(user)
    await update.message.reply_text(text, reply_markup=kb)

# ---------------------- ОБРОБНИК КНОПОК ----------------------
async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    uid = str(query.from_user.id)
    user = get_user(uid)
    user = collect_water(user)
    cb = query.data

    try:
        # ---- ГОЛОВНЕ МЕНЮ ----
        if cb == "menu":
            text, kb = main_menu_text(user)
            save_user(uid, user)
            await query.edit_message_text(text, reply_markup=kb)
            return

        # ---- КОЛОДЕЦЬ ----
        if cb == "well":
            if user["well"] == 0:
                text = "🪣 КОЛОДЕЦ\n\nУ тебя нет колодца!\nКупи в магазине за $300"
            else:
                wph = WELL_LEVELS[user["well"]]["water_per_hour"]
                text = f"🪣 КОЛОДЕЦ Ур.{user['well']}\n\n💧 Производство: {wph} воды/час\n💧 Сейчас: {int(user['water'])} воды"
                if user["well"] < 5:
                    nxt = WELL_LEVELS[user["well"] + 1]
                    text += f"\n\nУлучшение до Ур.{user['well']+1}:\n💰 ${nxt['upgrade_price']}\n💧 {nxt['upgrade_water']} воды"
            rows = []
            if user["well"] > 0 and user["well"] < 5:
                rows.append([InlineKeyboardButton("⬆️ Улучшить колодец", callback_data="upgrade_well")])
            rows.append([InlineKeyboardButton("🔙 Назад", callback_data="menu")])
            await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(rows))
            return

        if cb == "upgrade_well":
            if user["well"] >= 5:
                await query.answer("Максимальный уровень!", show_alert=True)
                return
            nxt = WELL_LEVELS[user["well"] + 1]
            if user["usd"] < nxt["upgrade_price"]:
                await query.answer(f"Нужно ${nxt['upgrade_price']}", show_alert=True)
                return
            if user["water"] < nxt["upgrade_water"]:
                await query.answer(f"Нужно {nxt['upgrade_water']} воды", show_alert=True)
                return
            user["usd"] -= nxt["upgrade_price"]
            user["water"] -= nxt["upgrade_water"]
            user["well"] += 1
            save_user(uid, user)
            await query.answer(f"Колодец улучшен до ур.{user['well']}!", show_alert=True)
            text, kb = main_menu_text(user)
            await query.edit_message_text(text, reply_markup=kb)
            return

        # ---- ТЕПЛИЦЯ ----
        if cb == "greenhouse":
            if user["greenhouse"] == 0:
                text = "🌱 ТЕПЛИЦА\n\nУ тебя нет теплицы!\nКупи в магазине за $500"
                rows = [[InlineKeyboardButton("🔙 Назад", callback_data="menu")]]
            else:
                beds = GREENHOUSE_LEVELS[user["greenhouse"]]["beds"]
                text = f"🌱 ТЕПЛИЦА Ур.{user['greenhouse']}\nГрядок: {beds}\n💧 Вода: {int(user['water'])}\n\n"
                if user["growing"]:
                    left = int(user["growing"]["finish"] - time.time())
                    if left > 0:
                        mins = left // 60
                        vname = VEGS[user["growing"]["veg"]]["name"]
                        text += f"🌱 Растёт: {vname} {user['growing']['amount']}шт\nОсталось: {mins} мин"
                        rows = [[InlineKeyboardButton("🔙 Назад", callback_data="menu")]]
                    else:
                        veg = VEGS[user["growing"]["veg"]]
                        text += f"✅ {veg['name']} готов!\nСобери урожай!"
                        rows = [
                            [InlineKeyboardButton("🧺 Собрать урожай", callback_data="harvest")],
                            [InlineKeyboardButton("🔙 Назад", callback_data="menu")]
                        ]
                else:
                    text += "Что посадить?"
                    rows = []
                    veg_list = list(VEGS.items())
                    for i in range(0, len(veg_list), 2):
                        row = []
                        vid, vdata = veg_list[i]
                        row.append(InlineKeyboardButton(f"{vdata['emoji']} {vdata['name']}", callback_data=f"plant_{vid}"))
                        if i + 1 < len(veg_list):
                            vid2, vdata2 = veg_list[i + 1]
                            row.append(InlineKeyboardButton(f"{vdata2['emoji']} {vdata2['name']}", callback_data=f"plant_{vid2}"))
                        rows.append(row)
                    rows.append([InlineKeyboardButton("🔙 Назад", callback_data="menu")])
            await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(rows))
            return

        if cb == "harvest":
            if not user["growing"]:
                await query.answer("Нечего собирать!", show_alert=True)
                return
            left = int(user["growing"]["finish"] - time.time())
            if left > 0:
                await query.answer(f"Ещё {left//60} мин!", show_alert=True)
                return
            veg = VEGS[user["growing"]["veg"]]
            amt = user["growing"]["amount"]
            harvest = veg["harvest"] * amt
            grass = veg["grass"] * amt
            if user["growing"]["fertilized"]:
                harvest = int(harvest * 1.5)
            vid = user["growing"]["veg"]
            user["harvest"][vid] = user["harvest"].get(vid, 0) + harvest
            user["grass"] += grass
            user["growing"] = None
            save_user(uid, user)
            await query.edit_message_text(
                f"🧺 Собрано!\n\n{veg['emoji']} {veg['name']}: {harvest} шт\n🌿 Трава: +{grass}\n\nОтличный урожай!",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Назад", callback_data="greenhouse")]])
            )
            return

        # ---- ПОСАДКА ----
        if cb.startswith("plant_"):
            vid = cb[6:]
            veg = VEGS[vid]
            text = (
                f"{veg['emoji']} {veg['name']}\n\n"
                f"Семена: ${veg['seed_price']} за 3шт\n"
                f"Урожай: {veg['harvest']} шт с 3 семян\n"
                f"Трава: {veg['grass']} шт\n"
                f"Цена: ${veg['price'][0]}-${veg['price'][1]} за шт\n\n"
                f"Сколько посадить?\n"
                f"💧 Вода: {int(user['water'])}"
            )
            rows = [
                [InlineKeyboardButton("3шт", callback_data=f"sow_{vid}_3"),
                 InlineKeyboardButton("6шт", callback_data=f"sow_{vid}_6"),
                 InlineKeyboardButton("9шт", callback_data=f"sow_{vid}_9")],
                [InlineKeyboardButton("15шт", callback_data=f"sow_{vid}_15"),
                 InlineKeyboardButton("30шт", callback_data=f"sow_{vid}_30"),
                 InlineKeyboardButton("50шт", callback_data=f"sow_{vid}_50")],
                [InlineKeyboardButton("🔙 Назад", callback_data="greenhouse")]
            ]
            await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(rows))
            return

        if cb.startswith("sow_"):
            parts = cb.split("_")
            vid = parts[1]
            amount = int(parts[2])
            veg = VEGS[vid]
            seed_cost = int(veg["seed_price"] * amount / 3)
            water_need = amount * 5
            if user["usd"] < seed_cost:
                await query.answer(f"Нужно ${seed_cost} на семена!", show_alert=True)
                return
            if user["water"] < water_need:
                await query.answer(f"Нужно {water_need} воды!", show_alert=True)
                return
            if user["growing"]:
                await query.answer("Уже что-то растёт!", show_alert=True)
                return
            gt = grow_time(vid, amount)
            fertilized = False
            if user["fertilizer"] > 0:
                gt //= 2
                user["fertilizer"] -= 1
                fertilized = True
            user["usd"] -= seed_cost
            user["water"] -= water_need
            user["growing"] = {"veg": vid, "amount": amount, "finish": time.time() + gt, "fertilized": fertilized}
            save_user(uid, user)
            mins = gt // 60
            await query.edit_message_text(
                f"🌱 Посажено!\n\n{veg['emoji']} {veg['name']} {amount}шт\n"
                f"💰 Потрачено: ${seed_cost}\n💧 Вода: -{water_need}\n"
                f"⏱ Растёт: {mins} мин\n"
                + ("🧪 С удобрением - вдвое быстрее!" if fertilized else ""),
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Назад", callback_data="menu")]])
            )
            return

        # ---- ЗАВОД ----
        if cb == "factory":
            if not user["factory"]:
                text = "🏭 ЗАВОД УДОБРЕНИЙ\n\nНет завода!\nКупи в магазине за $10,000"
                rows = [[InlineKeyboardButton("🔙 Назад", callback_data="menu")]]
            else:
                text = (f"🏭 ЗАВОД УДОБРЕНИЙ\n\n🌿 Трава: {user['grass']} шт\n"
                        f"🧪 Удобрения: {user['fertilizer']} мешков\n\n"
                        "Нужно 200 травы = 100 мешков удобрений")
                rows = []
                if user["grass"] >= 200:
                    rows.append([InlineKeyboardButton("⚗️ Переработать траву", callback_data="make_fertilizer")])
                rows.append([InlineKeyboardButton("🔙 Назад", callback_data="menu")])
            await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(rows))
            return

        if cb == "make_fertilizer":
            if not user["factory"]:
                await query.answer("Нет завода!", show_alert=True)
                return
            if user["grass"] < 200:
                await query.answer("Нужно 200 травы!", show_alert=True)
                return
            batches = user["grass"] // 200
            user["grass"] -= batches * 200
            user["fertilizer"] += batches * 100
            save_user(uid, user)
            await query.edit_message_text(
                f"🧪 Готово!\n\n🌿 Потрачено травы: {batches * 200}\n🧪 Получено удобрений: {batches * 100} мешков",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Назад", callback_data="factory")]])
            )
            return

        # ---- МАГАЗИН ----
        if cb == "shop":
            text = "🛒 МАГАЗИН\n\n"
            rows = []
            if user["well"] == 0:
                text += "🪣 Колодец - $300\n"
                rows.append([InlineKeyboardButton("🪣 Купить колодец", callback_data="buy_well")])
            if user["greenhouse"] == 0:
                text += "🌱 Теплица - $500\n"
                rows.append([InlineKeyboardButton("🌱 Купить теплицу", callback_data="buy_greenhouse")])
            if not user["factory"]:
                text += "🏭 Завод удобрений - $10,000\n"
                rows.append([InlineKeyboardButton("🏭 Купить завод", callback_data="buy_factory")])
            if not rows:
                text += "Всё уже куплено!"
            rows.append([InlineKeyboardButton("🔙 Назад", callback_data="menu")])
            await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(rows))
            return

        if cb.startswith("buy_"):
            item = cb[4:]
            if item == "well" and user["well"] == 0:
                if user["usd"] >= 300:
                    user["usd"] -= 300
                    user["well"] = 1
                    user["last_water"] = time.time()
                    save_user(uid, user)
                    await query.answer("Колодец куплен!", show_alert=True)
                else:
                    await query.answer("Недостаточно денег!", show_alert=True)
                    return
            elif item == "greenhouse" and user["greenhouse"] == 0:
                if user["usd"] >= 500:
                    user["usd"] -= 500
                    user["greenhouse"] = 1
                    save_user(uid, user)
                    await query.answer("Теплица куплена!", show_alert=True)
                else:
                    await query.answer("Недостаточно денег!", show_alert=True)
                    return
            elif item == "factory" and not user["factory"]:
                if user["usd"] >= 10000:
                    user["usd"] -= 10000
                    user["factory"] = True
                    save_user(uid, user)
                    await query.answer("Завод куплен!", show_alert=True)
                else:
                    await query.answer("Недостаточно денег!", show_alert=True)
                    return
            else:
                await query.answer("Уже куплено!", show_alert=True)
                return
            text, kb = main_menu_text(user)
            await query.edit_message_text(text, reply_markup=kb)
            return

        # ---- СКЛАД ----
        if cb == "warehouse":
            text = "📦 СКЛАД\n\n"
            has = False
            for vid, cnt in user["harvest"].items():
                if cnt > 0:
                    veg = VEGS[vid]
                    price = random.randint(veg["price"][0], veg["price"][1])
                    text += f"{veg['emoji']} {veg['name']} x{cnt} (~${price * cnt})\n"
                    has = True
            if not has:
                text += "Пусто! Вырасти овощи"
            text += f"\n🌿 Трава: {user['grass']}\n🧪 Удобрения: {user['fertilizer']}"
            rows = []
            if has:
                rows.append([InlineKeyboardButton("💵 Продать всё",
