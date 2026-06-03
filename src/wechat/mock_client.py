"""Terminal-based mock WeChat client for local development and testing.

Replaces wxauto on macOS/Linux by reading messages from stdin
and printing AI responses to stdout. Supports the same interface
as WeChatClient so it can be injected into WeChatListener.

Usage:
    python run_wechat_listener.py --mock
"""

import logging
import queue
import threading
import time
from dataclasses import dataclass, field

from src.wechat.client import WeChatMessage

logger = logging.getLogger(__name__)


class MockWeChatClient:
    """Terminal-based mock WeChat client.

    Reads user messages from stdin in a background thread,
    queues them for the listener to consume, and prints
    AI responses to stdout.
    """

    def __init__(self, default_chat: str = "测试客户"):
        self._connected = False
        self._processed_ids: set[str] = set()
        self._queue: queue.Queue[WeChatMessage] = queue.Queue()
        self._default_chat = default_chat
        self._input_thread: threading.Thread | None = None
        self._stop_event = threading.Event()

    def start(self) -> bool:
        """Start the mock client and begin reading from stdin."""
        self._connected = True
        self._stop_event.clear()

        self._input_thread = threading.Thread(
            target=self._read_input_loop, daemon=True
        )
        self._input_thread.start()

        print("\n" + "=" * 60)
        print("  WeChat Mock Client - 终端模拟模式")
        print("=" * 60)
        print(f"  默认对话: {self._default_chat}")
        print("  输入消息后按回车发送，AI 回复将显示在此终端")
        print("  输入 /quit 退出，/switch <名称> 切换对话")
        print("  输入 /status 查看当前状态")
        print("=" * 60 + "\n")
        return True

    @property
    def is_connected(self) -> bool:
        return self._connected

    def _read_input_loop(self):
        """Background thread: read lines from stdin and enqueue as messages."""
        while not self._stop_event.is_set():
            try:
                line = input()
            except EOFError:
                break

            line = line.strip()
            if not line:
                continue

            if line.lower() == "/quit":
                logger.info("Mock client received quit signal")
                self._stop_event.set()
                # Put a sentinel so the listener can detect shutdown
                break

            if line.lower().startswith("/switch "):
                new_chat = line[8:].strip()
                if new_chat:
                    self._default_chat = new_chat
                    print(f"[Mock] 切换对话: {new_chat}")
                continue

            if line.lower() == "/status":
                print(f"[Mock] 当前对话: {self._default_chat}")
                print(f"[Mock] 队列中消息数: {self._queue.qsize()}")
                print(f"[Mock] 已处理消息数: {len(self._processed_ids)}")
                continue

            msg = WeChatMessage(
                chat_name=self._default_chat,
                sender=self._default_chat,
                content=line,
                msg_type="text",
                timestamp=time.time(),
            )
            self._queue.put(msg)

    def get_new_messages(self, chat_name: str) -> list[WeChatMessage]:
        """Dequeue new messages for the given chat name."""
        messages = []
        while not self._queue.empty():
            try:
                msg = self._queue.get_nowait()
                if msg.chat_name == chat_name:
                    msg_id = f"mock_{msg.sender}_{msg.content}_{msg.timestamp}"
                    if msg_id not in self._processed_ids:
                        self._processed_ids.add(msg_id)
                        messages.append(msg)
            except queue.Empty:
                break
        return messages

    def send_message(self, chat_name: str, message: str) -> bool:
        """Print the AI response to stdout."""
        print(f"\n{'─' * 50}")
        print(f"[{chat_name}] AI回复:")
        print(f"{'─' * 50}")
        print(message)
        print(f"{'─' * 50}\n")
        return True

    def get_contacts(self) -> list[str]:
        return [self._default_chat]

    def cleanup_processed_ids(self, max_size: int = 10000):
        if len(self._processed_ids) > max_size:
            ids_list = list(self._processed_ids)
            self._processed_ids = set(ids_list[len(ids_list) // 2:])

    def stop(self):
        """Shut down the mock client."""
        self._stop_event.set()
        self._connected = False
        print("\n[Mock] 客户端已断开")

    @property
    def should_stop(self) -> bool:
        return self._stop_event.is_set()
