"""Phone number authorization service."""

import logging
import re

logger = logging.getLogger(__name__)


class AuthService:
    """
    Phone number authorization service.

    Following Ousterhout's "define errors out of existence" principle,
    is_authorized() returns a boolean and never raises exceptions.
    """

    def __init__(self, allowed_numbers: list[str]):
        """
        Initialize with allowed phone numbers.

        Args:
            allowed_numbers: List of allowed phone numbers in E.164 format.
                             Empty list means open mode (allow all).
        """
        self._allowed = {self._normalize(n) for n in allowed_numbers if n}
        self._open_mode = len(self._allowed) == 0

        if self._open_mode:
            logger.info("AuthService initialized in OPEN mode (all numbers allowed)")
        else:
            logger.info(f"AuthService initialized with {len(self._allowed)} allowed numbers")

    def is_authorized(self, phone_number: str) -> bool:
        """
        Check if phone number is authorized.

        Returns True if:
        - Open mode (no allowlist configured), OR
        - Phone number is in allowlist

        Never raises exceptions.
        """
        if self._open_mode:
            return True

        normalized = self._normalize(phone_number)
        authorized = normalized in self._allowed

        if not authorized:
            logger.warning(f"Unauthorized message attempt from {phone_number}")

        return authorized

    @staticmethod
    def _normalize(phone: str) -> str:
        """
        Normalize phone number for comparison.

        Removes all non-digit characters except leading +.
        """
        if not phone:
            return ""

        # Keep only digits and leading +
        phone = phone.strip()
        if phone.startswith("+"):
            return "+" + re.sub(r"[^\d]", "", phone[1:])
        return re.sub(r"[^\d]", "", phone)
