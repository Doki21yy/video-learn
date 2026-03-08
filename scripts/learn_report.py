#!/usr/bin/env python3
"""
learn_report.py - Dark minimalist learning report HTML generator
Generates premium dark-themed learning guide reports from video analysis data.
"""

import argparse
import base64
import html as html_lib
import json
import os
import re
from datetime import datetime


def escape_html(text):
    if not text:
        return ""
    return html_lib.escape(str(text))


def markdown_to_html(md_text):
    """Simple Markdown -> HTML conversion."""
    if not md_text:
        return ""
    text = str(md_text)

    # Code blocks
    def code_block_repl(m):
        code = escape_html(m.group(2).strip())
        return f'<pre class="code-block"><code>{code}</code></pre>'
    text = re.sub(r'```(\w*)\n(.*?)```', code_block_repl, text, flags=re.DOTALL)

    # Inline code
    text = re.sub(r'`([^`]+)`', r'<code class="inline-code">\1</code>', text)

    # Bold
    text = re.sub(r'\*\*(.+?)\*\*', r'<strong>\1</strong>', text)

    # Italic
    text = re.sub(r'\*(.+?)\*', r'<em>\1</em>', text)

    # Links
    text = re.sub(r'\[([^\]]+)\]\(([^)]+)\)', r'<a href="\2" target="_blank" rel="noopener">\1</a>', text)

    # Headers
    text = re.sub(r'^#### (.+)$', r'<h5 class="content-h5">\1</h5>', text, flags=re.MULTILINE)
    text = re.sub(r'^### (.+)$', r'<h4 class="content-h4">\1</h4>', text, flags=re.MULTILINE)

    lines = text.split('\n')
    result = []
    in_list = False
    list_type = None

    for line in lines:
        stripped = line.strip()
        ol_match = re.match(r'^(\d+)\.\s+(.+)$', stripped)
        ul_match = re.match(r'^[-*]\s+(.+)$', stripped)

        if ol_match:
            if not in_list or list_type != 'ol':
                if in_list:
                    result.append(f'</{list_type}>')
                result.append('<ol class="content-list">')
                in_list = True
                list_type = 'ol'
            result.append(f'<li>{ol_match.group(2)}</li>')
        elif ul_match:
            if not in_list or list_type != 'ul':
                if in_list:
                    result.append(f'</{list_type}>')
                result.append('<ul class="content-list">')
                in_list = True
                list_type = 'ul'
            result.append(f'<li>{ul_match.group(1)}</li>')
        else:
            if in_list:
                result.append(f'</{list_type}>')
                in_list = False
                list_type = None
            if stripped and not stripped.startswith('<'):
                result.append(f'<p>{stripped}</p>')
            elif stripped:
                result.append(stripped)

    if in_list:
        result.append(f'</{list_type}>')

    return '\n'.join(result)


def seconds_to_display(seconds):
    try:
        s = float(seconds)
        m = int(s) // 60
        sec = int(s) % 60
        return f"{m}:{sec:02d}"
    except (ValueError, TypeError):
        return str(seconds)


def time_to_seconds(time_str):
    try:
        parts = str(time_str).split(":")
        if len(parts) == 2:
            return int(parts[0]) * 60 + int(parts[1])
        elif len(parts) == 3:
            return int(parts[0]) * 3600 + int(parts[1]) * 60 + int(parts[2])
        return float(time_str)
    except (ValueError, TypeError):
        return 0


def detect_platform_from_url(url):
    if not url:
        return "unknown"
    url = url.lower()
    if "bilibili" in url:
        return "bilibili"
    if "youtube" in url or "youtu.be" in url:
        return "youtube"
    if "xiaohongshu" in url or "xhslink" in url:
        return "xiaohongshu"
    if "douyin" in url:
        return "douyin"
    return "unknown"


PLATFORM_COLORS = {
    "bilibili": "#00A1D6",
    "youtube": "#FF0000",
    "xiaohongshu": "#FE2C55",
    "douyin": "#FFFFFF",
    "unknown": "#6366F1",
}

PLATFORM_LABELS = {
    "bilibili": "Bilibili",
    "youtube": "YouTube",
    "xiaohongshu": "XHS",
    "douyin": "Douyin",
    "unknown": "Video",
}


def build_video_embed(source_url):
    """Build platform-specific video embed HTML."""
    if not source_url:
        return '<a href="#" class="video-link-fallback"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><polygon points="5 3 19 12 5 21 5 3"/></svg><span>No video link available</span></a>'

    url = source_url.strip()

    # Bilibili
    if "bilibili.com" in url:
        bv_match = re.search(r'(BV[\w]+)', url)
        if bv_match:
            bvid = bv_match.group(1)
            return f'<iframe src="//player.bilibili.com/player.html?bvid={bvid}&high_quality=1&danmaku=0" allowfullscreen="true" frameborder="0"></iframe>'

    # YouTube
    if "youtube.com" in url or "youtu.be" in url:
        yt_match = re.search(r'(?:v=|youtu\.be/)([\w-]+)', url)
        if yt_match:
            vid = yt_match.group(1)
            return f'<iframe src="https://www.youtube.com/embed/{vid}" allowfullscreen frameborder="0"></iframe>'

    # Fallback: link button
    return f'<a href="{escape_html(url)}" target="_blank" class="video-link-fallback"><svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.5"><polygon points="5 3 19 12 5 21 5 3"/></svg><span>Watch on original platform</span></a>'


def build_platform_badge(source_url):
    platform = detect_platform_from_url(source_url)
    color = PLATFORM_COLORS.get(platform, PLATFORM_COLORS["unknown"])
    label = PLATFORM_LABELS.get(platform, "Video")
    return f'<span class="meta-badge platform"><span class="p-dot" style="background:{color}"></span>{label}</span>'


def build_score_badge(score):
    if not score:
        return ""
    return f'<span class="meta-badge score">{float(score):.1f}/10</span>'


def build_duration_badge(duration_sec):
    if not duration_sec:
        return ""
    return f'<span class="meta-badge duration">{seconds_to_display(duration_sec)}</span>'


def build_date_badge(date_str):
    if not date_str:
        return ""
    return f'<span class="meta-badge date">{escape_html(date_str)}</span>'


def build_difficulty_tag(difficulty):
    labels = {
        "beginner": ("Beginner", "difficulty-beginner"),
        "intermediate": ("Intermediate", "difficulty-intermediate"),
        "advanced": ("Advanced", "difficulty-advanced"),
    }
    label, cls = labels.get(difficulty, labels["intermediate"])
    return f'<span class="tag-pill {cls}">{label}</span>'


def build_category_tag(category):
    if not category:
        return ""
    return f'<span class="tag-pill">{escape_html(category)}</span>'


def build_speaker_tag(speaker):
    if not speaker:
        return ""
    return f'<span class="tag-pill">{escape_html(speaker)}</span>'


def build_knowledge_items(sections):
    """Build knowledge points from analysis sections."""
    if not sections:
        return '<li class="knowledge-item"><div class="knowledge-explain">No knowledge points extracted.</div></li>'
    items = []
    for sec in sections:
        title = escape_html(sec.get("title", ""))
        # Use first paragraph of content as explanation
        content = sec.get("content", "")
        # Extract first meaningful line
        explain = ""
        for line in str(content).split("\n"):
            line = line.strip()
            if line and not line.startswith("#") and not line.startswith("```"):
                explain = line[:300]
                break
        if not explain:
            explain = content[:300] if content else ""

        items.append(f'''<li class="knowledge-item">
            <div class="knowledge-concept">{title}</div>
            <div class="knowledge-explain">{escape_html(explain)}</div>
        </li>''')
    return "\n".join(items)


def build_chapter_items(scene_breakdown):
    """Build chapter accordion from scene breakdown data."""
    chapters = []
    if isinstance(scene_breakdown, dict):
        chapters = scene_breakdown.get("chapters", [])

    if not chapters:
        return '<div class="chapter-item"><div class="chapter-header"><div class="chapter-header-left"><span class="chapter-time">--</span><span class="chapter-title">No chapter data available</span></div></div></div>'

    items = []
    for ch in chapters:
        ch_title = escape_html(ch.get("chapter", ch.get("title", "Chapter")))
        ch_start = escape_html(str(ch.get("start", "")))
        ch_end = escape_html(str(ch.get("end", "")))
        time_range = f"{ch_start}" if ch_start else ""

        scenes = ch.get("scenes", [])
        summary_parts = []
        key_points = []
        for s in scenes:
            narr = s.get("narration", s.get("visual", ""))
            if narr:
                summary_parts.append(str(narr))
            concept = s.get("core_concept", "")
            if concept:
                key_points.append(escape_html(str(concept)))

        summary = escape_html(". ".join(summary_parts)[:300]) if summary_parts else ""
        points_html = "".join(f"<li>{p}</li>" for p in key_points[:5])

        arrow_svg = '<svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M6 9l6 6 6-6"/></svg>'

        items.append(f'''<div class="chapter-item">
            <div class="chapter-header">
                <div class="chapter-header-left">
                    <span class="chapter-time">{time_range}</span>
                    <span class="chapter-title">{ch_title}</span>
                </div>
                <span class="chapter-arrow">{arrow_svg}</span>
            </div>
            <div class="chapter-content">
                <div class="chapter-inner">
                    {f'<div class="chapter-summary">{summary}</div>' if summary else ''}
                    {f'<ul class="chapter-points">{points_html}</ul>' if points_html else ''}
                </div>
            </div>
        </div>''')

    return "\n".join(items)


def build_quote_items(analysis):
    """Build quote cards. Try quotes from scene breakdown or key insights."""
    quotes = []

    # Try to extract notable quotes from scene breakdown
    scene_breakdown = analysis.get("scene_breakdown", {})
    if isinstance(scene_breakdown, dict):
        for ch in scene_breakdown.get("chapters", []):
            for s in ch.get("scenes", []):
                note = s.get("note", "")
                if note and len(str(note)) > 20:
                    time_str = s.get("start", "")
                    quotes.append({"text": str(note), "time": str(time_str)})

    # Also extract from key_tips as notable insights
    for tip in analysis.get("key_tips", []):
        if tip and len(str(tip)) > 20:
            quotes.append({"text": str(tip), "time": ""})

    if not quotes:
        return '<div class="quote-card"><div class="quote-text">No notable quotes extracted from this video.</div></div>'

    # Limit to 5 quotes
    items = []
    for q in quotes[:5]:
        text = escape_html(q["text"])
        time_html = f'<div class="quote-time">{escape_html(q["time"])}</div>' if q["time"] else ""
        items.append(f'''<div class="quote-card">
            <div class="quote-text">{text}</div>
            {time_html}
        </div>''')

    return "\n".join(items)


def build_takeaway_items(analysis):
    """Build takeaway checklist from key_tips and summary."""
    takeaways = []

    for tip in analysis.get("key_tips", []):
        if tip:
            takeaways.append(str(tip))

    # Add FAQ answers as additional takeaways
    for faq in analysis.get("faq", []):
        q = faq.get("question", "")
        if q:
            takeaways.append(str(q))

    if not takeaways:
        return '<li class="takeaway-item"><span class="takeaway-check"></span>No takeaways extracted.</li>'

    check_svg = '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2.5"><path d="M20 6L9 17l-5-5"/></svg>'
    items = []
    for t in takeaways[:8]:
        items.append(f'''<li class="takeaway-item">
            <span class="takeaway-check">{check_svg}</span>
            {escape_html(t)}
        </li>''')

    return "\n".join(items)


def build_resource_rows(resources):
    """Build resource table rows."""
    if not resources:
        return '<tr><td colspan="3" style="color:var(--text-muted);font-style:italic">No tools or resources mentioned.</td></tr>'

    rows = []
    for r in resources:
        name = escape_html(r.get("name", ""))
        desc = escape_html(r.get("description", ""))
        url = r.get("url", "")
        if url and url.startswith("http"):
            link_html = f'<a href="{escape_html(url)}" target="_blank" rel="noopener">Link</a>'
        else:
            link_html = '<span style="color:var(--text-muted)">--</span>'
        rows.append(f'<tr><td>{name}</td><td>{desc}</td><td>{link_html}</td></tr>')

    return "\n".join(rows)


def build_sections_html(sections):
    """Build detailed content sections (the main learning content)."""
    if not sections:
        return ""

    parts = []
    for i, sec in enumerate(sections):
        title = escape_html(sec.get("title", f"Section {i+1}"))
        content = markdown_to_html(sec.get("content", ""))
        subs = sec.get("subsections", [])
        subs_html = ""
        if subs:
            sub_parts = []
            for sub in subs:
                sub_title = escape_html(sub.get("title", ""))
                sub_content = markdown_to_html(sub.get("content", ""))
                sub_parts.append(f'''<div class="subsection">
                    <h4 class="subsec-title">{sub_title}</h4>
                    <div class="subsec-body">{sub_content}</div>
                </div>''')
            subs_html = "".join(sub_parts)
        parts.append(f'''<div class="section-block">
            <h3 class="sec-title"><span class="sec-num">{i+1:02d}</span>{title}</h3>
            <div class="sec-body">{content}</div>
            {subs_html}
        </div>''')
    return "".join(parts)


def generate_html(analysis, title, video_base64=None, video_path=None):
    """Generate the full dark-themed learning report HTML."""
    a = analysis

    # Metadata
    title_cn = a.get("title_cn", title)
    category = a.get("category", "")
    diff_str = a.get("difficulty", "intermediate")
    rating = a.get("learning_rating", 0)
    speaker = a.get("speaker", "")
    overview = a.get("overview", a.get("summary", ""))
    summary_text = a.get("summary", "")

    # Duration and source
    meta = a.get("_meta", {})
    duration_sec = meta.get("video_duration", 0)
    source_url = meta.get("source_url", "")
    date_str = datetime.now().strftime("%Y-%m-%d")

    # Build components
    video_embed = build_video_embed(source_url)
    platform_badge = build_platform_badge(source_url)
    score_badge = build_score_badge(rating)
    duration_badge = build_duration_badge(duration_sec)
    date_badge = build_date_badge(date_str)
    difficulty_tag = build_difficulty_tag(diff_str)
    category_tag = build_category_tag(category)
    speaker_tag = build_speaker_tag(speaker)
    knowledge_items = build_knowledge_items(a.get("sections", []))
    chapter_items = build_chapter_items(a.get("scene_breakdown", {}))
    quote_items = build_quote_items(a)
    takeaway_items = build_takeaway_items(a)
    resource_rows = build_resource_rows(a.get("resources", []))

    # Build detailed content sections
    sections_html = build_sections_html(a.get("sections", []))

    # FAQ section
    faq_html = ""
    faq_list = a.get("faq", [])
    if faq_list:
        faq_items = []
        for f in faq_list:
            q = escape_html(f.get("question", ""))
            ans = markdown_to_html(f.get("answer", ""))
            faq_items.append(f'''<div class="faq-item">
                <div class="faq-q">Q: {q}</div>
                <div class="faq-a">{ans}</div>
            </div>''')
        faq_html = f'''<div class="section-card">
            <div class="section-label">FAQ</div>
            {"".join(faq_items)}
        </div>'''

    # Summary section
    summary_html = ""
    if summary_text:
        summary_html = f'''<div class="section-card">
            <div class="section-label">Summary</div>
            <div class="summary-box"><p>{escape_html(summary_text)}</p></div>
        </div>'''

    html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{escape_html(title_cn)} - Learning Archive</title>
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;700;900&display=swap');
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500&display=swap');

*, *::before, *::after {{ margin: 0; padding: 0; box-sizing: border-box; }}

:root {{
  --bg-deep: #06060B;
  --bg-surface: #0D0D14;
  --bg-card: #12121C;
  --bg-card-hover: #181826;
  --border-subtle: rgba(99, 102, 241, 0.08);
  --border-hover: rgba(99, 102, 241, 0.2);
  --text-primary: #E8E8ED;
  --text-secondary: #7A7A8E;
  --text-muted: #4A4A5E;
  --accent: #6366F1;
  --accent-glow: rgba(99, 102, 241, 0.15);
  --accent-soft: #818CF8;
  --radius: 12px;
  --font-heading: 'DM Sans', -apple-system, sans-serif;
  --font-mono: 'IBM Plex Mono', monospace;
}}

html {{ scroll-behavior: smooth; }}

body {{
  background: var(--bg-deep);
  color: var(--text-primary);
  font-family: var(--font-heading);
  font-weight: 400;
  line-height: 1.7;
  min-height: 100vh;
}}

body::before {{
  content: '';
  position: fixed;
  top: -200px; left: 50%;
  transform: translateX(-50%);
  width: 800px; height: 600px;
  background: radial-gradient(ellipse, rgba(99, 102, 241, 0.05) 0%, transparent 70%);
  pointer-events: none;
  z-index: 0;
}}

.container {{
  max-width: 860px;
  margin: 0 auto;
  padding: 0 24px;
  position: relative;
  z-index: 1;
}}

a {{ color: var(--accent-soft); text-decoration: none; }}
a:hover {{ text-decoration: underline; }}

/* Back Nav */
.back-nav {{ padding: 24px 0; }}
.back-link {{
  display: inline-flex; align-items: center; gap: 6px;
  color: var(--text-muted); text-decoration: none;
  font-family: var(--font-mono); font-size: 0.78rem;
  transition: color 0.2s;
}}
.back-link:hover {{ color: var(--accent-soft); text-decoration: none; }}
.back-link svg {{ width: 16px; height: 16px; }}

/* Hero */
.hero {{ padding-bottom: 40px; }}

.video-embed {{
  width: 100%; aspect-ratio: 16/9;
  border-radius: var(--radius); overflow: hidden;
  background: var(--bg-surface);
  border: 1px solid var(--border-subtle);
  margin-bottom: 28px;
}}
.video-embed iframe {{ width: 100%; height: 100%; border: none; }}
.video-embed .video-link-fallback {{
  width: 100%; height: 100%;
  display: flex; align-items: center; justify-content: center;
  flex-direction: column; gap: 12px;
  color: var(--text-secondary); text-decoration: none;
}}
.video-embed .video-link-fallback:hover {{ color: var(--accent-soft); }}
.video-embed .video-link-fallback svg {{ width: 48px; height: 48px; opacity: 0.5; }}

.hero-title {{
  font-family: var(--font-heading);
  font-weight: 900;
  font-size: clamp(1.6rem, 4vw, 2.4rem);
  letter-spacing: -0.02em; line-height: 1.25;
  color: var(--text-primary);
  margin-bottom: 16px;
}}

.hero-meta {{
  display: flex; align-items: center; gap: 12px; flex-wrap: wrap;
}}

.meta-badge {{
  display: inline-flex; align-items: center; gap: 5px;
  padding: 4px 12px; border-radius: 6px;
  font-family: var(--font-mono); font-size: 0.72rem;
  font-weight: 500; letter-spacing: 0.03em;
}}
.meta-badge.platform {{
  background: rgba(0, 0, 0, 0.4);
  border: 1px solid var(--border-subtle);
  color: var(--text-primary);
}}
.meta-badge.platform .p-dot {{
  width: 6px; height: 6px; border-radius: 50%;
}}
.meta-badge.score {{
  background: var(--accent-glow);
  border: 1px solid rgba(99, 102, 241, 0.15);
  color: var(--accent-soft);
}}
.meta-badge.duration, .meta-badge.date {{
  color: var(--text-muted);
  font-family: var(--font-mono); font-size: 0.72rem;
}}

/* Section Cards */
.section-card {{
  background: var(--bg-card);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius);
  padding: 28px 32px;
  margin-bottom: 16px;
}}
.section-label {{
  font-family: var(--font-mono);
  font-size: 0.68rem; font-weight: 500;
  color: var(--accent-soft);
  text-transform: uppercase;
  letter-spacing: 0.1em;
  margin-bottom: 16px;
}}
.section-heading {{
  font-family: var(--font-heading);
  font-weight: 700; font-size: 1.15rem;
  color: var(--text-primary);
  margin-bottom: 12px;
}}
.section-text {{
  font-size: 0.9rem;
  color: var(--text-secondary);
  line-height: 1.75;
}}

/* Tags */
.tag-row {{ display: flex; gap: 8px; flex-wrap: wrap; margin-bottom: 16px; }}
.tag-pill {{
  padding: 3px 10px; border-radius: 4px;
  font-family: var(--font-mono); font-size: 0.7rem; font-weight: 500;
  border: 1px solid var(--border-subtle);
  color: var(--text-secondary);
}}
.tag-pill.difficulty-beginner {{ border-color: rgba(34, 197, 94, 0.2); color: #4ADE80; }}
.tag-pill.difficulty-intermediate {{ border-color: rgba(250, 204, 21, 0.2); color: #FACC15; }}
.tag-pill.difficulty-advanced {{ border-color: rgba(239, 68, 68, 0.2); color: #F87171; }}

/* Knowledge Points */
.knowledge-list {{ list-style: none; }}
.knowledge-item {{ padding: 14px 0; border-bottom: 1px solid var(--border-subtle); }}
.knowledge-item:last-child {{ border-bottom: none; }}
.knowledge-concept {{
  font-family: var(--font-heading); font-weight: 700;
  font-size: 0.9rem; color: var(--text-primary);
  margin-bottom: 4px;
}}
.knowledge-explain {{
  font-size: 0.84rem; color: var(--text-secondary); line-height: 1.65;
}}

/* Chapters Accordion */
.chapter-item {{ border-bottom: 1px solid var(--border-subtle); }}
.chapter-item:last-child {{ border-bottom: none; }}
.chapter-header {{
  display: flex; align-items: center; justify-content: space-between;
  padding: 16px 0; cursor: pointer; user-select: none;
  transition: color 0.2s;
}}
.chapter-header:hover {{ color: var(--accent-soft); }}
.chapter-header-left {{
  display: flex; align-items: center; gap: 12px; flex: 1; min-width: 0;
}}
.chapter-time {{
  font-family: var(--font-mono); font-size: 0.72rem;
  color: var(--accent-soft); white-space: nowrap; flex-shrink: 0;
}}
.chapter-title {{
  font-family: var(--font-heading); font-weight: 600;
  font-size: 0.9rem; color: var(--text-primary);
  overflow: hidden; text-overflow: ellipsis; white-space: nowrap;
}}
.chapter-arrow {{
  color: var(--text-muted);
  transition: transform 0.3s ease; flex-shrink: 0;
}}
.chapter-item.open .chapter-arrow {{ transform: rotate(180deg); }}
.chapter-content {{ max-height: 0; overflow: hidden; transition: max-height 0.35s ease; }}
.chapter-item.open .chapter-content {{ max-height: 500px; }}
.chapter-inner {{ padding: 0 0 20px 0; }}
.chapter-summary {{
  font-size: 0.85rem; color: var(--text-secondary);
  margin-bottom: 12px; line-height: 1.7;
}}
.chapter-points {{ list-style: none; padding: 0; }}
.chapter-points li {{
  position: relative; padding-left: 16px;
  margin-bottom: 6px; font-size: 0.82rem; color: var(--text-secondary);
}}
.chapter-points li::before {{
  content: ''; position: absolute; left: 0; top: 9px;
  width: 4px; height: 4px; border-radius: 50%; background: var(--accent);
}}

/* Quotes */
.quote-card {{
  position: relative; padding: 20px 24px;
  margin-bottom: 12px;
  border-left: 2px solid var(--accent);
  background: rgba(99, 102, 241, 0.03);
  border-radius: 0 8px 8px 0;
}}
.quote-card:last-child {{ margin-bottom: 0; }}
.quote-text {{
  font-size: 0.9rem; color: var(--text-primary);
  font-style: italic; line-height: 1.65; margin-bottom: 8px;
}}
.quote-time {{
  font-family: var(--font-mono); font-size: 0.7rem; color: var(--accent-soft);
}}

/* Takeaways */
.takeaway-list {{ list-style: none; }}
.takeaway-item {{
  display: flex; align-items: flex-start; gap: 10px;
  padding: 8px 0; font-size: 0.88rem; color: var(--text-secondary);
}}
.takeaway-check {{
  width: 18px; height: 18px;
  border: 1.5px solid var(--border-hover);
  border-radius: 4px; flex-shrink: 0; margin-top: 2px;
  display: flex; align-items: center; justify-content: center;
}}
.takeaway-check svg {{
  width: 12px; height: 12px; color: var(--accent-soft);
}}

/* Resources Table */
.resource-table {{ width: 100%; border-collapse: collapse; }}
.resource-table th {{
  text-align: left; font-family: var(--font-mono);
  font-size: 0.7rem; font-weight: 500; color: var(--text-muted);
  text-transform: uppercase; letter-spacing: 0.06em;
  padding: 10px 0; border-bottom: 1px solid var(--border-subtle);
}}
.resource-table td {{
  padding: 10px 0; font-size: 0.84rem;
  color: var(--text-secondary);
  border-bottom: 1px solid var(--border-subtle);
}}
.resource-table tr:last-child td {{ border-bottom: none; }}
.resource-table a {{ color: var(--accent-soft); text-decoration: none; }}
.resource-table a:hover {{ text-decoration: underline; }}

/* Detailed Content Sections */
.section-block {{
  margin-bottom: 20px;
  background: rgba(99, 102, 241, 0.02);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius);
  padding: 24px 28px;
}}
.sec-title {{
  font-family: var(--font-heading);
  font-size: 1rem; font-weight: 700;
  margin-bottom: 14px; display: flex; align-items: center; gap: 10px;
  color: var(--text-primary);
}}
.sec-num {{
  font-family: var(--font-mono); font-size: 0.68rem;
  color: #fff; background: var(--accent);
  width: 24px; height: 24px; border-radius: 50%;
  display: inline-flex; align-items: center; justify-content: center;
  flex-shrink: 0;
}}
.sec-body {{ color: var(--text-secondary); line-height: 1.8; font-size: 0.88rem; }}
.sec-body p {{ margin-bottom: 10px; }}
.sec-body strong {{ color: var(--text-primary); font-weight: 600; }}
.subsection {{ margin-top: 16px; padding-top: 12px; border-top: 1px solid var(--border-subtle); }}
.subsec-title {{ font-size: 0.92rem; font-weight: 600; margin-bottom: 8px; color: var(--text-primary); }}
.subsec-body {{ color: var(--text-secondary); font-size: 0.86rem; }}
.subsec-body p {{ margin-bottom: 8px; }}
.content-list {{ margin: 10px 0; padding-left: 22px; }}
.content-list li {{ margin-bottom: 5px; line-height: 1.65; }}
.content-h4 {{ font-size: 0.95rem; font-weight: 600; margin: 14px 0 8px; color: var(--text-primary); }}
.content-h5 {{ font-size: 0.88rem; font-weight: 600; margin: 10px 0 6px; color: var(--text-secondary); }}
.code-block {{
  background: #0D0D14; color: #CDD6F4;
  padding: 14px 18px; border-radius: 8px;
  overflow-x: auto; font-family: var(--font-mono);
  font-size: 0.8rem; line-height: 1.6; margin: 10px 0;
  border: 1px solid var(--border-subtle);
}}
.inline-code {{
  background: var(--accent-glow); color: var(--accent-soft);
  padding: 1px 6px; border-radius: 4px;
  font-family: var(--font-mono); font-size: 0.85em;
}}

/* FAQ */
.faq-item {{
  margin-bottom: 14px; padding: 16px 20px;
  background: rgba(99, 102, 241, 0.02);
  border: 1px solid var(--border-subtle);
  border-radius: 8px;
}}
.faq-q {{ font-weight: 600; color: var(--accent-soft); margin-bottom: 8px; font-size: 0.9rem; }}
.faq-a {{ color: var(--text-secondary); font-size: 0.86rem; }}
.faq-a p {{ margin-bottom: 6px; }}

/* Summary Box */
.summary-box {{
  background: rgba(99, 102, 241, 0.04);
  border: 1px solid rgba(99, 102, 241, 0.1);
  border-radius: var(--radius);
  padding: 24px 28px;
}}
.summary-box p {{ color: var(--text-secondary); line-height: 1.85; font-size: 0.92rem; }}

/* Footer */
.report-footer {{
  padding: 48px 0 32px;
  text-align: center;
  font-family: var(--font-mono);
  font-size: 0.72rem;
  color: var(--text-muted);
}}

/* Animations */
@keyframes fadeInUp {{
  from {{ opacity: 0; transform: translateY(16px); }}
  to {{ opacity: 1; transform: translateY(0); }}
}}
.section-card {{ animation: fadeInUp 0.5s ease both; }}
.section-card:nth-child(1) {{ animation-delay: 0.1s; }}
.section-card:nth-child(2) {{ animation-delay: 0.15s; }}
.section-card:nth-child(3) {{ animation-delay: 0.2s; }}
.section-card:nth-child(4) {{ animation-delay: 0.25s; }}
.section-card:nth-child(5) {{ animation-delay: 0.3s; }}
.section-card:nth-child(6) {{ animation-delay: 0.35s; }}

/* Responsive */
@media (max-width: 640px) {{
  .container {{ padding: 0 16px; }}
  .section-card {{ padding: 20px 18px; }}
  .hero-title {{ font-size: 1.4rem; }}
  .section-block {{ padding: 18px 16px; }}
}}
</style>
</head>
<body>

<div class="container">
  <nav class="back-nav">
    <a href="../../../" class="back-link">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M19 12H5M12 19l-7-7 7-7"/></svg>
      Archive
    </a>
  </nav>

  <section class="hero">
    <div class="video-embed">
      {video_embed}
    </div>

    <h1 class="hero-title">{escape_html(title_cn)}</h1>

    <div class="hero-meta">
      {platform_badge}
      {score_badge}
      {duration_badge}
      {date_badge}
    </div>
  </section>

  <!-- Overview -->
  <div class="section-card">
    <div class="section-label">Overview</div>
    <div class="tag-row">
      {difficulty_tag}
      {category_tag}
      {speaker_tag}
    </div>
    <div class="section-text">{escape_html(overview)}</div>
  </div>

  <!-- Key Knowledge Points -->
  <div class="section-card">
    <div class="section-label">Key Knowledge</div>
    <ul class="knowledge-list">
      {knowledge_items}
    </ul>
  </div>

  <!-- Detailed Content -->
  {f"""<div class="section-card">
    <div class="section-label">Detailed Content</div>
    {sections_html}
  </div>""" if sections_html else ""}

  <!-- Chapters -->
  <div class="section-card">
    <div class="section-label">Chapters</div>
    {chapter_items}
  </div>

  <!-- Quotes -->
  <div class="section-card">
    <div class="section-label">Notable Quotes</div>
    {quote_items}
  </div>

  <!-- Takeaways -->
  <div class="section-card">
    <div class="section-label">Takeaways</div>
    <ul class="takeaway-list">
      {takeaway_items}
    </ul>
  </div>

  <!-- Resources -->
  <div class="section-card">
    <div class="section-label">Tools & Resources</div>
    <table class="resource-table">
      <thead><tr><th>Name</th><th>Description</th><th>Link</th></tr></thead>
      <tbody>
        {resource_rows}
      </tbody>
    </table>
  </div>

  {faq_html}

  {summary_html}

  <footer class="report-footer">
    powered by video-learn
  </footer>
</div>

<script>
// Chapter accordion
document.querySelectorAll('.chapter-header').forEach(header => {{
  header.addEventListener('click', () => {{
    header.parentElement.classList.toggle('open');
  }});
}});
</script>
</body>
</html>'''
    return html


def generate_meta_json(analysis, title, report_dir):
    """Generate meta.json for GitHub sync."""
    meta = {
        "title": title,
        "type": "learning",
        "topic": analysis.get("topic", title),
        "category": analysis.get("category", ""),
        "difficulty": analysis.get("difficulty", "intermediate"),
        "learning_rating": analysis.get("learning_rating", 0),
        "summary": analysis.get("overview", analysis.get("summary", "")),
        "speaker": analysis.get("speaker", ""),
        "tags": analysis.get("tags", []),
        "source_url": analysis.get("_meta", {}).get("source_url", ""),
        "duration": analysis.get("_meta", {}).get("video_duration", 0),
        "generated_at": datetime.now().isoformat(),
    }
    path = os.path.join(report_dir, "meta.json")
    with open(path, "w", encoding="utf-8") as f:
        json.dump(meta, f, ensure_ascii=False, indent=2)
    return path


def main():
    parser = argparse.ArgumentParser(description="Generate learning guide HTML report")
    parser.add_argument("--analysis-json", required=True, help="Path to analysis JSON")
    parser.add_argument("--video-path", default=None, help="Path to video file")
    parser.add_argument("--title", default="", help="Video title")
    parser.add_argument("--output-dir", default=".", help="Output directory")
    parser.add_argument("--video-base64-path", default=None, help="Video file to embed as base64")

    args = parser.parse_args()

    with open(args.analysis_json, "r", encoding="utf-8") as f:
        analysis = json.load(f)

    title = args.title or analysis.get("_meta", {}).get("title", "Learning Notes")

    video_b64 = None
    if args.video_base64_path and os.path.isfile(args.video_base64_path):
        with open(args.video_base64_path, "rb") as vf:
            video_b64 = base64.b64encode(vf.read()).decode("utf-8")

    html = generate_html(analysis, title, video_base64=video_b64, video_path=args.video_path)

    os.makedirs(args.output_dir, exist_ok=True)

    # Full report
    report_path = os.path.join(args.output_dir, "report.html")
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(html)
    print(f"Report: {report_path}")

    # Lite report (no base64 video)
    lite_html = generate_html(analysis, title, video_base64=None, video_path=None)
    lite_path = os.path.join(args.output_dir, "report-lite.html")
    with open(lite_path, "w", encoding="utf-8") as f:
        f.write(lite_html)
    print(f"Lite: {lite_path}")

    # Meta JSON
    generate_meta_json(analysis, title, args.output_dir)
    print(f"Meta: {os.path.join(args.output_dir, 'meta.json')}")


if __name__ == "__main__":
    main()
