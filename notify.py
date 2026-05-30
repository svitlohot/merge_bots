import os
import json
import requests
from datetime import datetime, timedelta

# ============================================
# НАЛАШТУВАННЯ
# ============================================

SVITLO_KEY1    = os.environ.get("SVITLO_KEY1", "")      # Хотянівка СТ
SVITLO_KEY2    = os.environ.get("SVITLO_KEY2", "")      # ПБХ/Осещина
BOT_TOKEN      = os.environ.get("NOTIFY_BOT_TOKEN", "")
CHAT_ID        = os.environ.get("NOTIFY_CHAT_ID", "")
STATE_FILE     = "state.json"

# ============================================
# ФУНКЦІЇ
# ============================================

def fetch_status(key):
    try:
        url = f"https://api.svitlobot.in.ua/status?channel_key={key}"
        text = requests.get(url, timeout=5).text
        if "світло є" in text.lower():      return "on"
        elif "світла немає" in text.lower(): return "off"
        else:                                return "unknown"
    except Exception as e:
        print(f"Fetch error: {e}")
        return "unknown"


def load_state():
    try:
        with open(STATE_FILE, "r") as f:
            return json.load(f)
    except:
        return {
            "s1": "unknown",
            "s2": "unknown",
            "message_id": None
        }


def save_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)


def send_message(text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    resp = requests.post(url, json={
        "chat_id": CHAT_ID,
        "text": text,
        "parse_mode": "HTML"
    }, timeout=10)
    data = resp.json()
    if data.get("ok"):
        return data["result"]["message_id"]
    else:
        print(f"Send error: {data}")
        return None


def edit_message(message_id, text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/editMessageText"
    resp = requests.post(url, json={
        "chat_id": CHAT_ID,
        "message_id": message_id,
        "text": text,
        "parse_mode": "HTML"
    }, timeout=10)
    data = resp.json()
    if not data.get("ok"):
        print(f"Edit error: {data}")


def build_message(s1, s2):
    now = datetime.utcnow() + timedelta(hours=3)
    time_str = now.strftime("%H:%M")

    s1_icon = "🟢" if s1 == "on" else ("🔴" if s1 == "off" else "⚪")
    s2_icon = "🟢" if s2 == "on" else ("🔴" if s2 == "off" else "⚪")

    s1_text = "є" if s1 == "on" else ("немає" if s1 == "off" else "невідомо")
    s2_text = "є" if s2 == "on" else ("немає" if s2 == "off" else "невідомо")

    lines = [
        f"💡 <b>Статус світла</b> • {time_str}",
        f"",
        f"{s1_icon} Хотянівка СТ: світло <b>{s1_text}</b>",
        f"{s2_icon} ПБХ/Осещина: світло <b>{s2_text}</b>",
    ]

    if s1 == "on" and s2 == "on":
        lines.append(f"\n✅ Світло скрізь є")
    elif s1 == "off" and s2 == "off":
        lines.append(f"\n❌ Світла немає ніде")
    else:
        lines.append(f"\n⚠️ Часткове відключення")

    return "\n".join(lines)


# ============================================
# ОСНОВНА ЛОГІКА
# ============================================

state = load_state()
prev_s1 = state["s1"]
prev_s2 = state["s2"]
message_id = state["message_id"]

curr_s1 = fetch_status(SVITLO_KEY1)
curr_s2 = fetch_status(SVITLO_KEY2)

print(f"Попередній стан: s1={prev_s1}, s2={prev_s2}")
print(f"Поточний стан:  s1={curr_s1}, s2={curr_s2}")

# Перевіряємо чи змінився статус
s1_changed = curr_s1 != prev_s1 and curr_s1 != "unknown"
s2_changed = curr_s2 != prev_s2 and curr_s2 != "unknown"

if s1_changed or s2_changed:
    print("Статус змінився! Надсилаємо повідомлення...")
    text = build_message(curr_s1, curr_s2)

    if message_id:
        # Редагуємо існуюче повідомлення
        edit_message(message_id, text)
        print(f"Відредаговано повідомлення {message_id}")
    else:
        # Надсилаємо нове
        message_id = send_message(text)
        print(f"Надіслано нове повідомлення {message_id}")

    # Якщо світло скрізь є — скидаємо message_id (наступна подія = нове повідомлення)
    if curr_s1 == "on" and curr_s2 == "on":
        message_id = None
        print("Світло скрізь є — скидаємо message_id")

    state["s1"] = curr_s1
    state["s2"] = curr_s2
    state["message_id"] = message_id
    save_state(state)
else:
    print("Статус не змінився, нічого не робимо")

print("DONE")