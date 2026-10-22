"""
Мост между Telegram ботом и AtlantSDK
Обеспечивает взаимодействие между компонентами
"""

import asyncio
import logging
from typing import Optional
from aiogram import Bot
from aiogram.exceptions import TelegramAPIError, TelegramBadRequest
from aiogram.utils.keyboard import InlineKeyboardBuilder

logger = logging.getLogger(__name__)


class Bridge:
    """Класс для взаимодействия между bot и atlant"""

    def __init__(self):
        self.telegram_bot: Optional[Bot] = None
        self.atlant_dispatcher = None
        self.bot_loop: Optional[asyncio.AbstractEventLoop] = None

    def set_telegram_bot(self, bot: Bot, loop: asyncio.AbstractEventLoop):
        """Установка Telegram бота и event loop"""
        self.telegram_bot = bot
        self.bot_loop = loop

    def set_atlant_dispatcher(self, dispatcher):
        """Установка AtlantSDK Dispatcher"""
        self.atlant_dispatcher = dispatcher

    def send_to_atlant(self, command: str):
        """Отправка команды в AtlantSDK"""
        if self.atlant_dispatcher:
            self.atlant_dispatcher.proccess_update(command)

    def _split_message(self, text: str, max_length: int = 4096) -> list:
        """Разбивает длинное сообщение на части (максимум 4096 символов для Telegram)"""
        if len(text) <= max_length:
            return [text]

        parts = []
        # Пытаемся разбить по абзацам (двойной перенос строки)
        paragraphs = text.split("\n\n")
        current_part = ""

        for para in paragraphs:
            # Если параграф сам по себе длиннее лимита, разбиваем по предложениям
            if len(para) > max_length:
                if current_part:
                    parts.append(current_part.strip())
                    current_part = ""

                # Разбиваем длинный параграф по предложениям
                sentences = para.split(". ")
                for sent in sentences:
                    sent_with_dot = sent + (". " if not sent.endswith(".") else " ")
                    if len(current_part) + len(sent_with_dot) > max_length:
                        if current_part:
                            parts.append(current_part.strip())
                        current_part = sent_with_dot
                    else:
                        current_part += sent_with_dot
            else:
                # Проверяем, поместится ли параграф в текущую часть
                separator = "\n\n" if current_part else ""
                if len(current_part) + len(separator) + len(para) > max_length:
                    if current_part:
                        parts.append(current_part.strip())
                    current_part = para
                else:
                    current_part += separator + para

        if current_part:
            parts.append(current_part.strip())

        # Проверяем, что все части не превышают лимит (на всякий случай)
        final_parts = []
        for part in parts:
            if len(part) > max_length:
                # Принудительно разбиваем по символам, если всё ещё слишком длинное
                for i in range(0, len(part), max_length - 100):  # -100 для запаса
                    final_parts.append(part[i : i + max_length - 100])
            else:
                final_parts.append(part)

        return final_parts

    def send_message_to_user(self, user_id: int, text: str, reply_markup=None):
        """Отправка сообщения пользователю через Telegram"""
        if not self.telegram_bot or not self.bot_loop:
            logger.warning(
                f"[Bridge] Bot or loop not initialized! bot={self.telegram_bot is not None}, loop={self.bot_loop is not None}"
            )
            return

        try:
            logger.info(
                f"[Bridge] Sending message to user {user_id}, text length: {len(text)}"
            )

            # Разбиваем на части, если сообщение слишком длинное
            parts = self._split_message(text)
            if len(parts) > 1:
                logger.debug(f"[Bridge] Message split into {len(parts)} parts")

            # Отправляем все части, клавиатуру добавляем только к последней
            for i, part in enumerate(parts):
                part_reply_markup = reply_markup if i == len(parts) - 1 else None

                future = asyncio.run_coroutine_threadsafe(
                    self.telegram_bot.send_message(
                        user_id, part, reply_markup=part_reply_markup
                    ),
                    self.bot_loop,
                )

                def on_done(fut, part_num=i, total=len(parts)):
                    try:
                        result = fut.result()
                        logger.info(
                            f"[Bridge] Message part {part_num + 1}/{total} sent successfully to user {user_id}, message_id: {result.message_id}"
                        )
                    except TelegramAPIError as e:
                        logger.error(
                            f"[Bridge] Telegram API error sending message part {part_num + 1} to user {user_id}: {e}",
                            exc_info=True,
                        )
                    except Exception as e:
                        logger.exception(
                            f"[Bridge] Unexpected error sending message part {part_num + 1} to user {user_id}: {e}"
                        )

                future.add_done_callback(on_done)

        except Exception as e:
            logger.exception(
                f"[Bridge] Error scheduling message to user {user_id}: {e}"
            )

    def edit_message(self, chat_id: int, message_id: int, text: str, reply_markup=None):
        """Редактирование сообщения пользователю через Telegram"""
        if not self.telegram_bot or not self.bot_loop:
            logger.warning(
                f"[Bridge] Bot or loop not initialized! bot={self.telegram_bot is not None}, loop={self.bot_loop is not None}"
            )
            return

        try:
            logger.info(
                f"[Bridge] Editing message {message_id} for user {chat_id}, text length: {len(text)}"
            )

            # Если сообщение слишком длинное, редактируем только первую часть, остальные отправляем новыми
            if len(text) > 4096:
                logger.debug(
                    f"[Bridge] Message too long ({len(text)} chars), splitting..."
                )
                parts = self._split_message(text)

                # Редактируем первое сообщение первой частью
                if parts:
                    future = asyncio.run_coroutine_threadsafe(
                        self.telegram_bot.edit_message_text(
                            parts[0],
                            chat_id=chat_id,
                            message_id=message_id,
                            reply_markup=reply_markup,
                        ),
                        self.bot_loop,
                    )

                    def on_edit_done(fut):
                        try:
                            result = fut.result()
                            logger.info(
                                f"[Bridge] Message edited successfully for user {chat_id}"
                            )
                        except TelegramBadRequest as e:
                            # Сообщение уже было изменено или удалено
                            logger.warning(
                                f"[Bridge] Cannot edit message {message_id} for user {chat_id}: {e}"
                            )
                        except TelegramAPIError as e:
                            logger.error(
                                f"[Bridge] Telegram API error editing message {message_id} for user {chat_id}: {e}",
                                exc_info=True,
                            )
                        except Exception as e:
                            logger.exception(
                                f"[Bridge] Unexpected error editing message {message_id} for user {chat_id}: {e}"
                            )

                    future.add_done_callback(on_edit_done)

                    # Отправляем остальные части как новые сообщения
                    for i, part in enumerate(parts[1:], 1):
                        # Клавиатуру добавляем только к последней части
                        part_reply_markup = (
                            reply_markup if i == len(parts) - 1 else None
                        )

                        future = asyncio.run_coroutine_threadsafe(
                            self.telegram_bot.send_message(
                                chat_id, part, reply_markup=part_reply_markup
                            ),
                            self.bot_loop,
                        )

                        def on_send_done(fut, part_num=i, total=len(parts)):
                            try:
                                result = fut.result()
                                logger.info(
                                    f"[Bridge] Additional message part {part_num + 1}/{total} sent to user {chat_id}"
                                )
                            except TelegramAPIError as e:
                                logger.error(
                                    f"[Bridge] Telegram API error sending additional part {part_num} to user {chat_id}: {e}",
                                    exc_info=True,
                                )
                            except Exception as e:
                                logger.exception(
                                    f"[Bridge] Unexpected error sending additional part {part_num} to user {chat_id}: {e}"
                                )

                        future.add_done_callback(on_send_done)
            else:
                # Обычное редактирование для коротких сообщений
                future = asyncio.run_coroutine_threadsafe(
                    self.telegram_bot.edit_message_text(
                        text,
                        chat_id=chat_id,
                        message_id=message_id,
                        reply_markup=reply_markup,
                    ),
                    self.bot_loop,
                )

                def on_done(fut):
                    try:
                        result = fut.result()
                        logger.info(
                            f"[Bridge] Message edited successfully for user {chat_id}"
                        )
                    except TelegramBadRequest as e:
                        # Сообщение уже было изменено или удалено
                        logger.warning(
                            f"[Bridge] Cannot edit message {message_id} for user {chat_id}: {e}"
                        )
                    except TelegramAPIError as e:
                        logger.error(
                            f"[Bridge] Telegram API error editing message {message_id} for user {chat_id}: {e}",
                            exc_info=True,
                        )
                    except Exception as e:
                        logger.exception(
                            f"[Bridge] Unexpected error editing message {message_id} for user {chat_id}: {e}"
                        )

                future.add_done_callback(on_done)

        except Exception as e:
            logger.exception(
                f"[Bridge] Error scheduling edit for message {message_id} to user {chat_id}: {e}"
            )

    def delete_message(self, chat_id: int, message_id: int):
        """Удаление сообщения через Telegram"""
        if not self.telegram_bot or not self.bot_loop:
            logger.warning(
                f"[Bridge] Bot or loop not initialized! bot={self.telegram_bot is not None}, loop={self.bot_loop is not None}"
            )
            return

        try:
            future = asyncio.run_coroutine_threadsafe(
                self.telegram_bot.delete_message(
                    chat_id=chat_id, message_id=message_id
                ),
                self.bot_loop,
            )

            def on_done(fut):
                try:
                    fut.result()
                    logger.debug(
                        f"[Bridge] Message {message_id} deleted for user {chat_id}"
                    )
                except TelegramBadRequest as e:
                    # Сообщение уже удалено
                    logger.debug(
                        f"[Bridge] Message {message_id} already deleted for user {chat_id}: {e}"
                    )
                except TelegramAPIError as e:
                    logger.error(
                        f"[Bridge] Telegram API error deleting message {message_id} for user {chat_id}: {e}",
                        exc_info=True,
                    )
                except Exception as e:
                    logger.exception(
                        f"[Bridge] Unexpected error deleting message {message_id} for user {chat_id}: {e}"
                    )

            future.add_done_callback(on_done)
        except Exception as e:
            logger.exception(
                f"[Bridge] Error scheduling delete for message {message_id} to user {chat_id}: {e}"
            )


# Глобальный экземпляр моста
bridge = Bridge()
