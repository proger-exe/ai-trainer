"""
Утилиты для повторных попыток при ошибках
"""

import asyncio
import logging
from functools import wraps
from typing import Callable, TypeVar, ParamSpec

logger = logging.getLogger(__name__)

P = ParamSpec("P")
T = TypeVar("T")


def retry_on_failure(
    max_retries: int = 3,
    delay: float = 1.0,
    backoff: float = 2.0,
    exceptions: tuple = (Exception,),
):
    """
    Декоратор для повторных попыток при ошибках

    Args:
        max_retries: Максимальное количество попыток
        delay: Начальная задержка между попытками (секунды)
        backoff: Множитель для экспоненциальной задержки
        exceptions: Кортеж исключений, при которых нужно повторять попытки
    """

    def decorator(func: Callable[P, T]) -> Callable[P, T]:
        @wraps(func)
        async def async_wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            last_exception = None
            current_delay = delay

            for attempt in range(max_retries):
                try:
                    return await func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt < max_retries - 1:
                        logger.warning(
                            f"[Retry] Attempt {attempt + 1}/{max_retries} failed for {func.__name__}: {e}. "
                            f"Retrying in {current_delay}s..."
                        )
                        await asyncio.sleep(current_delay)
                        current_delay *= backoff
                    else:
                        logger.error(
                            f"[Retry] All {max_retries} attempts failed for {func.__name__}: {e}"
                        )

            # Если все попытки исчерпаны, пробрасываем последнее исключение
            raise last_exception

        @wraps(func)
        def sync_wrapper(*args: P.args, **kwargs: P.kwargs) -> T:
            last_exception = None
            current_delay = delay

            for attempt in range(max_retries):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exception = e
                    if attempt < max_retries - 1:
                        logger.warning(
                            f"[Retry] Attempt {attempt + 1}/{max_retries} failed for {func.__name__}: {e}. "
                            f"Retrying in {current_delay}s..."
                        )
                        import time

                        time.sleep(current_delay)
                        current_delay *= backoff
                    else:
                        logger.error(
                            f"[Retry] All {max_retries} attempts failed for {func.__name__}: {e}"
                        )

            raise last_exception

        # Определяем, является ли функция асинхронной
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator
