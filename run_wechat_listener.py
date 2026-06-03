#!/usr/bin/env python3
"""Standalone WeChat message listener runner.

Connects to WeChat desktop via wxauto and bridges messages
to the DeerFlow AI customer service backend.

Requirements:
    - Windows OS with WeChat desktop running
    - wxauto installed: pip install wxauto
    - FastAPI backend running (default: http://localhost:8000)

Configuration (via .env or environment):
    WECHAT_API_URL        - Backend URL (default: http://localhost:8000)
    WECHAT_POLL_INTERVAL  - Seconds between checks (default: 2)
    WECHAT_MAX_RESPONSE_LEN - Max AI response length (default: 500)
    WECHAT_WATCH_TARGETS  - Comma-separated "chat:tenant:user" entries

Usage:
    # Configure in .env first, then:
    python run_wechat_listener.py

    # Or add targets interactively:
    python run_wechat_listener.py --interactive
"""

import argparse
import logging
import sys

from src.wechat.listener import WeChatListener, WeChatListenerConfig
from src.wechat.mock_client import MockWeChatClient

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(name)s] %(levelname)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
logger = logging.getLogger("wechat_runner")


def interactive_add_targets(listener: WeChatListener):
    """Interactively add watch targets via stdin."""
    print("\n=== WeChat Listener - Add Watch Targets ===")
    print("Enter contacts to monitor (empty line to start):\n")

    while True:
        chat_name = input("WeChat contact/group name: ").strip()
        if not chat_name:
            break

        tenant_id = input(f"  Tenant ID for '{chat_name}': ").strip()
        if not tenant_id:
            print("  Skipping (no tenant ID)")
            continue

        user_id = input(f"  User ID for '{chat_name}': ").strip()
        if not user_id:
            user_id = chat_name  # Default to chat name
            print(f"  Using chat name as user ID: {user_id}")

        listener.add_watch(chat_name, tenant_id, user_id)
        print(f"  Added: {chat_name} (tenant={tenant_id}, user={user_id})\n")

    if not listener._watch_targets:
        print("No targets added. Exiting.")
        sys.exit(0)


def main():
    parser = argparse.ArgumentParser(
        description="WeChat AI Customer Service Listener",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "--interactive", "-i",
        action="store_true",
        help="Interactively add watch targets",
    )
    parser.add_argument(
        "--api-url",
        type=str,
        default=None,
        help="FastAPI backend URL (overrides WECHAT_API_URL env)",
    )
    parser.add_argument(
        "--poll-interval",
        type=float,
        default=None,
        help="Poll interval in seconds (overrides WECHAT_POLL_INTERVAL env)",
    )
    parser.add_argument(
        "--mock", "-m",
        action="store_true",
        help="Use terminal-based mock client instead of wxauto (for macOS/Linux testing)",
    )
    parser.add_argument(
        "--chat-name",
        type=str,
        default="测试客户",
        help="Default chat name for mock mode (default: 测试客户)",
    )
    args = parser.parse_args()

    # Build listener from config
    config = WeChatListenerConfig()

    if args.api_url:
        config.api_url = args.api_url
    if args.poll_interval:
        config.poll_interval = args.poll_interval

    # Mock mode: use terminal client instead of wxauto
    mock_client = None
    if args.mock:
        mock_client = MockWeChatClient(default_chat=args.chat_name)
        listener = WeChatListener(
            api_base_url=config.api_url,
            poll_interval=config.poll_interval,
            max_response_length=config.max_response_len,
            client=mock_client,
        )
    else:
        listener = config.create_listener()

    # Interactive mode or env-configured targets
    if args.interactive:
        interactive_add_targets(listener)

    # Mock mode: auto-add a default target if none configured
    if args.mock and not listener._watch_targets:
        listener.add_watch(args.chat_name, "tenant_001", f"user_{args.chat_name}")

    if not listener._watch_targets:
        print("No watch targets configured.")
        print("Use --interactive or set WECHAT_WATCH_TARGETS in .env")
        print('Example: WECHAT_WATCH_TARGETS="客户A:tenant_001:user_a,客户B:tenant_001:user_b"')
        sys.exit(1)

    # Show configured targets
    mode = "MOCK (终端模拟)" if args.mock else "WXAUTO (微信桌面)"
    print(f"\nStarting listener [{mode}] with {len(listener._watch_targets)} target(s):")
    for name, target in listener._watch_targets.items():
        print(f"  - {name} (tenant={target.tenant_id}, user={target.user_id})")
    print(f"API: {listener.api_base_url}")
    print(f"Poll interval: {listener.poll_interval}s")
    print()

    # Run the listener (blocks)
    try:
        listener.run()
    except KeyboardInterrupt:
        print("\n[Runner] 收到中断信号，正在退出...")
    finally:
        if mock_client:
            mock_client.stop()


if __name__ == "__main__":
    main()
