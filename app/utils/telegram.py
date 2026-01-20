"""Telegram-related utilities."""

import re
from typing import List, Optional, Tuple

from aiogram.types import Message


def escape_html(text: str) -> str:
    """Escape HTML special characters for Telegram."""
    return (
        text
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def truncate_text(text: str, max_length: int = 100, suffix: str = "...") -> str:
    """Truncate text to max length with suffix."""
    if len(text) <= max_length:
        return text
    return text[:max_length - len(suffix)] + suffix


def parse_button_text(text: str) -> List[Tuple[str, str]]:
    """
    Parse button definitions from text.
    
    Supported formats:
    - "Button Text - https://example.com"
    - "Button Text | https://example.com"
    - Each button on a new line
    - Empty lines separate button rows
    
    Returns:
        List of (text, url) tuples
    """
    buttons = []
    lines = text.strip().split("\n")
    
    for line in lines:
        line = line.strip()
        if not line:
            continue
        
        # Try different separators
        for separator in [" - ", " | ", " — "]:
            if separator in line:
                parts = line.split(separator, 1)
                if len(parts) == 2:
                    btn_text = parts[0].strip()
                    btn_url = parts[1].strip()
                    
                    # Validate URL
                    if is_valid_url(btn_url):
                        buttons.append((btn_text, btn_url))
                break
    
    return buttons


def is_valid_url(url: str) -> bool:
    """Check if string is a valid URL for Telegram buttons."""
    url_pattern = re.compile(
        r"^https?://"  # http:// or https://
        r"(?:(?:[A-Z0-9](?:[A-Z0-9-]{0,61}[A-Z0-9])?\.)+[A-Z]{2,6}\.?|"  # domain
        r"localhost|"  # localhost
        r"\d{1,3}\.\d{1,3}\.\d{1,3}\.\d{1,3})"  # IP
        r"(?::\d+)?"  # optional port
        r"(?:/?|[/?]\S+)$",
        re.IGNORECASE
    )
    return bool(url_pattern.match(url))


def extract_message_text(message: Message) -> Optional[str]:
    """Extract text from message (text or caption)."""
    return message.text or message.caption


def format_post_preview_text(
    text: Optional[str],
    max_lines: int = 3,
    max_chars: int = 150,
) -> str:
    """Format post text for list preview."""
    if not text:
        return "<i>Без текста</i>"
    
    # Take first N lines
    lines = text.split("\n")[:max_lines]
    preview = "\n".join(lines)
    
    # Truncate if too long
    if len(preview) > max_chars:
        preview = preview[:max_chars] + "..."
    elif len(lines) < len(text.split("\n")):
        preview += "..."
    
    return escape_html(preview)


def get_media_type_emoji(media_type: str) -> str:
    """Get emoji for media type."""
    emojis = {
        "photo": "🖼",
        "video": "🎬",
        "document": "📎",
        "audio": "🎵",
        "animation": "🎞",
    }
    return emojis.get(media_type, "📁")
