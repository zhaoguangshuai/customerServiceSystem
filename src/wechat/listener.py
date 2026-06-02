"""WeChat message listener - bridges wxauto messages to the DeerFlow chat API.

Polls configured WeChat contacts/groups for new messages, forwards them
to the FastAPI chat endpoint, and sends AI responses back via WeChat.

Usage:
    listener = WeChatListener(config)
    listener.add_watch("客户A", tenant_id="tenant_001", user_id="user_a")
    listener.run()  # Blocks, polling loop
"""

import asyncio
import logging
import time
from dataclasses import dataclass
from typing import Optional

import httpx

from src.wechat.client import WeChatClient, WeChatMessage

logger = logging.getLogger(__name__)


@dataclass
class WatchTarget:
    """A WeChat contact/group being monitored."""
    chat_name: str
    tenant_id: str
    user_id: str
    session_id: str  # Generated from tenant_id + user_id
    enabled: bool = True


class WeChatListener:
    """Polls WeChat for new messages and routes them through the AI pipeline.

    Configuration:
        api_base_url: FastAPI server URL (default: http://localhost:8000)
        poll_interval: Seconds between message checks (default: 2)
        max_response_length: Truncate AI responses longer than this (default: 500)
    """

    def __init__(
        self,
        api_base_url: str = "http://localhost:8000",
        poll_interval: float = 2.0,
        max_response_length: int = 500,
    ):
        self.client = WeChatClient()
        self.api_base_url = api_base_url.rstrip("/")
        self.poll_interval = poll_interval
        self.max_response_length = max_response_length
        self._watch_targets: dict[str, WatchTarget] = {}
        self._running = False

    def add_watch(
        self,
        chat_name: str,
        tenant_id: str,
        user_id: str,
        session_id: Optional[str] = None,
    ):
        """Add a WeChat contact/group to monitor.

        Args:
            chat_name: WeChat display name of the contact or group.
            tenant_id: Tenant ID for multi-tenant isolation.
            user_id: Customer user ID (can be WeChat nickname or custom ID).
            session_id: Optional session ID. Auto-generated if not provided.
        """
        if not session_id:
            session_id = f"{tenant_id}_{user_id}_{int(time.time())}"

        self._watch_targets[chat_name] = WatchTarget(
            chat_name=chat_name,
            tenant_id=tenant_id,
            user_id=user_id,
            session_id=session_id,
        )
        logger.info(f"Now watching: '{chat_name}' (tenant={tenant_id}, user={user_id})")

    def remove_watch(self, chat_name: str):
        """Stop monitoring a WeChat contact/group."""
        self._watch_targets.pop(chat_name, None)
        logger.info(f"Stopped watching: '{chat_name}'")

    async def _call_chat_api(self, target: WatchTarget, query: str) -> dict:
        """Call the FastAPI chat endpoint.

        Returns:
            Dict with 'answer', 'need_manual', 'manual_reason', 'sources'.
        """
        url = f"{self.api_base_url}/api/v1/jewelry/chat"
        payload = {
            "tenant_id": target.tenant_id,
            "user_id": target.user_id,
            "session_id": target.session_id,
            "query": query,
            "channel": "wechat",
        }

        async with httpx.AsyncClient(timeout=30.0) as http:
            resp = await http.post(url, json=payload)
            resp.raise_for_status()
            data = resp.json()

        if data.get("code") != 200:
            raise RuntimeError(f"Chat API error: {data}")

        return data["data"]

    def _format_response(self, result: dict) -> str:
        """Format the AI response for WeChat sending.

        Handles:
        - Truncating long responses
        - Appending handoff notice if needed
        - Cleaning up markdown that doesn't render in WeChat
        """
        answer = result.get("answer", "抱歉，暂时无法回答您的问题。")

        # Truncate if too long for WeChat readability
        if len(answer) > self.max_response_length:
            answer = answer[:self.max_response_length - 20] + "...\n\n[回复较长，已截断]"

        # Append handoff notice
        if result.get("need_manual"):
            reason = result.get("manual_reason", "")
            answer += f"\n\n---\n已转接人工客服，请稍候。({reason})"

        return answer

    def _process_message(self, target: WatchTarget, msg: WeChatMessage):
        """Process a single incoming message: call AI and send reply."""
        logger.info(f"Processing: [{target.chat_name}] {msg.sender}: {msg.content[:50]}")

        try:
            result = asyncio.run(self._call_chat_api(target, msg.content))
            reply = self._format_response(result)
        except Exception as e:
            logger.error(f"Chat API call failed: {e}")
            reply = "抱歉，系统暂时出现问题，请稍后再试。"

        success = self.client.send_message(target.chat_name, reply)
        if success:
            logger.info(f"Reply sent to '{target.chat_name}': {reply[:50]}...")
        else:
            logger.error(f"Failed to send reply to '{target.chat_name}'")

    def _poll_once(self):
        """Single poll cycle: check all watch targets for new messages."""
        for target in self._watch_targets.values():
            if not target.enabled:
                continue

            try:
                messages = self.client.get_new_messages(target.chat_name)
                for msg in messages:
                    if msg.is_text:
                        self._process_message(target, msg)
            except Exception as e:
                logger.error(f"Error polling '{target.chat_name}': {e}")

    def run(self):
        """Start the message listener loop.

        Connects to WeChat and polls for messages until stopped.
        This method blocks the calling thread.
        """
        if not self.client.start():
            logger.error("Cannot start listener: WeChat client connection failed")
            return

        if not self._watch_targets:
            logger.warning("No watch targets configured. Add targets with add_watch() before running.")
            return

        self._running = True
        logger.info(
            f"WeChat listener started. Watching {len(self._watch_targets)} target(s), "
            f"poll interval: {self.poll_interval}s"
        )

        try:
            while self._running:
                self._poll_once()
                self.client.cleanup_processed_ids()
                time.sleep(self.poll_interval)
        except KeyboardInterrupt:
            logger.info("Listener interrupted by user")
        finally:
            self._running = False
            self.client.stop()

    def stop(self):
        """Signal the listener to stop after the current poll cycle."""
        self._running = False
        logger.info("Listener stop requested")


class WeChatListenerConfig:
    """Load listener configuration from environment or .env file.

    Environment variables:
        WECHAT_API_URL: FastAPI server URL (default: http://localhost:8000)
        WECHAT_POLL_INTERVAL: Poll interval in seconds (default: 2)
        WECHAT_MAX_RESPONSE_LEN: Max response length (default: 500)
        WECHAT_WATCH_TARGETS: Comma-separated "chat_name:tenant_id:user_id" entries
    """

    def __init__(self):
        from dotenv import load_dotenv
        import os

        load_dotenv()

        self.api_url = os.getenv("WECHAT_API_URL", "http://localhost:8000")
        self.poll_interval = float(os.getenv("WECHAT_POLL_INTERVAL", "2"))
        self.max_response_len = int(os.getenv("WECHAT_MAX_RESPONSE_LEN", "500"))
        self._targets_raw = os.getenv("WECHAT_WATCH_TARGETS", "")

    def parse_targets(self) -> list[dict]:
        """Parse WECHAT_WATCH_TARGETS into a list of target dicts.

        Format: "客户A:tenant_001:user_a,客户B:tenant_001:user_b"
        """
        if not self._targets_raw:
            return []

        targets = []
        for entry in self._targets_raw.split(","):
            parts = entry.strip().split(":")
            if len(parts) >= 3:
                targets.append({
                    "chat_name": parts[0],
                    "tenant_id": parts[1],
                    "user_id": parts[2],
                })
            else:
                logger.warning(f"Invalid watch target format: '{entry}', expected 'chat_name:tenant_id:user_id'")

        return targets

    def create_listener(self) -> WeChatListener:
        """Create a WeChatListener from this configuration."""
        listener = WeChatListener(
            api_base_url=self.api_url,
            poll_interval=self.poll_interval,
            max_response_length=self.max_response_len,
        )

        for target in self.parse_targets():
            listener.add_watch(**target)

        return listener
