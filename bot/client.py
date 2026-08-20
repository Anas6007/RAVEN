from pyrogram import Client

from config.settings import settings

app = Client(
    "tg_giveaway_bot",
    api_id=settings.API_ID,
    api_hash=settings.API_HASH,
    bot_token=settings.BOT_TOKEN,
    # عدد الـ workers المتزامنين لمعالجة التحديثات الواردة (ضغطات الأزرار،
    # الرسائل...). كان هذا الإعداد موجودًا في .env لكن غير مُمرَّر فعليًا
    # للعميل، فكان البوت يعمل دائمًا بالقيمة الافتراضية بغض النظر عن أي
    # ضبط. عند حمل كبير (آلاف الضغطات المتزامنة) ارفع WORKERS في .env حسب
    # عدد أنوية المعالج المتاحة على الخادم.
    workers=settings.WORKERS,
)