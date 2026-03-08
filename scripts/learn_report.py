#!/usr/bin/env python3
"""
learn_report.py - 深度学习指南 HTML 报告生成器
生成文章式知识结构报告，类似高质量学习笔记/教程文档
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
    """简单的 Markdown -> HTML 转换（支持常用语法）"""
    if not md_text:
        return ""
    text = str(md_text)

    # Code blocks ``` ... ```
    def code_block_repl(m):
        lang = m.group(1) or ""
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

    # Headers within section content (h4/h5 only since h2/h3 used for sections)
    text = re.sub(r'^#### (.+)$', r'<h5 class="content-h5">\1</h5>', text, flags=re.MULTILINE)
    text = re.sub(r'^### (.+)$', r'<h4 class="content-h4">\1</h4>', text, flags=re.MULTILINE)

    # Convert line groups to paragraphs and lists
    lines = text.split('\n')
    result = []
    in_list = False
    list_type = None  # 'ul' or 'ol'

    for line in lines:
        stripped = line.strip()

        # Numbered list
        ol_match = re.match(r'^(\d+)\.\s+(.+)$', stripped)
        # Bullet list
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


def difficulty_label(d):
    labels = {
        "beginner": ("初级", "pill-diff-b"),
        "intermediate": ("中级", "pill-diff-i"),
        "advanced": ("高级", "pill-diff-a"),
    }
    return labels.get(d, labels["intermediate"])


def build_tags_html(analysis):
    tags = analysis.get("tags", [])
    return "".join(f'<span class="tag">{escape_html(t)}</span>' for t in tags[:6])


def build_resources_html(resources):
    if not resources:
        return '<p class="empty-hint">视频中未提及具体工具或资源链接。</p>'
    rows = []
    for r in resources:
        name = escape_html(r.get("name", ""))
        url = r.get("url", "")
        desc = escape_html(r.get("description", ""))
        rtype = escape_html(r.get("type", ""))
        type_badge = f'<span class="res-type">{rtype}</span>' if rtype else ""
        if url and url.startswith("http"):
            name_html = f'<a href="{escape_html(url)}" target="_blank" rel="noopener">{name}</a>'
        else:
            name_html = name
        rows.append(f'''<tr>
            <td class="res-name">{name_html} {type_badge}</td>
            <td class="res-desc">{desc}</td>
        </tr>''')
    return f'''<table class="res-table">
        <thead><tr><th>名称</th><th>说明</th></tr></thead>
        <tbody>{"".join(rows)}</tbody>
    </table>'''


def build_sections_html(sections):
    if not sections:
        return ""
    parts = []
    for i, sec in enumerate(sections):
        title = escape_html(sec.get("title", f"第{i+1}节"))
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


def build_tips_html(tips):
    if not tips:
        return ""
    items = "".join(f'<li>{escape_html(t)}</li>' for t in tips)
    return f'<ul class="tips-list">{items}</ul>'


def build_faq_html(faq):
    if not faq:
        return ""
    parts = []
    for f in faq:
        q = escape_html(f.get("question", ""))
        a = markdown_to_html(f.get("answer", ""))
        parts.append(f'''<div class="faq-item">
            <div class="faq-q">Q: {q}</div>
            <div class="faq-a">{a}</div>
        </div>''')
    return "".join(parts)


def build_audience_html(audience):
    if not audience:
        return ""
    items = "".join(f'<li>{escape_html(a)}</li>' for a in audience)
    return f'<ol class="audience-list">{items}</ol>'


def build_links_html(links):
    if not links:
        return ""
    items = []
    for lnk in links:
        label = escape_html(lnk.get("label", ""))
        url = lnk.get("url", "")
        if url and url.startswith("http"):
            items.append(f'<li><a href="{escape_html(url)}" target="_blank" rel="noopener">{label}</a></li>')
        else:
            items.append(f'<li>{label}: {escape_html(url)}</li>')
    return f'<ul class="links-list">{"".join(items)}</ul>'


def build_video_embed(source_url):
    """Build platform-specific video embed (iframe or link)."""
    if not source_url:
        return ""

    url = source_url.strip()

    # Bilibili
    if "bilibili.com" in url:
        import re
        bv_match = re.search(r'(BV[\w]+)', url)
        if bv_match:
            bvid = bv_match.group(1)
            return f'''<div class="embed-wrap">
  <iframe src="//player.bilibili.com/player.html?bvid={bvid}&high_quality=1&danmaku=0"
    allowfullscreen="true" frameborder="0"
    style="width:100%;aspect-ratio:16/9;border-radius:var(--r)"></iframe>
</div>
<a href="{escape_html(url)}" target="_blank" class="yt-btn" style="display:inline-block;margin-top:10px">在 B 站观看</a>'''

    # YouTube
    if "youtube.com" in url or "youtu.be" in url:
        import re
        yt_match = re.search(r'(?:v=|youtu\.be/)([\w-]+)', url)
        if yt_match:
            vid = yt_match.group(1)
            return f'''<div class="embed-wrap">
  <iframe src="https://www.youtube.com/embed/{vid}"
    allowfullscreen frameborder="0"
    style="width:100%;aspect-ratio:16/9;border-radius:var(--r)"></iframe>
</div>
<a href="{escape_html(url)}" target="_blank" class="yt-btn" style="display:inline-block;margin-top:10px">在 YouTube 观看</a>'''

    # Other platforms: just a link button
    return f'<a href="{escape_html(url)}" target="_blank" class="yt-btn" style="display:inline-block;margin-top:10px;font-size:1rem">在原平台观看视频</a>'


def build_scene_cards(scene_breakdown):
    """Build scene cards for video player sync panel."""
    chapters = []
    if isinstance(scene_breakdown, dict):
        chapters = scene_breakdown.get("chapters", [])
    cards = []
    for ch in chapters:
        for s in ch.get("scenes", []):
            sid = escape_html(s.get("scene_id", ""))
            start_s = time_to_seconds(s.get("start", "0:00"))
            end_s = time_to_seconds(s.get("end", "0:30"))
            concept = escape_html(s.get("core_concept", ""))
            narr = escape_html(s.get("narration", s.get("visual", "")))
            method = escape_html(s.get("teaching_method", ""))
            clarity = s.get("clarity", "medium")
            start_d = escape_html(s.get("start", "0:00"))
            end_d = escape_html(s.get("end", ""))
            cards.append(f'''<div class="sc" data-start="{start_s}" data-end="{end_s}" onclick="seekTo({start_s})">
                <div class="sc-head">
                    <span class="sc-id">{sid}</span>
                    <span class="sc-time">{start_d} - {end_d}</span>
                </div>
                <div class="sc-concept">{concept}</div>
                <div class="sc-narr">{narr}</div>
                <div class="sc-tags">
                    <span class="sc-tag method">{method}</span>
                    <span class="clarity-dot clarity-{clarity}"></span>
                </div>
            </div>''')
    return "".join(cards)


def generate_html(analysis, title, video_base64=None, video_path=None):
    """Generate the full learning guide HTML report."""
    a = analysis

    # Metadata
    title_cn = a.get("title_cn", title)
    topic = a.get("topic", title)
    category = a.get("category", "")
    diff_str = a.get("difficulty", "intermediate")
    diff_label, diff_class = difficulty_label(diff_str)
    rating = a.get("learning_rating", 0)
    speaker = a.get("speaker", "")
    language = a.get("language", "")
    overview = a.get("overview", a.get("summary", ""))
    summary = a.get("summary", "")
    hw_req = a.get("hardware_requirements", "")

    # Duration
    meta = a.get("_meta", {})
    duration_sec = meta.get("video_duration", 0)
    duration_str = seconds_to_display(duration_sec) if duration_sec else ""
    source_url = meta.get("source_url", "")
    date_str = datetime.now().strftime("%Y-%m-%d")

    # Video embed (platform iframe or fallback link)
    video_embed_html = build_video_embed(source_url)

    # Build content sections
    sections_html = build_sections_html(a.get("sections", []))
    resources_html = build_resources_html(a.get("resources", []))
    tips_html = build_tips_html(a.get("key_tips", []))
    faq_html = build_faq_html(a.get("faq", []))
    audience_html = build_audience_html(a.get("target_audience", []))
    links_html = build_links_html(a.get("related_links", []))
    tags_html = build_tags_html(a)
    scene_cards = build_scene_cards(a.get("scene_breakdown", {}))
    scene_count = sum(len(ch.get("scenes", [])) for ch in a.get("scene_breakdown", {}).get("chapters", []))

    # Video info
    vi = a.get("video_info", {})
    pub_date = vi.get("publish_date", "")
    views = vi.get("views_estimate", "")

    # YouTube link button
    yt_btn = ""
    if source_url:
        yt_btn = f'<a href="{escape_html(source_url)}" target="_blank" class="yt-btn">在原平台观看</a>'

    html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{escape_html(title_cn)} - 视频学习笔记</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Noto+Serif+SC:wght@400;600;700&family=DM+Sans:ital,opsz,wght@0,9..40,400;0,9..40,500;0,9..40,600;0,9..40,700;1,9..40,400&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
<style>
*{{margin:0;padding:0;box-sizing:border-box}}
:root{{
  --bg:#F6F5F0;--card:#FFFFFF;--border:#E2E0D8;--border-light:#EDEBE4;
  --text:#1A1816;--text-2:#4A4640;--text-3:#8A857D;--text-4:#B5B0A6;
  --ink:#6C63FF;--ink-light:#EEEDFF;--ink-mid:#C5C1FF;--ink-deep:#4F46E5;
  --green:#16A34A;--green-bg:#F0FDF4;--amber:#D97706;--amber-bg:#FFFBEB;
  --rose:#E11D48;--rose-bg:#FFF1F2;--teal:#0D9488;--teal-bg:#F0FDFA;
  --serif:'Noto Serif SC',Georgia,serif;
  --sans:'DM Sans',-apple-system,'Noto Sans SC',sans-serif;
  --mono:'JetBrains Mono',monospace;
  --r:14px;--r-sm:8px;
  --sh:0 1px 2px rgba(26,24,22,.04),0 2px 8px rgba(26,24,22,.04);
}}
html{{scroll-behavior:smooth}}
body{{font-family:var(--sans);background:var(--bg);color:var(--text);line-height:1.8;-webkit-font-smoothing:antialiased;font-size:15px}}
.page{{max-width:860px;margin:0 auto;padding:32px 24px 80px}}
a{{color:var(--ink)}}

/* Header */
.badge-line{{font-family:var(--mono);font-size:.72rem;color:var(--ink);letter-spacing:.06em;margin-bottom:12px}}
h1{{font-family:var(--serif);font-size:clamp(1.4rem,3vw,2rem);font-weight:700;line-height:1.35;letter-spacing:-.01em;margin-bottom:16px}}
.meta-row{{display:flex;flex-wrap:wrap;align-items:center;gap:8px;margin-bottom:20px}}
.pill{{display:inline-flex;align-items:center;padding:3px 12px;border-radius:14px;font-size:.78rem;font-weight:500;border:1px solid var(--border)}}
.pill-diff-b{{background:var(--green-bg);color:var(--green);border-color:#BBF7D0}}
.pill-diff-i{{background:var(--amber-bg);color:var(--amber);border-color:#FDE68A}}
.pill-diff-a{{background:var(--rose-bg);color:var(--rose);border-color:#FECACA}}
.pill-cat{{background:var(--ink-light);color:var(--ink-deep);border-color:var(--ink-mid)}}
.pill-mono{{font-family:var(--mono);font-size:.72rem;color:var(--text-3)}}
.tag{{display:inline-flex;padding:2px 10px;border-radius:10px;font-size:.72rem;background:var(--card);border:1px solid var(--border);color:var(--text-3);margin:2px}}
.yt-btn{{display:inline-flex;align-items:center;gap:6px;padding:6px 14px;border-radius:8px;background:var(--ink);color:#fff;text-decoration:none;font-size:.82rem;font-weight:500;transition:all .2s}}
.yt-btn:hover{{background:var(--ink-deep)}}

/* Overview */
.overview{{font-size:1rem;color:var(--text-2);line-height:1.9;margin-bottom:32px;padding:24px 28px;background:var(--card);border:1px solid var(--border);border-radius:var(--r);box-shadow:var(--sh)}}

/* Module divider */
.module{{margin-bottom:40px}}
.module-title{{font-family:var(--serif);font-size:1.2rem;font-weight:600;margin-bottom:16px;padding-bottom:10px;border-bottom:2px solid var(--ink-mid);color:var(--text);display:flex;align-items:center;gap:8px}}
.module-icon{{font-size:1rem}}

/* Sections (main content) */
.section-block{{margin-bottom:32px;background:var(--card);border:1px solid var(--border);border-radius:var(--r);padding:28px 32px;box-shadow:var(--sh)}}
.sec-title{{font-family:var(--serif);font-size:1.1rem;font-weight:600;margin-bottom:16px;display:flex;align-items:center;gap:10px}}
.sec-num{{font-family:var(--mono);font-size:.72rem;color:#fff;background:var(--ink);width:28px;height:28px;border-radius:50%;display:inline-flex;align-items:center;justify-content:center;flex-shrink:0}}
.sec-body{{color:var(--text-2);line-height:1.9}}
.sec-body p{{margin-bottom:12px}}
.sec-body strong{{color:var(--text);font-weight:600}}
.subsection{{margin-top:20px;padding-top:16px;border-top:1px solid var(--border-light)}}
.subsec-title{{font-size:.95rem;font-weight:600;margin-bottom:10px;color:var(--text)}}
.subsec-body{{color:var(--text-2)}}
.subsec-body p{{margin-bottom:10px}}

/* Content elements */
.content-list{{margin:12px 0;padding-left:24px}}
.content-list li{{margin-bottom:6px;line-height:1.7}}
.content-h4{{font-size:1rem;font-weight:600;margin:16px 0 8px;color:var(--text)}}
.content-h5{{font-size:.92rem;font-weight:600;margin:12px 0 6px;color:var(--text-2)}}
.code-block{{background:#1E1E2E;color:#CDD6F4;padding:16px 20px;border-radius:var(--r-sm);overflow-x:auto;font-family:var(--mono);font-size:.82rem;line-height:1.6;margin:12px 0}}
.inline-code{{background:var(--ink-light);color:var(--ink-deep);padding:1px 6px;border-radius:4px;font-family:var(--mono);font-size:.85em}}

/* Resources table */
.res-table{{width:100%;border-collapse:collapse;margin:8px 0;font-size:.88rem}}
.res-table th{{text-align:left;padding:10px 12px;border-bottom:2px solid var(--border);color:var(--text-3);font-weight:500;font-size:.78rem}}
.res-table td{{padding:10px 12px;border-bottom:1px solid var(--border-light)}}
.res-name{{font-weight:500;white-space:nowrap}}
.res-name a{{text-decoration:none}}
.res-name a:hover{{text-decoration:underline}}
.res-type{{font-size:.65rem;padding:2px 6px;border-radius:6px;background:var(--ink-light);color:var(--ink);margin-left:6px;font-weight:500}}
.res-desc{{color:var(--text-3)}}

/* Tips */
.tips-list{{list-style:none;padding:0}}
.tips-list li{{padding:10px 16px 10px 40px;position:relative;border-bottom:1px solid var(--border-light);font-size:.92rem}}
.tips-list li::before{{content:'\\2713';position:absolute;left:12px;top:10px;color:var(--green);font-weight:700}}

/* FAQ */
.faq-item{{margin-bottom:16px;padding:16px 20px;background:var(--card);border:1px solid var(--border);border-radius:var(--r-sm)}}
.faq-q{{font-weight:600;color:var(--ink-deep);margin-bottom:8px}}
.faq-a{{color:var(--text-2);font-size:.92rem}}
.faq-a p{{margin-bottom:6px}}

/* Audience */
.audience-list{{padding-left:24px}}
.audience-list li{{margin-bottom:6px;font-size:.92rem}}

/* Links */
.links-list{{list-style:none;padding:0}}
.links-list li{{padding:6px 0;border-bottom:1px solid var(--border-light);font-size:.88rem}}

/* Summary box */
.summary-box{{background:linear-gradient(135deg,var(--ink-light) 0%,#F5F3FF 100%);border:1px solid var(--ink-mid);border-radius:var(--r);padding:28px 32px;margin-top:16px}}
.summary-box p{{color:var(--text);line-height:1.9;font-size:.95rem}}

/* HW requirements */
.hw-box{{background:var(--teal-bg);border:1px solid #99F6E4;border-radius:var(--r-sm);padding:16px 20px;font-size:.88rem;color:#0F766E}}

/* Video player */
.player-grid{{display:grid;grid-template-columns:1fr 340px;gap:16px;align-items:start;margin-bottom:8px}}
.player-grid video,.player-grid .embed-wrap{{width:100%;border-radius:var(--r);background:#0a0a0f;aspect-ratio:16/9}}
.scene-scroll{{max-height:400px;overflow-y:auto;display:flex;flex-direction:column;gap:6px;padding-right:4px}}
.scene-scroll::-webkit-scrollbar{{width:3px}}
.scene-scroll::-webkit-scrollbar-thumb{{background:var(--border);border-radius:2px}}
.scene-label{{font-size:.78rem;color:var(--text-3);margin-bottom:6px}}
.sc{{background:var(--card);border:1px solid var(--border);border-left:3px solid transparent;border-radius:8px;padding:10px 12px;cursor:pointer;transition:all .2s;font-size:.82rem}}
.sc:hover{{border-left-color:var(--ink-mid);background:#FEFDFB}}
.sc.active{{border-left-color:var(--ink);background:var(--ink-light)}}
.sc-head{{display:flex;justify-content:space-between;align-items:center;margin-bottom:3px}}
.sc-id{{font-weight:600;font-size:.72rem;color:var(--ink)}}
.sc-time{{font-size:.68rem;color:var(--text-4)}}
.sc-concept{{font-weight:600;font-size:.82rem;margin-bottom:2px}}
.sc-narr{{font-size:.75rem;color:var(--text-3);line-height:1.5;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden}}
.sc-tags{{display:flex;gap:4px;margin-top:4px}}
.sc-tag{{font-size:.65rem;padding:1px 6px;border-radius:8px;background:#F5F5F4;color:var(--text-4)}}
.sc-tag.method{{background:var(--ink-light);color:var(--ink)}}
.clarity-dot{{width:6px;height:6px;border-radius:50%;display:inline-block;margin-left:2px}}
.clarity-high{{background:var(--green)}}.clarity-medium{{background:var(--amber)}}.clarity-low{{background:var(--rose)}}

.empty-hint{{color:var(--text-4);font-size:.88rem;font-style:italic}}

/* Footer */
.foot{{text-align:center;padding:24px 0;color:var(--text-4);font-size:.78rem;border-top:1px solid var(--border-light);margin-top:40px}}
.foot a{{color:var(--ink);text-decoration:none}}

@media(max-width:768px){{
  .page{{padding:20px 16px 60px}}
  .player-grid{{grid-template-columns:1fr}}
  .scene-scroll{{max-height:260px}}
  .section-block{{padding:20px}}
}}
</style>
</head>
<body>
<div class="page">

<!-- Header -->
<div class="badge-line">VIDEO LEARNING NOTES</div>
<h1>{escape_html(title_cn)}</h1>
<div class="meta-row">
  <span class="pill {diff_class}">{diff_label}</span>
  <span class="pill pill-cat">{escape_html(category)}</span>
  {f'<span class="pill pill-mono">{escape_html(speaker)}</span>' if speaker else ''}
  {f'<span class="pill pill-mono">{duration_str}</span>' if duration_str else ''}
  <span class="pill pill-mono">{date_str}</span>
  {yt_btn}
</div>
{f'<div style="margin-bottom:16px">{tags_html}</div>' if tags_html else ''}

<!-- Overview -->
<div class="overview">{escape_html(overview)}</div>

<!-- Video Embed -->
{f'<div class="module"><div class="module-title">视频播放</div>{video_embed_html}</div>' if video_embed_html else ""}

<!-- Main Content Sections -->
<div class="module">
  <div class="module-title">详细内容</div>
  {sections_html if sections_html else '<p class="empty-hint">暂无详细内容分析</p>'}
</div>

<!-- Resources -->
<div class="module">
  <div class="module-title">工具与资源</div>
  <div class="section-block" style="padding:20px 24px">
    {resources_html}
  </div>
</div>

<!-- Key Tips -->
{f"""<div class="module">
  <div class="module-title">实用技巧与最佳实践</div>
  <div class="section-block" style="padding:16px 20px">
    {tips_html}
  </div>
</div>""" if tips_html else ""}

<!-- Hardware Requirements -->
{f"""<div class="module">
  <div class="module-title">硬件要求</div>
  <div class="hw-box">{escape_html(hw_req)}</div>
</div>""" if hw_req else ""}

<!-- FAQ -->
{f"""<div class="module">
  <div class="module-title">常见问题</div>
  {faq_html}
</div>""" if faq_html else ""}

<!-- Target Audience -->
{f"""<div class="module">
  <div class="module-title">适用人群</div>
  <div class="section-block" style="padding:16px 24px">
    {audience_html}
  </div>
</div>""" if audience_html else ""}

<!-- Summary -->
{f"""<div class="module">
  <div class="module-title">总结</div>
  <div class="summary-box"><p>{escape_html(summary)}</p></div>
</div>""" if summary else ""}

<!-- Related Links -->
{f"""<div class="module">
  <div class="module-title">相关链接</div>
  <div class="section-block" style="padding:16px 24px">
    {links_html}
  </div>
</div>""" if links_html else ""}

<div class="foot">
  Powered by <a href="https://github.com/anthropics/claude-code" target="_blank">Claude Code</a> video-learn skill
</div>

</div>

<script>/* video-learn report */</script>
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

    title = args.title or analysis.get("_meta", {}).get("title", "学习笔记")

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
