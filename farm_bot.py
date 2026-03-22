import os,json,time,random
from telegram import Update,InlineKeyboardButton,InlineKeyboardMarkup
from telegram.ext import ApplicationBuilder,CommandHandler,CallbackQueryHandler,ContextTypes

TOKEN=os.environ.get("TOKEN")
DATA="farm_users.json"

VEGS={
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

WELL_LEVELS={
    1:{"water_per_hour":20,"upgrade_price":0,"upgrade_water":0},
    2:{"water_per_hour":50,"upgrade_price":1000,"upgrade_water":100},
    3:{"water_per_hour":100,"upgrade_price":5000,"upgrade_water":300},
    4:{"water_per_hour":200,"upgrade_price":15000,"upgrade_water":800},
    5:{"water_per_hour":500,"upgrade_price":50000,"upgrade_water":2000},
}

GREENHOUSE_LEVELS={
    1:{"beds":1, "upgrade_price":0,    "upgrade_seeds":0,   "upgrade_water":0},
    2:{"beds":3, "upgrade_price":1000, "upgrade_seeds":50,  "upgrade_water":100},
    3:{"beds":8, "upgrade_price":5000, "upgrade_seeds":200, "upgrade_water":300},
    4:{"beds":15,"upgrade_price":15000,"upgrade_seeds":500, "upgrade_water":800},
    5:{"beds":30,"upgrade_price":50000,"upgrade_seeds":1500,"upgrade_water":2000},
}

def db():
    try:
        with open(DATA) as f: return json.load(f)
    except: return {}

def save(d):
    with open(DATA,"w") as f: json.dump(d,f,ensure_ascii=False)

def gu(uid):
    d=db()
    if uid not in d:
        d[uid]={
            "usd":1000.0,
            "water":0,
            "grass":0,
            "fertilizer":0,
            "seeds":{},
            "harvest":{},
            "well":0,
            "greenhouse":0,
            "factory":False,
            "last_water":time.time(),
            "growing":None,
            "market_offers":[],
        }
        save(d)
    return d

def save_user(uid,u):
    d=db()
    d[uid]=u
    save(d)

def collect_water(u):
    if u["well"]==0: return u
    now=time.time()
    hours=(now-u["last_water"])/3600
    wph=WELL_LEVELS[u["well"]]["water_per_hour"]
    u["water"]=min(u["water"]+int(wph*hours),9999)
    u["last_water"]=now
    return u

def grow_time(veg_id,amount):
    base=VEGS[veg_id]["base_time"]
    if amount<=5: return base
    elif amount<=15: return base*2
    elif amount<=30: return base*3
    elif amount<=50: return base*5
    else: return base*8

def main_menu(u):
    collect_water(u)
    beds=GREENHOUSE_LEVELS[u["greenhouse"]]["beds"] if u["greenhouse"]>0 else 0
    growing=""
    if u["growing"]:
        left=int(u["growing"]["finish"]-time.time())
        if left>0:
            mins=left//60
            growing="\n🌱 Растёт: "+str(mins)+" мин осталось"
        else:
            growing="\n✅ Урожай готов!"

    text=(
        "🌾 ФЕРМА\n\n"
        "💰 $"+str(int(u["usd"]))+"\n"
        "💧 Вода: "+str(int(u["water"]))+"\n"
        "🌿 Трава: "+str(u["grass"])+"\n"
        "🧪 Удобрения: "+str(u["fertilizer"])+" мешков\n"
        "🌱 Теплица: "+(str(u["greenhouse"])+" ур. ("+str(beds)+" грядок)" if u["greenhouse"]>0 else "нет")+"\n"
        "🪣 Колодец: "+(str(u["well"])+" ур." if u["well"]>0 else "нет")
        +growing
    )
    rows=[
        [InlineKeyboardButton("🪣 Колодец",callback_data="well"),
         InlineKeyboardButton("🌱 Теплица",callback_data="greenhouse")],
        [InlineKeyboardButton("🏭 Завод",callback_data="factory"),
         InlineKeyboardButton("🏪 Базар",callback_data="market")],
        [InlineKeyboardButton("🛒 Магазин",callback_data="shop"),
         InlineKeyboardButton("📦 Склад",callback_data="warehouse")],
    ]
    return text,InlineKeyboardMarkup(rows)

async def farm(update,ctx):
    uid=str(update.effective_user.id)
    d=gu(uid)
    u=d[uid]
    u=collect_water(u)
    save_user(uid,u)
    text,kb=main_menu(u)
    await update.message.reply_text(text,reply_markup=kb)

async def start(update,ctx):
    uid=str(update.effective_user.id)
    gu(uid)
    name=update.effective_user.first_name
    await update.message.reply_text(
        "🌾 Привет "+name+"!\n\n"
        "Добро пожаловать на ферму!\n"
        "Ты переехал в деревню с $1000.\n"
        "Стань богатым фермером!\n\n"
        "Напиши /farm чтобы открыть ферму!"
    )

async def btn(update,ctx):
    q=update.callback_query
    await q.answer()
    uid=str(q.from_user.id)
    d=gu(uid)
    u=d[uid]
    u=collect_water(u)
    cb=q.data

    # ГЛАВНОЕ МЕНЮ
    if cb=="menu":
        text,kb=main_menu(u)
        save_user(uid,u)
        await q.edit_message_text(text,reply_markup=kb)
        return

    # КОЛОДЕЦ
    if cb=="well":
        if u["well"]==0:
            text="🪣 КОЛОДЕЦ\n\nУ тебя нет колодца!\nКупи в магазине за $300"
        else:
            wph=WELL_LEVELS[u["well"]]["water_per_hour"]
            text="🪣 КОЛОДЕЦ Ур."+str(u["well"])+"\n\n💧 Производство: "+str(wph)+" воды/час\n💧 Сейчас: "+str(int(u["water"]))+" воды"
            if u["well"]<5:
                next_lvl=WELL_LEVELS[u["well"]+1]
                text+="\n\nУлучшение до Ур."+str(u["well"]+1)+":\n💰 $"+str(next_lvl["upgrade_price"])+"\n💧 "+str(next_lvl["upgrade_water"])+" воды"
        rows=[]
        if u["well"]>0 and u["well"]<5:
            rows.append([InlineKeyboardButton("⬆️ Улучшить колодец",callback_data="upgrade_well")])
        rows.append([InlineKeyboardButton("🔙 Назад",callback_data="menu")])
        save_user(uid,u)
        await q.edit_message_text(text,reply_markup=InlineKeyboardMarkup(rows))
        return

    # УЛУЧШИТЬ КОЛОДЕЦ
    if cb=="upgrade_well":
        if u["well"]>=5:
            await q.answer("Максимальный уровень!",show_alert=True); return
        next_lvl=WELL_LEVELS[u["well"]+1]
        if u["usd"]<next_lvl["upgrade_price"]:
            await q.answer("Нужно $"+str(next_lvl["upgrade_price"]),show_alert=True); return
        if u["water"]<next_lvl["upgrade_water"]:
            await q.answer("Нужно "+str(next_lvl["upgrade_water"])+" воды",show_alert=True); return
        u["usd"]-=next_lvl["upgrade_price"]
        u["water"]-=next_lvl["upgrade_water"]
        u["well"]+=1
        save_user(uid,u)
        await q.answer("Колодец улучшен до ур."+str(u["well"])+"!",show_alert=True)
        cb="well"

    # ТЕПЛИЦА
    if cb=="greenhouse":
        if u["greenhouse"]==0:
            text="🌱 ТЕПЛИЦА\n\nУ тебя нет теплицы!\nКупи в магазине за $500"
            rows=[[InlineKeyboardButton("🔙 Назад",callback_data="menu")]]
        else:
            beds=GREENHOUSE_LEVELS[u["greenhouse"]]["beds"]
            text="🌱 ТЕПЛИЦА Ур."+str(u["greenhouse"])+"\nГрядок: "+str(beds)+"\n💧 Вода: "+str(int(u["water"]))+"\n\n"
            if u["growing"]:
                left=int(u["growing"]["finish"]-time.time())
                if left>0:
                    mins=left//60
                    vname=VEGS[u["growing"]["veg"]]["name"]
                    text+="🌱 Растёт: "+vname+" "+str(u["growing"]["amount"])+"шт\nОсталось: "+str(mins)+" мин"
                    rows=[[InlineKeyboardButton("🔙 Назад",callback_data="menu")]]
                else:
                    veg=VEGS[u["growing"]["veg"]]
                    amt=u["growing"]["amount"]
                    harvest=veg["harvest"]*amt
                    grass=veg["grass"]*amt
                    vname=veg["name"]
                    text+="✅ "+vname+" готов!\nСобери урожай!"
                    rows=[
                        [InlineKeyboardButton("🧺 Собрать урожай",callback_data="harvest")],
                        [InlineKeyboardButton("🔙 Назад",callback_data="menu")]
                    ]
            else:
                text+="Что посадить?"
                rows=[]
                veg_list=list(VEGS.items())
                for i in range(0,len(veg_list),2):
                    row=[]
                    vid,vdata=veg_list[i]
                    row.append(InlineKeyboardButton(vdata["emoji"]+" "+vdata["name"],callback_data="plant_"+vid))
                    if i+1<len(veg_list):
                        vid2,vdata2=veg_list[i+1]
                        row.append(InlineKeyboardButton(vdata2["emoji"]+" "+vdata2["name"],callback_data="plant_"+vid2))
                    rows.append(row)
                rows.append([InlineKeyboardButton("🔙 Назад",callback_data="menu")])
        save_user(uid,u)
        await q.edit_message_text(text,reply_markup=InlineKeyboardMarkup(rows))
        return

    # СОБРАТЬ УРОЖАЙ
    if cb=="harvest":
        if not u["growing"]:
            await q.answer("Нечего собирать!",show_alert=True); return
        left=int(u["growing"]["finish"]-time.time())
        if left>0:
            await q.answer("Ещё "+str(left//60)+" мин!",show_alert=True); return
        veg=VEGS[u["growing"]["veg"]]
        amt=u["growing"]["amount"]
        harvest=veg["harvest"]*amt
        grass=veg["grass"]*amt
        if u["growing"]["fertilized"]:
            harvest=int(harvest*1.5)
        vname=veg["name"]
        vid=u["growing"]["veg"]
        u["harvest"][vid]=u["harvest"].get(vid,0)+harvest
        u["grass"]+=grass
        u["growing"]=None
        save_user(uid,u)
        await q.edit_message_text(
            "🧺 Собрано!\n\n"
            +veg["emoji"]+" "+vname+": "+str(harvest)+" шт\n"
            "🌿 Трава: +"+str(grass)+"\n\n"
            "Отличный урожай!",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Назад",callback_data="greenhouse")]])
        )
        return

    # ПОСАДИТЬ ОВОЩ
    if cb.startswith("plant_"):
        vid=cb[6:]
        veg=VEGS[vid]
        beds=GREENHOUSE_LEVELS[u["greenhouse"]]["beds"]
        text=(
            veg["emoji"]+" "+veg["name"]+"\n\n"
            "Семена: $"+str(veg["seed_price"])+" за 3шт\n"
            "Урожай: "+str(veg["harvest"])+" шт с 3 семян\n"
            "Трава: "+str(veg["grass"])+" шт\n"
            "Цена: $"+str(veg["price"][0])+"-"+str(veg["price"][1])+" за шт\n\n"
            "Сколько посадить?\n"
            "💧 Вода: "+str(int(u["water"]))
        )
        rows=[
            [InlineKeyboardButton("3шт",callback_data="sow_"+vid+"_3"),
             InlineKeyboardButton("6шт",callback_data="sow_"+vid+"_6"),
             InlineKeyboardButton("9шт",callback_data="sow_"+vid+"_9")],
            [InlineKeyboardButton("15шт",callback_data="sow_"+vid+"_15"),
             InlineKeyboardButton("30шт",callback_data="sow_"+vid+"_30"),
             InlineKeyboardButton("50шт",callback_data="sow_"+vid+"_50")],
            [InlineKeyboardButton("🔙 Назад",callback_data="greenhouse")]
        ]
        await q.edit_message_text(text,reply_markup=InlineKeyboardMarkup(rows))
        return

    # ПОСЕВ
    if cb.startswith("sow_"):
        parts=cb.split("_")
        vid=parts[1]
        amount=int(parts[2])
        veg=VEGS[vid]
        seed_cost=int(veg["seed_price"]*amount/3)
        water_need=amount*5
        if u["usd"]<seed_cost:
            await q.answer("Нужно $"+str(seed_cost)+" на семена!",show_alert=True); return
        if u["water"]<water_need:
            await q.answer("Нужно "+str(water_need)+" воды!",show_alert=True); return
        if u["growing"]:
            await q.answer("Уже что-то растёт!",show_alert=True); return
        gt=grow_time(vid,amount)
        if u["fertilizer"]>0:
            gt=gt//2
            u["fertilizer"]-=1
            fertilized=True
        else:
            fertilized=False
        u["usd"]-=seed_cost
        u["water"]-=water_need
        u["growing"]={"veg":vid,"amount":amount,"finish":time.time()+gt,"fertilized":fertilized}
        save_user(uid,u)
        mins=gt//60
        await q.edit_message_text(
            "🌱 Посажено!\n\n"
            +veg["emoji"]+" "+veg["name"]+" "+str(amount)+"шт\n"
            "💰 Потрачено: $"+str(seed_cost)+"\n"
            "💧 Вода: -"+str(water_need)+"\n"
            "⏱ Растёт: "+str(mins)+" мин\n"
            +("🧪 С удобрением - вдвое быстрее!" if fertilized else ""),
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Назад",callback_data="menu")]])
        )
        return

    # ЗАВОД
    if cb=="factory":
        if not u["factory"]:
            text="🏭 ЗАВОД УДОБРЕНИЙ\n\nНет завода!\nКупи в магазине за $10,000"
            rows=[[InlineKeyboardButton("🔙 Назад",callback_data="menu")]]
        else:
            text="🏭 ЗАВОД УДОБРЕНИЙ\n\n🌿 Трава: "+str(u["grass"])+" шт\n🧪 Удобрения: "+str(u["fertilizer"])+" мешков\n\nНужно 200 травы = 100 мешков удобрений"
            rows=[]
            if u["grass"]>=200:
                rows.append([InlineKeyboardButton("⚗️ Переработать траву",callback_data="make_fertilizer")])
            rows.append([InlineKeyboardButton("🔙 Назад",callback_data="menu")])
        await q.edit_message_text(text,reply_markup=InlineKeyboardMarkup(rows))
        return

    # СДЕЛАТЬ УДОБРЕНИЯ
    if cb=="make_fertilizer":
        if not u["factory"]:
            await q.answer("Нет завода!",show_alert=True); return
        if u["grass"]<200:
            await q.answer("Нужно 200 травы!",show_alert=True); return
        batches=u["grass"]//200
        u["grass"]-=batches*200
        u["fertilizer"]+=batches*100
        save_user(uid,u)
        await q.edit_message_text(
            "🧪 Готово!\n\n"
            "🌿 Потрачено травы: "+str(batches*200)+"\n"
            "🧪 Получено удобрений: "+str(batches*100)+" мешков",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Назад",callback_data="factory")]])
        )
        return

    # СКЛАД
    if cb=="warehouse":
        text="📦 СКЛАД\n\n"
        has=False
        for vid,cnt in u["harvest"].items():
            if cnt>0:
                veg=VEGS[vid]
                price=random.randint(veg["price"][0],veg["price"][1])
                text+=veg["emoji"]+" "+veg["name"]+" x"+str(cnt)+" (~$"+str(price*cnt)+")\n"
                has=True
        if not has:
            text+="Пусто! Вырасти овощи"
        text+="\n🌿 Трава: "+str(u["grass"])+"\n🧪 Удобрения: "+str(u["fertilizer"])
        rows=[]
        if has:
            rows.append([InlineKeyboardButton("💵 Продать всё",callback_data="sell_all")])
        rows.append([InlineKeyboardButton("🔙 Назад",callback_data="menu")])
        await q.edit_message_text(text,reply_markup=InlineKeyboardMarkup(rows))
        return

    # ПРОДАТЬ ВСЁ
    if cb=="sell_all":
        total=0
        text="💵 Продано:\n\n"
        has=False
        for vid,cnt in u["harvest"].items():
            if cnt>0:
                veg=VEGS[vid]
                price=random.randint(veg["price"][0],veg["price"][1])*cnt
                total+=price
                text+=veg["emoji"]+" "+veg["name"]+" x"+str(cnt)+" = $"+str(price)+"\n"
                has=True
        if not has:
            await q.answer("Нечего продавать!",show_alert=True); return
        u["harvest"]={}
        u["usd"]+=total
        save_user(uid,u)
        await q.edit_message_text(
            text+"\n💰 Итого: +$"+str(total)+"\n💵 Баланс: $"+str(int(u["usd"])),
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Назад",callback_data="menu")]])
        )
        return

    # БАЗАР
    if cb=="market":
        d=db()
        offers=[]
        for other_uid,other_u in d.items():
            if other_uid!=uid:
                for offer in other_u.get("market_offers",[]):
                    offers.append({"seller":other_uid,"offer":offer})
        text="🏪 БАЗАР ИГРОКОВ\n\n"
        rows=[]
        if not offers:
            text+="Пока никто ничего не продаёт!\nПродай свои овощи:"
        else:
            text+="Предложения:\n\n"
            for i,o in enumerate(offers[:5]):
                of=o["offer"]
                veg=VEGS.get(of["vid"],None)
                if veg:
                    text+=veg["emoji"]+" "+veg["name"]+" x"+str(of["amount"])+" за $"+str(of["price"])+" шт\n"
                    rows.append([InlineKeyboardButton("Купить "+veg["name"]+" x"+str(of["amount"]),callback_data="buy_offer_"+o["seller"]+"_"+str(of["id"]))])
        rows.append([InlineKeyboardButton("📤 Выставить товар",callback_data="add_offer")])
        rows.append([InlineKeyboardButton("🔙 Назад",callback_data="menu")])
        save_user(uid,u)
        await q.edit_message_text(text,reply_markup=InlineKeyboardMarkup(rows))
        return

    # ВЫСТАВИТЬ ТОВАР
    if cb=="add_offer":
        text="📤 Что продать?\n\n"
        rows=[]
        has=False
        for vid,cnt in u["harvest"].items():
            if cnt>0:
                veg=VEGS[vid]
                rows.append([InlineKeyboardButton(veg["emoji"]+" "+veg["name"]+" ("+str(cnt)+"шт)",callback_data="offer_"+vid)])
                has=True
        if not has:
            text+="У тебя нет урожая!"
        rows.append([InlineKeyboardButton("🔙 Назад",callback_data="market")])
        await q.edit_message_text(text,reply_markup=InlineKeyboardMarkup(rows))
        return

    if cb.startswith("offer_"):
        vid=cb[6:]
        veg=VEGS[vid]
        cnt=u["harvest"].get(vid,0)
        avg=sum(veg["price"])//2
        text=veg["emoji"]+" "+veg["name"]+" ("+str(cnt)+"шт)\nВыбери цену за штуку:"
        rows=[
            [InlineKeyboardButton("$"+str(avg-2),callback_data="post_"+vid+"_"+str(avg-2)+"_"+str(cnt)),
             InlineKeyboardButton("$"+str(avg),callback_data="post_"+vid+"_"+str(avg)+"_"+str(cnt)),
             InlineKeyboardButton("$"+str(avg+2),callback_data="post_"+vid+"_"+str(avg+2)+"_"+str(cnt))],
            [InlineKeyboardButton("🔙 Назад",callback_data="add_offer")]
        ]
        await q.edit_message_text(text,reply_markup=InlineKeyboardMarkup(rows))
        return

    if cb.startswith("post_"):
        parts=cb.split("_")
        vid=parts[1]
        price=int(parts[2])
        amount=int(parts[3])
        if u["harvest"].get(vid,0)<amount:
            await q.answer("Недостаточно товара!",show_alert=True); return
        u["harvest"][vid]=u["harvest"].get(vid,0)-amount
        offer_id=int(time.time())
        if "market_offers" not in u:
            u["market_offers"]=[]
        u["market_offers"].append({"id":offer_id,"vid":vid,"amount":amount,"price":price})
        save_user(uid,u)
        veg=VEGS[vid]
        await q.edit_message_text(
            "✅ Выставлено на базар!\n\n"
            +veg["emoji"]+" "+veg["name"]+" x"+str(amount)+" за $"+str(price)+" шт",
            reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Назад",callback_data="market")]])
        )
        return

    if cb.startswith("buy_offer_"):
        parts=cb[10:].split("_")
        seller_uid=parts[0]
        offer_id=int(parts[1])
        d2=db()
        if seller_uid not in d2:
            await q.answer("Продавец не найден!",show_alert=True); return
        seller=d2[seller_uid]
        offer=next((o for o in seller.get("market_offers",[]) if o["id"]==offer_id),None)
        if not offer:
            await q.answer("Товар уже продан!",show_alert=True); return
        total=offer["price"]*offer["amount"]app.run_polling()
        
