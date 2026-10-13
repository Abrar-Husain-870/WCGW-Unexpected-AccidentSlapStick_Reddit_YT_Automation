import re
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont

import config
from src.logger import logger
from src.reddit.models import RedditPost


def _wrap_text(text: str, draw: ImageDraw.ImageDraw, font: ImageFont.FreeTypeFont, max_width: int) -> list[str]:
    """Wrap text to fit within a maximum width in pixels."""
    words = text.split()
    lines = []
    current_line = []
    
    for word in words:
        current_line.append(word)
        line_str = " ".join(current_line)
        # Get width of current line
        bbox = draw.textbbox((0, 0), line_str, font=font)
        w = bbox[2] - bbox[0]
        
        if w > max_width:
            if len(current_line) == 1:
                # Word itself is too long, force split it
                lines.append(line_str)
                current_line = []
            else:
                current_line.pop()
                lines.append(" ".join(current_line))
                current_line = [word]
                
    if current_line:
        lines.append(" ".join(current_line))
        
    return lines


def generate_reddit_card(post: RedditPost) -> Path:
    """
    Generate a beautiful dark mode Reddit post card overlay.
    Returns the path to the saved transparent PNG image.
    """
    output_path = config.OUTPUT_DIR / "reddit_card.png"
    
    # ── Dimensions & Padding ─────────────────────────────────
    card_width = 900
    padding = 40
    
    # Fonts loading with fallbacks
    try:
        # Try loading standard windows / unix sans fonts
        font_title = ImageFont.truetype("arialbd.ttf", 36)
        font_meta = ImageFont.truetype("arial.ttf", 24)
        font_meta_bold = ImageFont.truetype("arialbd.ttf", 24)
    except Exception:
        try:
            font_title = ImageFont.truetype("DejaVuSans-Bold.ttf", 36)
            font_meta = ImageFont.truetype("DejaVuSans.ttf", 24)
            font_meta_bold = ImageFont.truetype("DejaVuSans-Bold.ttf", 24)
        except Exception:
            # Absolute fallback
            font_title = ImageFont.load_default()
            font_meta = ImageFont.load_default()
            font_meta_bold = ImageFont.load_default()

    # Pre-render wrap to calculate dynamic height
    temp_img = Image.new("RGBA", (card_width, 100))
    temp_draw = ImageDraw.Draw(temp_img)
    
    max_text_width = card_width - (padding * 2)
    wrapped_title = _wrap_text(post.title, temp_draw, font_title, max_text_width)
    
    # Title height estimation
    line_spacing = 8
    title_height = 0
    for line in wrapped_title:
        bbox = temp_draw.textbbox((0, 0), line, font=font_title)
        h = bbox[3] - bbox[1]
        title_height += h + line_spacing
    title_height = max(title_height - line_spacing, 40)
    
    # Header: 60px, Footer: 50px, Padding/Spacing: 100px
    card_height = 60 + title_height + 50 + (padding * 2) + 20
    
    # ── Draw Card ────────────────────────────────────────────
    # Transparent canvas
    canvas = Image.new("RGBA", (card_width, card_height), (0, 0, 0, 0))
    draw = ImageDraw.Draw(canvas)
    
    # Colors
    bg_color = (26, 26, 27, 240)        # Reddit Dark Mode Background (#1A1A1B, 94% opaque)
    reddit_orange = (255, 69, 0, 255)   # #FF4500
    text_white = (255, 255, 255, 255)   # #FFFFFF
    text_gray = (120, 124, 126, 255)    # #787C7E
    border_gray = (52, 53, 54, 255)     # #343536
    
    # Draw rounded background
    draw.rounded_rectangle(
        [(0, 0), (card_width, card_height)],
        radius=20,
        fill=bg_color,
        outline=border_gray,
        width=2
    )
    
    # 1. Header (Subreddit Badge, Subreddit Name, Author, Timestamp)
    y_cursor = padding
    
    if config.OVERLAY_PROFILE_ICON:
        # Draw circular orange badge placeholder
        badge_radius = 20
        badge_center = (padding + badge_radius, y_cursor + badge_radius)
        draw.ellipse(
            [(badge_center[0] - badge_radius, badge_center[1] - badge_radius),
             (badge_center[0] + badge_radius, badge_center[1] + badge_radius)],
            fill=reddit_orange
        )
        # Draw small 'r/' text on badge
        draw.text(
            (badge_center[0] - 8, badge_center[1] - 12),
            "r",
            font=font_meta_bold,
            fill=text_white
        )
        x_cursor = padding + (badge_radius * 2) + 15
    else:
        x_cursor = padding
        
    # Subreddit Name
    sub_tag = f"r/{post.subreddit}" if config.OVERLAY_SUBREDDIT_TAG else "r/Reddit"
    draw.text((x_cursor, y_cursor + 6), sub_tag, font=font_meta_bold, fill=text_white)
    
    # Get width of subreddit tag to align u/author
    sub_bbox = draw.textbbox((0, 0), sub_tag, font=font_meta_bold)
    sub_w = sub_bbox[2] - sub_bbox[0]
    
    # Author and Meta info
    meta_text = f" • Posted by u/{post.author}"
    draw.text(
        (x_cursor + sub_w + 5, y_cursor + 6),
        meta_text,
        font=font_meta,
        fill=text_gray
    )
    
    y_cursor += 65  # Advance below header
    
    # 2. Post Title
    for line in wrapped_title:
        draw.text((padding, y_cursor), line, font=font_title, fill=text_white)
        # Compute height of line
        bbox = draw.textbbox((0, 0), line, font=font_title)
        h = bbox[3] - bbox[1]
        y_cursor += h + line_spacing
        
    y_cursor += 15  # Spacing before footer
    
    # Draw simple thin separator line
    draw.line(
        [(padding, y_cursor), (card_width - padding, y_cursor)],
        fill=border_gray,
        width=1
    )
    y_cursor += 15
    
    # 3. Footer (Upvotes & Comments counts)
    # Formats count like 1.2k if > 1000
    def format_count(num: int) -> str:
        if num >= 1000:
            return f"{num / 1000:.1f}k"
        return str(num)
        
    stats_text = f"▲ {format_count(post.score)}  |  💬 {format_count(post.num_comments)} Comments"
    draw.text((padding, y_cursor), stats_text, font=font_meta_bold, fill=text_gray)
    
    # Save the card image
    canvas.save(output_path, "PNG")
    logger.info(f"Reddit card overlay generated at {output_path} ({card_width}x{card_height})")
    return output_path


def split_caption_for_landscape(title: str) -> tuple[str, str | None]:
    """
    Intelligently splits a title into (top_text, bottom_text) for landscape videos.
    If the title is short, keeps it as a single punchy top title and returns (top_text, None).
    """
    clean = re.sub(r'\s+', ' ', title).strip()
    words = clean.split()
    
    # If title is short (<= 7 words and <= 38 characters), keep together on top
    if len(words) <= 7 and len(clean) <= 38:
        return clean, None
        
    # Check for strong sentence/clause delimiters: ".", "?", "!", ";", " - ", " | "
    for delim in [". ", "? ", "! ", " - ", " | ", "; "]:
        if delim in clean:
            parts = clean.split(delim, 1)
            p1, p2 = parts[0].strip(), parts[1].strip()
            if delim.strip() in [".", "?", "!"]:
                p1 += delim.strip()
            if len(p1) >= 8 and len(p2) >= 8:
                return p1, p2
                
    # Check for secondary punctuation like commas
    if ", " in clean:
        parts = clean.split(", ", 1)
        p1, p2 = parts[0].strip(), parts[1].strip()
        if len(p1) >= 10 and len(p2) >= 10:
            return p1, p2
            
    # Check for natural conjunction split points near middle
    conjunctions = [" while ", " when ", " but ", " until ", " then ", " and ", " because "]
    mid_idx = len(clean) // 2
    best_conj = None
    best_dist = 999
    for conj in conjunctions:
        idx = clean.lower().find(conj)
        while idx != -1:
            dist = abs(idx - mid_idx)
            if dist < best_dist and idx > 10 and (len(clean) - idx) > 10:
                best_dist = dist
                best_conj = (idx, conj)
            idx = clean.lower().find(conj, idx + len(conj))
            
    if best_conj and best_dist < len(clean) * 0.35:
        idx, conj = best_conj
        p1 = clean[:idx].strip()
        p2 = clean[idx:].strip()
        return p1, p2
        
    # Fallback: split evenly by words
    mid_word = len(words) // 2
    p1 = " ".join(words[:mid_word])
    p2 = " ".join(words[mid_word:])
    return p1, p2


def generate_creator_caption_banner(
    text: str,
    max_width: int = 1000,
    min_width: int = 840,
    font_size: int = 0,
    is_bottom: bool = False,
    is_vertical: bool = False,
    filename: str = "top_caption.png"
) -> Path:
    """
    Generate an impactful, viral creator-style caption banner.
    Dynamically scales font size and container width to eliminate dead blank space.
    """
    output_path = config.OUTPUT_DIR / filename
    output_path.parent.mkdir(parents=True, exist_ok=True)
    
    clean_text = re.sub(r'\s+', ' ', text).strip()
    if not clean_text:
        return output_path

    # Determine dynamic font size based on text length and placement
    if font_size <= 0:
        if is_vertical:
            font_size = 42
            min_width = 650
        elif is_bottom:
            font_size = 48 if len(clean_text) <= 35 else 42
            min_width = 780
        else:
            # Top banner for horizontal/square:
            if len(clean_text) <= 26:
                font_size = 56  # Bold, punchy text for short titles
                min_width = 820
            elif len(clean_text) <= 48:
                font_size = 48
                min_width = 800
            else:
                font_size = 42
                min_width = 760

    # Load bold fonts
    font = None
    for font_path in [
        "C:/Windows/Fonts/ariblk.ttf",      # Arial Black (extra bold)
        "C:/Windows/Fonts/arialbd.ttf",     # Arial Bold
        "C:/Windows/Fonts/segoeuib.ttf",    # Segoe UI Bold
        "arialbd.ttf",
        "DejaVuSans-Bold.ttf"
    ]:
        try:
            font = ImageFont.truetype(font_path, font_size)
            break
        except Exception:
            continue
    if font is None:
        font = ImageFont.load_default()

    # Pre-render dummy image for text measurement
    dummy = Image.new("RGBA", (max_width, 100))
    d = ImageDraw.Draw(dummy)
    
    # Calculate wrapped lines
    padding_x = 48
    padding_y = 28
    line_spacing = 14
    max_text_w = max_width - (padding_x * 2)
    lines = _wrap_text(clean_text, d, font, max_text_w)
    if not lines:
        lines = [clean_text]
    full_text = "\n".join(lines)
        
    # Measure whole multiline text block accurately using Pillow's multiline_textbbox
    mb = d.multiline_textbbox((0, 0), full_text, font=font, spacing=line_spacing, align="center")
    text_w = int(mb[2] - mb[0])
    text_h = int(mb[3] - mb[1])
    
    # Proportional banner width to balance and fill upper/lower zones
    banner_w = min(max_width, max(min_width, text_w + (padding_x * 2)))
    banner_h = text_h + (padding_y * 2)
    
    canvas = Image.new("RGBA", (banner_w, banner_h), (0, 0, 0, 0))
    draw = ImageDraw.Draw(canvas)
    
    # Clean, vibrant white card container with rounded corners and subtle crisp border
    bg_color = (255, 255, 255, 255)
    border_color = (212, 215, 222, 255)
    draw.rounded_rectangle(
        [(0, 0), (banner_w - 1, banner_h - 1)],
        radius=24,
        fill=bg_color,
        outline=border_color,
        width=2
    )
    
    # Draw centered text lines with razor-sharp black text (offset by mb[0], mb[1] for exact centering)
    text_x = int((banner_w - text_w) // 2 - mb[0])
    text_y = int((banner_h - text_h) // 2 - mb[1])
    text_color = (12, 12, 16, 255)  # Deep bold black
    
    draw.multiline_text(
        (text_x, text_y),
        full_text,
        font=font,
        fill=text_color,
        align="center",
        spacing=line_spacing
    )
        
    canvas.save(output_path, "PNG")
    logger.info(f"Caption banner '{filename}' generated at {output_path} ({banner_w}x{banner_h}, font_size={font_size})")
    return output_path


# Backward compatibility alias
generate_top_caption_banner = generate_creator_caption_banner
