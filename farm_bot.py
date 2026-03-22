async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    uid = str(query.from_user.id)
    u = get_user(uid)
    u = collect_water(u)
    cb = query.data
    
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
                    text += f"{veg['emoji']} {veg['name']} x{cnt} (~${price * cnt})\n"
                    has = True
            if not has:
                text += "Пусто! Вырасти овощи"
            text += f"\n🌿 Трава: {u['grass']}\n🧪 Удобрения: {u['fertilizer']}"
            rows = []
            if has:
                rows.append([InlineKeyboardButton("💵 Продать всё", callback_data="sell_all")])
            rows.append([InlineKeyboardButton("🔙 Назад", callback_data="menu")])
            await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(rows))
            return

        # ПРОДАТЬ ВСЁ
        if cb == "sell_all":
            total = 0
            text = "💵 Продано:\n\n"
            has = False
            for vid, cnt in list(u["harvest"].items()):
                if cnt > 0:
                    veg = VEGS[vid]
                    price = random.randint(veg["price"][0], veg["price"][1]) * cnt
                    total += price
                    text += f"{veg['emoji']} {veg['name']} x{cnt} = ${price}\n"
                    has = True
            if not has:
                await query.answer("Нечего продавать!", show_alert=True)
                return
            u["harvest"] = {}
            u["usd"] += total
            save_user(uid, u)
            await query.edit_message_text(
                f"{text}\n💰 Итого: +${total}\n💵 Баланс: ${int(u['usd'])}",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Назад", callback_data="menu")]])
            )
            return

        # БАЗАР
        if cb == "market":
            all_users = db()
            offers = []
            for other_uid, other_u in all_users.items():
                if other_uid != uid:
                    for offer in other_u.get("market_offers", []):
                        offers.append({"seller": other_uid, "offer": offer})
            
            text = "🏪 БАЗАР ИГРОКОВ\n\n"
            rows = []
            
            if not offers:
                text += "Пока никто ничего не продаёт!\nПродай свои овощи:"
            else:
                text += "Предложения:\n\n"
                for i, o in enumerate(offers[:5]):
                    of = o["offer"]
                    veg = VEGS.get(of["vid"])
                    if veg:
                        text += f"{veg['emoji']} {veg['name']} x{of['amount']} за ${of['price']} шт\n"
                        rows.append([InlineKeyboardButton(f"Купить {veg['name']} x{of['amount']}", callback_data=f"buy_offer_{o['seller']}_{of['id']}")])
            
            rows.append([InlineKeyboardButton("📤 Выставить товар", callback_data="add_offer")])
            rows.append([InlineKeyboardButton("🔙 Назад", callback_data="menu")])
            save_user(uid, u)
            await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(rows))
            return

        # ВЫСТАВИТЬ ТОВАР
        if cb == "add_offer":
            text = "📤 Что продать?\n\n"
            rows = []
            has = False
            for vid, cnt in u["harvest"].items():
                if cnt > 0:
                    veg = VEGS[vid]
                    rows.append([InlineKeyboardButton(f"{veg['emoji']} {veg['name']} ({cnt}шт)", callback_data=f"offer_{vid}")])
                    has = True
            if not has:
                text += "У тебя нет урожая!"
            rows.append([InlineKeyboardButton("🔙 Назад", callback_data="market")])
            await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(rows))
            return

        if cb.startswith("offer_"):
            vid = cb[6:]
            veg = VEGS[vid]
            cnt = u["harvest"].get(vid, 0)
            avg = sum(veg["price"]) // 2
            text = f"{veg['emoji']} {veg['name']} ({cnt}шт)\nВыбери цену за штуку:"
            rows = [
                [InlineKeyboardButton(f"${avg-2}", callback_data=f"post_{vid}_{avg-2}_{cnt}"),
                 InlineKeyboardButton(f"${avg}", callback_data=f"post_{vid}_{avg}_{cnt}"),
                 InlineKeyboardButton(f"${avg+2}", callback_data=f"post_{vid}_{avg+2}_{cnt}")],
                [InlineKeyboardButton("🔙 Назад", callback_data="add_offer")]
            ]
            await query.edit_message_text(text, reply_markup=InlineKeyboardMarkup(rows))
            return

        if cb.startswith("post_"):
            parts = cb.split("_")
            vid = parts[1]
            price = int(parts[2])
            amount = int(parts[3])
            if u["harvest"].get(vid, 0) < amount:
                await query.answer("Недостаточно товара!", show_alert=True)
                return
            u["harvest"][vid] = u["harvest"].get(vid, 0) - amount
            offer_id = int(time.time())
            if "market_offers" not in u:
                u["market_offers"] = []
            u["market_offers"].append({"id": offer_id, "vid": vid, "amount": amount, "price": price})
            save_user(uid, u)
            veg = VEGS[vid]
            await query.edit_message_text(
                f"✅ Выставлено на базар!\n\n"
                f"{veg['emoji']} {veg['name']} x{amount} за ${price} шт",
                reply_markup=InlineKeyboardMarkup([[InlineKeyboardButton("🔙 Назад", callback_data="market")]])
            )
            return

        if cb.startswith("buy_offer_"):
            parts = cb[10:].split("_")
            seller_uid = parts[0]
            offer_id = int(parts[1])
            all_users = db()
            if seller_uid not in all_users:
                await query.answer("Продавец не найден!", show_alert=True)
                return
            seller = all_users[seller_uid]
            offer = next((o for o in seller.get("market_offers", []) if o["id"] == offer_id), None)
            if not offer:
                await query.answer("Товар уже продан!", show_alert=True)
                return
            
            total_cost = offer["price"] * offer["amount"]
            
            if u["usd"] < total_cost:
                await query.answer(f"Нужно ${total_cost}!", show_alert=True)
                return
            
            u["usd"] -= total_cost
            seller["usd"] += total_cost
            u["harvest"][offer["vid"]] = u["harvest"].get(offer["vid"], 0) + offer["amount"]
            seller["market_offers"] = [o for o in seller["market_offers"] if o["id"] != offer_id]
            
            save_user(uid, u)
            save_user(seller_uid, seller)
            
            veg = VEGS[offer["vid"]]
            await query.edit_message_text(
                f"✅ Куплено!\n\n"
                f"{veg['emoji']} 
