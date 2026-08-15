import sqlite3
import datetime
from config import DB_NAME
from data_loader import load_activities, load_achievements, evaluate_rule

ACTIVITIES = load_activities()
ACHIEVEMENTS_LIST = load_achievements()



def get_connection():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                first_name TEXT,
                strength INTEGER DEFAULT 0,
                intelligence INTEGER DEFAULT 0,
                agility INTEGER DEFAULT 0,
                wisdom INTEGER DEFAULT 0,
                health INTEGER DEFAULT 0,
                total_xp INTEGER DEFAULT 0,
                streak_days INTEGER DEFAULT 0,
                last_active_date TEXT,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS activity_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                activity_key TEXT,
                activity_title TEXT,
                stat_name TEXT,
                stat_gained INTEGER,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (user_id)
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS user_achievements (
                user_id INTEGER,
                achievement_id TEXT,
                unlocked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                PRIMARY KEY (user_id, achievement_id),
                FOREIGN KEY (user_id) REFERENCES users (user_id)
            )
        ''')
        conn.commit()


def register_user(user_id: int, username: str, first_name: str):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT user_id FROM users WHERE user_id = ?", (user_id,))
        user = cursor.fetchone()
        if not user:
            cursor.execute(
                "INSERT INTO users (user_id, username, first_name) VALUES (?, ?, ?)",
                (user_id, username or "", first_name or "Пользователь")
            )
        else:
            cursor.execute(
                "UPDATE users SET username = ?, first_name = ? WHERE user_id = ?",
                (username or "", first_name or "Пользователь", user_id)
            )
        conn.commit()

def get_user(user_id: int):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
        return cursor.fetchone()

def update_streak(conn, user_id: int):
    today = datetime.date.today().isoformat()
    yesterday = (datetime.date.today() - datetime.timedelta(days=1)).isoformat()

    cursor = conn.cursor()
    cursor.execute("SELECT last_active_date, streak_days FROM users WHERE user_id = ?", (user_id,))
    row = cursor.fetchone()
    if not row:
        return 1

    last_date = row['last_active_date']
    current_streak = row['streak_days'] or 0

    if last_date == today:
        return current_streak
    elif last_date == yesterday:
        new_streak = current_streak + 1
    else:
        new_streak = 1

    cursor.execute("UPDATE users SET streak_days = ?, last_active_date = ? WHERE user_id = ?", (new_streak, today, user_id))
    return new_streak

def add_activity(user_id: int, activity_key: str, quantity: float = None):
    if activity_key not in ACTIVITIES:
        return None

    act_info = ACTIVITIES[activity_key]
    stat_field = act_info['stat']

    if quantity is None or quantity <= 0:
        quantity = act_info['presets'][1][0] if act_info.get('presets') else 1.0

    reward = act_info['calc_pts'](quantity)
    unit = act_info['unit']

    qty_val_str = f"{int(quantity) if quantity == int(quantity) else quantity}"
    qty_str = f"{qty_val_str} {unit}"
    log_title = f"{act_info['title']} ({qty_str})"

    with get_connection() as conn:
        cursor = conn.cursor()
        streak = update_streak(conn, user_id)

        cursor.execute(f"""
            UPDATE users
            SET {stat_field} = {stat_field} + ?,
                total_xp = total_xp + ?
            WHERE user_id = ?
        """, (reward, reward, user_id))

        cursor.execute("""
            INSERT INTO activity_logs (user_id, activity_key, activity_title, stat_name, stat_gained)
            VALUES (?, ?, ?, ?, ?)
        """, (user_id, activity_key, log_title, act_info['stat_title'], reward))

        conn.commit()
        new_achievements = check_achievements(conn, user_id)

    return {
        "activity": act_info,
        "quantity_str": qty_str,
        "gained": reward,
        "streak": streak,
        "new_achievements": new_achievements
    }


def check_achievements(conn, user_id: int):
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
    user_row = cursor.fetchone()
    if not user_row:
        return []

    stats = dict(user_row)

    cursor.execute("SELECT COUNT(*) as cnt FROM activity_logs WHERE user_id = ?", (user_id,))
    activity_count = cursor.fetchone()['cnt']

    today = datetime.date.today().isoformat()
    cursor.execute(
        "SELECT COUNT(*) as cnt FROM activity_logs WHERE user_id = ? AND date(timestamp) = ?",
        (user_id, today)
    )
    today_count = cursor.fetchone()['cnt']

    current_hour = datetime.datetime.now().hour

    cursor.execute(
        "SELECT activity_key, COUNT(*) as cnt FROM activity_logs WHERE user_id = ? GROUP BY activity_key",
        (user_id,)
    )
    act_counts = {r['activity_key']: r['cnt'] for r in cursor.fetchall()}

    ctx = {
        "stats": stats,
        "count": activity_count,
        "today_count": today_count,
        "hour": current_hour,
        "act_counts": act_counts
    }

    cursor.execute("SELECT achievement_id FROM user_achievements WHERE user_id = ?", (user_id,))
    unlocked = {r['achievement_id'] for r in cursor.fetchall()}

    newly_unlocked = []
    for ach in ACHIEVEMENTS_LIST:
        if ach['id'] not in unlocked:
            if evaluate_rule(ach.get('rule', {}), ctx):
                cursor.execute(
                    "INSERT INTO user_achievements (user_id, achievement_id) VALUES (?, ?)",
                    (user_id, ach['id'])
                )
                newly_unlocked.append(ach)

    return newly_unlocked


def get_user_achievements(user_id: int):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("SELECT achievement_id, unlocked_at FROM user_achievements WHERE user_id = ?", (user_id,))
        unlocked = {r['achievement_id']: r['unlocked_at'] for r in cursor.fetchall()}

    result = []
    for ach in ACHIEVEMENTS_LIST:
        is_unlocked = ach['id'] in unlocked
        is_secret = ach.get('secret', False)

        if is_unlocked:
            title = ach['title']
            desc = ach['desc']
        else:
            if is_secret:
                title = "❓ ???"
                desc = "🔒 Секретное достижение (условия скрыты)"
            else:
                title = ach['title']
                desc = ach['desc']

        result.append({
            "id": ach['id'],
            "title": title,
            "desc": desc,
            "unlocked": is_unlocked,
            "secret": is_secret,
            "date": unlocked.get(ach['id'])
        })
    return result


def get_leaderboard(stat_type: str = "total_xp", limit: int = 10):
    valid_stats = {
        "total_xp": "Общий опыт",
        "strength": "Сила",
        "intelligence": "Интеллект",
        "agility": "Ловкость",
        "wisdom": "Мудрость"
    }

    stat_col = stat_type if stat_type in valid_stats else "total_xp"

    with get_connection() as conn:
        cursor = conn.cursor()
        query = f"""
            SELECT user_id, username, first_name, {stat_col} as score, total_xp, strength, intelligence, agility, wisdom
            FROM users
            ORDER BY {stat_col} DESC, total_xp DESC
            LIMIT ?
        """
        cursor.execute(query, (limit,))
        return cursor.fetchall(), valid_stats.get(stat_col, "Общий опыт")

def get_user_activity_history(user_id: int, limit: int = 5):
    with get_connection() as conn:
        cursor = conn.cursor()
        cursor.execute("""
            SELECT activity_title, stat_name, stat_gained, timestamp
            FROM activity_logs
            WHERE user_id = ?
            ORDER BY timestamp DESC
            LIMIT ?
        """, (user_id, limit))
        return cursor.fetchall()

