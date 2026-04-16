import logging
from telegram import Update, ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    CallbackQueryHandler,
    ConversationHandler,
    filters,
    ContextTypes,
)
import db
import random
import os

ADMIN_ID = 524551673

# Setup logging
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)
logger = logging.getLogger(__name__)

# Conversation states
ADDING_HABIT = 1

def get_keyboard(user_id):
    keyboard = [
        [KeyboardButton("📝 My Habits"), KeyboardButton("➕ Add Habit")],
        [KeyboardButton("✅ Complete Habit"), KeyboardButton("🗑 Delete Habit")],
        [KeyboardButton("📊 Statistics")]
    ]
    if user_id == ADMIN_ID:
        keyboard.append([KeyboardButton("👑 Admin Panel")])
    return ReplyKeyboardMarkup(keyboard, resize_keyboard=True)

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    db.add_user_if_not_exists(user_id)
    welcome_message = (
        "Welcome to the Habit Tracker Bot! 🚀\n\n"
        "I can help you build good habits and track your consistent progress.\n"
        "Use the menu below to get started:"
    )
    await update.message.reply_text(welcome_message, reply_markup=get_keyboard(user_id))

async def view_habits(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    habits = db.get_habits(user_id)
    if not habits:
        await update.message.reply_text("You don't have any habits yet. Click '➕ Add Habit' to create one!")
        return
        
    text = "📋 *Your Habits:*\n\n"
    for h in habits:
        text += f"🔹 {h['name']} \n"
    await update.message.reply_text(text, parse_mode='Markdown')

async def add_habit_start(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    await update.message.reply_text(
        "Please type the name of the new habit you want to track:\n(or type /cancel to abort)"
    )
    return ADDING_HABIT

async def add_habit_save(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.effective_user.id
    habit_name = update.message.text
    
    if not habit_name.strip():
        await update.message.reply_text("Habit name cannot be empty. Try again or /cancel.")
        return ADDING_HABIT
        
    db.add_habit(user_id, habit_name)
    await update.message.reply_text(f"✅ Habit '{habit_name}' added successfully!", reply_markup=get_keyboard(user_id))
    return ConversationHandler.END

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> int:
    user_id = update.effective_user.id
    await update.message.reply_text("Action canceled.", reply_markup=get_keyboard(user_id))
    return ConversationHandler.END

async def complete_habit_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    logs = db.get_today_logs(user_id)
    
    if not logs:
        await update.message.reply_text("You don't have any habits to complete. Add one first!")
        return
        
    keyboard = []
    for log in logs:
        status_icon = "✅" if log['status'] else "⬜️"
        btn_text = f"{status_icon} {log['name']}"
        cb_data = f"log_{log['habit_id']}" if not log['status'] else "noop"
        keyboard.append([InlineKeyboardButton(btn_text, callback_data=cb_data)])
        
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("Select a habit to mark as completed for today:", reply_markup=reply_markup)

async def delete_habit_menu(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    habits = db.get_habits(user_id)
    
    if not habits:
        await update.message.reply_text("You don't have any habits to delete.")
        return
        
    keyboard = []
    for h in habits:
        keyboard.append([InlineKeyboardButton(f"🗑 {h['name']}", callback_data=f"del_{h['habit_id']}")])
        
    reply_markup = InlineKeyboardMarkup(keyboard)
    await update.message.reply_text("⚠️ Select a habit to delete (This cannot be undone):", reply_markup=reply_markup)

async def statistics(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    habits = db.get_habits(user_id)
    
    if not habits:
        await update.message.reply_text("No habits tracked yet.")
        return
        
    text = "📊 *Your Habit Statistics:*\n\n"
    for h in habits:
        streak = db.get_streak(user_id, h['habit_id'])
        text += f"🔹 *{h['name']}*\n🔥 Current Streak: {streak} days\n\n"
        
    await update.message.reply_text(text, parse_mode='Markdown')

async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    user_id = update.effective_user.id
    if user_id != ADMIN_ID:
        return
        
    users, habits, logs = db.get_admin_stats()
    text = (
        "👑 *Admin Dashboard*\n\n"
        f"👥 Total Users: {users}\n"
        f"📝 Total Habits Tracked: {habits}\n"
        f"✅ Total Habits Logged: {logs}\n"
    )
    await update.message.reply_text(text, parse_mode='Markdown')

async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    query = update.callback_query
    await query.answer()
    
    data = query.data
    user_id = update.effective_user.id
    
    if data.startswith("log_"):
        habit_id = int(data.split('_')[1])
        success, msg = db.log_habit_today(user_id, habit_id)
        
        if success:
            # Refresh the menu
            logs = db.get_today_logs(user_id)
            keyboard = []
            for log in logs:
                status_icon = "✅" if log['status'] else "⬜️"
                btn_text = f"{status_icon} {log['name']}"
                cb_data = f"log_{log['habit_id']}" if not log['status'] else "noop"
                keyboard.append([InlineKeyboardButton(btn_text, callback_data=cb_data)])
            
            quotes = [
                "Great job! Keep up the good work! 💪", 
                "Every day counts! 🌟", 
                "Small steps lead to big changes! 🚀", 
                "Consistency is key! 🔑"
            ]
            msg_extra = "\n_" + random.choice(quotes) + "_"
            
            await query.edit_message_text(
                f"✅ *Awesome!*\n{msg_extra}\n\nSelect another habit to mark as completed for today:", 
                reply_markup=InlineKeyboardMarkup(keyboard),
                parse_mode='Markdown'
            )
        else:
            await query.message.reply_text(msg)

    elif data.startswith("del_"):
        habit_id = int(data.split('_')[1])
        db.delete_habit(user_id, habit_id)
        
        # Refresh the delete menu
        habits = db.get_habits(user_id)
        keyboard = []
        for h in habits:
            keyboard.append([InlineKeyboardButton(f"🗑 {h['name']}", callback_data=f"del_{h['habit_id']}")])
        
        if keyboard:
            await query.edit_message_text(
                "Habit deleted. Select another habit to delete:", 
                reply_markup=InlineKeyboardMarkup(keyboard)
            )
        else:
            await query.edit_message_text("All habits deleted.")

def main() -> None:
    # Initialize database
    db.init_db()
    
    # Use environment variable for token, fallback to hardcoded for local dev
    TOKEN = os.getenv("TELEGRAM_TOKEN", "8748639619:AAFwXAwS4TSnHuL5XMRmICphNdmVGV8T-Vg")
    
    # Create the app
    application = Application.builder().token(TOKEN).build()
    
    conv_handler = ConversationHandler(
        entry_points=[MessageHandler(filters.Regex("^➕ Add Habit$"), add_habit_start)],
        states={
            ADDING_HABIT: [MessageHandler(filters.TEXT & ~filters.COMMAND, add_habit_save)],
        },
        fallbacks=[CommandHandler("cancel", cancel)],
    )

    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.Regex("^📝 My Habits$"), view_habits))
    application.add_handler(conv_handler)
    application.add_handler(MessageHandler(filters.Regex("^✅ Complete Habit$"), complete_habit_menu))
    application.add_handler(MessageHandler(filters.Regex("^🗑 Delete Habit$"), delete_habit_menu))
    application.add_handler(MessageHandler(filters.Regex("^📊 Statistics$"), statistics))
    application.add_handler(MessageHandler(filters.Regex("^👑 Admin Panel$"), admin_panel))
    
    application.add_handler(CallbackQueryHandler(button_callback))
    
    # Run the bot
    application.run_polling(allowed_updates=Update.ALL_TYPES)

if __name__ == "__main__":
    main()
