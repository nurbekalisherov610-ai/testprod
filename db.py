import sqlite3
import datetime
import logging

import os

def get_connection():
    db_path = os.getenv("DB_PATH", "habit_tracker.db")
    conn = sqlite3.connect(db_path, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            user_id INTEGER PRIMARY KEY
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS habits (
            habit_id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER,
            name TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY(user_id) REFERENCES users(user_id)
        )
    ''')
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS daily_logs (
            log_id INTEGER PRIMARY KEY AUTOINCREMENT,
            habit_id INTEGER,
            log_date DATE,
            status TEXT DEFAULT 'completed',
            FOREIGN KEY(habit_id) REFERENCES habits(habit_id),
            UNIQUE(habit_id, log_date)
        )
    ''')
    conn.commit()
    conn.close()

def add_user_if_not_exists(user_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('INSERT OR IGNORE INTO users (user_id) VALUES (?)', (user_id,))
    conn.commit()
    conn.close()

def add_habit(user_id, name):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('INSERT INTO habits (user_id, name) VALUES (?, ?)', (user_id, name))
    conn.commit()
    habit_id = cursor.lastrowid
    conn.close()
    return habit_id

def get_habits(user_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT * FROM habits WHERE user_id = ?', (user_id,))
    rows = cursor.fetchall()
    conn.close()
    return rows

def delete_habit(user_id, habit_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('DELETE FROM habits WHERE user_id = ? AND habit_id = ?', (user_id, habit_id))
    # Also delete related logs to maintain clear data
    cursor.execute('DELETE FROM daily_logs WHERE habit_id = ?', (habit_id,))
    conn.commit()
    conn.close()

def log_habit_today(user_id, habit_id):
    conn = get_connection()
    cursor = conn.cursor()
    today = datetime.date.today().isoformat()
    
    # Check if this habit belongs to the user
    cursor.execute('SELECT habit_id FROM habits WHERE user_id = ? AND habit_id = ?', (user_id, habit_id))
    if not cursor.fetchone():
        conn.close()
        return False, "This habit does not belong to you."
        
    try:
        cursor.execute('''
            INSERT INTO daily_logs (habit_id, log_date, status)
            VALUES (?, ?, ?)
        ''', (habit_id, today, 'completed'))
        conn.commit()
        success = True
        msg = "Logged successfully!"
    except sqlite3.IntegrityError:
        success = False
        msg = "You have already completed this habit today!"
    conn.close()
    return success, msg

def get_today_logs(user_id):
    conn = get_connection()
    cursor = conn.cursor()
    today = datetime.date.today().isoformat()
    cursor.execute('''
        SELECT h.habit_id, h.name, d.status 
        FROM habits h
        LEFT JOIN daily_logs d ON h.habit_id = d.habit_id AND d.log_date = ?
        WHERE h.user_id = ?
    ''', (today, user_id))
    rows = cursor.fetchall()
    conn.close()
    return rows

def get_streak(user_id, habit_id):
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('''
        SELECT log_date FROM daily_logs 
        WHERE habit_id = ? AND status = 'completed'
        ORDER BY log_date DESC
    ''', (habit_id,))
    rows = cursor.fetchall()
    conn.close()
    
    if not rows:
        return 0
        
    logs = [datetime.date.fromisoformat(row['log_date']) for row in rows]
    current_date = datetime.date.today()
    
    if logs and (current_date - logs[0]).days > 1:
        return 0 # Streak broken
        
    streak = 0
    expected_date = logs[0]
    
    for log_date in logs:
        if log_date == expected_date:
            streak += 1
            expected_date = expected_date - datetime.timedelta(days=1)
        else:
            break
            
    return streak

def get_admin_stats():
    conn = get_connection()
    cursor = conn.cursor()
    cursor.execute('SELECT COUNT(*) FROM users')
    total_users = cursor.fetchone()[0]
    cursor.execute('SELECT COUNT(*) FROM habits')
    total_habits = cursor.fetchone()[0]
    cursor.execute('SELECT COUNT(*) FROM daily_logs')
    total_logs = cursor.fetchone()[0]
    conn.close()
    return total_users, total_habits, total_logs

