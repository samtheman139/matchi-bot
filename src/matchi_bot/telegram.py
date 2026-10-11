import httpx

MAX_MESSAGE_LEN = 4096


def send_message(token: str, chat_id: str, text: str) -> None:
    """Send an HTML-formatted message, split into chunks if it is too long."""
    chunks, current = [], ""
    for line in text.splitlines(keepends=True):
        if len(current) + len(line) > MAX_MESSAGE_LEN:
            chunks.append(current)
            current = ""
        current += line
    if current:
        chunks.append(current)

    for chunk in chunks:
        response = httpx.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": chat_id, "text": chunk, "parse_mode": "HTML", "disable_web_page_preview": True},
            timeout=20,
        )
        response.raise_for_status()
