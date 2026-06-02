"""wxauto WeChat desktop client wrapper.

Provides a clean interface over the wxauto library for:
- Receiving messages from WeChat contacts/groups
- Sending reply messages back
- Tracking processed messages to avoid duplicates

Requires: Windows + WeChat desktop running.
"""

import logging
import time
from dataclasses import dataclass, field
from typing import Optional

logger = logging.getLogger(__name__)


@dataclass
class WeChatMessage:
    """Represents a single WeChat message."""
    chat_name: str          # Contact or group name
    sender: str             # Message sender
    content: str            # Message text content
    msg_type: str = "text"  # text, image, file, etc.
    timestamp: float = field(default_factory=time.time)

    @property
    def is_text(self) -> bool:
        return self.msg_type == "text"

    def __str__(self) -> str:
        return f"[{self.chat_name}] {self.sender}: {self.content[:50]}"


class WeChatClient:
    """Wrapper around wxauto.WeChat for desktop message automation.

    Usage:
        client = WeChatClient()
        client.start()
        messages = client.get_new_messages("客户昵称")
        client.send_message("客户昵称", "您好，请问有什么可以帮助您？")
    """

    def __init__(self):
        self._wx = None
        self._connected = False
        self._processed_ids: set[str] = set()

    def start(self) -> bool:
        """Initialize connection to WeChat desktop.

        Returns True if successfully connected to running WeChat instance.
        """
        try:
            from wxauto import WeChat
            self._wx = WeChat()
            self._connected = True
            logger.info("WeChat client connected successfully")
            return True
        except ImportError:
            logger.error(
                "wxauto not installed. Install with: pip install wxauto\n"
                "Note: wxauto only works on Windows with WeChat desktop running."
            )
            return False
        except Exception as e:
            logger.error(f"Failed to connect to WeChat desktop: {e}")
            return False

    @property
    def is_connected(self) -> bool:
        return self._connected and self._wx is not None

    def get_new_messages(self, chat_name: str) -> list[WeChatMessage]:
        """Get new (unprocessed) messages from a specific chat.

        Args:
            chat_name: The WeChat contact or group name to read from.

        Returns:
            List of new WeChatMessage objects since last call.
        """
        if not self.is_connected:
            logger.warning("WeChat client not connected")
            return []

        try:
            # Switch to the target chat
            self._wx.ChatWith(chat_name)
            time.sleep(0.3)

            # Get recent messages
            raw_messages = self._wx.GetAllMessage()
            new_messages = []

            for msg in raw_messages:
                # wxauto returns message objects with id, sender, content, type
                msg_id = getattr(msg, "id", None) or f"{chat_name}_{msg.sender}_{msg.content}_{msg.timestamp}"

                if msg_id in self._processed_ids:
                    continue

                # Skip system messages and self-sent messages
                msg_type = getattr(msg, "type", "text")
                sender = getattr(msg, "sender", "unknown")
                content = getattr(msg, "content", "")

                if msg_type == "sys" or not content:
                    self._processed_ids.add(msg_id)
                    continue

                wx_msg = WeChatMessage(
                    chat_name=chat_name,
                    sender=sender,
                    content=content,
                    msg_type=msg_type,
                )
                new_messages.append(wx_msg)
                self._processed_ids.add(msg_id)

            return new_messages

        except Exception as e:
            logger.error(f"Error getting messages from '{chat_name}': {e}")
            return []

    def send_message(self, chat_name: str, message: str) -> bool:
        """Send a text message to a contact or group.

        Args:
            chat_name: The WeChat contact or group name.
            message: The text message to send.

        Returns:
            True if message was sent successfully.
        """
        if not self.is_connected:
            logger.warning("WeChat client not connected")
            return False

        try:
            self._wx.ChatWith(chat_name)
            time.sleep(0.3)
            self._wx.SendMsg(message, chat_name)
            logger.info(f"Message sent to '{chat_name}': {message[:50]}...")
            return True
        except Exception as e:
            logger.error(f"Failed to send message to '{chat_name}': {e}")
            return False

    def get_contacts(self) -> list[str]:
        """Get list of recent chat contacts.

        Returns:
            List of contact/group names.
        """
        if not self.is_connected:
            return []

        try:
            return self._wx.GetRecentChat()
        except Exception as e:
            logger.error(f"Error getting contacts: {e}")
            return []

    def cleanup_processed_ids(self, max_size: int = 10000):
        """Clear processed message IDs to prevent memory growth.

        Keeps the most recent half when max_size is exceeded.
        """
        if len(self._processed_ids) > max_size:
            ids_list = list(self._processed_ids)
            self._processed_ids = set(ids_list[len(ids_list) // 2:])
            logger.info(f"Cleaned up processed IDs, kept {len(self._processed_ids)}")

    def stop(self):
        """Disconnect from WeChat."""
        self._wx = None
        self._connected = False
        logger.info("WeChat client disconnected")
