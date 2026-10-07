import re
import html
import logging
from typing import Optional

logger = logging.getLogger("agrikural.tts.processor")

def strip_markdown_for_tts(text: str, language: str = "en", expand_percent: bool = False) -> str:
    """
    Converts AI Markdown responses into clean plain text for natural TTS voice synthesis.
    Strips formatting characters (*, _, #, -, `, >, []) while preserving human-readable text.
    Ensures natural pauses by inserting sentence periods for headings and list items.
    """
    if not text:
        return ""

    # 1. Strip fenced code blocks completely
    cleaned = re.sub(r'```[\s\S]*?```', '', text)
    # Remove inline code backticks: `foo` -> foo
    cleaned = re.sub(r'`([^`\n]+)`', r'\1', cleaned)

    # 2. Strip HTML tags and decode entities
    cleaned = re.sub(r'<br\s*/?>', '\n', cleaned, flags=re.IGNORECASE)
    cleaned = re.sub(r'<[^>]+>', '', cleaned)
    cleaned = html.unescape(cleaned)

    # 3. Strip images and format links: [link text](url) -> link text
    cleaned = re.sub(r'!\[([^\]]*)\]\([^)]+\)', '', cleaned)
    cleaned = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', cleaned)

    # 4. Strip inline formatting markers (bold, italic, strikethrough)
    # Bold-italic
    cleaned = re.sub(r'\*\*\*(.+?)\*\*\*', r'\1', cleaned)
    cleaned = re.sub(r'___(.+?)___', r'\1', cleaned)
    # Bold
    cleaned = re.sub(r'\*\*(.+?)\*\*', r'\1', cleaned)
    cleaned = re.sub(r'__(.+?)__', r'\1', cleaned)
    # Italic
    cleaned = re.sub(r'\*(.+?)\*', r'\1', cleaned)
    cleaned = re.sub(r'_(.+?)_', r'\1', cleaned)
    # Strikethrough
    cleaned = re.sub(r'~~(.+?)~~', r'\1', cleaned)

    # 5. Process line by line for structural blocks (headings, lists, quotes)
    lines = cleaned.split('\n')
    processed_paragraphs = []
    current_para = []

    for line in lines:
        stripped_line = line.strip()
        if not stripped_line:
            if current_para:
                processed_paragraphs.append(' '.join(current_para))
                current_para = []
            continue

        # Horizontal rules
        if re.match(r'^[\s\-_*]{3,}$', stripped_line):
            continue

        # Headings: # Heading
        heading_match = re.match(r'^#{1,6}\s*(.+)$', stripped_line)
        if heading_match:
            if current_para:
                processed_paragraphs.append(' '.join(current_para))
                current_para = []
            h_text = heading_match.group(1).strip()
            if not h_text.endswith(('.', '!', '?', ':', ';')):
                h_text += '.'
            processed_paragraphs.append(h_text)
            continue

        # Blockquotes: > quote
        if stripped_line.startswith('>'):
            stripped_line = re.sub(r'^>\s*', '', stripped_line).strip()

        # Bullet list items: - item, * item, + item, • item (must have whitespace after bullet marker)
        bullet_match = re.match(r'^[\s]*(?:[-+•]|\*(?!\*))\s+(.+)$', stripped_line)
        if bullet_match:
            if current_para:
                processed_paragraphs.append(' '.join(current_para))
                current_para = []
            b_text = bullet_match.group(1).strip()
            if not b_text.endswith(('.', '!', '?', ':', ';')):
                b_text += '.'
            processed_paragraphs.append(b_text)
            continue

        # Numbered list items: 1. item
        num_match = re.match(r'^[\s]*(\d+)\.\s*(.+)$', stripped_line)
        if num_match:
            if current_para:
                processed_paragraphs.append(' '.join(current_para))
                current_para = []
            num = num_match.group(1)
            n_text = num_match.group(2).strip()
            if not n_text.endswith(('.', '!', '?', ':', ';')):
                n_text += '.'
            processed_paragraphs.append(f"{num}. {n_text}")
            continue

        # Regular text line
        current_para.append(stripped_line)

    if current_para:
        processed_paragraphs.append(' '.join(current_para))

    # Rejoin paragraphs with double newlines
    result_text = '\n\n'.join(processed_paragraphs)

    # Ensure individual paragraphs end with terminal punctuation
    paragraphs = result_text.split('\n\n')
    cleaned_paras = []
    for p in paragraphs:
        p = p.strip()
        if p and not p.endswith(('.', '!', '?', ':', ';')):
            p += '.'
        if p:
            cleaned_paras.append(p)
    result_text = '\n\n'.join(cleaned_paras)

    # 6. Units and symbols expansion
    lang_lower = (language or "en").lower()
    if lang_lower == 'en':
        result_text = re.sub(r'(?<=\d)\s*(?:°\s*C|℃)\b', ' degrees Celsius', result_text)
        result_text = re.sub(r'(?:°\s*C|℃)\b', 'degrees Celsius', result_text)
        result_text = re.sub(r'(?<=\d)\s*(?:°\s*F|℉)\b', ' degrees Fahrenheit', result_text)
        if expand_percent:
            result_text = re.sub(r'(\d+(?:\.\d+)?)\s*%', r'\1 percent', result_text)
    elif lang_lower == 'ta':
        result_text = re.sub(r'(?<=\d)\s*(?:°\s*C|℃)\b', ' டிகிரி செல்சியஸ்', result_text)
        result_text = re.sub(r'(?:°\s*C|℃)\b', 'டிகிரி செல்சியஸ்', result_text)
        if expand_percent:
            result_text = re.sub(r'(\d+(?:\.\d+)?)\s*%', r'\1 சதவீதம்', result_text)
    elif lang_lower == 'ml':
        result_text = re.sub(r'(?<=\d)\s*(?:°\s*C|℃)\b', ' ഡിഗ്രി സെൽഷ്യസ്', result_text)
        result_text = re.sub(r'(?:°\s*C|℃)\b', 'ഡിഗ്രി സെൽഷ്യസ്', result_text)
        if expand_percent:
            result_text = re.sub(r'(\d+(?:\.\d+)?)\s*%', r'\1 ശതമാനം', result_text)

    # Clean up whitespace
    result_text = re.sub(r'[ \t]+', ' ', result_text)
    result_text = re.sub(r'\n{3,}', '\n\n', result_text)
    return result_text.strip()


class TTSTextProcessor:
    """
    Dedicated processor for sanitizing and stripping Markdown formatting
    before speech synthesis while keeping the original Markdown intact for UI rendering.
    """

    def clean_for_tts(self, text: str, language: str = "en", expand_percent: bool = False) -> str:
        clean = strip_markdown_for_tts(text, language=language, expand_percent=expand_percent)
        logger.debug(f"Stripped Markdown for TTS ({language}): before={len(text)} chars, after={len(clean)} chars")
        return clean


tts_processor = TTSTextProcessor()
