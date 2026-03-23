"""
supervisor/telegram_bridge.py — Telegram channel for Ouroboros.

Long-polling bot that mirrors messages to/from the existing message bus.
Runs as a daemon thread inside server.py.

Usage:
    bridge = TelegramBridge(
        token="...",
        allowed_chat_ids={233232566},
        message_bus_bridge=bus_bridge,  # LocalChatBridge instance
        on_incoming=callback,           # fn(chat_id, user_id, text)
    )
    bridge.start()
    ...
    bridge.stop()
"""

from __future__ import annotations

import json
import logging
import threading
import time
from typing import Any, Callable, Dict, Optional, Set

import urllib.request
import urllib.error
import urllib.parse

log = logging.getLogger(__name__)

_API_BASE = "https://api.telegram.org/bot{token}/{method}"
_POLL_TIMEOUT = 30      # seconds for long-poll
_RETRY_SLEEP = 5        # seconds between error retries
_MAX_MSG_LEN = 4096     # Telegram message limit


def _tg_request(
    token: str,
    method: str,
    params: Optional[Dict[str, Any]] = None,
    timeout: int = 35,
) -> Optional[Dict[str, Any]]:
    """Make a Telegram Bot API call. Returns parsed JSON or None on error."""
    url = _API_BASE.format(token=token, method=method)
    if params:
        data = json.dumps(params).encode("utf-8")
        req = urllib.request.Request(
            url,
            data=data,
            headers={"Content-Type": "application/json"},
        )
    else:
        req = urllib.request.Request(url)
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            return json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        body = ""
        try:
            body = exc.read().decode("utf-8")
        except Exception:
            pass
        log.warning("Telegram API %s HTTP %d: %s", method, exc.code, body)
    except Exception as exc:
        log.warning("Telegram API %s error: %s", method, exc)
    return None


def _split_message(text: str, limit: int = _MAX_MSG_LEN):
    """Yield chunks of `text` up to `limit` chars, splitting on newlines."""
    while len(text) > limit:
        cut = text.rfind("\n", 0, limit)
        if cut < limit // 2:
            cut = limit
        yield text[:cut]
        text = text[cut:]
    if text:
        yield text


class TelegramBridge:
    """Daemon thread that polls Telegram and routes messages to the agent."""

    def __init__(
        self,
        token: str,
        allowed_chat_ids: Set[int],
        on_incoming: Callable[[int, int, str], None],
    ):
        self._token = token
        self._allowed = allowed_chat_ids
        self._on_incoming = on_incoming
        self._offset = 0
        self._stop_event = threading.Event()
        self._thread: Optional[threading.Thread] = None
        self._outbox_thread: Optional[threading.Thread] = None
        # Queue for outgoing messages: (chat_id, text, parse_mode)
        import queue
        self._outbox: queue.Queue = queue.Queue()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def start(self) -> None:
        if self._thread and self._thread.is_alive():
            return
        self._stop_event.clear()
        self._thread = threading.Thread(
            target=self._poll_loop,
            name="telegram-poll",
            daemon=True,
        )
        self._outbox_thread = threading.Thread(
            target=self._send_loop,
            name="telegram-send",
            daemon=True,
        )
        self._thread.start()
        self._outbox_thread.start()
        log.info("TelegramBridge started (allowed_ids=%s)", self._allowed)

    def stop(self) -> None:
        self._stop_event.set()
        if self._thread:
            self._thread.join(timeout=5)
        if self._outbox_thread:
            self._outbox_thread.join(timeout=5)
        log.info("TelegramBridge stopped.")

    @property
    def is_running(self) -> bool:
        return bool(self._thread and self._thread.is_alive())

    def send_message(self, chat_id: int, text: str, parse_mode: str = "Markdown") -> None:
        """Queue a message to be sent to a Telegram chat."""
        self._outbox.put((chat_id, text, parse_mode))

    def send_photo(self, chat_id: int, photo_bytes: bytes, caption: str = "") -> None:
        """Send a photo to a Telegram chat (best-effort)."""
        self._outbox.put(("photo", chat_id, photo_bytes, caption))

    # ------------------------------------------------------------------
    # Internal threads
    # ------------------------------------------------------------------

    def _poll_loop(self) -> None:
        log.info("Telegram long-poll loop starting…")
        while not self._stop_event.is_set():
            try:
                result = _tg_request(
                    self._token,
                    "getUpdates",
                    params={"offset": self._offset, "timeout": _POLL_TIMEOUT,
                            "allowed_updates": ["message"]},
                    timeout=_POLL_TIMEOUT + 5,
                )
                if result is None:
                    self._stop_event.wait(_RETRY_SLEEP)
                    continue

                if not result.get("ok"):
                    log.warning("getUpdates not ok: %s", result)
                    self._stop_event.wait(_RETRY_SLEEP)
                    continue

                for upd in result.get("result", []):
                    self._offset = int(upd["update_id"]) + 1
                    self._handle_update(upd)

            except Exception:
                log.exception("Telegram poll loop error")
                self._stop_event.wait(_RETRY_SLEEP)

    def _send_loop(self) -> None:
        import queue
        while not self._stop_event.is_set():
            try:
                item = self._outbox.get(timeout=1)
            except queue.Empty:
                continue
            try:
                if isinstance(item, tuple) and item[0] == "photo":
                    _, chat_id, photo_bytes, caption = item
                    self._send_photo_now(chat_id, photo_bytes, caption)
                else:
                    chat_id, text, parse_mode = item
                    self._send_text_now(chat_id, str(text), parse_mode)
            except Exception:
                log.exception("Telegram send loop error")

    def _send_text_now(self, chat_id: int, text: str, parse_mode: str) -> None:
        for chunk in _split_message(text):
            params: Dict[str, Any] = {"chat_id": chat_id, "text": chunk}
            if parse_mode:
                params["parse_mode"] = parse_mode
            result = _tg_request(self._token, "sendMessage", params)
            # If Markdown parsing failed, retry as plain text
            if result and not result.get("ok") and parse_mode:
                params.pop("parse_mode", None)
                _tg_request(self._token, "sendMessage", params)

    def _send_photo_now(self, chat_id: int, photo_bytes: bytes, caption: str) -> None:
        # multipart/form-data upload
        import io, uuid as _uuid
        boundary = _uuid.uuid4().hex
        body = (
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="chat_id"\r\n\r\n'
            f"{chat_id}\r\n"
            f"--{boundary}\r\n"
            f'Content-Disposition: form-data; name="photo"; filename="photo.png"\r\n'
            f"Content-Type: image/png\r\n\r\n"
        ).encode("utf-8") + photo_bytes + (
            f"\r\n--{boundary}--\r\n"
        ).encode("utf-8")
        if caption:
            body = (
                f"--{boundary}\r\n"
                f'Content-Disposition: form-data; name="chat_id"\r\n\r\n'
                f"{chat_id}\r\n"
                f"--{boundary}\r\n"
                f'Content-Disposition: form-data; name="caption"\r\n\r\n'
                f"{caption}\r\n"
                f"--{boundary}\r\n"
                f'Content-Disposition: form-data; name="photo"; filename="photo.png"\r\n'
                f"Content-Type: image/png\r\n\r\n"
            ).encode("utf-8") + photo_bytes + (
                f"\r\n--{boundary}--\r\n"
            ).encode("utf-8")
        url = _API_BASE.format(token=self._token, method="sendPhoto")
        req = urllib.request.Request(
            url,
            data=body,
            headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        )
        try:
            with urllib.request.urlopen(req, timeout=30) as resp:
                pass
        except Exception as exc:
            log.warning("Telegram sendPhoto failed: %s", exc)

    def _handle_update(self, upd: Dict[str, Any]) -> None:
        msg = upd.get("message") or upd.get("edited_message")
        if not msg:
            return

        chat_id = int(msg["chat"]["id"])
        user_id = int(msg.get("from", {}).get("id", chat_id))
        text = msg.get("text") or ""

        if self._allowed and chat_id not in self._allowed:
            log.debug("Ignoring message from unauthorized chat_id=%d", chat_id)
            # Optionally send a polite rejection:
            _tg_request(self._token, "sendMessage", {
                "chat_id": chat_id,
                "text": "⛔ Unauthorized.",
            })
            return

        if not text:
            return

        log.info("Telegram ← chat=%d user=%d: %s", chat_id, user_id, text[:80])
        try:
            self._on_incoming(chat_id, user_id, text)
        except Exception:
            log.exception("on_incoming callback error")
