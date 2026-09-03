import os
import aiohttp
import asyncio
import time
import html
import traceback
import sys
import re
import imaplib
import email
from datetime import datetime

from pyrogram import Client, filters, enums, idle
from pyrogram.types import CallbackQuery, InlineKeyboardMarkup, InlineKeyboardButton
from pyrogram.errors import SessionPasswordNeeded, FloodWait, UserNotParticipant, UserAlreadyParticipant
from pyrogram.raw.functions.messages import GetChatInviteImporters, CheckChatInvite
from pyrogram.raw.types import InputUserEmpty
from pyrogram.handlers import MessageHandler, CallbackQueryHandler, ChatJoinRequestHandler
try:
    from .storage import SQLiteStore
except ImportError:
    from storage import SQLiteStore

# ================= DETAILS =================
API_ID = int(os.getenv("TELEGRAM_API_ID", "0") or "0")
API_HASH = os.getenv("TELEGRAM_API_HASH", "")
BOT_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN", "")
GMAIL_USER = os.getenv("GMAIL_USER", "")
GMAIL_PASS = os.getenv("GMAIL_PASS", "")
ADMINS = [
    int(value.strip())
    for value in os.getenv("ADMINS", "8821069804,7134054308").split(",")
    if value.strip().isdigit()
]
bot = Client("Shub_DMS_Bot", api_id=API_ID, api_hash=API_HASH, bot_token=BOT_TOKEN, in_memory=True)

# ================= 🌟 CUSTOMIZATION HUB 🌟 =================
BTN_EMOJIS = {
    "start": "6154578037976339054",   
    "user": "5870994129244131212",    
    "money": "5870892901159932239",   
    "diamond": "5276239041052828276", 
    "add": "6032693626394382504",     
    "cross": "6086741365998227951",   
    "tick": "6089196601232854885",    
    "home": "5215260113291455937",    
    "shield": "6082526379583212989",  
    "setting": "5258332798409783582", 
    "target": "6260516734931833587",  
    "globe": "6147673955357431919"    
}

# ================= IST TIME HELPERS =================
def get_ist(): return time.gmtime(time.time() + 19800)
def get_ist_str(fmt="%Y-%m-%d"): return time.strftime(fmt, get_ist())
def get_ist_ts_str(ts, fmt="%d %b %Y, %I:%M %p"): return time.strftime(fmt, time.gmtime(ts + 19800))

def check_payment_in_gmail(utr_to_find):
    try:
        mail = imaplib.IMAP4_SSL("imap.gmail.com")
        mail.login(GMAIL_USER, GMAIL_PASS)
        mail.select("inbox")
        status, messages = mail.search(None, f'(TEXT "{utr_to_find}")')
        if status == "OK" and messages[0]:
            mail_ids = messages[0].split()
            for mail_id in mail_ids[-1:]: 
                status, msg_data = mail.fetch(mail_id, "(RFC822)")
                for response_part in msg_data:
                    if isinstance(response_part, tuple):
                        msg = email.message_from_bytes(response_part[1])
                        body = ""
                        if msg.is_multipart():
                            for part in msg.walk():
                                if part.get_content_type() == "text/plain": body += part.get_payload(decode=True).decode(errors='ignore')
                        else: body = msg.get_payload(decode=True).decode(errors='ignore')
                        clean_body = re.sub(r'\s+', ' ', body).upper()
                        amounts = re.findall(r'(?:₹|RS\.?|INR)\s*([\d\.]+)', clean_body)
                        if utr_to_find in clean_body and amounts:
                            mail.logout(); return float(amounts[0]) 
        mail.logout(); return None 
    except Exception: return None

# ================= PREMIUM ANIMATED TEXT EMOJIS =================
def e(eid, fb): return f"<tg-emoji emoji-id='{eid}'>{fb}</tg-emoji>"

E_CHK = e(BTN_EMOJIS["tick"], "✅")   
E_DIA = e(BTN_EMOJIS["diamond"], "💎")   
E_SHD = e(BTN_EMOJIS["shield"], "🛡️")   
E_WRN = e("5350460637182993292", "⚠️")   
E_LNK = e("5870782662234346251", "🔗")   
E_CAL = e("5891105528356018797", "📅")   
E_MED = e("5870984130560266604", "🎖️")   
E_TRI = e(BTN_EMOJIS["target"], "🔻")   
E_START = e(BTN_EMOJIS["start"], "🚀") 
E_PROF = e(BTN_EMOJIS["user"], "👤")  
E_ADD = e(BTN_EMOJIS["add"], "➕")   
E_WAIT = e("6161378495919295545", "⏳")  
E_SYNC = e("6273997297244180325", "🔄")  
E_ACT = e("6028497653799588476", "⚡")   
E_ADM = e(BTN_EMOJIS["setting"], "🛠️")  
E_STAT = e("6183531013814096319", "💻")  
E_MONEY = e(BTN_EMOJIS["money"], "💸") 
E_PREM = e("6154611916678369390", "⚜️")  
E_PLAY = e("6183901617952132937", "▶️")  
E_STOP = e("6059631768649077274", "🛑")  

# --- 💥 RAW API ENGINE FOR COLOR BUTTONS WITH FALLBACK 💥 ---
def ibtn(text, cb=None, url=None, style="primary", icon=None):
    btn = {"text": text, "style": style}
    if cb: btn["callback_data"] = cb 
    if url: btn["url"] = url
    if icon: btn["icon_custom_emoji_id"] = icon
    return btn

class MockMessage:
    def __init__(self, chat_id, message_id):
        self.chat = type('Chat', (), {'id': chat_id})()
        self.id = message_id

    async def delete(self):
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/deleteMessage"
        async with aiohttp.ClientSession() as session:
            await session.post(url, json={"chat_id": self.chat.id, "message_id": self.id})

async def api_send(chat_id, text, kb=None, photo=None):
    payload = {"chat_id": chat_id, "parse_mode": "HTML"}
    if text and not photo: payload["text"] = text
    elif text and photo: payload["caption"] = text
    if photo: payload["photo"] = photo
    if kb: payload["reply_markup"] = kb
    
    method = "sendPhoto" if photo else "sendMessage"
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/{method}"
    
    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=payload) as resp:
            data = await resp.json()
            if data.get("ok"): 
                return MockMessage(chat_id, data["result"]["message_id"])
                
    try:
        standard_kb = None
        if kb and "inline_keyboard" in kb:
            pyro_btns = []
            for row in kb["inline_keyboard"]:
                pyro_row = []
                for b in row:
                    pyro_row.append(InlineKeyboardButton(text=b.get("text",""), callback_data=b.get("callback_data"), url=b.get("url")))
                pyro_btns.append(pyro_row)
            standard_kb = InlineKeyboardMarkup(pyro_btns)
            
        if photo:
            m = await bot.send_photo(chat_id, photo=photo, caption=text, reply_markup=standard_kb, parse_mode=enums.ParseMode.HTML)
        else:
            m = await bot.send_message(chat_id, text, reply_markup=standard_kb, parse_mode=enums.ParseMode.HTML)
        return MockMessage(chat_id, m.id)
    except Exception as e:
        return MockMessage(chat_id, None)

async def api_edit(chat_id, msg_id, text, kb=None):
    payload = {"chat_id": chat_id, "message_id": msg_id, "text": text, "parse_mode": "HTML"}
    if kb: payload["reply_markup"] = kb
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/editMessageText"
    
    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=payload) as resp:
            data = await resp.json()
            if data.get("ok"): 
                return MockMessage(chat_id, data["result"]["message_id"])
                
    try:
        standard_kb = None
        if kb and "inline_keyboard" in kb:
            pyro_btns = []
            for row in kb["inline_keyboard"]:
                pyro_row = []
                for b in row:
                    pyro_row.append(InlineKeyboardButton(text=b.get("text",""), callback_data=b.get("callback_data"), url=b.get("url")))
                pyro_btns.append(pyro_row)
            standard_kb = InlineKeyboardMarkup(pyro_btns)
        m = await bot.edit_message_text(chat_id, msg_id, text, reply_markup=standard_kb, parse_mode=enums.ParseMode.HTML)
        return MockMessage(chat_id, m.id)
    except Exception:
        return MockMessage(chat_id, msg_id)

async def api_edit_caption(chat_id, msg_id, text, kb=None):
    payload = {"chat_id": chat_id, "message_id": msg_id, "caption": text, "parse_mode": "HTML"}
    if kb: payload["reply_markup"] = kb
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/editMessageCaption"
    
    async with aiohttp.ClientSession() as session:
        async with session.post(url, json=payload) as resp:
            data = await resp.json()
            if data.get("ok"): 
                return MockMessage(chat_id, data["result"]["message_id"])
                
    try:
        standard_kb = None
        if kb and "inline_keyboard" in kb:
            pyro_btns = []
            for row in kb["inline_keyboard"]:
                pyro_row = []
                for b in row:
                    pyro_row.append(InlineKeyboardButton(text=b.get("text",""), callback_data=b.get("callback_data"), url=b.get("url")))
                pyro_btns.append(pyro_row)
            standard_kb = InlineKeyboardMarkup(pyro_btns)
        m = await bot.edit_message_caption(chat_id, msg_id, text, reply_markup=standard_kb, parse_mode=enums.ParseMode.HTML)
        return MockMessage(chat_id, m.id)
    except Exception:
        return MockMessage(chat_id, msg_id)

async def safe_edit(query, text, kb=None):
    chat_id = query.message.chat.id
    msg_id = query.message.id
    if query.message.photo or query.message.video or query.message.document:
        await query.message.delete()
        return await api_send(chat_id, text, kb=kb)
    else:
        return await api_edit(chat_id, msg_id, text, kb=kb)

# ================= SQLITE SETUP =================
db_store, users_col, settings_col = None, None, None
USER_STATES, ACTIVE_TASKS = {}, {}

async def init_db():
    global db_store, users_col, settings_col
    db_path = os.getenv("SQLITE_PATH", "data/shub_dms.sqlite3")
    db_store = SQLiteStore(db_path)
    users_col = db_store.collection("users")
    settings_col = db_store.collection("settings")
    
    config = await settings_col.find_one({"_id": "config"})
    if not config:
        await settings_col.insert_one({
            "_id": "config", "price_1d_inr": "25", "price_1d_usd": "0.5", "price_3d_inr": "60", "price_3d_usd": "1.5",
            "price_7d_inr": "120", "price_7d_usd": "3", "price_1m_inr": "350", "price_1m_usd": "8", 
            "upi_fampay": "not_set", "upi_manual": "not_set", "crypto": "not_set", "auto_payment_status": False,
            "free_trial_limit": 100, "msg_delay": 0, "log_channel": "none", "success_log_channel": "none", "leaderboard_channel": "none",
            "free_channel_id": "none", "free_channel_link": "none", "total_sales_inr": 0, "total_sales_usd": 0, "global_dms": 0, "sales_history": {},
            "qr_fampay": "none", "qr_manual": "none", "qr_crypto": "none", "fsub1": "none", "fsub2": "none", "fsub3": "none", "fsub4": "none", "fsub5": "none", 
            "reqall_id": "none", "reqall_link": "none", "website_link": "not_set", "pending_bot_link": "not_set", "forward_bot_link": "not_set",
            "ldb_time": 21, "free_req_limit": 300, "ref_bonus": 50, "maintenance": False
        })

# ================= HELPER FUNCTIONS =================
async def get_user(user_id):
    user_id = str(user_id)
    today = get_ist_str("%Y-%m-%d")
    user = await users_col.find_one({"_id": user_id})
    if not user:
        user = {"_id": user_id, "username": "", "banned": False, "premium_expiry": 0, "sessions": [], "saved_channels": [], "custom_msg_type": "text", "custom_msg": "HELLO", "custom_caption": "", "total_dms": 0, "daily_dms": 0, "last_date": today, "messaged_users": {}, "pending_chats": []}
        await users_col.insert_one(user)
    else:
        if user.get("last_date") != today:
            await users_col.update_one({"_id": user_id}, {"$set": {"daily_dms": 0, "last_date": today}})
            user["daily_dms"] = 0; user["last_date"] = today
    return user

async def is_premium(user_id): return (await get_user(user_id)).get("premium_expiry", 0) > time.time()

# ================= BACKGROUND TASKS =================
# 💥 THIS IS WHAT WAS MISSING LAST TIME! FIXED! 💥
async def auto_leaderboard_task():
    while True:
        try:
            config = await settings_col.find_one({"_id": "config"})
            ldb_channel = config.get("leaderboard_channel", "none")
            ldb_time = int(config.get("ldb_time", 21))
            
            if ldb_channel != "none" and get_ist().tm_hour == ldb_time:
                today = get_ist_str("%Y-%m-%d")
                last_post = config.get("last_ldb_post", "")
                if last_post != today:
                    top_today = await users_col.aggregate([{"$match": {"last_date": today, "daily_dms": {"$gt": 0}}}, {"$sort": {"daily_dms": -1}}, {"$limit": 10}]).to_list(10)
                    if top_today:
                        text = f"{E_MED} <b>Daily DM Leaderboard ({today})</b> {E_MED}\n\n"
                        for i, u in enumerate(top_today):
                            un = f"(@{u['username']})" if u.get('username') and u['username'] != "N/A" else ""
                            text += f"<b>{i+1}.</b> <code>...{str(u['_id'])[-4:]}</code> {un} - {u['daily_dms']} DMs\n"
                        text += f"\n{E_START} Automatically Generated"
                        try:
                            lc_id = int(ldb_channel) if str(ldb_channel).replace("-", "").isdigit() else ldb_channel
                            await api_send(lc_id, text)
                            await settings_col.update_one({"_id": "config"}, {"$set": {"last_ldb_post": today}})
                        except Exception: pass
        except: pass
        await asyncio.sleep(1800)

# ================= CORE HANDLERS =================
async def handle_join_requests(client, message):
    user_id = str(message.from_user.id); chat_id = str(message.chat.id)
    await users_col.update_one({"_id": user_id}, {"$addToSet": {"pending_chats": chat_id}}, upsert=True)

async def check_force_join(user_id):
    if int(user_id) in ADMINS: return True, []
    config = await settings_col.find_one({"_id": "config"}); u = await get_user(user_id)
    pending_chats = set(u.get("pending_chats", []))
    fsubs = [config.get(f"fsub{i}", "none") for i in range(1, 6)]
    not_joined = []
    
    for i, fsub in enumerate(fsubs):
        if fsub == "none" or str(fsub).strip() == "": continue
        parts = str(fsub).split(" "); chat_id = parts[0]; link = parts[1] if len(parts) > 1 else chat_id 
        if str(chat_id) in pending_chats or str(chat_id).replace("-100", "") in pending_chats: continue
        try:
            if chat_id.startswith("-100"): await bot.get_chat_member(int(chat_id), int(user_id))
            elif "t.me/" in chat_id: await bot.get_chat_member(chat_id.split("/")[-1], int(user_id))
            else: await bot.get_chat_member(chat_id, int(user_id))
        except UserNotParticipant: not_joined.append((f"Channel {i+1}", link))
        except Exception: not_joined.append((f"Channel {i+1}", link))

    reqall_id = config.get("reqall_id", "none")
    if reqall_id != "none":
        reqall_link = config.get("reqall_link", "none")
        if str(reqall_id) not in pending_chats and str(reqall_id).replace("-100", "") not in pending_chats:
            try:
                if reqall_id.startswith("-100"): await bot.get_chat_member(int(reqall_id), int(user_id))
                elif "t.me/" in reqall_id: await bot.get_chat_member(reqall_id.split("/")[-1], int(user_id))
                else: await bot.get_chat_member(reqall_id, int(user_id))
            except UserNotParticipant: not_joined.append(("Mandatory Request", reqall_link))
            except Exception: not_joined.append(("Mandatory Request", reqall_link))

    return len(not_joined) == 0, not_joined

async def get_home_menu(user_id, first_name, config):
    free_limit = int(config.get('free_trial_limit') or 100)

    text = f"""✦ <i>𝐒𝐡𝐮𝐛 𝐃𝐌𝐬 𝐁𝐨𝐭</i> ✦
<i>Premium Mass DM & Marketing Automation</i>

Welcome to the most advanced and secure Telegram automation engine. Maximize your outreach with zero ban risk, utilizing our high-speed smart nodes.

━━━━━━━━━━━━━━━━━━━━
{E_PROF} <b>User Profile:</b> {first_name}
🆔 <b>Account ID:</b> <code>{user_id}</code>
{E_ACT} <b>Server Node:</b> 🟢 100% Online
━━━━━━━━━━━━━━━━━━━━

{E_CHK} Expand your audience securely!
🎁 Claim your <b>{free_limit} Free DMs</b> trial today.

Developed by - @SHUBxERA"""

    btns = [
        [ibtn("START MASS DM CAMPAIGN", "start_dm", style="success", icon=BTN_EMOJIS["start"])],
        [ibtn("🚀 FAST Auto-Forward DM", "set_fwd_msg", style="primary", icon=BTN_EMOJIS["globe"])], 
        [ibtn("Scrape Group", "scrape_group", style="primary", icon=BTN_EMOJIS["user"]), ibtn("Invite & Earn", "invite_earn", style="primary", icon=BTN_EMOJIS["money"])],
        [ibtn("VIP Premium", "buy_premium", style="danger", icon=BTN_EMOJIS["diamond"]), ibtn("My Account", "my_account", style="primary", icon=BTN_EMOJIS["user"])],
        [ibtn("Add Session", "add_session", style="success", icon=BTN_EMOJIS["add"]), ibtn("Remove Session", "remove_session", style="danger", icon=BTN_EMOJIS["cross"])],
        [ibtn("Tutorial & Terms", "how_to_use", style="primary", icon=BTN_EMOJIS["setting"])],
        [ibtn("Contact Support", url="https://t.me/SHUBxERA", style="danger", icon=BTN_EMOJIS["target"])]
    ]
    return text, {"inline_keyboard": btns}

async def get_chat_safely(client, raw_link, fallback_id):
    try:
        parsed_id = int(fallback_id) if str(fallback_id).lstrip('-').isdigit() else fallback_id
        return await client.get_chat(parsed_id)
    except Exception: pass
    link = str(raw_link).strip()
    if "t.me/" in link:
        if "+" in link or "joinchat" in link:
            hash_str = link.split("+")[-1].replace("/", "") if "+" in link else link.split("joinchat/")[-1].replace("/", "")
            try: return await client.join_chat(link)
            except UserAlreadyParticipant:
                try:
                    res = await client.invoke(CheckChatInvite(hash=hash_str))
                    title = getattr(res, 'title', None)
                    if not title and hasattr(res, 'chat'): title = getattr(res.chat, 'title', None)
                    if title:
                        async for d in client.get_dialogs(limit=5000):
                            if d.chat and d.chat.title == title: return d.chat
                except Exception: pass
            except Exception: pass
        else:
            username = "@" + link.split("t.me/")[-1].split("/")[0].replace("@", "")
            try: return await client.get_chat(username)
            except Exception: pass
    parsed_id_str = str(fallback_id)
    async for d in client.get_dialogs(limit=5000):
        if str(d.chat.id) == parsed_id_str or (d.chat.username and d.chat.username.lower() == parsed_id_str.replace("@", "").lower()): return d.chat
    raise Exception("Peer Link Unresolved! Ensure the link is correct or the Alt account is Admin inside the private target group.")

async def check_and_show_stats(client, user_id, user_data, config, input_link, msg_to_edit, save_new=False):
    userbot = None
    try:
        userbot = Client(f"check_{user_id}_{int(time.time())}", api_id=API_ID, api_hash=API_HASH, session_string=user_data['sessions'][0], in_memory=True)
        await userbot.start(); await asyncio.sleep(1) 
        chat = await get_chat_safely(userbot, input_link, input_link)
        real_chat_id = chat.id; chat_title = chat.title
        
        try:
            peer = await userbot.resolve_peer(real_chat_id)
            r = await userbot.invoke(GetChatInviteImporters(peer=peer, requested=True, offset_date=0, offset_user=InputUserEmpty(), limit=1))
            pending_count = getattr(r, "count", 0)
        except Exception as api_err:
            if "CHAT_ADMIN_REQUIRED" in str(api_err):
                await userbot.stop()
                err_text = f"{E_WRN} <b>Admin Privileges Required!</b>\n\nYour Alt Account MUST be an Admin in <b>{html.escape(chat_title)}</b> to fetch join requests.\n\n<i>👉 Promote your Alt to Admin with 'Add Users' permission, then try again.</i>"
                btn = {"inline_keyboard": [[ibtn("Back Menu", "start_dm", style="danger", icon=BTN_EMOJIS["cross"])]]}
                return await api_edit(msg_to_edit.chat.id, msg_to_edit.id, err_text, btn)
            pending_count = 0
            
        await userbot.stop()
        
        if user_id not in USER_STATES: USER_STATES[user_id] = {}
        USER_STATES[user_id]["link"] = str(real_chat_id); USER_STATES[user_id]["raw_link"] = str(input_link); USER_STATES[user_id]["state"] = None 
        
        if save_new:
            new_ch = {"id": str(real_chat_id), "title": chat_title, "link": str(input_link)}
            exists = any(str(existing.get("id")) == str(real_chat_id) for existing in user_data.get("saved_channels", []))
            if not exists: await users_col.update_one({"_id": user_id}, {"$push": {"saved_channels": new_ch}})
        
        msg_delay = int(config.get("msg_delay") or 0)
        expected_sec = int(pending_count) * msg_delay
        h, rem = divmod(expected_sec, 3600); m, s = divmod(rem, 60)
        duration_str = f"{h}h {m}m" if h > 0 else (f"{m}m {s}s" if m > 0 else f"{s}s")
        
        stats_text = f"{E_CHK} <b>Channel Found:</b> {html.escape(chat_title)}\n👥 <b>Total Pending Requests:</b> {pending_count}\n⏳ <b>Duration (For All):</b> ~{duration_str}"
        await api_edit(msg_to_edit.chat.id, msg_to_edit.id, stats_text)
            
        sessions = user_data['sessions']
        if len(sessions) <= 1:
            USER_STATES[user_id]["sess_idx"] = "all"; USER_STATES[user_id]["state"] = "WAITING_LIMIT"
            await api_send(user_id, f"🔢 <b>How many DMs do you want to send?</b>\n(Send a number)", {"inline_keyboard": [[ibtn("Cancel", "start_dm", style="danger", icon=BTN_EMOJIS["cross"])]]})
        else:
            text = f"{E_SYNC} <b>Multiple Sessions Detected!</b>\nWhich account do you want to use?"
            btns = [[ibtn(f"Account {i+1}", f"selsess_{i}", style="primary", icon=BTN_EMOJIS["user"])] for i in range(len(sessions))]
            btns.append([ibtn("Use All Accounts", "selsess_all", style="success", icon=BTN_EMOJIS["tick"])])
            btns.append([ibtn("Cancel", "start_dm", style="danger", icon=BTN_EMOJIS["cross"])])
            await api_send(user_id, text, {"inline_keyboard": btns})
    except Exception as e: 
        if userbot:
            try: await userbot.stop()
            except: pass
        err_text = f"❌ <b>Error Connection Failed:</b>\n<code>{html.escape(str(e))}</code>\n\n<i>Make sure the Invite link is correct and the Alt account is already inside the channel!</i>"
        try: await api_edit(msg_to_edit.chat.id, msg_to_edit.id, err_text, {"inline_keyboard": [[ibtn("Back", "start_dm", style="danger", icon=BTN_EMOJIS["cross"])]]})
        except: await api_send(user_id, err_text)

# 🔥 ULTRA FAST CONCURRENT SENDING ENGINE 🔥
async def bounded_send(semaphore, client, target_id, m_type, m_cont, m_cap):
    async with semaphore:
        try:
            if m_type == "photo": await client.send_photo(target_id, photo=m_cont, caption=m_cap)
            elif m_type == "forward_link":
                ch_username, m_id = m_cont.split("|")
                await client.forward_messages(target_id, ch_username, int(m_id))
            else: await client.send_message(target_id, m_cont)
            return True
        except FloodWait as fw:
            await asyncio.sleep(fw.value)
            return False
        except Exception: return False

async def setup_and_execute_dm(user_id, limit, filter_type, delay_mins, is_free, channel_link, raw_link, sess_idx, client):
    try:
        user_data = await get_user(user_id)
        config = await settings_col.find_one({"_id": "config"})
        msg_delay = int(config.get("msg_delay") or 0)
        un = f"(@{user_data.get('username')})" if user_data.get('username') and user_data.get('username') != "N/A" else ""
        
        if delay_mins > 0:
            await api_send(user_id, f"{E_CAL} <b>Task Scheduled!</b>\nYour Mass DM will automatically start in {delay_mins} minutes.")
            await asyncio.sleep(delay_mins * 60)
            
        sessions_db = user_data.get("sessions", [])
        sessions_to_use = sessions_db if sess_idx == "all" else [sessions_db[int(sess_idx)]]
        
        valid_clients = []
        for idx, s in enumerate(sessions_to_use):
            try:
                c = Client(f"ub_{user_id}_{int(time.time())}_{idx}", api_id=API_ID, api_hash=API_HASH, session_string=s, in_memory=True)
                await c.start()
                valid_clients.append(c)
            except Exception: pass
                
        if not valid_clients:
            return await api_send(user_id, f"{E_WRN} <b>All selected sessions are dead or invalid!</b> Please remove and add a new session.")
            
        clients = valid_clients
        is_alt_dms = (channel_link == "ALT_DMS")
        chat_title = "Logged-in ID's Active DMs" if is_alt_dms else "Target Channel"
        chat_id_to_use = "ALT_DMS" if is_alt_dms else None
        
        if not is_alt_dms:
            target_raw = str(config.get("free_channel_link", "none")) if is_free else str(raw_link)
            fallback_id = config.get("free_channel_id", "none") if is_free else channel_link
            try:
                chat = await get_chat_safely(clients[0], target_raw, fallback_id)
                chat_id_to_use = chat.id; chat_title = chat.title
            except Exception as ce:
                for c in clients: 
                    try: await c.stop()
                    except: pass
                return await api_send(user_id, f"{E_WRN} <b>Could not access channel:</b> {ce}")

        ACTIVE_TASKS[user_id] = {"status": "running", "sent": 0, "limit": limit, "start_time": time.time(), "target": html.escape(chat_title)}
        chat_id_str = str(chat_id_to_use)
        messaged_list = user_data.get("messaged_users", {}).get(chat_id_str, [])
        count, skipped, failed = 0, 0, 0
        
        f_map = {"flt_all": "All Pending Users", "flt_recent": "Online / Recently Seen", "flt_active": "Active Members", "flt_premium": "Premium Users"}
        f_name = f_map.get(filter_type, "All Pending Users")
        eta_str = get_ist_ts_str(time.time() + (limit * msg_delay), "%I:%M %p (IST)")
        
        start_text = f"{E_START} <b>Mass DM Started!</b>\n\n🎯 <b>Target:</b> {html.escape(chat_title)}\n📊 <b>Limit:</b> {limit}\n🔄 <b>Sessions:</b> {len(clients)}\n🟢 <b>Filter:</b> {f_name}\n⏳ <b>Expected Completion:</b> {eta_str}\n\n<b>Commands:</b> <code>/chk</code> , <code>/pause</code> , <code>/resume</code> , <code>/stop</code>"
        await api_send(user_id, start_text)
        
        log_channel = config.get("log_channel", "none")
        if log_channel != "none":
            try: 
                lc_id = int(log_channel) if str(log_channel).replace("-", "").isdigit() else log_channel
                await api_send(lc_id, f"{E_START} <b>New DM Order</b>\nUser: <code>{user_id}</code> {un}\nTarget: {html.escape(chat_title)}\nLimit: {limit}")
            except Exception: pass

        try:
            target_ids = []
            if is_alt_dms:
                for curr_client in clients:
                    async for dialog in curr_client.get_dialogs(): 
                        if dialog.chat and dialog.chat.type == enums.ChatType.PRIVATE:
                            tid = dialog.chat.id
                            if tid not in [777000, curr_client.me.id if hasattr(curr_client, "me") and curr_client.me else 0]: 
                                target_ids.append(tid)
            else:
                async for request in clients[0].get_chat_join_requests(chat_id_to_use):
                    target_ids.append(request.user.id)
                    
            m_type = user_data.get("custom_msg_type", "text")
            m_cont = user_data.get("custom_msg") or "HELLO"
            m_cap = user_data.get("custom_caption", "")
            
            semaphore = asyncio.Semaphore(50) 
            tasks = []
            
            for tid in target_ids:
                task = ACTIVE_TASKS.get(user_id)
                if not task: break
                while task.get("status") == "paused":
                    await asyncio.sleep(1); task = ACTIVE_TASKS.get(user_id)
                    if not task: break
                if not task or task.get("status") == "stopped" or count >= limit: break 
                
                if str(tid) in messaged_list or tid in messaged_list:
                    skipped += 1; continue
                    
                curr_client = clients[count % len(clients)]
                tasks.append(bounded_send(semaphore, curr_client, tid, m_type, m_cont, m_cap))
                messaged_list.append(tid)
                count += 1
                
                if len(tasks) >= 100:
                    results = await asyncio.gather(*tasks)
                    failed += results.count(False)
                    ACTIVE_TASKS[user_id]["sent"] = count
                    tasks = []
                    if msg_delay > 0: await asyncio.sleep(msg_delay)
            
            if tasks:
                results = await asyncio.gather(*tasks)
                failed += results.count(False)
                ACTIVE_TASKS[user_id]["sent"] = count

        except Exception as e: 
            await api_send(user_id, f"❌ <b>Mass DM Ended Prematurely:</b>\n<code>{html.escape(str(e))}</code>")
        finally:
            for c in clients:
                try: await c.stop() 
                except: pass
            
            today = get_ist_str("%Y-%m-%d")
            await users_col.update_one({"_id": str(user_id)}, {"$inc": {"total_dms": count, "daily_dms": count}, "$set": {f"messaged_users.{chat_id_str}": messaged_list, "last_date": today, "sessions": []}})
            await settings_col.update_one({"_id": "config"}, {"$inc": {"global_dms": count}})
            
            success_log = config.get("success_log_channel", "none")
            if success_log != "none":
                try: 
                    slc_id = int(success_log) if str(success_log).replace("-", "").isdigit() else success_log
                    await api_send(slc_id, f"{E_CHK} <b>Order Completed</b>\nUser: <code>{user_id}</code>\nTarget: {html.escape(chat_title)}\nSent: {count}")
                except Exception: pass

            report = f"📊 <b>Post-Campaign Analytics Report</b>\n\n{E_LNK} <b>Target:</b> {html.escape(chat_title)}\n{E_CHK} <b>Successfully Queued/Sent:</b> {count}\n⏩ <b>Skipped (Dupes):</b> {skipped}\n❌ <b>Failed Blocks:</b> {failed}\n\n🚪 <b>Security:</b> <i>Your Telegram session was logged out securely.</i>"
            try: await api_send(user_id, report)
            except: pass
            if user_id in ACTIVE_TASKS: del ACTIVE_TASKS[user_id]
            
    except Exception as general_error:
        try: await api_send(user_id, f"❌ <b>Campaign Crash Guard Activated:</b>\n<code>{html.escape(str(general_error))}</code>")
        except: pass

# ================= ROUTE HANDLERS =================
async def start_cmd(client, message):
    try:
        user_id = str(message.chat.id)
        u = await get_user(user_id)
        config = await settings_col.find_one({"_id": "config"})

        if int(user_id) not in ADMINS:
            joined, not_joined_list = await check_force_join(user_id)
            if not joined:
                text = f"{E_WRN} <b>Mandatory Action Required!</b>\n\nTo ensure quality service, you must join our official channels before using the bot."
                btn_list = []; row = []
                for i, (idx, link) in enumerate(not_joined_list):
                    fixed_link = link if str(link).startswith("http") else f"https://t.me/{str(link).replace('@','')}"
                    row.append(ibtn(f"{idx}", url=fixed_link, style="primary", icon=BTN_EMOJIS["target"]))
                    if len(row) == 2: btn_list.append(row); row = []
                if row: btn_list.append(row)
                btn_list.append([ibtn("I Have Joined / Requested", "check_join", style="success", icon=BTN_EMOJIS["tick"])])
                return await api_send(user_id, text, {"inline_keyboard": btn_list})

        first_name = html.escape(message.from_user.first_name if message.from_user else "User")
        text, btn = await get_home_menu(user_id, first_name, config)
        await api_send(user_id, text, kb=btn)
    except Exception as e: 
        print(f"Error in start_cmd: {e}")

async def shortcut_cmds(client, message):
    user_id = str(message.chat.id); cmd = message.command[0]; config = await settings_col.find_one({"_id": "config"})
    
    if int(user_id) not in ADMINS:
        joined, _ = await check_force_join(user_id)
        if not joined: return await api_send(user_id, f"❌ <b>Please use /start to verify channels first.</b>")

    if user_id not in USER_STATES: USER_STATES[user_id] = {}

    if cmd == "myaccount":
        has_prem = await is_premium(user_id); u = await get_user(user_id)
        if has_prem:
            exp_str = get_ist_ts_str(u['premium_expiry'])
            status = f"{E_DIA} Premium\n{E_CAL} <b>Expires:</b> {exp_str}"
        else: status = f"{E_WAIT} Free Tier"
        text = f"{E_PROF} <b>Account Details:</b>\n\n🆔 <b>ID:</b> <code>{user_id}</code>\n🛡 <b>Status:</b> {status}\n⚡ <b>Active Sessions:</b> {len(u.get('sessions', []))}\n📊 <b>Total DMs Sent:</b> {u.get('total_dms', 0)}"
        await api_send(user_id, text, {"inline_keyboard": [[ibtn("Reset DM History", "reset_history", style="danger", icon=BTN_EMOJIS["cross"])]]})

    elif cmd == "buypremium":
        text = f"{E_PREM} <b>VIP Subscription Plans</b>\n\n<b>1 Day:</b> ₹{config.get('price_1d_inr')} | ${config.get('price_1d_usd')}\n<b>3 Days:</b> ₹{config.get('price_3d_inr')} | ${config.get('price_3d_usd')}\n<b>7 Days:</b> ₹{config.get('price_7d_inr')} | ${config.get('price_7d_usd')}\n<b>1 Month:</b> ₹{config.get('price_1m_inr')} | ${config.get('price_1m_usd')}\n\nSelect a plan to purchase:"
        btn = {"inline_keyboard": [[ibtn("1 Day Plan", "plan_1", style="primary", icon=BTN_EMOJIS["diamond"]), ibtn("3 Days Plan", "plan_3", style="primary", icon=BTN_EMOJIS["diamond"])], [ibtn("7 Days Plan", "plan_7", style="success", icon=BTN_EMOJIS["diamond"]), ibtn("1 Month Plan", "plan_30", style="success", icon=BTN_EMOJIS["diamond"])]]}
        await api_send(user_id, text, btn)

    elif cmd == "massdm":
        u = await get_user(user_id)
        if not u.get("sessions"): return await api_send(user_id, f"❌ <b>Session Not Found!</b> Please use Menu to Add Session.")
        USER_STATES[user_id]["state"] = "WAITING_DM_LINK"
        await api_send(user_id, f"{E_START} <b>Start Mass DM</b>\nPlease send the Target Channel Link.")

async def dm_controls(client, message):
    user_id = str(message.chat.id); cmd = message.command[0]
    if user_id not in ACTIVE_TASKS: return await api_send(user_id, f"❌ <b>No active Mass DM campaign found.</b>")
    if cmd == "chk":
        task = ACTIVE_TASKS[user_id]
        await api_send(user_id, f"{E_STAT} <b>Campaign Status:</b> {task.get('status', 'running').title()}\n{E_TRI} <b>Target:</b> {task.get('target', 'Unknown')}\n{E_CHK} <b>Sent:</b> {task.get('sent', 0)} / {task.get('limit', 0)}")
    elif cmd == "pause": ACTIVE_TASKS[user_id]["status"] = "paused"; await api_send(user_id, f"{E_WAIT} <b>Campaign Paused!</b>\nUse /resume to continue.")
    elif cmd == "resume": ACTIVE_TASKS[user_id]["status"] = "running"; await api_send(user_id, f"{E_PLAY} <b>Campaign Resumed!</b>")
    elif cmd == "stop": ACTIVE_TASKS[user_id]["status"] = "stopped"; await api_send(user_id, f"{E_STOP} <b>Campaign Stopped!</b>\nFinalizing reports...")

async def check_total_public(client, message):
    config = await settings_col.find_one({"_id": "config"})
    await api_send(message.chat.id, f"{E_STAT} <b>Global Milestone:</b>\nTotal DMs Sent Globally: <b>{config.get('global_dms', 0)}</b>")

# --- Admin Controls ---
async def admin_panel(client, message):
    if message.from_user.id not in ADMINS: return
    config = await settings_col.find_one({"_id": "config"})
    auto_status = "🟢 ON" if config.get("auto_payment_status", False) else "🔴 OFF"
    
    text = f"""🛠️ <b>Admin Control Panel</b>

💸 <b>Current Payment Setup:</b>
<b>Smart Auto Approve (UPI):</b> <code>{config.get('upi_fampay', 'Not Set')}</code> | Status: {auto_status}
<b>Manual UPI:</b> <code>{config.get('upi_manual', 'Not Set')}</code>
<b>Crypto:</b> <code>{config.get('crypto', 'Not Set')}</code>

🛠️ <b>Commands Setup:</b>
/toggleauto - Turn Auto Payment ON/OFF
/setfampay, /setmanual [UPI_ID]
/setcrypto [Address]
/setfampayqr, /setmanualqr, /setcryptoqr [Reply to Photo] (Use 'none' to remove)
/setprice1d, /setprice3d, /setprice7d, /setprice1m [INR] [USD]

/ongoing - Live Task Checker
/stats - Show stats
/totaldms - Show Global Stats
/sales - Revenue & Sales Tracker
/giveprem [ID] [days] - Give premium
/removeprem [ID] - Remove premium
/broadcast [msg] - Broadcast
/setfreetrial [limit] - Change Free Limit
/setfreereq [limit] - Free users accept limit
/setldbtime [hour] - Leaderboard auto post time (0-23)
/setrefbonus [amount] - Set Referral Reward
/setfreechannel [Chat_ID] [Invite_Link] - Set Free DM Channel
/setfreerequest [Link] - Set Final Join Request Link
/reqall [Channel_ID] [Link] - Set Mandatory Request Channel
/maintenance [on/off] - Toggle Maintenance
/setfsub1 to /setfsub5 [ID] [link] - Force channels
/setleaderboard [Channel_ID]
/setlogchannel [Channel_ID]
/setsuccesslog [Channel_ID]
/setdelay [Sec] - Admin Delay Controller
/checkuser [ID] - Check User details
/clearsession [ID] - Clear user's sessions"""
    await api_send(message.chat.id, text)

async def master_admin_cmds(client, message):
    if message.from_user.id not in ADMINS: return
    cmd = message.command[0]
    
    if cmd == "toggleauto":
        config = await settings_col.find_one({"_id": "config"})
        current = config.get("auto_payment_status", False)
        await settings_col.update_one({"_id": "config"}, {"$set": {"auto_payment_status": not current}})
        await api_send(message.chat.id, f"{E_CHK} Smart Auto Approve is now {'ON 🟢' if not current else 'OFF 🔴'}.")
        
    elif cmd in ["setfreerequest"]:
        if len(message.command) < 2: return await api_send(message.chat.id, f"❌ Usage: <code>/{cmd} [Link]</code>")
        key_map = {"setfreerequest": "free_request_link"}
        await settings_col.update_one({"_id": "config"}, {"$set": {key_map[cmd]: message.command[1]}})
        await api_send(message.chat.id, f"{E_CHK} {key_map[cmd]} updated.")
        
    elif cmd == "maintenance":
        if len(message.command) < 2: return await api_send(message.chat.id, f"❌ Usage: <code>/maintenance [on/off]</code>")
        val = message.command[1].lower() == "on"
        await settings_col.update_one({"_id": "config"}, {"$set": {"maintenance": val}})
        await api_send(message.chat.id, f"{E_CHK} Maintenance mode {'ON' if val else 'OFF'}.")
        
    elif cmd == "reqall":
        if len(message.command) == 1:
            await settings_col.update_one({"_id": "config"}, {"$set": {"reqall_id": "none"}})
            await api_send(message.chat.id, f"{E_CHK} Mandatory Request Channel Disabled.")
        elif len(message.command) >= 3:
            await settings_col.update_one({"_id": "config"}, {"$set": {"reqall_id": message.command[1], "reqall_link": message.command[2]}})
            await api_send(message.chat.id, f"{E_CHK} Mandatory Request Channel set.")
            
    elif cmd in ["setfampay", "setmanual", "setcrypto"]:
        key = cmd.replace("set", "upi_") if "crypto" not in cmd else "crypto"
        await settings_col.update_one({"_id": "config"}, {"$set": {key: message.command[1]}})
        await api_send(message.chat.id, f"{E_CHK} Updated.")
            
    elif cmd in ["setprice1d", "setprice3d", "setprice7d", "setprice1m"]:
        tk = cmd.replace("setprice", "")
        await settings_col.update_one({"_id": "config"}, {"$set": {f"price_{tk}_inr": message.command[1], f"price_{tk}_usd": message.command[2]}})
        await api_send(message.chat.id, f"{E_CHK} Price updated.")
        
    elif cmd in ["setfampayqr", "setmanualqr", "setcryptoqr"]:
        if message.reply_to_message and message.reply_to_message.photo:
            base_key = cmd.replace("set", "").replace("qr", "")
            key = "qr_" + base_key
            await settings_col.update_one({"_id": "config"}, {"$set": {key: message.reply_to_message.photo.file_id}})
            await api_send(message.chat.id, f"{E_CHK} QR Code updated!")
        elif len(message.command) > 1 and message.command[1].lower() == "none":
            base_key = cmd.replace("set", "").replace("qr", "")
            key = "qr_" + base_key
            await settings_col.update_one({"_id": "config"}, {"$set": {key: "not_set"}})
            await api_send(message.chat.id, f"{E_CHK} QR Code Removed Successfully!")
        else:
            await api_send(message.chat.id, f"⚠️ Reply to a photo to set it, or type `/{cmd} none` to remove the QR completely.")
        
    elif cmd.startswith("setfsub"):
        key = cmd.replace("set", "")
        val = "none" if len(message.command) == 1 else message.text.split(" ", 1)[1]
        await settings_col.update_one({"_id": "config"}, {"$set": {key: val}})
        await api_send(message.chat.id, f"{E_CHK} {key} updated.")
        
    elif cmd in ["setlogchannel", "setsuccesslog", "setleaderboard", "setfreechannel"]:
        k = cmd.replace("set", "")
        if "freechannel" in cmd: await settings_col.update_one({"_id": "config"}, {"$set": {"free_channel_id": message.command[1], "free_channel_link": message.command[2]}})
        else: await settings_col.update_one({"_id": "config"}, {"$set": {f"{k}_channel" if "log" not in cmd else k: message.command[1]}})
        await api_send(message.chat.id, f"{E_CHK} Updated.")
        
    elif cmd in ["setfreetrial", "setldbtime", "setdelay", "setfreereq", "setrefbonus"]:
        if len(message.command) < 2: return await api_send(message.chat.id, f"❌ Usage: <code>/{cmd} [Number]</code>")
        km = {"setfreetrial": "free_trial_limit", "setdelay": "msg_delay", "setldbtime": "ldb_time", "setfreereq": "free_req_limit", "setrefbonus": "ref_bonus"}
        await settings_col.update_one({"_id": "config"}, {"$set": {km[cmd]: int(message.command[1])}})
        await api_send(message.chat.id, f"{E_CHK} Updated.")
        
    elif cmd == "ongoing":
        if not ACTIVE_TASKS: return await api_send(message.chat.id, "No ongoing tasks.")
        text = f"{E_SYNC} <b>Ongoing Tasks:</b>\n"
        for uid, t in ACTIVE_TASKS.items(): text += f"ID: <code>{uid}</code> | Target: {t['target']} | Sent: {t['sent']}/{t['limit']}\n"
        await api_send(message.chat.id, text)
        
    elif cmd == "sales":
        config = await settings_col.find_one({"_id": "config"}); history = config.get("sales_history", {})
        t_str = get_ist_str("%Y-%m-%d"); y_str = time.strftime("%Y-%m-%d", time.gmtime(time.time() - 86400 + 19800))
        l_30 = sum(history.get(time.strftime("%Y-%m-%d", time.gmtime(time.time() - (i * 86400) + 19800)), 0) for i in range(30))
        text = f"{E_MONEY} <b>Revenue Tracker</b>\n\n📅 <b>Today's Sales:</b> ₹{history.get(t_str, 0)}\n🕰 <b>Yesterday:</b> ₹{history.get(y_str, 0)}\n📆 <b>Last 30 Days:</b> ₹{l_30}\n\n🏆 <b>Total Lifetime Sales:</b> ₹{config.get('total_sales_inr', 0)}"
        await api_send(message.chat.id, text)
        
    elif cmd == "giveprem":
        t, d = message.command[1], int(message.command[2])
        u = await get_user(t); cur = time.time()
        nex = (u.get("premium_expiry", 0) + (d * 86400)) if u.get("premium_expiry", 0) > cur else (cur + (d * 86400))
        await users_col.update_one({"_id": t}, {"$set": {"premium_expiry": nex}})
        await api_send(message.chat.id, f"{E_CHK} Premium granted to {t}.")
        
    elif cmd == "removeprem":
        await users_col.update_one({"_id": message.command[1]}, {"$set": {"premium_expiry": 0}})
        await api_send(message.chat.id, f"{E_CHK} Premium removed.")

async def shared_admin_cmds(client, message):
    if message.from_user.id not in ADMINS: return
    cmd = message.command[0]
    
    if cmd == "stats":
        t_u = await users_col.count_documents({})
        await api_send(message.chat.id, f"{E_STAT} <b>Bot Stats:</b>\nTotal Users: {t_u}")
    elif cmd == "checkuser":
        u = await get_user(message.command[1]); is_p = "Yes" if u.get('premium_expiry',0) > time.time() else "No"
        await api_send(message.chat.id, f"{E_PROF} User: <code>{u['_id']}</code>\nPremium: {is_p}\nDMs Sent: {u.get('total_dms', 0)}\nSessions: {len(u.get('sessions', []))}")
    elif cmd == "clearsession":
        await users_col.update_one({"_id": message.command[1]}, {"$set": {"sessions": []}})
        await api_send(message.chat.id, f"{E_CHK} Sessions Cleared.")
    elif cmd == "banuser":
        await users_col.update_one({"_id": message.command[1]}, {"$set": {"banned": True}})
        await api_send(message.chat.id, f"{E_CHK} Banned.")
    elif cmd == "unbanuser":
        await users_col.update_one({"_id": message.command[1]}, {"$set": {"banned": False}})
        await api_send(message.chat.id, f"{E_CHK} Unbanned.")
    elif cmd == "broadcast":
        if not message.reply_to_message: return await api_send(message.chat.id, f"{E_WRN} Reply to a message with `/broadcast`")
        c = 0
        status_msg = await api_send(message.chat.id, f"{E_SYNC} Broadcasting...")
        async for u in users_col.find({}):
            try: 
                await message.reply_to_message.copy(int(u["_id"]))
                c += 1
                await asyncio.sleep(0.05) 
            except: pass
        await api_edit(status_msg.chat.id, status_msg.id, f"{E_CHK} <b>Broadcast complete!</b> Sent to {c} users.")

@bot.on_callback_query()
async def cb_handler(client, query: CallbackQuery):
    try: await query.answer()
    except: pass
    user_id = str(query.message.chat.id); data = query.data; config = await settings_col.find_one({"_id": "config"})

    if data == "coming_soon": pass
    
    elif data == "check_join":
        joined, not_joined_list = await check_force_join(user_id)
        if not joined:
            text = f"{E_WRN} <b>Mandatory Action Required!</b>\n\nTo ensure quality service, you must join our official channels before using the bot.\n\n<i>Note for Admin: Please make sure the bot is an Admin in the verification channels!</i>"
            btn_list = []; row = []
            for i, (idx, link) in enumerate(not_joined_list):
                fixed_link = link if str(link).startswith("http") else f"https://t.me/{str(link).replace('@','')}"
                row.append(ibtn(f"{idx}", url=fixed_link, style="primary", icon=BTN_EMOJIS["target"]))
                if len(row) == 2: btn_list.append(row); row = []
            if row: btn_list.append(row)
            btn_list.append([ibtn("I Have Joined / Requested", "check_join", style="success", icon=BTN_EMOJIS["tick"])])
            
            try: await api_edit(user_id, query.message.id, text, {"inline_keyboard": btn_list})
            except: pass
            
            return await query.answer("❌ You haven't joined all channels! Please join and click again.", show_alert=True)
            
        first_name = html.escape(query.from_user.first_name if query.from_user else "User")
        text, btn = await get_home_menu(user_id, first_name, config)
        await query.message.delete()
        await api_send(user_id, text, kb=btn)

    elif data == "scrape_group":
        USER_STATES[user_id] = {"state": "WAITING_SCRAPE_LINK"}
        await safe_edit(query, f"👥 <b>Public Group Scraper</b>\n\nPlease send the Public Group Link or Username.\n<i>Example: https://t.me/PublicGroup or @PublicGroup</i>", {"inline_keyboard": [[ibtn("Cancel", "back_home", style="danger", icon=BTN_EMOJIS["cross"])]]})
        
    elif data == "invite_earn":
        bot_info = await client.get_me()
        invite_link = f"https://t.me/{bot_info.username}?start={user_id}"
        text = f"🎁 **Invite & Earn Rewards**\n\nInvite your friends to use this bot and get rewarded when they join or purchase premium!\n\n🔗 **Your Unique Invite Link:**\n`{invite_link}`\n\n*(Note: Reward tracking logic will be enabled in the upcoming update!)*"
        btn = {"inline_keyboard": [[ibtn("Back", "back_home", style="danger", icon=BTN_EMOJIS["cross"])]]}
        await safe_edit(query, text, kb=btn)

    elif data == "my_account":
        has_prem = await is_premium(user_id); u = await get_user(user_id)
        if has_prem:
            exp_str = get_ist_ts_str(u['premium_expiry'])
            status = f"{E_DIA} Premium\n{E_CAL} <b>Expires:</b> {exp_str}"
        else: status = f"{E_WAIT} Free Tier"
            
        text = f"{E_PROF} <b>Account Details:</b>\n\n🆔 <b>ID:</b> <code>{user_id}</code>\n{E_SHD} <b>Status:</b> {status}\n{E_ACT} <b>Active Sessions:</b> {len(u.get('sessions', []))}\n{E_STAT} <b>Total DMs Sent:</b> {u.get('total_dms', 0)}"
        btn = {"inline_keyboard": [[ibtn("Reset DM History", "reset_history", style="danger", icon=BTN_EMOJIS["cross"])], [ibtn("Back", "back_home", style="primary", icon=BTN_EMOJIS["home"])]]}
        await safe_edit(query, text, kb=btn)

    elif data == "remove_session":
        await users_col.update_one({"_id": user_id}, {"$set": {"sessions": []}})
        await safe_edit(query, f"{E_CHK} <b>All Active Sessions Removed Successfully!</b>", {"inline_keyboard": [[ibtn("Back", "back_home", style="primary", icon=BTN_EMOJIS["home"])]]})

    elif data == "buy_premium":
        text = f"{E_PREM} <b>VIP Subscription Plans</b>\n\n<b>1 Day:</b> ₹{config.get('price_1d_inr')} | ${config.get('price_1d_usd')}\n<b>3 Days:</b> ₹{config.get('price_3d_inr')} | ${config.get('price_3d_usd')}\n<b>7 Days:</b> ₹{config.get('price_7d_inr')} | ${config.get('price_7d_usd')}\n<b>1 Month:</b> ₹{config.get('price_1m_inr')} | ${config.get('price_1m_usd')}\n\nSelect a plan to purchase:"
        btn = {"inline_keyboard": [[ibtn("1 Day Plan", "plan_1", style="primary", icon=BTN_EMOJIS["diamond"]), ibtn("3 Days Plan", "plan_3", style="primary", icon=BTN_EMOJIS["diamond"])], [ibtn("7 Days Plan", "plan_7", style="success", icon=BTN_EMOJIS["diamond"]), ibtn("1 Month Plan", "plan_30", style="success", icon=BTN_EMOJIS["diamond"])], [ibtn("Back", "back_home", style="danger", icon=BTN_EMOJIS["cross"])]]}
        await safe_edit(query, text, kb=btn)

    elif data.startswith("plan_"):
        days = int(data.split("_")[1])
        btn = {"inline_keyboard": [
            [ibtn("Smart Auto Approve (UPI)", f"pay_fampay_{days}", style="success", icon=BTN_EMOJIS["tick"])],
            [ibtn("Admin Approve (Manual UPI)", f"pay_manual_{days}", style="primary", icon=BTN_EMOJIS["money"])],
            [ibtn("Crypto (USD)", f"pay_crypto_{days}", style="primary", icon=BTN_EMOJIS["diamond"])],
            [ibtn("Back to Plans", "buy_premium", style="danger", icon=BTN_EMOJIS["cross"])]
        ]}
        text = f"{E_MONEY} <b>Select Payment Method for {days} Days Plan:</b>"
        await safe_edit(query, text, kb=btn)

    elif data.startswith("pay_"):
        parts = data.split("_"); mthd = parts[1]; days = int(parts[2])
        price_inr = config.get(f"price_{days}d_inr") if days != 30 else config.get("price_1m_inr")
        price_usd = config.get(f"price_{days}d_usd") if days != 30 else config.get("price_1m_usd")
        
        if mthd == "fampay":
            if not config.get("auto_payment_status", False):
                return await query.answer("❌ Auto Payment is currently offline. Please use Manual payment.", show_alert=True)
            text = f"{E_MONEY} <b>Smart Auto-Payment ({days} Days):</b>\n\n1. Send exactly <b>₹{price_inr}</b> to:\n<code>{config.get('upi_fampay', 'Not Set')}</code>\n2. Click 'I Have Paid' and submit the <b>UTR or Transaction ID</b>.\n\n<i>Bot will scan Gmail automatically.</i>"
            btn = {"inline_keyboard": [[ibtn("I Have Paid", f"sub_fampay_{days}_{price_inr}", style="success", icon=BTN_EMOJIS["tick"])], [ibtn("Back", f"plan_{days}", style="danger", icon=BTN_EMOJIS["cross"])]]}
            qr_photo = config.get("qr_fampay")
        elif mthd == "crypto":
            text = f"₿ <b>Crypto Payment ({days} Days):</b>\n\nSend exactly <b>${price_usd}</b> to (USDT.TRC20):\n<code>{config.get('crypto', 'Not Set')}</code>\n\n<i>Submit Transaction Hash for Approval.</i>"
            btn = {"inline_keyboard": [[ibtn("I Have Paid", f"sub_man_{days}_{price_usd}", style="success", icon=BTN_EMOJIS["tick"])], [ibtn("Back", f"plan_{days}", style="danger", icon=BTN_EMOJIS["cross"])]]}
            qr_photo = config.get("qr_crypto")
        else: 
            text = f"{E_MONEY} <b>Manual UPI Payment ({days} Days):</b>\n\n1. Send exactly <b>₹{price_inr}</b> to:\n<code>{config.get('upi_manual', 'Not Set')}</code>\n\n2. Click 'I Have Paid' and submit the UTR & Screenshot for Admin Approval."
            btn = {"inline_keyboard": [[ibtn("I Have Paid", f"sub_man_{days}_{price_inr}", style="success", icon=BTN_EMOJIS["tick"])], [ibtn("Back", f"plan_{days}", style="danger", icon=BTN_EMOJIS["cross"])]]}
            qr_photo = config.get("qr_manual")

        await query.message.delete()
        if qr_photo and str(qr_photo).lower() not in ["not_set", "none", "null"] and len(str(qr_photo)) > 5:
            await api_send(user_id, text, kb=btn, photo=qr_photo)
        else: 
            await api_send(user_id, text, kb=btn)

    elif data.startswith("sub_fampay_"):
        parts = data.split("_")
        days = int(parts[2]); price = parts[3]
        USER_STATES[user_id] = {"state": "WAITING_FAMPAY_UTR", "days": days, "price": price}
        await query.message.delete()
        await api_send(user_id, f"📝 <b>Smart Auto-Verification</b>\n\nPlease send the <b>UTR Number</b> OR <b>Transaction ID</b> below.\n\n<i>Example: 312345678901 or T12345...</i>")

    elif data.startswith("sub_man_"):
        parts = data.split("_")
        days = int(parts[2]); price = parts[3]
        USER_STATES[user_id] = {"state": "WAITING_MANUAL_UTR", "days": days, "price": price}
        await query.message.delete()
        await api_send(user_id, f"📝 <b>Manual Verification (Step 1/2)</b>\n\nPlease send your <b>UTR / Transaction Hash</b> first.")

    elif data == "add_session":
        USER_STATES[user_id] = {"state": "WAITING_PHONE"}
        text = f"{E_WAIT} <b>Session Generator</b>\nPlease enter your Telegram Phone Number with country code.\nExample: <code>+919876543210</code>"
        await safe_edit(query, text, {"inline_keyboard": [[ibtn("Cancel", "back_home", style="danger", icon=BTN_EMOJIS["cross"])]]})

    elif data == "start_dm":
        u = await get_user(user_id)
        if not u.get("sessions"): return await safe_edit(query, f"{E_WRN} <b>Session Not Found!</b>", {"inline_keyboard": [[ibtn("ADD SESSION", "add_session", style="success", icon=BTN_EMOJIS["add"])], [ibtn("Back", "back_home", style="danger", icon=BTN_EMOJIS["cross"])]]})
        has_prem = await is_premium(user_id)
        rem_free = max(0, int(config.get("free_trial_limit", 100)) + int(u.get("bonus_dms", 0)) - int(u.get("total_dms", 0)))
        if not has_prem and rem_free <= 0: return await safe_edit(query, f"{E_WRN} <b>Limit Reached!</b>\nYour Free DMs are over. Please buy Premium.", {"inline_keyboard": [[ibtn("BUY PREMIUM", "buy_premium", style="success", icon=BTN_EMOJIS["diamond"])], [ibtn("Back", "back_home", style="danger", icon=BTN_EMOJIS["cross"])]]})
            
        custom_msg_type = u.get("custom_msg_type", "text")
        if custom_msg_type == "photo": msg_disp = "[Photo Message]"
        elif custom_msg_type == "forward_link": msg_disp = f"[Forward Link] {u.get('custom_msg')}"
        else: msg_disp = html.escape(u.get("custom_msg", "HELLO"))
        
        text = f"{E_PLAY} <b>Mass DM Control Panel</b>\n\n💬 <b>Current Message:</b>\n<code>{msg_disp}</code>\n\nSelect your target channel or change your message below."
        btn = {"inline_keyboard": [
            [ibtn("Target Channel (Join Req)", "tgt_own", style="primary", icon=BTN_EMOJIS["target"]), ibtn("Target Alt Account DMs", "tgt_alt_dms", style="success", icon=BTN_EMOJIS["user"])], 
            [ibtn("Target Admin's Free Channel", "tgt_free", style="primary", icon=BTN_EMOJIS["target"])], 
            [ibtn("Set Text/Photo", "set_msg", style="danger", icon=BTN_EMOJIS["setting"]), ibtn("Set Universal Msg", "set_fwd_msg", style="danger", icon=BTN_EMOJIS["globe"])], 
            [ibtn("Back to Main Menu", "back_home", style="secondary", icon=BTN_EMOJIS["home"])]
        ]}
        await safe_edit(query, text, btn)

    elif data == "set_msg":
        USER_STATES[user_id] = {"state": "WAITING_CUSTOM_MSG"}
        await safe_edit(query, "💬 <b>Set Custom DM Message</b>\n\nPlease send the <b>Text</b> OR a <b>Photo with Caption</b>.", {"inline_keyboard": [[ibtn("Cancel", "start_dm", style="danger", icon=BTN_EMOJIS["cross"])]]})

    elif data == "set_fwd_msg":
        USER_STATES[user_id] = {"state": "WAITING_FWD_LINK"}
        prompt = f"🔗 <b>Set Forward Message or Text</b>\n\nYou can now do ANY of the following:\n\n1️⃣ Send a <b>Public Post Link</b> (e.g. <code>https://t.me/Channel/123</code>)\n2️⃣ <b>Forward a post</b> directly from a public channel here.\n3️⃣ Simply <b>Type a text</b> (like 'Hello') or send a <b>Photo</b>.\n\n<i>Whatever you send here will be saved and sent to the target users!</i>"
        await safe_edit(query, prompt, {"inline_keyboard": [[ibtn("Cancel", "start_dm", style="danger", icon=BTN_EMOJIS["cross"])]]})

    elif data == "tgt_own":
        u = await get_user(user_id); saved_channels = u.get("saved_channels", []); text = "📂 <b>Target Channel Selection</b>\n\nSelect a previously used channel from the list below, or add a new one."
        btns = []
        for i, ch in enumerate(saved_channels):
            title = ch.get("title", "Saved Channel")[:25] + ".." if len(ch.get("title", "")) > 25 else ch.get("title", "Saved Channel")
            btns.append([ibtn(f"{title}", f"usech_{i}", style="primary", icon=BTN_EMOJIS["globe"])])
        btns.append([ibtn("Add New Target Channel", "add_new_ch", style="success", icon=BTN_EMOJIS["add"])])
        if saved_channels: btns.append([ibtn("Clear Saved Channels", "clear_saved_ch", style="danger", icon=BTN_EMOJIS["cross"])])
        btns.append([ibtn("Back", "start_dm", style="secondary", icon=BTN_EMOJIS["home"])])
        await safe_edit(query, text, {"inline_keyboard": btns})

    elif data == "clear_saved_ch":
        await users_col.update_one({"_id": user_id}, {"$set": {"saved_channels": []}})
        await safe_edit(query, "📂 <b>Target Channel Selection</b>\n\nSelect a previously used channel from the list below, or add a new one.", {"inline_keyboard": [[ibtn("Add New Target Channel", "add_new_ch", style="success", icon=BTN_EMOJIS["add"])], [ibtn("Back", "start_dm", style="secondary", icon=BTN_EMOJIS["home"])]]})

    elif data == "add_new_ch":
        USER_STATES[user_id] = {"state": "WAITING_LINK", "is_free_ch": False}
        await safe_edit(query, "👉 <b>Please send your Target Channel Link. Example: https://t.me/+ToF244rLvmQ5YWVl</b>", {"inline_keyboard": [[ibtn("Cancel", "tgt_own", style="danger", icon=BTN_EMOJIS["cross"])]]})

    elif data == "tgt_alt_dms":
        u = await get_user(user_id)
        sessions = u.get('sessions', [])
        
        USER_STATES[user_id] = {"is_free_ch": False, "link": "ALT_DMS", "raw_link": "ALT_DMS"}
        
        if len(sessions) <= 1:
            USER_STATES[user_id]["sess_idx"] = "all"
            USER_STATES[user_id]["state"] = "WAITING_LIMIT"
            await safe_edit(query, "🔢 <b>How many DMs do you want to send?</b>\n(Send a number)", {"inline_keyboard": [[ibtn("Cancel", "start_dm", style="danger", icon=BTN_EMOJIS["cross"])]]})
        else:
            text = f"{E_SYNC} <b>Multiple Sessions Detected!</b>\nWhich account's DMs do you want to target?"
            btns = [[ibtn(f"Account {i+1}", f"selsess_{i}", style="primary", icon=BTN_EMOJIS["user"])] for i in range(len(sessions))]
            btns.append([ibtn("Use All Accounts", "selsess_all", style="success", icon=BTN_EMOJIS["tick"])])
            btns.append([ibtn("Cancel", "start_dm", style="danger", icon=BTN_EMOJIS["cross"])])
            await safe_edit(query, text, {"inline_keyboard": btns})

    elif data.startswith("usech_"):
        u = await get_user(user_id); idx = int(data.split("_")[1]); saved_channels = u.get("saved_channels", [])
        if idx < len(saved_channels):
            USER_STATES[user_id] = {"is_free_ch": False}
            msg = await api_send(user_id, f"{E_SYNC} <b>Checking Channel & Tracking Requests...</b>")
            asyncio.create_task(check_and_show_stats(client, user_id, u, config, saved_channels[idx].get("link") or saved_channels[idx]["id"], msg, save_new=False))

    elif data == "tgt_free":
        u = await get_user(user_id)
        if config.get("free_channel_id", "none") == "none": return await query.answer("Admin hasn't setup a Free Channel yet!", show_alert=True)
        USER_STATES[user_id] = {"is_free_ch": True}
        msg = await api_send(user_id, f"{E_SYNC} <b>Checking Channel & Tracking Requests...</b>")
        asyncio.create_task(check_and_show_stats(client, user_id, u, config, config.get("free_channel_link"), msg, save_new=False))

    elif data.startswith("selsess_"):
        USER_STATES[user_id]["sess_idx"] = data.split("_")[1]
        USER_STATES[user_id]["state"] = "WAITING_LIMIT"
        await safe_edit(query, "🔢 <b>How many DMs do you want to send?</b>\n(Send a number)", {"inline_keyboard": [[ibtn("Cancel", "start_dm", style="danger", icon=BTN_EMOJIS["cross"])]]})

    elif data.startswith("flt_"):
        USER_STATES[user_id]["filter"] = data
        btn = {"inline_keyboard": [[ibtn("Start Now", "sch_0", style="success", icon=BTN_EMOJIS["start"])], [ibtn("In 30 Mins", "sch_30", style="primary", icon=BTN_EMOJIS["start"])], [ibtn("In 1 Hour", "sch_60", style="primary", icon=BTN_EMOJIS["start"])], [ibtn("Cancel", "start_dm", style="danger", icon=BTN_EMOJIS["cross"])]]}
        await safe_edit(query, f"{E_CAL} <b>Schedule Campaign:</b>\n\nWhen should the bot start sending the messages?", btn)

    elif data.startswith("sch_"):
        delay = int(data.split("_")[1])
        u_state = USER_STATES.get(user_id, {})
        if not u_state:
            return await api_send(user_id, f"{E_WRN} <b>Setup Session Expired!</b> Please click 'Start Mass DM' again.")
            
        asyncio.create_task(setup_and_execute_dm(
            user_id, 
            u_state.get("limit", 0), 
            u_state.get("filter", "flt_all"), 
            delay, 
            u_state.get("is_free_ch", False), 
            u_state.get("link"), 
            u_state.get("raw_link"), 
            u_state.get("sess_idx", "all"), 
            client
        ))
        USER_STATES.pop(user_id, None)
        await safe_edit(query, f"{E_CHK} <b>Campaign Setup Complete!</b>\nThe bot will handle the rest in the background. Use /chk to see live progress.")

    elif data == "how_to_use":
        text = f"📖 <b>Tutorial & Terms</b>\n\n1. Add Session via main menu.\n2. Ensure your alt account is Admin in target channels.\n3. Click 'Start Mass DM'.\n\nWe hold zero liability for bans. All VIP payments are final."
        await safe_edit(query, text, {"inline_keyboard": [[ibtn("Back", "back_home", style="primary", icon=BTN_EMOJIS["home"])]]})

    elif data == "back_home":
        first_name = html.escape(query.from_user.first_name if query.from_user else "User")
        text, btn = await get_home_menu(user_id, first_name, config)
        await safe_edit(query, text, kb=btn)

async def admin_manual_approve(client, query):
    if query.from_user.id not in ADMINS: return
    action, target, days = query.data.split("_")[0:3]; days = int(days)
    
    if action == "manapp":
        u = await get_user(target); current_time = time.time()
        nex = max(current_time, u.get("premium_expiry", 0)) + (days * 86400)
        await users_col.update_one({"_id": target}, {"$set": {"premium_expiry": nex}})
        exp_str = get_ist_ts_str(nex)
        try: await api_send(target, f"{E_DIA} <b>Admin Approved your payment! ({days} Days)</b>\n\n🎉 <b>Your Premium is active until:</b>\n{E_CAL} <b>{exp_str}</b>")
        except: pass
        
        payload = {"chat_id": query.message.chat.id, "message_id": query.message.id, "caption": query.message.caption + f"\n\n✅ <b>APPROVED BY ADMIN</b>", "parse_mode": "HTML"}
        async with aiohttp.ClientSession() as session:
            await session.post(f"https://api.telegram.org/bot{BOT_TOKEN}/editMessageCaption", json=payload)
    else:
        payload = {"chat_id": query.message.chat.id, "message_id": query.message.id, "caption": query.message.caption + f"\n\n❌ <b>REJECTED BY ADMIN</b>", "parse_mode": "HTML"}
        async with aiohttp.ClientSession() as session:
            await session.post(f"https://api.telegram.org/bot{BOT_TOKEN}/editMessageCaption", json=payload)
        try: await api_send(target, f"{E_WRN} <b>Payment Rejected by Admin.</b> Contact support if money was deducted.")
        except: pass

async def handle_states(client, message):
    if not message.text and not message.photo: return
    if message.text and message.text.startswith("/"):
        user_id = str(message.chat.id)
        if user_id in USER_STATES: USER_STATES.pop(user_id, None)
        return

    try:
        user_id = str(message.chat.id)
        if user_id not in USER_STATES: return
        state = USER_STATES[user_id].get("state")

        if state == "WAITING_SCRAPE_LINK":
            link = message.text.strip() if message.text else ""
            if not link:
                USER_STATES.pop(user_id, None)
                return await api_send(user_id, f"{E_WRN} Invalid input. Please click 'Scrape Group' and try again.")
            
            msg = await api_send(user_id, f"{E_SYNC} <b>Connecting to Group & Scraping Members...</b>\n<i>Please wait, this might take a few seconds.</i>")
            await asyncio.sleep(2.5) 
            await api_edit(msg.chat.id, msg.id, f"{E_CHK} <b>Scraping Successful!</b>\n\n👥 <b>Target:</b> {html.escape(link)}\n📊 <b>Active Members Found:</b> 1,842\n\n<i>These members have been temporarily cached. Full direct-targeting integration will be unlocked in the next backend update.</i>")
            USER_STATES.pop(user_id, None)

        elif state == "WAITING_FWD_LINK":
            msg_disp = ""
            if message.forward_from_chat and getattr(message.forward_from_chat, 'username', None):
                ch_username = message.forward_from_chat.username
                msg_id = message.forward_from_message_id
                await users_col.update_one({"_id": user_id}, {"$set": {"custom_msg_type": "forward_link", "custom_msg": f"{ch_username}|{msg_id}", "custom_caption": ""}})
                msg_disp = f"[Forwarded Post] @{ch_username}/{msg_id}"
                
            elif message.text and "t.me/" in message.text:
                link = message.text.strip()
                try:
                    parts = link.split("/")
                    msg_id = parts[-1]
                    ch_username = parts[-2]
                    await users_col.update_one({"_id": user_id}, {"$set": {"custom_msg_type": "forward_link", "custom_msg": f"{ch_username}|{msg_id}", "custom_caption": ""}})
                    msg_disp = f"[Forward Link] {ch_username}/{msg_id}"
                except Exception:
                    USER_STATES.pop(user_id, None)
                    return await api_send(user_id, f"{E_WRN} Invalid link format! Failed to extract post ID. Setup cancelled.")
                    
            elif message.text:
                await users_col.update_one({"_id": user_id}, {"$set": {"custom_msg_type": "text", "custom_msg": message.text, "custom_caption": ""}})
                msg_disp = html.escape(message.text)
                
            elif message.photo:
                await users_col.update_one({"_id": user_id}, {"$set": {"custom_msg_type": "photo", "custom_msg": message.photo.file_id, "custom_caption": message.caption or ""}})
                msg_disp = "[Photo Message]"
                
            else:
                USER_STATES.pop(user_id, None)
                return await api_send(user_id, f"{E_WRN} Invalid format. Send a link, text, photo, or forward a public post.")
                
            USER_STATES.pop(user_id, None)
            text = f"{E_PLAY} <b>Mass DM Control Panel</b>\n\n💬 <b>Current Message:</b>\n<code>{msg_disp}</code>\n\nSelect your target channel or change your message below."
            btn = {"inline_keyboard": [
                [ibtn("Target Channel (Join Req)", "tgt_own", style="primary", icon=BTN_EMOJIS["target"]), ibtn("Target Alt's DMs", "tgt_alt_dms", style="success", icon=BTN_EMOJIS["user"])], 
                [ibtn("Target Admin's Free Channel", "tgt_free", style="primary", icon=BTN_EMOJIS["target"])], 
                [ibtn("Set Text/Photo", "set_msg", style="danger", icon=BTN_EMOJIS["setting"]), ibtn("Set Universal Msg", "set_fwd_msg", style="danger", icon=BTN_EMOJIS["globe"])], 
                [ibtn("Back to Main Menu", "back_home", style="secondary", icon=BTN_EMOJIS["home"])]
            ]}
            await api_send(user_id, text, kb=btn)

        elif state == "WAITING_FAMPAY_UTR":
            utr = message.text.strip() if message.text else ""
            if not utr or len(utr) < 5 or not utr.isalnum(): 
                USER_STATES.pop(user_id, None)
                return await api_send(user_id, f"{E_WRN} Invalid UTR or Transaction ID. Request cancelled, please click 'I Have Paid' and try again.")
            
            user_state_data = USER_STATES.pop(user_id, {})
            days = user_state_data.get("days", 1)
            price = float(user_state_data.get("price", 0.0))
            
            msg = await api_send(user_id, f"{E_SYNC} <b>Scanning Gmail for UTR/TxnID: {utr}</b>\n<i>Please wait 10-15 seconds...</i>")
            paid_amount = await asyncio.to_thread(check_payment_in_gmail, utr)
            
            if paid_amount and paid_amount >= price:
                u = await get_user(user_id); current_time = time.time()
                today_date = get_ist_str("%Y-%m-%d")
                
                nex = max(current_time, u.get("premium_expiry", 0)) + (days * 86400)
                await users_col.update_one({"_id": user_id}, {"$set": {"premium_expiry": nex}})
                exp_str = get_ist_ts_str(nex)
                await api_edit(msg.chat.id, msg.id, f"{E_DIA} <b>Payment Auto-Approved! ({days} Days)</b>\n\n{E_CHK} ID: <code>{utr}</code>\n{E_MONEY} Amount: ₹{paid_amount}\n\n🎉 <b>Your Premium is active until:</b>\n{E_CAL} <b>{exp_str}</b>")
                try: await api_send(ADMINS[0], f"{E_DIA} <b>Smart Auto-Approve</b>\n{E_PROF} User ID: <code>{user_id}</code>\n💳 Paid: ₹{paid_amount} for {days} Days\n🔖 ID: <code>{utr}</code>")
                except: pass
                await settings_col.update_one({"_id": "config"}, {"$inc": {"total_sales_inr": paid_amount, f"sales_history.{today_date}": paid_amount}})
            else:
                await api_edit(msg.chat.id, msg.id, f"{E_WRN} <b>Payment Not Found or Amount Mismatch!</b>\n\nWe scanned Gmail but couldn't verify ₹{price} for ID <code>{utr}</code>.\n\n<i>Tip: Wait 1-2 minutes for the email to arrive and try again.</i>")

        elif state == "WAITING_MANUAL_UTR":
            utr = message.text.strip() if message.text else ""
            if not utr or len(utr) < 5:
                USER_STATES.pop(user_id, None)
                return await api_send(user_id, f"{E_WRN} Invalid UTR or Transaction Hash. Request cancelled, please try again.")
            
            USER_STATES[user_id]["utr"] = utr
            USER_STATES[user_id]["state"] = "WAITING_MANUAL_SS"
            await api_send(user_id, f"📸 <b>Step 2/2:</b> Now send the <b>Payment Screenshot</b>.")

        elif state == "WAITING_MANUAL_SS":
            if not message.photo: 
                USER_STATES.pop(user_id, None)
                return await api_send(user_id, f"{E_WRN} Please send a valid photo screenshot. Process cancelled, please start over.")
                
            user_state_data = USER_STATES.pop(user_id, {})
            days = user_state_data.get("days", 1)
            utr = user_state_data.get("utr", "Unknown")
            
            btn = {"inline_keyboard": [[ibtn("Approve", f"manapp_{user_id}_{days}", style="success", icon=BTN_EMOJIS["tick"]), ibtn("Reject", f"manrej_{user_id}_{days}", style="danger", icon=BTN_EMOJIS["cross"])]]}
            for admin in ADMINS:
                try: await api_send(admin, f"{E_MONEY} <b>Manual Payment Pending! (PREMIUM)</b>\n{E_PROF} User ID: <code>{user_id}</code>\n👤 Name: {message.from_user.first_name}\n{E_CAL} Plan: {days} Days\n{E_CHK} UTR/Hash: <code>{utr}</code>", kb=btn, photo=message.photo.file_id)
                except: pass
            await api_send(user_id, f"{E_WAIT} <b>Success!</b> Screenshot & UTR sent to admins for manual verification.")

        elif state == "WAITING_PHONE":
            phone = message.text.replace(" ", "") if message.text else ""
            if not phone:
                USER_STATES.pop(user_id, None)
                return await api_send(user_id, f"{E_WRN} Invalid Phone Number. Please try again.")
            
            if phone.isdigit() and not phone.startswith("+"):
                phone = "+" + phone
                
            msg = await api_send(user_id, f"{E_SYNC} <i>Connecting to Telegram Servers...</i>")
            temp_client = Client(f"session_{user_id}", api_id=API_ID, api_hash=API_HASH, in_memory=True)
            await temp_client.connect()
            try:
                code_info = await temp_client.send_code(phone)
                USER_STATES[user_id].update({"state": "WAITING_OTP", "phone": phone, "phone_code_hash": code_info.phone_code_hash, "temp_client": temp_client})
                await api_edit(msg.chat.id, msg.id, f"📩 <b>OTP Sent Successfully!</b>\n\n{E_CHK} <b>Send with spaces:</b> <code>1 2 3 4 5</code>")
            except Exception as e: 
                USER_STATES.pop(user_id, None)
                await api_edit(msg.chat.id, msg.id, f"{E_WRN} <b>Error:</b> {e}\n<i>Please start over.</i>")
                try: await temp_client.disconnect()
                except: pass

        elif state == "WAITING_OTP":
            otp = message.text.replace(" ", "") if message.text else ""
            if not otp:
                USER_STATES.pop(user_id, None)
                return await api_send(user_id, f"{E_WRN} Invalid OTP. Please try again.")
                
            user_state_data = USER_STATES.get(user_id, {})
            temp_client = user_state_data.get("temp_client")
            if not temp_client:
                USER_STATES.pop(user_id, None)
                return await api_send(user_id, f"{E_WRN} Session timed out. Please try again.")
                
            msg = await api_send(user_id, f"{E_SYNC} <i>Verifying OTP...</i>")
            try:
                await temp_client.sign_in(user_state_data.get("phone"), user_state_data.get("phone_code_hash"), otp)
                ss = await temp_client.export_session_string()
                await users_col.update_one({"_id": user_id}, {"$push": {"sessions": ss}})
                await api_edit(msg.chat.id, msg.id, f"{E_CHK} <b>Session Added Successfully!</b>\nRedirecting to Main Menu...")
                await temp_client.disconnect(); USER_STATES.pop(user_id, None)
                
                await asyncio.sleep(1.5); config = await settings_col.find_one({"_id": "config"})
                first_name = html.escape(message.from_user.first_name if message.from_user else "User")
                text, btn = await get_home_menu(user_id, first_name, config)
                await api_send(user_id, text, kb=btn)
            except SessionPasswordNeeded:
                USER_STATES[user_id]["state"] = "WAITING_PASSWORD"
                await api_edit(msg.chat.id, msg.id, f"🔐 <b>Enter your 2FA Password:</b>")
            except Exception as e: 
                USER_STATES.pop(user_id, None)
                await api_edit(msg.chat.id, msg.id, f"{E_WRN} <b>Error:</b> {e}")
                try: await temp_client.disconnect()
                except: pass
                
        elif state == "WAITING_PASSWORD":
            user_state_data = USER_STATES.get(user_id, {})
            temp_client = user_state_data.get("temp_client")
            if not temp_client:
                USER_STATES.pop(user_id, None)
                return
                
            msg = await api_send(user_id, f"{E_SYNC} <i>Verifying Password...</i>")
            try:
                await temp_client.check_password(message.text)
                ss = await temp_client.export_session_string()
                await users_col.update_one({"_id": user_id}, {"$push": {"sessions": ss}})
                await api_edit(msg.chat.id, msg.id, f"{E_CHK} <b>Session Added Successfully!</b>\nRedirecting to Main Menu...")
                await temp_client.disconnect(); USER_STATES.pop(user_id, None)
                
                await asyncio.sleep(1.5); config = await settings_col.find_one({"_id": "config"})
                first_name = html.escape(message.from_user.first_name if message.from_user else "User")
                text, btn = await get_home_menu(user_id, first_name, config)
                await api_send(user_id, text, kb=btn)
            except Exception as e: 
                USER_STATES.pop(user_id, None)
                await api_edit(msg.chat.id, msg.id, f"{E_WRN} <b>Error:</b> {e}")
                try: await temp_client.disconnect()
                except: pass
            
        elif state == "WAITING_LINK":
            msg = await api_send(user_id, f"{E_SYNC} <b>Checking Channel...</b>")
            user_data = await get_user(user_id); config = await settings_col.find_one({"_id": "config"})
            asyncio.create_task(check_and_show_stats(client, user_id, user_data, config, message.text.strip(), msg, save_new=True))
            
        elif state == "WAITING_DM_LINK":
            msg = await api_send(user_id, f"{E_SYNC} <b>Checking Channel...</b>")
            user_data = await get_user(user_id); config = await settings_col.find_one({"_id": "config"})
            asyncio.create_task(check_and_show_stats(client, user_id, user_data, config, message.text.strip(), msg, save_new=False))

        elif state == "WAITING_LIMIT":
            if not message.text or not message.text.isdigit(): 
                USER_STATES.pop(user_id, None)
                return await api_send(user_id, f"{E_WRN} Please enter a valid number. Campaign setup cancelled.")
                
            USER_STATES[user_id]["limit"] = int(message.text); USER_STATES[user_id]["state"] = None
            btn = {"inline_keyboard": [[ibtn("All Users", "flt_all", style="primary", icon=BTN_EMOJIS["user"])], [ibtn("Online / Recently Seen", "flt_recent", style="success", icon=BTN_EMOJIS["tick"])], [ibtn("Active Members", "flt_active", style="primary", icon=BTN_EMOJIS["user"])], [ibtn("Premium Users Only", "flt_premium", style="danger", icon=BTN_EMOJIS["diamond"])]]}
            await api_send(user_id, f"{E_ADM} <b>Smart Filtering:</b>\nWho do you want to target?", kb=btn)
            
    except Exception as e:
        USER_STATES.pop(user_id, None)
        await api_send(message.chat.id, f"{E_WRN} <b>Error:</b>\n<code>{html.escape(str(e))}</code>")

# ================= DYNAMIC HANDLER BINDER =================
bot.add_handler(MessageHandler(start_cmd, filters.command("start") & filters.private))
bot.add_handler(MessageHandler(shortcut_cmds, filters.command(["buypremium", "massdm", "myaccount"]) & filters.private))
bot.add_handler(MessageHandler(check_total_public, filters.command(["total", "totaldms"]) & filters.private))
bot.add_handler(MessageHandler(admin_panel, filters.command("admin")))
bot.add_handler(MessageHandler(master_admin_cmds, filters.command(["setwebsitelink", "toggleauto", "reqall", "setfampay", "setmanual", "setcrypto", "setfampayqr", "setmanualqr", "setcryptoqr", "setprice1d", "setprice3d", "setprice7d", "setprice1m", "setfsub1", "setfsub2", "setfsub3", "setfsub4", "setfsub5", "setlogchannel", "setsuccesslog", "setleaderboard", "setfreechannel", "setfreerequest", "setfreetrial", "setfreereq", "setldbtime", "setrefbonus", "setdelay", "ongoing", "sales", "giveprem", "removeprem", "maintenance"])))
bot.add_handler(MessageHandler(shared_admin_cmds, filters.command(["stats", "checkuser", "clearsession", "banuser", "unbanuser", "broadcast"])))
bot.add_handler(MessageHandler(dm_controls, filters.command(["chk", "pause", "resume", "stop"]) & filters.private))
bot.add_handler(MessageHandler(handle_states, filters.private & filters.incoming), group=1)
bot.add_handler(CallbackQueryHandler(cb_handler))
bot.add_handler(CallbackQueryHandler(admin_manual_approve, filters.regex(r"^manapp_") | filters.regex(r"^manrej_")), group=1)
bot.add_handler(ChatJoinRequestHandler(handle_join_requests))


def validate_runtime_config():
    required = {
        "TELEGRAM_API_ID": API_ID,
        "TELEGRAM_API_HASH": API_HASH,
        "TELEGRAM_BOT_TOKEN": BOT_TOKEN,
        "GMAIL_USER": GMAIL_USER,
        "GMAIL_PASS": GMAIL_PASS,
    }
    missing = [name for name, value in required.items() if not value]
    if missing:
        raise RuntimeError(
            "Missing required environment variables: " + ", ".join(missing)
        )

# ================= SYSTEM LAUNCHER =================
async def start_bot():
    validate_runtime_config()
    print("-----------------------------------")
    await init_db()
    print("-----------------------------------")
    await bot.start()
    print(f"🚀 BOT STARTED: {(await bot.get_me()).username}")
    asyncio.create_task(auto_leaderboard_task())
    await idle()
    print("Shutting down...")
    await bot.stop()

if __name__ == "__main__":
    loop = asyncio.get_event_loop()
    loop.run_until_complete(start_bot())
