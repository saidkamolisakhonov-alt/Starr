import os

BOT_TOKEN = os.getenv("BOT_TOKEN")
ADMIN_ID = '5328760224'
if not BOT_TOKEN:
    raise RuntimeError("BOT_TOKEN is not set in Railway Variables")

