"""Date/time parser for scheduling posts."""

import logging
from datetime import datetime, timedelta
from typing import Optional, Tuple

from dateutil import parser as dateutil_parser
from dateutil.relativedelta import relativedelta

from app.config import get_settings

logger = logging.getLogger(__name__)

# Russian day names
RUSSIAN_DAYS = {
    "сегодня": 0,
    "завтра": 1,
    "послезавтра": 2,
}


def get_timezone():
    """Get timezone from settings."""
    import pytz
    settings = get_settings()
    try:
        return pytz.timezone(settings.tz)
    except Exception:
        return pytz.UTC


def parse_datetime(text: str) -> Tuple[Optional[datetime], Optional[str]]:
    """
    Parse datetime from Russian text input.
    
    Supported formats:
    - "15:30" - today at 15:30
    - "завтра 15:30" - tomorrow at 15:30
    - "сегодня 15:30" - today at 15:30
    - "25.01 15:30" - specific date at 15:30
    - "25.01.2025 15:30" - specific date with year
    - "25 января 15:30" - Russian month name
    - "now" or "сейчас" - immediately
    
    Args:
        text: User input text
        
    Returns:
        Tuple of (parsed datetime or None, error message or None)
    """
    text = text.strip().lower()
    
    # Immediate publication
    if text in ("now", "сейчас", "немедленно"):
        return datetime.now(get_timezone()), None
    
    try:
        now = datetime.now(get_timezone())
        
        # Check for Russian day prefixes
        target_date = now.date()
        time_part = text
        
        for day_name, day_offset in RUSSIAN_DAYS.items():
            if text.startswith(day_name):
                target_date = now.date() + timedelta(days=day_offset)
                time_part = text[len(day_name):].strip()
                break
        
        # Try to parse time (HH:MM format)
        if ":" in time_part and len(time_part.split()) == 1:
            try:
                hours, minutes = map(int, time_part.split(":"))
                result = datetime.combine(
                    target_date,
                    datetime.min.time().replace(hour=hours, minute=minutes)
                )
                result = get_timezone().localize(result)
                
                # If time has passed today, schedule for tomorrow
                if result <= now and target_date == now.date():
                    result += timedelta(days=1)
                
                return result, None
            except ValueError:
                pass
        
        # Try to parse date + time (DD.MM HH:MM or DD.MM.YYYY HH:MM)
        parts = time_part.split()
        if len(parts) == 2:
            date_str, time_str = parts
            
            # Parse date
            date_parts = date_str.replace("/", ".").split(".")
            if len(date_parts) >= 2:
                day = int(date_parts[0])
                month = int(date_parts[1])
                year = int(date_parts[2]) if len(date_parts) > 2 else now.year
                
                # Parse time
                hours, minutes = map(int, time_str.split(":"))
                
                result = datetime(year, month, day, hours, minutes)
                result = get_timezone().localize(result)
                
                return result, None
        
        # Fallback to dateutil parser
        parsed = dateutil_parser.parse(text, dayfirst=True)
        if parsed.tzinfo is None:
            parsed = get_timezone().localize(parsed)
        return parsed, None
        
    except Exception as e:
        logger.debug(f"Failed to parse datetime '{text}': {e}")
        return None, (
            "❌ Не удалось распознать дату/время.\n\n"
            "Используйте формат:\n"
            "• <code>15:30</code> — сегодня\n"
            "• <code>завтра 15:30</code>\n"
            "• <code>25.01 15:30</code>\n"
            "• <code>сейчас</code> — опубликовать немедленно"
        )


def format_datetime(dt: datetime) -> str:
    """Format datetime for display in Russian."""
    now = datetime.now(get_timezone())
    
    if dt.date() == now.date():
        return f"сегодня в {dt.strftime('%H:%M')}"
    elif dt.date() == (now + timedelta(days=1)).date():
        return f"завтра в {dt.strftime('%H:%M')}"
    else:
        return dt.strftime("%d.%m.%Y в %H:%M")
