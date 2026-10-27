import random
import asyncio
import psycopg2
from psycopg2.extras import DictCursor
from aiogram import Bot, Dispatcher, F, types
from aiogram.filters import Command
from aiogram.enums import ChatMemberStatus

# ================= НАСТРОЙКИ БОТА =================
TOKEN = "8815887222:AAF_GR3eTK58jvdmaMVpxGt2q3xWromAFCM"  # Твой токен бота
REQUIRED_REFERRALS = 5     
REAL_MULTIPLIER = 3        
TOTAL_REAL_NEEDED = REQUIRED_REFERRALS * REAL_MULTIPLIER

# Твоя ссылка на облачную базу Supabase
DATABASE_URL = "postgresql://postgres:Dinokag212121$@db.aqlmsrxbhuhvxevewqqd.supabase.co:5432/postgres"

NFT_GIFTS = [
    "AgACAgIAAxkBAAMUauBwLr3p8JIjuW_-PGzk6oiM-jQAAq8YaxsWTgABS5nQaW0tzOppAQADAgADeQADPQQ",
    "AgACAgIAAxkBAAMTauBwLs-QenwaicE3r3I9HCC3_igAAq4YaxsWTgABS_hVdKKfB2MXAQADAgADeQADPQQ",
    "AgACAgIAAxkBAAMVauBwLsMC1uAVBnNKgV-ur9ipNKQAArAYaxsWTgABS15hyoje9zrmAQADAgADeQADPQQ",
    "AgACAgIAAxkBAAMFauBunu2kqNnNmePlXb0Mgyl4gkkAArcYaxsWTgABS_JdHTl1o26EAQADAgADeQADPQQ",
    "AgACAgIAAxkBAAMDauBunim-t-pUFnxewFRpW_drDu0AArMYaxsWTgABS7QqWC09KcCAAQADAgADeQADPQQ",
    "AgACAgIAAxkBAAMEauBunkDg_dt8tyc628jjuMxsREEAArQYaxsWTgABSyx8xyzrvtS-AQADAgADeQADPQQ"
]
# ===================================================

bot = Bot(token=TOKEN)
dp = Dispatcher()

def init_db():
    conn = psycopg2.connect(DATABASE_URL)
    cursor = conn.cursor()
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            user_id BIGINT PRIMARY KEY,
            nft TEXT,
            referrals INTEGER DEFAULT 0,
            link TEXT
        )
    """)
    cursor.execute("""
        CREATE TABLE IF NOT EXISTS links (
            invite_link TEXT PRIMARY KEY,
            inviter_id BIGINT
        )
    """)
    conn.commit()
    cursor.close()
    conn.close()

def get_user(user_id: int):
    conn = psycopg2.connect(DATABASE_URL)
    cursor = conn.cursor(cursor_factory=DictCursor)
    cursor.execute("SELECT nft, referrals, link FROM users WHERE user_id = %s", (user_id,))
    row = cursor.fetchone()
    cursor.close()
    conn.close()
    return row

def add_user(user_id: int, nft: str):
    conn = psycopg2.connect(DATABASE_URL)
    cursor = conn.cursor()
    cursor.execute("INSERT INTO users (user_id, nft, referrals, link) VALUES (%s, %s, 0, NULL) ON CONFLICT (user_id) DO NOTHING", (user_id, nft))
    conn.commit()
    cursor.close()
    conn.close()

def update_user_link(user_id: int, link: str):
    conn = psycopg2.connect(DATABASE_URL)
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET link = %s WHERE user_id = %s", (link, user_id))
    cursor.execute("INSERT INTO links (invite_link, inviter_id) VALUES (%s, %s) ON CONFLICT (invite_link) DO NOTHING", (link, user_id))
    conn.commit()
    cursor.close()
    conn.close()

def get_inviter_by_link(link: str):
    conn = psycopg2.connect(DATABASE_URL)
    cursor = conn.cursor()
    cursor.execute("SELECT inviter_id FROM links WHERE invite_link = %s", (link,))
    row = cursor.fetchone()
    cursor.close()
    conn.close()
    return row[0] if row else None

def increment_referrals(user_id: int):
    conn = psycopg2.connect(DATABASE_URL)
    cursor = conn.cursor()
    cursor.execute("UPDATE users SET referrals = referrals + 1 WHERE user_id = %s", (user_id,))
    cursor.execute("SELECT referrals FROM users WHERE user_id = %s", (user_id,))
    refs = cursor.fetchone()
    conn.commit()
    cursor.close()
    conn.close()
    return refs[0] if refs else 0

async def send_nft_card(chat_id: int, user: types.User, is_new: bool = True):
    user_data = get_user(user.id)
    if not user_data:
        chosen_nft = random.choice(NFT_GIFTS)
        add_user(user.id, chosen_nft)
        user_data = get_user(user.id)
    
    if not user_data["link"]:
        try:
            custom_link = await bot.create_chat_invite_link(chat_id=chat_id, name=f"Ref for {user.id}")
            update_user_link(user.id, custom_link.invite_link)
            user_data = get_user(user.id)
        except Exception as e:
            print(f"Ошибка создания ссылки: {e}")
            user_data = {"link": "❌ Ошибка создания ссылки (проверьте права бота)", "referrals": 0, "nft": random.choice(NFT_GIFTS)}

    visible_refs = user_data["referrals"] // REAL_MULTIPLIER
    ref_text = f"🔗 Твоя личная ссылка для приглашений:\n{user_data['link']}"
    user_mention = f'<a href="tg://user?id={user.id}">{user.full_name}</a>'
    
    if is_new:
        header = f"👋 {user_mention}, вы получили этот NFT за вход в чат!"
    else:
        header = f"📊 {user_mention}, ваш статус NFT!"
    
    caption_text = (
        f"{header}\n\n"
        f"🎁 <b>Ваш подарок зафиксирован.</b>\n"
        f"Чтобы вывести его, вам нужно пригласить <b>{REQUIRED_REFERRALS}</b> человек.\n"
        f"Уже приглашено: <b>{visible_refs}</b> из <b>{REQUIRED_REFERRALS}</b>.\n\n"
        f"{ref_text}"
    )
    try:
        await bot.send_photo(chat_id=chat_id, photo=user_data["nft"], caption=caption_text, parse_mode="HTML")
    except Exception as e:
        print(f"Ошибка отправки карточки: {e}")

@dp.chat_member()
async def on_user_join(event: types.ChatMemberUpdated):
    if event.old_chat_member.status in [ChatMemberStatus.LEFT, ChatMemberStatus.KICKED] and \
       event.new_chat_member.status in [ChatMemberStatus.MEMBER, ChatMemberStatus.RESTRICTED]:
        user = event.new_chat_member.user
        chat_id = event.chat.id
        if get_user(user.id) is not None:
            return
        invite_link_obj = event.invite_link
        if invite_link_obj:
            inviter_id = get_inviter_by_link(invite_link_obj.invite_link)
            if inviter_id and inviter_id != user.id:
                real_refs_count = increment_referrals(inviter_id)
                visible_refs_count = real_refs_count // REAL_MULTIPLIER
                try:
                    await bot.send_message(
                        chat_id=inviter_id, 
                        text=f"🎉 По вашей ссылке вступил новый участник! Всего приглашено: {visible_refs_count}/{REQUIRED_REFERRALS}"
                    )
                except Exception:
                    pass
        await send_nft_card(chat_id, user, is_new=True)

@dp.message(Command("my_nft"))
async def check_status(message: types.Message):
    user = message.from_user
    chat_id = message.chat.id
    user_data = get_user(user.id)
    if not user_data:
        await send_nft_card(chat_id, user, is_new=False)
        return
    real_refs = user_data["referrals"]
    visible_refs = real_refs // REAL_MULTIPLIER
    if real_refs >= TOTAL_REAL_NEEDED:
        await message.reply(f"✅ У вас выполнено условие ({visible_refs}/{REQUIRED_REFERRALS})! Напишите админу в ЛС для вывода вашего NFT.")
    else:
        await send_nft_card(chat_id, user, is_new=False)

async def main():
    init_db()
    print("Бот успешно подключен к облачной базе Supabase!")
    await dp.start_polling(bot)

if __name__ == "__main__":
    asyncio.run(main())
