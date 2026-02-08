import re
from typing import Match

def _escape_plain_text(text: str) -> str:
    """Экранирует спецсимволы MarkdownV2, кроме тех, что используются в разметке."""
    return re.sub(r'([_*\[\]()~`>#+\-=|{}.!\\])', r'\\\1', text)

def _process_inline_code(match: Match) -> str:
    code = match.group(1)
    code = code.replace('`', '\\`')
    return f'`{code}`'

def _process_fenced_code(match: Match) -> str:
    code = match.group(2)
    code = re.sub(r'([_*\[\]()~`>#+\-=|{}.!\\])', r'\\\1', code)
    return f'```\n{code}\n```'

def _process_heading(match: Match) -> str:
    level = len(match.group(1))
    content = match.group(2).strip()
    content = _escape_plain_text(content)
    
    if level == 1:
        return f"🔴 *{content}*\n"
    elif level == 2:
        return f"🟠 *{content}*\n"
    elif level in (3, 4):
        return f"*{content}*\n"
    else:
        return f"_{content}_\n"

def _process_image(match: Match) -> str:
    alt = match.group(1)
    url = match.group(2)
    if url.startswith("tg://emoji?id="):
        return f"![{alt}]({url})"
    else:
        return f"[🖼 {alt}]({url})"

def _process_table_row(row: str) -> str:
    cells = [cell.strip() for cell in row.split('|')[1:-1]]
    escaped = [_escape_plain_text(cell) for cell in cells]
    return " | ".join(escaped)

def _process_table(match: Match) -> str:
    lines = match.group(0).strip().split('\n')
    if len(lines) < 2:
        return ""
    
    header = _process_table_row(lines[0])
    body = "\n".join(_process_table_row(line) for line in lines[2:] if line.strip())
    
    table_content = f"{header}\n{body}"
    return f"```\n{table_content}\n```"

def _process_latex_inline(match: Match) -> str:
    expr = match.group(1)
    expr = expr.replace("\\alpha", "α").replace("\\beta", "β").replace("\\sum", "∑")
    return f"`{expr}`"

def _process_latex_display(match: Match) -> str:
    expr = match.group(1)
    expr = expr.replace("\\alpha", "α").replace("\\beta", "β").replace("\\sum", "∑")
    return f"```\n{expr}\n```"

def markdown_to_telegram_v2(md_text: str) -> str:
    text = md_text
    
    text = re.sub(r'```(\w*)\n([\s\S]*?)\n```', _process_fenced_code, text)
    
    text = re.sub(r'^(#{1,6})\s+(.*)$', _process_heading, text, flags=re.MULTILINE)
    
    text = re.sub(r'\|\|(.*?)\|\|', r'||\1||', text)
    
    text = re.sub(r'~~(.*?)~~', r'~\1~', text)
    
    text = re.sub(r'\*\*(.*?)\*\*', r'*\1*', text)
    text = re.sub(r'__(.*?)__', r'*\1*', text)
    text = re.sub(r'\*(.*?)\*', r'_\1_', text)
    text = re.sub(r'_(.*?)_', r'_\1_', text)
    
    text = re.sub(r'!\[([^\]]*)\]\((tg://emoji[^)]+)\)', _process_image, text)
    text = re.sub(r'!\[([^\]]*)\]\(([^)]+)\)', _process_image, text)
    text = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'[\1](\2)', text)
    
    text = re.sub(r'`([^`]*)`', _process_inline_code, text)
    
    text = re.sub(r'^>\s+(.*)$', r'> \1', text, flags=re.MULTILINE)
    
    text = re.sub(r'^-\s+\[x\]\s+(.*)$', r'✅ \1', text, flags=re.MULTILINE)
    text = re.sub(r'^-\s+\[ \]\s+(.*)$', r'⬜ \1', text, flags=re.MULTILINE)
    
    text = re.sub(r'^---\s*$', r'⎯⎯⎯', text, flags=re.MULTILINE)
    
    text = re.sub(r'\\\((.*?)\\\)', _process_latex_inline, text)
    text = re.sub(r'\\\[(.*?)\\\]', _process_latex_display, text)
    
    text = re.sub(r'(\|[^\n]+\|\s*\n\|[-:\s|]+\|\s*\n(?:\|[^\n]+\|\s*\n)+)', _process_table, text)
    
    parts = re.split(
        r'(\|\|.*?\|\||~.*?~|\*.*?\*|_.*?_|`.*?`|```.*?```|\[.*?\]\(.*?\)|> .*?$)',
        text,
        flags=re.DOTALL | re.MULTILINE
    )
    
    result = []
    for part in parts:
        if re.match(r'^(\|\|.*?\|\||~.*?~|\*.*?\*|_.*?_|`.*?`|```.*?```|\[.*?\]\(.*?\)|> .*?$)', part, re.DOTALL):
            result.append(part)
        else:
            result.append(_escape_plain_text(part))
    
    return ''.join(result).strip()