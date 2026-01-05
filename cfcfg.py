import asyncio
import sqlite3
from aiogram import Bot, Dispatcher, F
from aiogram.types import Message, CallbackQuery, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from aiogram.fsm.state import State, StatesGroup
from aiogram.fsm.storage.memory import MemoryStorage

TOKEN = "8204900087:AAEpPTiB01lmVLzrrtl6R1q7jqf1ILzPrQo"
ADMIN_ID = 1123838913
MANAGER_USERNAME = "cestlavieq"

bot = Bot(TOKEN)
dp = Dispatcher(storage=MemoryStorage())

db = sqlite3.connect("shop.db")
sql = db.cursor()

# ---------- DATABASE ----------
sql.execute("""
CREATE TABLE IF NOT EXISTS products(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT,
    price INTEGER,
    photo TEXT,
    category TEXT,
    sizes TEXT
)
""")

sql.execute("""
CREATE TABLE IF NOT EXISTS cart(
    user_id INTEGER,
    product_id INTEGER,
    size TEXT
)
""")

sql.execute("""
CREATE TABLE IF NOT EXISTS orders(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    username TEXT,
    total INTEGER,
    items TEXT,
    address TEXT,
    comment TEXT
)
""")

db.commit()

RULES_TEXT = """
📜 ПРАВИЛА И ГАРАНТИИ

1. Оплата производится напрямую продавцу через ЮMoney или перевод.
2. Бот является технической платформой для оформления заказов.
3. После оплаты продавец обязан отправить товар клиенту.
4. В случае проблем вы можете написать менеджеру.
5. Заказы, оформленные без оплаты, не обрабатываются.
6. Возврат возможен только по договорённости с продавцом.

Нажимая «Оплатить заказ», вы соглашаетесь с этими правилами.
"""

PAY_TEXT = """
💳 ОПЛАТА ЗАКАЗА

Переведите сумму по номеру через СБП:

📱 +7 929 357-16-68
Банк: Тинькофф

В комментарии к переводу укажите:
👉 Ваш Telegram (@username)

После оплаты нажмите кнопку «Я оплатил».
"""

@dp.callback_query(F.data == "pay")
async def pay_info(c: CallbackQuery):
    await c.answer()
    kb = InlineKeyboardMarkup(inline_keyboard=[
        [InlineKeyboardButton(text="✅ Я оплатил", callback_data="paid")]
    ])
    await c.message.answer(PAY_TEXT, reply_markup=kb)

@dp.callback_query(F.data == "paid")
async def paid(c: CallbackQuery):
    await c.answer("Ожидаем подтверждение")
    await c.message.answer("Спасибо! Менеджер проверит оплату.")

    await bot.send_message(
        ADMIN_ID,
        f"💰 @{c.from_user.username} нажал «Я оплатил». Проверь перевод на +79293571668"
    )

sql.execute("""
CREATE TABLE IF NOT EXISTS categories(
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT UNIQUE
)
""")
db.commit()

for c in ["Куртки","Кофты","Штаны","Обувь","Аксессуары","Футболки","Головные уборы"]:
    try:
        sql.execute("INSERT INTO categories(name) VALUES(?)", (c,))
    except:
        pass
db.commit()

# ---------- STATES ----------
class AddProduct(StatesGroup):
    photo = State()
    name = State()
    price = State()
    category = State()
    sizes = State()

class Checkout(StatesGroup):
    address = State()
    comment = State()

class EditPrice(StatesGroup):
    price = State()

class AddCategory(StatesGroup):
    name = State()

@dp.callback_query(F.data == "addcat")
async def add_category_start(c: CallbackQuery, state: FSMContext):
    await c.answer()
    await c.message.answer("Введите название новой категории:")
    await state.set_state(AddCategory.name)

@dp.message(AddCategory.name)
async def add_category_save(m: Message, state: FSMContext):
    try:
        sql.execute("INSERT INTO categories(name) VALUES(?)", (m.text,))
        db.commit()
        await m.answer("✅ Категория добавлена")
    except:
        await m.answer("❌ Такая категория уже есть")

    await state.clear()

@dp.message(EditPrice.price)
async def edit_price_save(m: Message, state: FSMContext):
    if not m.text.isdigit():
        await m.answer("Введите число")
        return

    pid = edit_price_target.get(m.from_user.id)
    if not pid:
        await m.answer("Ошибка")
        await state.clear()
        return

    sql.execute("UPDATE products SET price=? WHERE id=?", (int(m.text), pid))
    db.commit()

    await m.answer("✅ Цена обновлена")
    await state.clear()

edit_price_target = {}

def get_categories():
    return [c[0] for c in sql.execute("SELECT name FROM categories").fetchall()]

def main_kb(uid):
    kb = [
        [KeyboardButton(text="🛍 Каталог"), KeyboardButton(text="🛒 Корзина")],
        [KeyboardButton(text="📦 Мои заказы"), KeyboardButton(text="💬 Менеджер")],
        [KeyboardButton(text="📜 Гарантии и правила")]
    ]
    if uid == ADMIN_ID:
        kb.append([KeyboardButton(text="⚙ Админ")])
    return ReplyKeyboardMarkup(keyboard=kb, resize_keyboard=True)

# ---------- START ----------
@dp.message(Command("start"))
async def start(m: Message):
    await m.answer("Добро пожаловать!", reply_markup=main_kb(m.from_user.id))

# ---------- MANAGER ----------
@dp.message(F.text == "💬 Менеджер")
async def manager(m: Message):
    await m.answer(f"https://t.me/{MANAGER_USERNAME}")

@dp.message(F.text == "📜 Гарантии и правила")
async def rules(m: Message):
    await m.answer(RULES_TEXT)

@dp.message(F.text == "📦 Мои заказы")
async def my_orders(m: Message):
    orders = sql.execute(
        "SELECT id, total, items, address FROM orders WHERE user_id=? ORDER BY id DESC",
        (m.from_user.id,)
    ).fetchall()

    if not orders:
        await m.answer("📭 У вас пока нет заказов")
        return

    text = ""
    for o in orders:
        text += (
            f"🧾 Заказ #{o[0]}\n"
            f"{o[2]}\n"
            f"💰 Сумма: {o[1]} ₽\n"
            f"📦 Адрес: {o[3]}\n\n"
        )

    await m.answer(text)

# ---------- CATALOG ----------
@dp.message(F.text == "🛍 Каталог")
async def catalog(m: Message):
    kb = [[InlineKeyboardButton(text=c, callback_data=f"cat:{c}")] for c in get_categories()]
    await m.answer("Выберите категорию:", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))

@dp.callback_query(F.data.startswith("cat:"))
async def show_category(c: CallbackQuery):
    await c.answer()
    cat = c.data.split(":")[1]
    items = sql.execute("SELECT * FROM products WHERE category=?", (cat,)).fetchall()

    if not items:
        await c.message.answer("В этой категории нет товаров")
        return

    for p in items:
        buttons = []
        for s in p[5].split(","):
            buttons.append([InlineKeyboardButton(text=s.strip(), callback_data=f"add:{p[0]}:{s.strip()}")])

        if c.from_user.id == ADMIN_ID:
            buttons.append([
                InlineKeyboardButton(text="✏ Цена", callback_data=f"edit:{p[0]}"),
                InlineKeyboardButton(text="🗑 Удалить", callback_data=f"del:{p[0]}")
            ])

        await bot.send_photo(
            c.from_user.id,
            p[3],
            caption=f"{p[1]}\nЦена: {p[2]} ₽",
            reply_markup=InlineKeyboardMarkup(inline_keyboard=buttons)
        )

# ---------- CART ----------
@dp.callback_query(F.data.startswith("add:"))
async def add_to_cart(c: CallbackQuery):
    await c.answer()
    _, pid, size = c.data.split(":")
    sql.execute("INSERT INTO cart VALUES(?,?,?)", (c.from_user.id, pid, size))
    db.commit()
    await c.message.answer("Добавлено в корзину")

@dp.callback_query(F.data.startswith("edit:"))
async def edit_price_start(c: CallbackQuery, state: FSMContext):
    await c.answer()

    pid = int(c.data.split(":")[1])
    edit_price_target[c.from_user.id] = pid

    await c.message.answer("Введите новую цену товара:")
    await state.set_state(EditPrice.price)

@dp.callback_query(F.data.startswith("delcat:"))
async def delete_category(c: CallbackQuery):
    await c.answer()
    name = c.data.split(":")[1]

    sql.execute("DELETE FROM categories WHERE name=?", (name,))
    db.commit()

    await c.message.answer(f"❌ Категория {name} удалена")

@dp.callback_query(F.data == "admin_categories")
async def admin_categories(c: CallbackQuery):
    await c.answer()

    cats = sql.execute("SELECT name FROM categories").fetchall()

    if not cats:
        await c.message.answer("Категорий пока нет")
        return

    kb = []
    for c_name in cats:
        kb.append([
            InlineKeyboardButton(text=f"❌ {c_name[0]}", callback_data=f"delcat:{c_name[0]}")
        ])

    kb.append([InlineKeyboardButton(text="➕ Добавить категорию", callback_data="addcat")])

    await c.message.answer("Управление категориями:", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))

@dp.message(F.text == "🛒 Корзина")
async def show_cart(m: Message):
    items = sql.execute("""
    SELECT products.name, products.price, cart.size
    FROM cart JOIN products ON cart.product_id = products.id
    WHERE cart.user_id=?
    """, (m.from_user.id,)).fetchall()

    if not items:
        await m.answer("Корзина пуста")
        return

    total = sum(i[1] for i in items)
    text = "\n".join([f"{i[0]} ({i[2]}) — {i[1]} ₽" for i in items])

    await m.answer(text + f"\n\nИтого: {total} ₽",
                   reply_markup=InlineKeyboardMarkup(inline_keyboard=[
                       [InlineKeyboardButton(text="💳 Оплатить", callback_data="pay")],
                       [InlineKeyboardButton(text="📦 Оформить заказ", callback_data="checkout")]
                   ])
                   )

# ---------- CHECKOUT ----------
@dp.callback_query(F.data == "checkout")
async def checkout_start(c: CallbackQuery, state: FSMContext):
    await c.answer()
    await c.message.answer("Введите адрес доставки")
    await state.set_state(Checkout.address)

@dp.message(Checkout.address)
async def checkout_address(m: Message, state: FSMContext):
    await state.update_data(address=m.text)
    await m.answer("Комментарий к заказу (или -)")
    await state.set_state(Checkout.comment)

@dp.message(Checkout.comment)
async def checkout_comment(m: Message, state: FSMContext):
    data = await state.get_data()
    comment = m.text

    # Берём корзину пользователя
    items = sql.execute("""
    SELECT products.name, products.price, cart.size
    FROM cart
    JOIN products ON cart.product_id = products.id
    WHERE cart.user_id=?
    """, (m.from_user.id,)).fetchall()

    if not items:
        await m.answer("❌ Корзина пуста")
        await state.clear()
        return

    total = 0
    items_text = ""

    for name, price, size in items:
        total += price
        items_text += f"{name} ({size}) — {price} ₽\n"

    sql.execute(
        "INSERT INTO orders (user_id, username, total, items, address, comment) VALUES (?, ?, ?, ?, ?, ?)",
        (
            m.from_user.id,
            m.from_user.username or "no_username",
            total,
            items_text,
            data["address"],
            comment
        )
    )
    db.commit()

    # очищаем корзину
    sql.execute("DELETE FROM cart WHERE user_id=?", (m.from_user.id,))
    db.commit()

    await m.answer("✅ Заказ оформлен! Мы с вами свяжемся.")

    await bot.send_message(
        ADMIN_ID,
        f"📦 Новый заказ\n"
        f"👤 @{m.from_user.username}\n"
        f"{items_text}\n"
        f"💰 Итого: {total} ₽\n"
        f"📦 Адрес: {data['address']}\n"
        f"💬 Комментарий: {comment}"
    )

    await state.clear()

# ---------- ADMIN ----------
@dp.message(F.text == "⚙ Админ")
async def admin(m: Message):
    if m.from_user.id != ADMIN_ID:
        return

    await m.answer(
        "Админ панель",
        reply_markup=InlineKeyboardMarkup(inline_keyboard=[
            [InlineKeyboardButton(text="➕ Добавить товар", callback_data="add_product")],
            [InlineKeyboardButton(text="📦 Все заказы", callback_data="all_orders")],
            [InlineKeyboardButton(text="🗂 Категории", callback_data="admin_categories")]
        ])
    )
@dp.callback_query(F.data == "all_orders")
async def all_orders(c: CallbackQuery):
    await c.answer()

    orders = sql.execute("SELECT id, username, total, items, address, comment FROM orders ORDER BY id DESC").fetchall()

    if not orders:
        await c.message.answer("📭 Заказов пока нет")
        return

    for o in orders:
        text = f"""
🧾 Заказ #{o[0]}
👤 Клиент: @{o[1]}
💰 Сумма: {o[2]} ₽

🛍 Товары:
{o[3]}

📦 Адрес:
{o[4]}

💬 Комментарий:
{o[5]}
"""
        await c.message.answer(text)

@dp.callback_query(F.data == "admin_categories")
async def admin_categories(c: CallbackQuery):
    await c.answer()

    kb = []
    for c in get_categories():
        kb.append([
            InlineKeyboardButton(text=f"❌ {c}", callback_data=f"delcat:{c}")
        ])

    kb.append([InlineKeyboardButton(text="➕ Добавить категорию", callback_data="addcat")])

    await c.message.answer("Управление категориями:", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))

@dp.callback_query(F.data.startswith("delcat:"))
async def delete_category(c: CallbackQuery):
    await c.answer()
    name = c.data.split(":")[1]
    sql.execute("DELETE FROM categories WHERE name=?", (name,))
    db.commit()
    await c.message.answer(f"❌ Категория {name} удалена")

@dp.callback_query(F.data.startswith("del:"))
async def delete_product(c: CallbackQuery):
    await c.answer()
    pid = int(c.data.split(":")[1])
    sql.execute("DELETE FROM products WHERE id=?", (pid,))
    db.commit()
    await c.message.answer("Товар удалён")
@dp.callback_query(F.data == "add_product")
async def add_product_start(c: CallbackQuery, state: FSMContext):
    await c.answer()
    await c.message.answer("Отправь фото товара")
    await state.set_state(AddProduct.photo)

@dp.message(AddProduct.photo)
async def add_photo(m: Message, state: FSMContext):
    await state.update_data(photo=m.photo[-1].file_id)
    await m.answer("Название товара")
    await state.set_state(AddProduct.name)

@dp.message(AddProduct.name)
async def add_name(m: Message, state: FSMContext):
    await state.update_data(name=m.text)
    await m.answer("Цена")
    await state.set_state(AddProduct.price)

@dp.message(AddProduct.price)
async def add_price(m: Message, state: FSMContext):
    if not m.text.isdigit():
        await m.answer("Введите число")
        return
    await state.update_data(price=int(m.text))

    kb = [[InlineKeyboardButton(text=c, callback_data=f"setcat:{c}")] for c in get_categories()]
    await m.answer("Выберите категорию:", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))
    await state.set_state(AddProduct.category)

@dp.callback_query(F.data.startswith("setcat:"))
async def set_category(c: CallbackQuery, state: FSMContext):
    await c.answer()
    await state.update_data(category=c.data.split(":")[1])
    await c.message.answer("Введите размеры через запятую (например: S,M,L или 41,42,43)")
    await state.set_state(AddProduct.sizes)

@dp.message(AddProduct.sizes)
async def add_sizes(m: Message, state: FSMContext):
    data = await state.get_data()
    sql.execute(
        "INSERT INTO products(name,price,photo,category,sizes) VALUES(?,?,?,?,?)",
        (data["name"], data["price"], data["photo"], data["category"], m.text)
    )
    db.commit()
    await m.answer("Товар добавлен")
    await state.clear()@dp.callback_query(F.data == "add_product")
async def add_product_start(c: CallbackQuery, state: FSMContext):
    await c.answer()
    await c.message.answer("Отправь фото товара")
    await state.set_state(AddProduct.photo)

@dp.message(AddProduct.photo)
async def add_photo(m: Message, state: FSMContext):
    await state.update_data(photo=m.photo[-1].file_id)
    await m.answer("Название товара")
    await state.set_state(AddProduct.name)

@dp.message(AddProduct.name)
async def add_name(m: Message, state: FSMContext):
    await state.update_data(name=m.text)
    await m.answer("Цена")
    await state.set_state(AddProduct.price)

@dp.message(AddProduct.price)
async def add_price(m: Message, state: FSMContext):
    if not m.text.isdigit():
        await m.answer("Введите число")
        return
    await state.update_data(price=int(m.text))

    kb = [[InlineKeyboardButton(text=c, callback_data=f"setcat:{c}")] for c in get_categories()]
    await m.answer("Выберите категорию:", reply_markup=InlineKeyboardMarkup(inline_keyboard=kb))
    await state.set_state(AddProduct.category)

@dp.callback_query(F.data.startswith("setcat:"))
async def set_category(c: CallbackQuery, state: FSMContext):
    await c.answer()
    await state.update_data(category=c.data.split(":")[1])
    await c.message.answer("Введите размеры через запятую (например: S,M,L или 41,42,43)")
    await state.set_state(AddProduct.sizes)

@dp.message(AddProduct.sizes)
async def add_sizes(m: Message, state: FSMContext):
    data = await state.get_data()
    sql.execute(
        "INSERT INTO products(name,price,photo,category,sizes) VALUES(?,?,?,?,?)",
        (data["name"], data["price"], data["photo"], data["category"], m.text)
    )
    db.commit()
    await m.answer("Товар добавлен")
    await state.clear()

# ---------- RUN ----------
async def main():
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())