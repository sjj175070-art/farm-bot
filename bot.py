================================

Telegram Mafia-like Bot (Anonymous Version)

================================

Файлы для GitHub:

1. bot.py        -> основной код бота

2. requirements.txt -> python-telegram-bot==20.7

3. Procfile      -> worker: python bot.py

4. runtime.txt   -> python-3.11.15

-------------------- bot.py --------------------

import asyncio import random import os from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup from telegram.ext import ApplicationBuilder, CommandHandler, CallbackQueryHandler, ContextTypes

TOKEN = os.environ.get("BOT_TOKEN")

Game state

games = {}

===== Start Game =====

async def game(update: Update, context: ContextTypes.DEFAULT_TYPE): chat_id = update.effective_chat.id games[chat_id] = {"players": [], "alive": [], "state": "lobby"} keyboard = [[InlineKeyboardButton("➕ Присоединиться", callback_data="join")]]

await update.message.reply_text(
    "🎮 Новая игра!\n\nИгроки: 0/20\n⏳ До старта 60 сек",
    reply_markup=InlineKeyboardMarkup(keyboard)
)

await asyncio.sleep(60)
await start_game(chat_id, context)

===== Join =====

async def join(update: Update, context: ContextTypes.DEFAULT_TYPE): query = update.callback_query await query.answer()

chat_id = query.message.chat.id
user = query.from_user

if chat_id not in games:
    return

game = games[chat_id]
if user.id not in game["players"]:
    game["players"].append(user.id)

players_text = "\n".join([f"- {p}" for p in game["players"]])

await query.edit_message_text(
    f"👥 Игроки: {len(game['players'])}/20\n\n{players_text}",
    reply_markup=query.message.reply_markup
)

===== Start the actual game =====

async def start_game(chat_id, context): game = games.get(chat_id) if not game or len(game["players"]) < 2: return

game["alive"] = game["players"].copy()
await context.bot.send_message(chat_id, "🌙 Ночь наступила...\nКто-то вышел из тени...")
await asyncio.sleep(3)
await night_round(chat_id, context)

===== Night round =====

async def night_round(chat_id, context): game = games[chat_id] if len(game["alive"]) <= 1: await end_game(chat_id, context) return

p1, p2 = random.sample(game["alive"], 2)
game["current"] = {"attacker": p1, "target": p2, "action": None, "defense": None}

kb1 = InlineKeyboardMarkup([
    [InlineKeyboardButton("🔪 Убить", callback_data="kill")],
    [InlineKeyboardButton("💋 Поцеловать", callback_data="kiss")],
    [InlineKeyboardButton("🤗 Обнять", callback_data="hug")]
])
kb2 = InlineKeyboardMarkup([
    [InlineKeyboardButton("😴 Спать", callback_data="sleep")],
    [InlineKeyboardButton("👀 Проснуться", callback_data="wake")],
    [InlineKeyboardButton("🚨 СОС", callback_data="sos")]
])

try:
    await context.bot.send_message(p1, "Ты выбрал цель. Что делать?", reply_markup=kb1)
    await context.bot.send_message(p2, "Ты слышишь шум...", reply_markup=kb2)
except:
    pass

await asyncio.sleep(15)
await resolve_night(chat_id, context)

===== Handle actions =====

async def action(update: Update, context: ContextTypes.DEFAULT_TYPE): query = update.callback_query await query.answer() user = query.from_user.id

for game in games.values():
    if "current" not in game:
        continue
    if user == game["current"]["attacker"]:
        game["current"]["action"] = query.data
    elif user == game["current"]["target"]:
        game["current"]["defense"] = query.data

===== Resolve night =====

async def resolve_night(chat_id, context): game = games[chat_id] cur = game["current"]

attacker = cur["attacker"]
target = cur["target"]
action = cur["action"]
defense = cur["defense"]

text = "🌅 Утро...\n\n"

if defense == "sos":
    if attacker in game["alive"]:
        game["alive"].remove(attacker)
    text += "🚨 Кто-то был пойман ночью..."

elif action == "kill":
    if defense == "wake":
        if random.random() < 0.5:
            game["alive"].remove(target)
            text += "💀 Кто-то погиб..."
        else:
            text += "😮 Кто-то смог выжить..."
    else:
        game["alive"].remove(target)
        text += "💀 Кто-то погиб..."

else:
    text += "🌙 Ночь прошла тихо..."

await context.bot.send_message(chat_id, text)
await asyncio.sleep(3)
await night_round(chat_id, context)

===== End game =====

async def end_game(chat_id, context): game = games[chat_id] if len(game["alive"]) == 1: winner = game["alive"][0] await context.bot.send_message(chat_id, f"🏆 Победитель: {winner}") else: await context.bot.send_message(chat_id, "Никто не выжил...") del games[chat_id]

===== Main =====

def main(): app = ApplicationBuilder().token(TOKEN).build() app.add_handler(CommandHandler("game", game)) app.add_handler(CallbackQueryHandler(join, pattern="join")) app.add_handler(CallbackQueryHandler(action)) app.run_polling()

if name == "main": main()

-------------------- requirements.txt --------------------

python-telegram-bot==20.7

-------------------- Procfile --------------------

worker: python bot.py

-------------------- runtime.txt --------------------

python-3.11.15
