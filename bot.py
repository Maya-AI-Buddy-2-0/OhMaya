import os
import time
import requests
import psycopg2
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer
from bs4 import BeautifulSoup
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from telegram.request import HTTPXRequest

# Capture Cloud Server Environment Variables
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN")
OPENROUTER_API_KEY = os.getenv("OPENROUTER_API_KEY")
SUPABASE_DB_CONNECTION = os.getenv("SUPABASE_DB_CONNECTION")

# Cloud providers assign a dynamic port. If none, default to 7860.
PORT = int(os.getenv("PORT", 7860))

# --- CLOUD HEALTH CHECK SERVER ---
class HealthCheckHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/plain')
        self.end_headers()
        self.wfile.write(b"Maya AI Engine is Awake & Listening to Telegram.")

def keep_alive_server():
    server = HTTPServer(('0.0.0.0', PORT), HealthCheckHandler)
    server.serve_forever()
# ----------------------------------------

def ask_hermes(system_prompt, user_input):
    """Sends dynamic system parameters and user prompts to the free OpenRouter Hermes 3 instance."""
    try:
        response = requests.post(
            url="https://openrouter.ai/api/v1/chat/completions",
            headers={
                "Authorization": f"Bearer {OPENROUTER_API_KEY}",
                "Content-Type": "application/json"
            },
            json={
                "model": "nousresearch/hermes-3-llama-3.1-405b:free",
                "messages": [
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": user_input}
                ]
            },
            timeout=30
        )
        data = response.json()
        
        # DIAGNOSTIC PATCH: Check if OpenRouter sent an error instead of a response
        if 'error' in data:
            return f"🚨 OpenRouter API Error: {data['error'].get('message', 'Unknown Error')}"
            
        return data['choices'][0]['message']['content']
    except Exception as e:
        return f"🚨 Engine Processing Error: {str(e)}"

async def start_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Dynamically generates a unique AI greeting before showing the command menu."""
    await update.message.reply_chat_action(action="typing")

    system_prompt = (
        "You are Maya 2.0, an elite, autonomous AI orchestrator. "
        "The system has just booted up. Write a short, punchy, 2-sentence greeting "
        "welcoming your creator back to the terminal. Hook him in. Make it sound highly capable, "
        "and ready to build the next empire. Do not use hashtags or emojis."
    )
    
    ai_greeting = ask_hermes(system_prompt, "System boot sequence complete. Greet the boss.")

    menu = (
        "\n\n⚡ **SYSTEM COMMANDS** ⚡\n"
        "🔹 `/analyze [URL]` - Scrape site & spawn isolated business/marketing agents.\n"
        "🔹 `/link [domain] [KEY=VALUE]` - Securely inject API keys.\n"
        "💬 Or just type a message to chat with my master node."
    )

    await update.message.reply_text(f"{ai_greeting}{menu}", parse_mode="Markdown")

async def analyze_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Dynamically parses websites, invokes sub-agents, and creates database isolation partitions."""
    if not context.args:
        await update.message.reply_text("⚠️ Execution Halt. Please pass a target URL. Example: /analyze https://thegreydiary.online/")
        return
        
    url = context.args[0]
    domain = url.replace("https://", "").replace("http://", "").split("/")[0]
    await update.message.reply_text(f"📡 Maya is deploying web crawlers to scan: `{domain}`...", parse_mode="Markdown")

    try:
        res = requests.get(url, headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)"}, timeout=15)
        soup = BeautifulSoup(res.text, 'html.parser')
        extracted_chunks = [s.get_text() for s in soup.find_all(['p', 'h1', 'h2', 'h3', 'li'])]
        raw_text = " ".join(extracted_chunks)[:4000]
        
        if not raw_text.strip():
            raw_text = "Fallback: Landing page loaded, but content extraction yielded minimal string output."
    except Exception as e:
        await update.message.reply_text(f"❌ Web Crawl Intercepted / Failed: {str(e)}")
        return

    biz_prompt = "You are Maya's Expert Business Strategist Sub-Agent. Analyze this scraped website content. Define the core product offering, target demographic, monetization layout, and market placement."
    mkt_prompt = "You are Maya's Expert Chief Marketing Officer (CMO) Sub-Agent. Analyze this scraped website content. Build actionable marketing hooks, zero-budget organic growth blueprints, and target social communities."

    await update.message.reply_chat_action(action="typing")
    business_analysis = ask_hermes(biz_prompt, raw_text)
    marketing_analysis = ask_hermes(mkt_prompt, raw_text)

    try:
        conn = psycopg2.connect(SUPABASE_DB_CONNECTION)
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO dynamic_nodes (domain_name, raw_scraped_data, ai_business_analysis, ai_marketing_playbook)
            VALUES (%s, %s, %s, %s)
            ON CONFLICT (domain_name) DO UPDATE SET 
                raw_scraped_data = EXCLUDED.raw_scraped_data,
                ai_business_analysis = EXCLUDED.ai_business_analysis,
                ai_marketing_playbook = EXCLUDED.ai_marketing_playbook;
        """, (domain, raw_text, business_analysis, marketing_analysis))
        conn.commit()
        cur.close()
        conn.close()
    except Exception as e:
        await update.message.reply_text(f"⚠️ Memory Write Warning (Supabase Error): {str(e)}")
        return

    await update.message.reply_text(
        f"🎯 *Node Activation Success: {domain}*\n\n"
        f"📊 *[Business Node Agent]*\n{business_analysis}\n\n"
        f"📈 *[CMO Node Agent]*\n{marketing_analysis}\n\n"
        f"👉 To pass specific API credentials dynamically into this profile, execute:\n"
        f"`/link {domain} STRIPE_KEY=your_key`",
        parse_mode="Markdown"
    )

async def link_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Dynamically binds environment credentials to specific domain structures on the fly."""
    if len(context.args) < 2 or "=" not in context.args[1]:
        await update.message.reply_text("⚠️ Syntax error. Correct format: `/link [domain_name] [KEY_NAME=VALUE]`", parse_mode="Markdown")
        return
        
    domain = context.args[0]
    kv_string = context.args[1]
    key, val = kv_string.split("=", 1)
    
    try:
        conn = psycopg2.connect(SUPABASE_DB_CONNECTION)
        cur = conn.cursor()
        cur.execute("""
            INSERT INTO node_credentials (domain_name, credential_key, credential_value)
            VALUES (%s, %s, %s)
            ON CONFLICT (domain_name, credential_key) DO UPDATE SET credential_value = EXCLUDED.credential_value;
        """, (domain, key.upper(), val))
        conn.commit()
        cur.close()
        conn.close()
        await update.message.reply_text(f"🔒 Securely isolated credential `{key.upper()}` for business node context: `{domain}`.", parse_mode="Markdown")
    except Exception as e:
        await update.message.reply_text(f"❌ Vault Write Failure: {str(e)}")

async def master_chat_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Master default routing handling casual prompts using our core identity."""
    user_input = update.message.text
    system_identity = (
        "You are Maya 2.0, a hyper-intelligent autonomous orchestrator backbone. "
        "You communicate with elite, philosophical tech-founder confidence, guiding strategic decisions across multiple nodes."
    )
    await update.message.reply_chat_action(action="typing")
    response = ask_hermes(system_identity, user_input)
    await update.message.reply_text(response)

def main():
    # 1. Fire up the invisible port router in a background thread to keep Render happy
    threading.Thread(target=keep_alive_server, daemon=True).start()

    # 2. Build the Telegram App with the timeout shield enabled
    t_request = HTTPXRequest(connection_pool_size=8, connect_timeout=100.0, read_timeout=100.0, write_timeout=100.0, http_version="1.1")
    app = Application.builder().token(TELEGRAM_TOKEN).request(t_request).build()
    
    app.add_handler(CommandHandler("start", start_command))
    app.add_handler(CommandHandler("analyze", analyze_command))
    app.add_handler(CommandHandler("link", link_command))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, master_chat_handler))
    
    print("Maya AI Engine fully deployed. Connecting to Telegram...")
    app.run_polling(drop_pending_updates=True)

if __name__ == "__main__":
    main()
