import os
import json
import time
import random
import logging
from datetime import datetime

# Налаштування логування
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, ContextTypes

# Отримуємо токен
TOKEN = os.environ.get("TOKEN")
if not TOKEN:
    logger.error("❌ TOKEN не знайдено!")
    # Для Railway/Heroku - не виходимо, але логуємо помилку
    # exit(1)  # Розкоментуйте якщо хочете зупинити запуск

DATA = "farm_users.json"

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
    1:{"water_per_hour":20,"upgrade_price":0,"upgrade_water":0},
    2:{"water_per_hour":50,"upgrade_price":1000,"upgrade_water":100},
    3:{"water_per_hour":100,"upgrade_price":5000,"upgrade_water":300},
    4:{"water_per_hour":200,"upgrade_price":15000,"upgrade_water":800},
    5:{"water_per_hour":500,"upgrade_price":50000,"upgrade_water":2000},
}

GREENHOUSE_LEVELS = {
    1:{"beds":1, "upgrade_price":0,    "upgrade_seeds":0,   "upgrade_water":0},
    2:{"beds":3, "upgrade_price":1000, "upgrade_seeds":50,  "upgrade_water":100},
    3:{"beds":8, "upgrade_price":5000, "upgrade_seeds":200, "upgrade_water":300},
    4:{"beds":15,"upgrade_price":15000,"upgrade_seeds":500, "upgrade_water":800},
    5:{"beds":30,"upgrade_price":50000,"upgrade_seeds":1500,"upgrade_water":2000},
}

SHOP_ITEMS = {
    "well": {"name": "Колодец", "price": 300, "emoji": "🪣"},
    "greenhouse": {"name": "Теплица", "price": 500, "emoji": "🌱"},
    "factory": {"name": "Завод удобрений", "price": 10000, "emoji": "🏭"},
}

def db():
    try:
        with open(DATA, 'r', encoding='utf-8') as f:
            return json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return {}

def save(d):
    with open(DATA, 'w', encoding='utf-8') as f:
        json.dump(d, f, ensure_ascii=False, indent=2)

def get_user(uid):
    d = db()
    if uid not in d:
        d[uid] = {
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
        save(d)
    return d[uid]

def save_user(uid, u):
    d = db()
    d[uid] = u
    save(d)

def collect_water(u):
    if u["well"] == 0:
        return u
    now = time.time()
    hours = (now - u["last_water"]) / 3600
    wph = WELL_LEVELS[u["well"]]["water_per_hour"]
    u["water"] = min(u["water"] + int(wph * hours), 9999)
    u["last_water"] = now
    return u

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

def main_menu(u):
    u = collect_water(u)
    beds = GREENHOUSE_LEVELS[u["greenhouse"]]["beds"] if u["greenhouse"] > 0 else 0
    growing = ""
    if u["growing"]:
        left = int(u["growing"]["finish"] - time.time())
        if left > 0:
            mins = left // 60
            hours = left // 3600
            if hours > 0:
                growing = f"\n🌱 Растёт: {hours}ч {mins % 60}мин осталось"
            else:
                growing = f"\n🌱 Растёт: {mins} мин осталось"
        else:
            growing = "\n✅ Урожай готов!"

    text = (
        "🌾 ФЕРМА\n\n"
        f"💰 ${int(u['usd'])}\n"
        f"💧 Вода: {int(u['water'])}\n"
        f"🌿 Трава: {u['grass']}\n"
        f"🧪 Удобрения: {u['fertilizer']} мешков\n"
        f"🌱 Теплица: {'Ур.' + str(u['greenhouse']) + ' (' + str(beds) + ' грядок)' if u['greenhouse'] > 0 else 'нет'}\n"
        f"🪣 Колодец: {'Ур.' + str(u['well']) if u['well'] > 0 else 'нет'}"
        + growing
    )
    rows = [
        [InlineKeyboardButton("🪣 Колодец", callback_data="well"),
         InlineKeyboardButton("🌱 Теплица", callback_data="greenhouse")],
        [InlineKeyboardButton("🏭 Завод", callback_data="factory"),
         InlineKeyboardButton("🏪 Базар", callback_data="market")],
        [InlineKeyboardButton("🛒 Магазин", callback_data="shop"),
         InlineKeyboardButton("📦 Склад", callback_data="warehouse")],
    ]
    return text, InlineKeyboardMarkup(rows)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = str(update.effective_user.id)
    get_user(uid)
    name = update.effective_user.first_name
    await update.message.reply_text(
        f"🌾 Привет {name}!\n\n"
        "Добро пожаловать на ферму!\n"
        "Ты переехал в деревню с $1000.\n"
        "Стань богатым фермером!\n\n"
        "Напиши /farm чтобы открыть ферму!"
    )
    logger.info(f"Пользователь {name} ({uid}) запустил бота")

async def farm(update: Update, context: ContextTypes.DEFAULT_TYPE):
    uid = str(update.effective_user.id)
    u = get_user(uid)
    u = collect_water(u)
    save_user(uid, u)
    text, kb = main_menu(u)
    await update.message.reply_text(text, reply_markup=kb)
    logger.info(f"Пользователь {uid} открыл ферму")

async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    uid = str(query.from_user.id)
    u = get_user(uid)
    u = collect_water(u)
    cb = query.data
    
    logger.info(f"Пользователь {uid} нажал кнопку: {cb}")

    try:
        # ГЛАВНОЕ МЕНЮ
        if cb == "menu":
            text, kb = main_menu(u)
            save_user(uid, u)
            await query.edit_message_text(text, reply_markup=kb)
            return

        # КОЛОДЕЦ
        if cb == "well":
            if u["well"] == 0:
                text = "🪣 КОЛОДЕЦ\n\nУ тебя нет колодца!\nКупи в магазине за $300"
            else:
                wph = WELL_LEVELS[u["well"]]["water_per_hour"]
                text = f"🪣 КОЛОДЕЦ Ур.{u['well']}\n\n💧 Производство: {wph} воды/час\n💧 Сейчас: {int(u['water'])} воды"
                if u["well"] < 5:
                    next_lvl = WELL_LEVELS[u["well"] + 1]
                    text += f"\n\nУлучшение до Ур.{u['well']+1}:\n💰 ${next_lvl['upgrade_price']}\n💧 {next_lvl['upgrade_water']} воды"
            rows = []
            if u["well"] > 0 and u["well"] < 5:
                rows.append([InlineKeyboardButton("⬆️ Улучшить колодец", callback_data="upgrade_well")])
            rows.append([InlineKeyboardButton("🔙 Назад", callback_data="menu")])
            save_user(uid, u)
            await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(rows))
            return

        # УЛУЧШИТЬ КОЛОДЕЦ
        if cb == "upgrade_well":
            if u["well"] >= 5:
                await query.answer("Максимальный уровень!", show_alert=True)
                return
            next_lvl = WELL_LEVELS[u["well"] + 1]
            if u["usd"] < next_lvl["upgrade_price"]:
                await query.answer(f"Нужно ${next_lvl['upgrade_price']}", show_alert=True)
                return
            if u["water"] < next_lvl["upgrade_water"]:
                await query.answer(f"Нужно {next_lvl['upgrade_water']} воды", show_alert=True)
                return
            u["usd"] -= next_lvl["upgrade_price"]
            u["water"] -= next_lvl["upgrade_water"]
            u["well"] += 1
            save_user(uid, u)
            await query.answer(f"Колодец улучшен до ур.{u['well']}!", show_alert=True)
            text, kb = main_menu(u)
            await query.edit_message_text(text, reply_markup=kb)
            return

        # ТЕПЛИЦА
        if cb == "greenhouse":
            if u["greenhouse"] == 0:
                text = "🌱 ТЕПЛИЦА\n\nУ тебя нет теплицы!\nКупи в магазине за $500"
                rows = [[InlineKeyboardButton("🔙 Назад", callback_data="menu")]]
            else:
                beds = GREENHOUSE_LEVELS[u["greenhouse"]]["beds"]
                text = f"🌱 ТЕПЛИЦА Ур.{u['greenhouse']}\nГрядок: {beds}\n💧 Вода: {int(u['water'])}\n\n"
                if u["growing"]:
                    left = int(u["growing"]["finish"] - time.time())
                    if left > 0:
                        mins = left // 60
                        vname = VEGS[u["growing"]["veg"]]["name"]
                        text += f"🌱 Растёт: {vname} {u['growing']['amount']}шт\nОсталось: {mins} мин"
                        rows = [[InlineKeyboardButton("🔙 Назад", callback_data="menu")]]
                    else:
                        veg = VEGS[u["growing"]["veg"]]
                        amt = u["growing"]["amount"]
                        vname = veg["name"]
                        text += f"✅ {vname} готов!\nСобери урожай!"
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
            save_user(uid, u)
            await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(rows))
            return

        # ЗІБРАТИ ВРОЖАЙ
        if cb == "harvest":
            if not u["growing"]:
                await query.answer("Нечего собирать!", show_alert=True)
                return
            left = int(u["growing"]["finish"] - time.time())
            if left > 0:
                await query.answer(f"Ещё {left//60} мин!", show_alert=True)
                return
            veg = VEGS[u["growing"]["veg"]]
            amt = u["growing"]["amount"]
            harvest = veg["harvest"] * amt
            grass = veg["grass"] * amt
            if u["growing"]["fertilized"]:
                harvest = int(harvest * 1.5)
            vname = veg["name"]
            vid = u["growing"]["veg"]
            u["harvest"][vid] = u["harvest"].get(vid, 0) + harvest
            u["grass"] += grass
            u["growing"] = None
            save_user(uid, u)
            await query.edit_message_text(
                f"🧺 Собрано!\n\n"
                f"{veg['emoji']} {vname}: {harvest} шт\n"
                f"🌿 Трава: +{grass}\n\n"
                "Отличный урожай!",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Назад", callback_data="greenhouse")]])
            )
            return

        # ПОСАДИТЬ ОВОЩ
        if cb.startswith("plant_"):
            vid = cb[6:]
            veg = VEGS[vid]
            beds = GREENHOUSE_LEVELS[u["greenhouse"]]["beds"]
            text = (
                f"{veg['emoji']} {veg['name']}\n\n"
                f"Семена: ${veg['seed_price']} за 3шт\n"
                f"Урожай: {veg['harvest']} шт с 3 семян\n"
                f"Трава: {veg['grass']} шт\n"
                f"Цена: ${veg['price'][0]}-${veg['price'][1]} за шт\n\n"
                f"Сколько посадить?\n"
                f"💧 Вода: {int(u['water'])}"
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

        # ПОСЕВ
        if cb.startswith("sow_"):
            parts = cb.split("_")
            vid = parts[1]
            amount = int(parts[2])
            veg = VEGS[vid]
            seed_cost = int(veg["seed_price"] * amount / 3)
            water_need = amount * 5
            if u["usd"] < seed_cost:
                await query.answer(f"Нужно ${seed_cost} на семена!", show_alert=True)
                return
            if u["water"] < water_need:
                await query.answer(f"Нужно {water_need} воды!", show_alert=True)
                return
            if u["growing"]:
                await query.answer("Уже что-то растёт!", show_alert=True)
                return
            gt = grow_time(vid, amount)
            if u["fertilizer"] > 0:
                gt = gt // 2
                u["fertilizer"] -= 1
                fertilized = True
            else:
                fertilized = False
            u["usd"] -= seed_cost
            u["water"] -= water_need
            u["growing"] = {"veg": vid, "amount": amount, "finish": time.time() + gt, "fertilized": fertilized}
            save_user(uid, u)
            mins = gt // 60
            hours = gt // 3600
            time_text = f"{hours}ч {mins % 60}мин" if hours > 0 else f"{mins} мин"
            await query.edit_message_text(
                f"🌱 Посажено!\n\n"
                f"{veg['emoji']} {veg['name']} {amount}шт\n"
                f"💰 Потрачено: ${seed_cost}\n"
                f"💧 Вода: -{water_need}\n"
                f"⏱ Растёт: {time_text}\n"
                + ("🧪 С удобрением - вдвое быстрее!" if fertilized else ""),
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Назад", callback_data="menu")]])
            )
            return

        # ЗАВОД
        if cb == "factory":
            if not u["factory"]:
                text = "🏭 ЗАВОД УДОБРЕНИЙ\n\nНет завода!\nКупи в магазине за $10,000"
                rows = [[InlineKeyboardButton("🔙 Назад", callback_data="menu")]]
            else:
                text = f"🏭 ЗАВОД УДОБРЕНИЙ\n\n🌿 Трава: {u['grass']} шт\n🧪 Удобрения: {u['fertilizer']} мешков\n\nНужно 200 травы = 100 мешков удобрений"
                rows = []
                if u["grass"] >= 200:
                    rows.append([InlineKeyboardButton("⚗️ Переработать траву", callback_data="make_fertilizer")])
                rows.append([InlineKeyboardButton("🔙 Назад", callback_data="menu")])
            await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(rows))
            return

        # СДЕЛАТЬ УДОБРЕНИЯ
        if cb == "make_fertilizer":
            if not u["factory"]:
                await query.answer("Нет завода!", show_alert=True)
                return
            if u["grass"] < 200:
                await query.answer("Нужно 200 травы!", show_alert=True)
                return
            batches = u["grass"] // 200
            u["grass"] -= batches * 200
            u["fertilizer"] += batches * 100
            save_user(uid, u)
            await query.edit_message_text(
                f"🧪 Готово!\n\n"
                f"🌿 Потрачено травы: {batches * 200}\n"
                f"🧪 Получено удобрений: {batches * 100} мешков",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Назад", callback_data="factory")]])
            )
            return

        # МАГАЗИН
        if cb == "shop":
            text = "🛒 МАГАЗИН\n\n"
            rows = []
            if u["well"] == 0:
                text += "🪣 Колодец - $300\n"
                rows.append([InlineKeyboardButton("🪣 Купить колодец", callback_data="buy_well")])
            if u["greenhouse"] == 0:
                text += "🌱 Теплица - $500\n"
                rows.append([InlineKeyboardButton("🌱 Купить теплицу", callback_data="buy_greenhouse")])
            if not u["factory"]:
                text += "🏭 Завод удобрений - $10,000\n"
                rows.append([InlineKeyboardButton("🏭 Купить завод", callback_data="buy_factory")])
            
            if not rows:
                text += "Всё уже куплено!"
            
            rows.append([InlineKeyboardButton("🔙 Назад", callback_data="menu")])
            await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(rows))
            return

        # КУПІВЛЯ
        if cb.startswith("buy_"):
            item = cb[4:]
            if item == "well" and u["well"] == 0:
                if u["usd"] >= 300:
                    u["usd"] -= 300
                    u["well"] = 1
                    u["last_water"] = time.time()
                    save_user(uid, u)
                    await query.answer("Колодец куплен!", show_alert=True)
                else:
                    await query.answer("Недостаточно денег!", show_alert=True)
                    return
            elif item == "greenhouse" and u["greenhouse"] == 0:
                if u["usd"] >= 500:
                    u["usd"] -= 500
                    u["greenhouse"] = 1
                    save_user(uid, u)
                    await query.answer("Теплица куплена!", show_alert=True)
                else:
                    await query.answer("Недостаточно денег!", show_alert=True)
                    return
            elif item == "factory" and not u["factory"]:
                if u["usd"] >= 10000:
                    u["usd"] -= 10000
                    u["factory"] = True
                    save_user(uid, u)
                    await query.answer("Завод куплен!", show_alert=True)
                else:
                    await query.answer("Недостаточно денег!", show_alert=True)
                    return
            else:
                await query.answer("Уже куплено!", show_alert=True)
                return
            
            text, kb = main_menu(u)
            await query.edit_message_text(text, reply_markup=kb)
            return

        # СКЛАД
        if cb == "warehouse":
            text = "📦 СКЛАД\n\n"
            has = False
            for vid, cnt in u["harvest"].items():
                if cnt > 0:
                    veg = VEGS[vid]
                    price = random.randint(veg["price"][0], veg["price"][1])
                    
