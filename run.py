import asyncio
import signal

from bot.client import app
from config import logger

import bot.handlers.start as start
import bot.handlers.callbacks as callbacks
import bot.handlers.giveaway_description as giveaway_description
import bot.handlers.link as link
import bot.handlers.my_channels as my_channels
import bot.handlers.required_channels as required_channels
import bot.handlers.giveaway_mode as giveaway_mode
import bot.handlers.giveaway_settings as giveaway_settings
import bot.handlers.publish as publish
import bot.handlers.draw as draw
import bot.handlers.stop_participation as stop_participation
import bot.handlers.giveaway_winners as giveaway_winners
import bot.handlers.competition_seats as competition_seats
import bot.handlers.competition_requests as competition_requests
import bot.handlers.giveaway_image as giveaway_image
import bot.handlers.giveaway_edit as giveaway_edit
import bot.handlers.preview as preview
import bot.handlers.check_join as check_join
import bot.handlers.remind as remind
import bot.handlers.participant_captcha as participant_captcha
import bot.handlers.my_giveaways as my_giveaways
import bot.handlers.my_competitions as my_competitions
import bot.handlers.giveaway_info as giveaway_info
import bot.handlers.comment_capture as comment_capture
import bot.handlers.misc as misc
import bot.handlers.dev_panel as dev_panel

from database.init import create_tables
from database.session import engine as db_engine
from scheduler.scheduler import start_scheduler, stop_scheduler


# ملاحظة على الترتيب: participant_captcha مسجَّل في النهاية لأنه معالج نصي
# عام (catch-all) يلتقط أي رسالة خاصة لم يلتقطها معالج أكثر تحديدًا قبله
# (وصف/عدد فائزين/شروط/رابط قناة...)، وذلك للتحقق من إجابات الكابتشا.

start.register(app)
callbacks.register(app)
giveaway_description.register(app)
link.register(app)
my_channels.register(app)
required_channels.register(app)
giveaway_mode.register(app)
giveaway_settings.register(app)
publish.register(app)
draw.register(app)
stop_participation.register(app)
giveaway_winners.register(app)
giveaway_image.register(app)
competition_seats.register(app)
competition_requests.register(app)
giveaway_edit.register(app)
preview.register(app)
check_join.register(app)
remind.register(app)
my_giveaways.register(app)
my_competitions.register(app)
giveaway_info.register(app)
misc.register(app)
dev_panel.register(app)
comment_capture.register(app)
participant_captcha.register(app)


async def startup():
    await create_tables()
    logger.info("✅ Database ready.")
    await publish.check_all_giveaways_channel(app)
    start_scheduler(app)


async def shutdown():
    """
    إيقاف آمن للبوت: نوقف الجدولة أولًا حتى لا يبدأ سحب جديد أثناء
    الإغلاق، ثم نغلق اتصال قاعدة البيانات بشكل نظيف. كل بيانات
    السحوبات والمشاركين محفوظة بالفعل في قاعدة البيانات فور حدوثها
    (وليست في الذاكرة)، لذا لا يوجد خطر فقدان السحوبات القائمة عند
    إيقاف البوت أو إعادة تشغيله.
    """

    logger.info("🛑 Shutting down...")

    try:
        stop_scheduler()
    except Exception as e:
        logger.warning("[Shutdown] Scheduler stop error: {}", repr(e))

    try:
        await db_engine.dispose()
        logger.info("✅ Database connections closed.")
    except Exception as e:
        logger.warning("[Shutdown] DB dispose error: {}", repr(e))


def _handle_signal(*_):
    raise KeyboardInterrupt


for sig in (signal.SIGINT, signal.SIGTERM):
    try:
        signal.signal(sig, _handle_signal)
    except (ValueError, OSError):
        # قد لا تكون بعض الإشارات متاحة على كل منصة (مثل Windows)
        pass


from pyrogram import idle

app.start()

app.loop.run_until_complete(startup())

logger.info("🤖 Bot Started...")

try:
    idle()
finally:
    app.loop.run_until_complete(shutdown())
    app.stop()
