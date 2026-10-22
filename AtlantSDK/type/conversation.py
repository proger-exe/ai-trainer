import logging
import google.generativeai as gemini
from AtlantSDK.utils.clear_md import clean_text

logger = logging.getLogger(__name__)


class Conversation:
    def __init__(self, model):
        self.model = model
        self.chat = self._get_chat()
        self.history = {}

    def _get_chat(self) -> gemini.ChatSession:
        """
        Get chat method

        Returns:
            ChatSession
        """
        model = gemini.GenerativeModel(
            model_name=self.model.model,
            system_instruction=self.model.system_instruction,
            generation_config=self.model.generation_setting.make_to_json(),
        )

        return model.start_chat()

    def send_command(self, command: str) -> str:
        # Отправляем сообщение с увеличенным таймаутом (120 секунд)
        # и отключенным streaming для получения полного ответа
        try:
            result = self.chat.send_message(
                command,
                request_options={"timeout": 120},  # Таймаут 120 секунд (2 минуты)
            )

            # Получаем полный текст ответа
            full_text = result.text if hasattr(result, "text") else str(result)

            # Логируем длину ответа для отладки
            logger.debug(
                f"[Conversation] Received response, length: {len(full_text)} chars"
            )
            if len(full_text) > 1000:
                logger.debug(
                    f"[Conversation] Response preview (first 500 chars): {full_text[:500]}..."
                )
                logger.debug(
                    f"[Conversation] Response preview (last 500 chars): ...{full_text[-500:]}"
                )

            cleaned = clean_text(full_text).strip()
            logger.debug(
                f"[Conversation] Cleaned response length: {len(cleaned)} chars"
            )

            return cleaned

        except Exception as e:
            logger.exception(f"[Conversation] Error in send_command: {e}")
            raise
