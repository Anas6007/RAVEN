class GiveawayState:

    START = "start"

    # ربط القناة أو المجموعة
    WAITING_CHANNEL = "waiting_channel"
    WAITING_GROUP = "waiting_group"

    # اختيار نوع السحب
    WAITING_MODE = "waiting_mode"

    # إعدادات السحب التلقائي
    WAITING_AUTO_COUNT = "waiting_auto_count"
    WAITING_AUTO_TIME = "waiting_auto_time"

    # بيانات السحب
    WAITING_DESCRIPTION = "waiting_description"
    WAITING_WINNERS = "waiting_winners"

    # بيانات المسابقة
    WAITING_CONTESTANT_SLOTS = "waiting_contestant_slots"

    # الاشتراك الإجباري
    WAITING_REQUIRED_CHANNELS = "waiting_required_channels"

    # الحماية
    WAITING_CAPTCHA = "waiting_captcha"

    # قائمة الإعدادات بعد إدخال البيانات الأساسية
    SETTINGS_MENU = "settings_menu"

    # صورة/فيديو السحب
    WAITING_IMAGE = "waiting_image"

    # شرط التعليق
    WAITING_DISCUSSION_LINK = "waiting_discussion_link"

    # المعاينة
    WAITING_PREVIEW = "waiting_preview"

    # بعد النشر
    PUBLISHED = "published"

    # انتهاء السحب
    FINISHED = "finished"

    # تعديل السحب
    EDITING = "editing"
