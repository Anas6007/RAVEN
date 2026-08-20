"""
أدوات إرسال جماعي آمنة (تُستخدم أساسًا لإشعار الفائزين، وقابلة للاستخدام
لأي إرسال جماعي آخر لاحقًا).

المشكلة عند الحجم الكبير (آلاف السحوبات يوميًا / عشرات آلاف الفائزين):
تيليجرام يفرض حدًا لمعدل الإرسال، وإرسال رسائل خاصة متتالية بسرعة كبيرة
دون أي تحكم يؤدي عاجلًا لخطأ FloodWait (تيليجرام يطلب الانتظار X ثانية).
الكود القديم كان يتجاهل هذا الخطأ تمامًا (except Exception: pass) فتضيع
رسالة الفوز دون أي محاولة إعادة إرسال. هنا نعالج الأمر بثلاث خطوات:

1. تهدئة خفيفة بين كل رسالة وأخرى (لا داعي للإسراع بلا داعٍ).
2. عند FloodWait: الانتظار المدة المطلوبة فعليًا من تيليجرام ثم إعادة
   المحاولة (بدل إسقاط الرسالة).
3. أي خطأ آخر (المستخدم حظر البوت، لم يبدأ محادثة معه، إلخ) يُسجَّل
   ويُتجاوز فورًا دون انتظار، لأنه لن ينجح بإعادة المحاولة.
"""

import asyncio

from pyrogram.errors import FloodWait

from config import logger


# تهدئة صغيرة بين كل رسالة وأخرى ضمن نفس الدفعة، لتقليل احتمال FloodWait
# أصلًا بدل انتظار حدوثه ثم التعامل معه فقط.
DEFAULT_PACING_SECONDS = 0.05

# أقصى عدد محاولات عند FloodWait لنفس المستلم قبل التخلي عنه.
MAX_FLOODWAIT_RETRIES = 3


async def safe_send(send_coro_factory, *, context: str = ""):
    """
    يُنفّذ عملية إرسال واحدة (send_coro_factory هي دالة بلا وسائط تُرجع
    coroutine الإرسال، لأن الـ coroutine يُستهلك مرة واحدة فقط ولا يمكن
    إعادة تشغيله عند إعادة المحاولة). يُعيد المحاولة تلقائيًا عند
    FloodWait، ويتجاوز بصمت أي خطأ آخر غير قابل للإصلاح بإعادة المحاولة.

    يُرجع True عند نجاح الإرسال فعليًا، أو False إن فشل نهائيًا.
    """

    for attempt in range(MAX_FLOODWAIT_RETRIES + 1):

        try:
            await send_coro_factory()
            return True

        except FloodWait as e:

            if attempt >= MAX_FLOODWAIT_RETRIES:
                logger.warning(
                    f"[BROADCAST] FloodWait متكرر ({context}), تم "
                    "التخلي بعد عدة محاولات."
                )
                return False

            await asyncio.sleep(e.value + 1)

        except Exception as e:
            # مستخدم حظر البوت، لم يبدأ محادثة خاصة معه، حساب محذوف...
            # لا فائدة من إعادة المحاولة هنا.
            logger.debug(f"[BROADCAST] فشل إرسال ({context}): {e!r}")
            return False

    return False


async def notify_users(client, user_ids, build_kwargs, *, context: str = ""):
    """
    يرسل رسالة خاصة لكل مستخدم في user_ids بأمان (مع معالجة FloodWait
    وتهدئة خفيفة بين الرسائل)، دون إيقاف الدفعة كاملة إن فشل مستلم واحد.

    build_kwargs: دالة تأخذ user_id وتُرجع dict من وسائط
    client.send_message (مثل text)، لتسمح بتخصيص كل رسالة لو لزم.

    يُرجع عدد الرسائل التي نجح إرسالها فعليًا.
    """

    sent = 0

    for user_id in user_ids:

        kwargs = build_kwargs(user_id)

        ok = await safe_send(
            lambda: client.send_message(chat_id=user_id, **kwargs),
            context=f"{context} -> {user_id}",
        )

        if ok:
            sent += 1

        await asyncio.sleep(DEFAULT_PACING_SECONDS)

    return sent
