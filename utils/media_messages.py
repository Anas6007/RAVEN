from __future__ import annotations

from typing import Literal

from pyrogram.errors import MessageNotModified

MediaKind = Literal["photo", "video", "animation", "text", None]


def _kind(kind: str | None) -> str:
    if kind in {"photo", "video", "animation"}:
        return kind
    return "text"


async def send_media(
    client,
    *,
    chat_id: int,
    media_type: MediaKind,
    media_file_id: str | None,
    text: str,
    reply_markup=None,
):
    kind = _kind(media_type)

    if kind == "photo" and media_file_id:
        return await client.send_photo(
            chat_id=chat_id,
            photo=media_file_id,
            caption=text,
            reply_markup=reply_markup,
        )

    if kind == "video" and media_file_id:
        return await client.send_video(
            chat_id=chat_id,
            video=media_file_id,
            caption=text,
            reply_markup=reply_markup,
        )

    if kind == "animation" and media_file_id:
        return await client.send_animation(
            chat_id=chat_id,
            animation=media_file_id,
            caption=text,
            reply_markup=reply_markup,
        )

    return await client.send_message(
        chat_id=chat_id,
        text=text,
        reply_markup=reply_markup,
    )


async def edit_media_message(
    client,
    *,
    chat_id: int,
    message_id: int,
    media_type: MediaKind,
    text: str,
    reply_markup=None,
):
    kind = _kind(media_type)

    try:
        if kind == "photo":
            return await client.edit_message_caption(
                chat_id=chat_id,
                message_id=message_id,
                caption=text,
                reply_markup=reply_markup,
            )

        if kind == "video":
            return await client.edit_message_caption(
                chat_id=chat_id,
                message_id=message_id,
                caption=text,
                reply_markup=reply_markup,
            )

        if kind == "animation":
            return await client.edit_message_caption(
                chat_id=chat_id,
                message_id=message_id,
                caption=text,
                reply_markup=reply_markup,
            )

        return await client.edit_message_text(
            chat_id=chat_id,
            message_id=message_id,
            text=text,
            reply_markup=reply_markup,
        )

    except MessageNotModified:
        return None
