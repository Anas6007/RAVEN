"""
أدوات مساعدة لتعديل الرسائل بأمان.

المشكلة: Pyrogram/Telegram يرميان خطأ MessageNotModified عند محاولة تعديل
رسالة بنفس المحتوى/الأزرار الحالية تمامًا. هذا يحدث كثيرًا في هذا البوت
(مثلًا عند الضغط على "سحب الفائزين" ولا يتغيّر شكل الأزرار). بدل تكرار
try/except في كل مكان، نجمعها هنا في دوال آمنة تُرجع True عند نجاح
التعديل الفعلي أو False إن كانت الرسالة بلا تغيير (وليس هذا خطأ حقيقيًا).
"""

from pyrogram.errors import MessageNotModified


async def safe_edit_reply_markup(message, reply_markup):
    """يعدّل أزرار رسالة موجودة (message.edit_reply_markup) بأمان."""

    try:
        await message.edit_reply_markup(reply_markup=reply_markup)
        return True

    except MessageNotModified:
        return False


async def safe_edit_text(message, text, reply_markup=None):
    """
    يعدّل نص/تعليق رسالة موجودة بأمان.

    المشكلة الأساسية: message.edit_text() يفشل بخطأ من تيليجرام إن كانت
    الرسالة تحتوي على وسائط (صورة مثلًا) لأن رسائل الوسائط تُعدَّل عبر
    caption وليس text — وهذا بالضبط ما كان يسبب فشل نشر السحب مع صورة
    مرفقة. هنا نكتشف نوع الرسالة تلقائيًا ونستخدم الدالة الصحيحة، مع
    التقاط MessageNotModified في الحالتين.
    """

    is_media = bool(getattr(message, "media", None))

    try:

        if is_media:
            await message.edit_caption(caption=text, reply_markup=reply_markup)
        else:
            await message.edit_text(text, reply_markup=reply_markup)

        return True

    except MessageNotModified:
        return False


async def safe_client_edit_reply_markup(client, chat_id, message_id, reply_markup):
    """نسخة تستخدم client.edit_message_reply_markup مباشرة (بدون كائن message)."""

    try:
        await client.edit_message_reply_markup(
            chat_id=chat_id,
            message_id=message_id,
            reply_markup=reply_markup,
        )
        return True

    except MessageNotModified:
        return False
