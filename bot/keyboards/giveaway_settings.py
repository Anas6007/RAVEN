from pyrogram.types import InlineKeyboardMarkup, InlineKeyboardButton

from services.flow_labels import flow_noun


def settings_text(session) -> str:
    noun = flow_noun(session)
    is_competition = getattr(session, 'flow_kind', 'giveaway') == 'competition'

    captcha = '✅ مفعلة' if session.enable_captcha else '❌ غير مفعلة'
    channels_count = len(session.required_channels)
    comment_status = '✅ مفعّل' if getattr(session, 'require_comment', False) else '❌ غير مفعّل'
    approval_status = '✅ مفعّل' if getattr(session, 'require_approval', False) else '❌ غير مفعّل'
    notify_status = '✅ مفعّل' if getattr(session, 'notify_winner', False) else '❌ غير مفعّل'
    announce_status = '✅ مفعّل' if getattr(session, 'announce_winner', False) else '❌ غير مفعّل'
    image_status = '—' if is_competition else ('✅ مرفقة' if session.image else '❌ غير مرفقة')

    if session.mode == 'manual':
        mode = '🖐 يدوي'
    elif session.mode == 'auto':
        if session.auto_trigger == 'count' and session.auto_threshold:
            label = 'أصوات' if is_competition else 'مشاركين'
            mode = f'⏰ تلقائي (عند {session.auto_threshold} {label})'
        elif session.auto_trigger == 'time':
            if is_competition and session.end_date:
                mode = f'⏰ تلقائي (حتى {session.end_date:%Y-%m-%d %H:%M})'
            elif session.auto_hours:
                mode = f'⏰ تلقائي (بعد {session.auto_hours} ساعة)'
            else:
                mode = '⏰ تلقائي (لم يُحدد بعد)'
        else:
            mode = '⏰ تلقائي (لم يُحدد بعد)'
    else:
        mode = '⚠️ لم يتم التحديد بعد'

    if is_competition:
        seats = session.contestant_slots or 'غير محدد'
        return f"""
🏆 **إعدادات المسابقة**

━━━━━━━━━━━━━━━━━━

📝 الوصف: تم الحفظ ✅
🪑 مقاعد المتسابقين: {seats}

━━━━━━━━━━━━━━━━━━

🛡 الكابتشا: {captcha}
📢 قنوات الاشتراك الإجباري: {channels_count}
💬 شرط التعليق: {comment_status}
👤 قبول المشاركين: {approval_status}
🔔 إشعار الفوز: {notify_status}
📢 إعلان الفائز: {announce_status}
🎯 طريقة الانتهاء: {mode}

━━━━━━━━━━━━━━━━━━

اضبط الخيارات من الأزرار بالأسفل، ثم اضغط **متابعة** للمعاينة النهائية.
"""

    return f"""
⚙️ **إعدادات السحب**

━━━━━━━━━━━━━━━━━━

📝 الوصف: تم الحفظ ✅
👥 عدد الفائزين: {session.winners_count}

━━━━━━━━━━━━━━━━━━

🛡 الكابتشا: {captcha}
📢 قنوات الاشتراك الإجباري: {channels_count}
🖼 الصورة/الفيديو: {image_status}
💬 شرط التعليق: {comment_status}
🎯 طريقة السحب: {mode}

━━━━━━━━━━━━━━━━━━

اضبط الخيارات من الأزرار بالأسفل، ثم اضغط **متابعة** للمعاينة النهائية.
"""


def settings_menu(session) -> InlineKeyboardMarkup:
    is_competition = getattr(session, 'flow_kind', 'giveaway') == 'competition'

    rows = [
        [InlineKeyboardButton('🛡 الكابتشا' + (' ✅' if session.enable_captcha else ''), callback_data='settings_toggle_captcha')],
        [InlineKeyboardButton(f'📢 قنوات الاشتراك ({len(session.required_channels)})', callback_data='settings_manage_channels')],
    ]

    if not is_competition:
        image_label = '🖼 تغيير/حذف الوسائط' if session.image else '🖼 إضافة صورة/فيديو (اختياري)'
        rows.append([InlineKeyboardButton(image_label, callback_data='settings_manage_image')])

    rows.append([InlineKeyboardButton('💬 شرط التعليق' + (' ✅' if getattr(session, 'require_comment', False) else ''), callback_data='settings_manage_comment')])

    if is_competition:
        rows.append([InlineKeyboardButton('👤 قبول المشاركين' + (' ✅' if getattr(session, 'require_approval', False) else ''), callback_data='settings_toggle_approval')])
        rows.append([InlineKeyboardButton('🔔 إشعار الفوز' + (' ✅' if getattr(session, 'notify_winner', False) else ''), callback_data='settings_toggle_notify_winner')])
        rows.append([InlineKeyboardButton('📢 إعلان الفائز' + (' ✅' if getattr(session, 'announce_winner', False) else ''), callback_data='settings_toggle_announce_winner')])
        rows.append([
            InlineKeyboardButton('🎯 عند بلوغ عدد أصوات', callback_data='auto_by_count'),
            InlineKeyboardButton('🕒 عند وقت محدد', callback_data='auto_by_time'),
        ])
    else:
        rows.append([
            InlineKeyboardButton('🖐 سحب يدوي' + (' ✅' if session.mode == 'manual' else ''), callback_data='settings_manual_mode'),
            InlineKeyboardButton('⏰ سحب تلقائي' + (' ✅' if session.mode == 'auto' else ''), callback_data='settings_auto_mode'),
        ])

    rows.extend([
        [InlineKeyboardButton('➡️ متابعة (المعاينة)', callback_data='settings_continue')],
        [InlineKeyboardButton('❌ إلغاء', callback_data='cancel_giveaway')],
    ])

    return InlineKeyboardMarkup(rows)


def auto_mode_settings_menu(session) -> InlineKeyboardMarkup:
    is_competition = getattr(session, 'flow_kind', 'giveaway') == 'competition'
    if is_competition:
        return InlineKeyboardMarkup([
            [InlineKeyboardButton('🎯 عند بلوغ عدد أصوات', callback_data='auto_by_count')],
            [InlineKeyboardButton('🕒 عند وقت محدد', callback_data='auto_by_time')],
            [InlineKeyboardButton('⬅️ رجوع للإعدادات', callback_data='settings_back')],
        ])

    return InlineKeyboardMarkup([
        [InlineKeyboardButton('🔢 عند وصول عدد المشاركين', callback_data='auto_by_count')],
        [InlineKeyboardButton('⏰ عند وقت محدد', callback_data='auto_by_time')],
        [InlineKeyboardButton('⬅️ رجوع للإعدادات', callback_data='settings_back')],
    ])


def back_to_settings_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([[InlineKeyboardButton('⬅️ رجوع للإعدادات', callback_data='settings_back')]])


def image_manage_keyboard(has_image: bool) -> InlineKeyboardMarkup:
    rows = []
    if has_image:
        rows.append([InlineKeyboardButton('🗑 حذف الصورة الحالية', callback_data='settings_remove_image')])
    rows.append([InlineKeyboardButton('⬅️ رجوع للإعدادات', callback_data='settings_back')])
    return InlineKeyboardMarkup(rows)


def channels_manage_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup([
        [InlineKeyboardButton('📂 عرض القنوات المضافة', callback_data='settings_show_channels')],
        [InlineKeyboardButton('🗑 حذف جميع القنوات', callback_data='settings_clear_channels')],
        [InlineKeyboardButton('⬅️ رجوع للإعدادات', callback_data='settings_back')],
    ])
