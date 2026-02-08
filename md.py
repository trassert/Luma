import re
from typing import List

# Спецсимволы MarkdownV2
MD_V2_CHARS = r'\_*[]()~`>#+-=|{}.!'

def _escape_outside_markup(text: str) -> str:
    """
    Экранирует спецсимволы MarkdownV2 ВНЕ разметки.
    Разметка: *...*, _..._, ~...~, ||...||, `...`, ```...```
    """
    # Шаблоны для поиска разметки (жадные, но корректные)
    patterns = [
        r'\|\|.*?\|\|',  # spoiler
        r'~.*?~',        # strikethrough
        r'\*.*?\*',      # bold
        r'_.*?_',        # italic
        r'`[^`]*`',      # inline code
        r'```[\s\S]*?```'  # fenced code
    ]
    
    # Находим все участки разметки
    markup_spans = []
    for pattern in patterns:
        for match in re.finditer(pattern, text):
            markup_spans.append((match.start(), match.end()))
    
    # Сортируем и объединяем перекрытия
    if not markup_spans:
        return re.sub(f'([{re.escape(MD_V2_CHARS)}])', r'\\\1', text)
    
    markup_spans.sort()
    merged = [markup_spans[0]]
    for start, end in markup_spans[1:]:
        last_start, last_end = merged[-1]
        if start <= last_end:
            merged[-1] = (last_start, max(last_end, end))
        else:
            merged.append((start, end))
    
    # Экранируем только вне разметки
    result = []
    last_end = 0
    for start, end in merged:
        # Экранируем текст до разметки
        plain = text[last_end:start]
        plain = re.sub(f'([{re.escape(MD_V2_CHARS)}])', r'\\\1', plain)
        result.append(plain)
        # Добавляем разметку как есть
        result.append(text[start:end])
        last_end = end
    
    # Экранируем остаток
    plain = text[last_end:]
    plain = re.sub(f'([{re.escape(MD_V2_CHARS)}])', r'\\\1', plain)
    result.append(plain)
    
    return ''.join(result)

def _convert_markdown_to_v2(md_text: str) -> str:
    """Конвертирует GitHub-стиль Markdown → Telegram MarkdownV2."""
    text = md_text
    
    # Заголовки
    def _heading_repl(m):
        level = len(m.group(1))
        content = m.group(2).strip()
        if level == 1: return "🔴 *{}*\n".format(_escape_outside_markup(content))
        elif level == 2: return "🟠 *{}*\n".format(_escape_outside_markup(content))
        elif level in (3, 4): return "*{}*\n".format(_escape_outside_markup(content))
        else: return "_{}_\n".format(_escape_outside_markup(content))
    
    text = re.sub(r'^(#{1,6})\s+(.*)$', _heading_repl, text, flags=re.MULTILINE)
    
    # Spoiler
    text = re.sub(r'\|\|(.*?)\|\|', r'||\1||', text)
    
    # Strikethrough
    text = re.sub(r'~~(.*?)~~', r'~\1~', text)
    
    # Bold / Italic
    text = re.sub(r'\*\*(.*?)\*\*', r'*\1*', text)
    text = re.sub(r'__(.*?)__', r'*\1*', text)
    text = re.sub(r'\*(.*?)\*', r'_\1_', text)
    text = re.sub(r'_(.*?)_', r'_\1_', text)
    
    # Код
    text = re.sub(r'`([^`]*)`', r'`\1`', text)
    text = re.sub(r'```(\w*)\n([\s\S]*?)\n```', r'```\n\2\n```', text)
    
    # Цитаты
    text = re.sub(r'^>\s+(.*)$', r'> \1', text, flags=re.MULTILINE)
    
    # Списки задач
    text = re.sub(r'^-\s+\[x\]\s+(.*)$', r'✅ \1', text, flags=re.MULTILINE)
    text = re.sub(r'^-\s+\[ \]\s+(.*)$', r'⬜ \1', text, flags=re.MULTILINE)
    
    # Горизонтальные линии
    text = re.sub(r'^---\s*$', r'⎯⎯⎯', text, flags=re.MULTILINE)
    
    # LaTeX (упрощённо)
    text = re.sub(r'\\\((.*?)\\\)', r'`\1`', text)
    text = re.sub(r'\\\[(.*?)\\\]', r'```\n\1\n```', text)
    
    # Ссылки и изображения
    text = re.sub(r'!\[([^\]]*)\]\((tg://emoji[^)]+)\)', r'![\1](\2)', text)
    text = re.sub(r'!\[([^\]]*)\]\(([^)]+)\)', r'[🖼 \1](\2)', text)
    text = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'[\1](\2)', text)
    
    # Таблицы → моноширинный блок
    def _table_repl(m):
        lines = m.group(0).strip().split('\n')
        if len(lines) < 2: return ""
        header = " | ".join(cell.strip() for cell in lines[0].split('|')[1:-1])
        body = "\n".join(
            " | ".join(cell.strip() for cell in line.split('|')[1:-1])
            for line in lines[2:] if line.strip()
        )
        table = f"{header}\n{body}"
        return f"```\n{table}\n```"
    
    text = re.sub(r'(\|[^\n]+\|\s*\n\|[-:\s|]+\|\s*\n(?:\|[^\n]+\|\s*\n)+)', _table_repl, text)
    
    return text

def markdown_to_telegram_v2(md_text: str) -> str:
    """Основная функция конвертации."""
    v2_text = _convert_markdown_to_v2(md_text)
    return _escape_outside_markup(v2_text)

def split_message_safe(text: str, max_length: int = 4096) -> List[str]:
    """
    Безопасный сплиттер для MarkdownV2.
    Разбивает ТОЛЬКО в местах, где нет активной разметки.
    """
    if len(text) <= max_length:
        return [text]
    
    parts = []
    current = ""
    
    # Разбиваем на токены: разметка и обычный текст
    tokens = re.findall(r'(\|\|.*?\|\||~.*?~|\*.*?\*|_.*?_|`[^`]*`|```[\s\S]*?```|.)', text)
    
    for token in tokens:
        test = current + token
        if len(test) > max_length:
            if current:
                parts.append(current)
                current = token
            else:
                # Токен сам длиннее лимита — дробим его как plain text
                subparts = _split_plain_token(token, max_length)
                if subparts:
                    parts.extend(subparts[:-1])
                    current = subparts[-1]
        else:
            current += token
    
    if current:
        parts.append(current)
    
    # Финальная проверка: экранируем любые остаточные спецсимволы
    safe_parts = []
    for part in parts:
        try:
            # Пробуем найти незакрытую разметку
            if _has_unbalanced_markup(part):
                # Если есть — отправляем как plain text
                safe_parts.append(re.sub(f'([{re.escape(MD_V2_CHARS)}])', r'\\\1', part))
            else:
                safe_parts.append(part)
        except Exception:
            safe_parts.append(re.sub(f'([{re.escape(MD_V2_CHARS)}])', r'\\\1', part))
    
    return safe_parts

def _split_plain_token(token: str, max_len: int) -> List[str]:
    """Дробит длинный токен (например, слово) на части."""
    if len(token) <= max_len:
        return [token]
    parts = []
    while token:
        if len(token) <= max_len:
            parts.append(token)
            break
        parts.append(token[:max_len])
        token = token[max_len:]
    return parts

def _has_unbalanced_markup(text: str) -> bool:
    """Проверяет, есть ли незакрытая разметка."""
    pairs = {'*': 0, '_': 0, '~': 0, '|': 0, '`': 0}
    i = 0
    while i < len(text):
        c = text[i]
        if c == '\\' and i + 1 < len(text):
            i += 2  # экранированный символ
            continue
        if c == '`':
            if i + 2 < len(text) and text[i:i+3] == '```':
                # fenced code — пропускаем до закрытия
                end = text.find('```', i+3)
                if end == -1:
                    return True
                i = end + 3
                continue
            else:
                pairs['`'] = (pairs['`'] + 1) % 2
        elif c in pairs:
            pairs[c] = (pairs[c] + 1) % 2
        i += 1
    return any(count != 0 for count in pairs.values())