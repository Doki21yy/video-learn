#!/usr/bin/env python3
"""Frontend generator for Video Learning Archive on GitHub Pages.
   Dark minimalist premium design.
"""


def generate_dashboard_html():
    return '''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Learning Archive</title>
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;700;900&display=swap');
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Mono:wght@400;500&display=swap');

*, *::before, *::after { margin: 0; padding: 0; box-sizing: border-box; }

:root {
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
  --bili: #00A1D6;
  --yt: #FF0000;
  --xhs: #FE2C55;
  --dy: #FFFFFF;
  --radius: 12px;
  --font-heading: 'DM Sans', -apple-system, sans-serif;
  --font-mono: 'IBM Plex Mono', monospace;
}

html { scroll-behavior: smooth; }

body {
  background: var(--bg-deep);
  color: var(--text-primary);
  font-family: var(--font-heading);
  font-weight: 400;
  line-height: 1.6;
  min-height: 100vh;
  overflow-x: hidden;
}

body::before {
  content: '';
  position: fixed;
  top: -200px;
  left: 50%;
  transform: translateX(-50%);
  width: 800px;
  height: 600px;
  background: radial-gradient(ellipse, rgba(99, 102, 241, 0.06) 0%, transparent 70%);
  pointer-events: none;
  z-index: 0;
}

.container {
  max-width: 1200px;
  margin: 0 auto;
  padding: 0 24px;
  position: relative;
  z-index: 1;
}

/* Header */
.header {
  padding: 80px 0 40px;
  text-align: left;
}

.header h1 {
  font-family: var(--font-heading);
  font-weight: 900;
  font-size: clamp(2.4rem, 5vw, 3.6rem);
  letter-spacing: -0.03em;
  color: var(--text-primary);
  line-height: 1.1;
}

.header h1 span {
  background: linear-gradient(135deg, var(--accent-soft), var(--accent));
  -webkit-background-clip: text;
  -webkit-text-fill-color: transparent;
  background-clip: text;
}

.header .subtitle {
  margin-top: 12px;
  font-family: var(--font-mono);
  font-size: 0.85rem;
  color: var(--text-muted);
  letter-spacing: 0.02em;
}

.header .subtitle .count { color: var(--accent-soft); }

/* Filter Bar */
.filter-bar {
  display: flex;
  align-items: center;
  gap: 12px;
  padding: 20px 0 32px;
  border-top: 1px solid var(--border-subtle);
  flex-wrap: wrap;
}

.filter-group {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}

.filter-chip {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 7px 16px;
  border-radius: 100px;
  border: 1px solid var(--border-subtle);
  background: transparent;
  color: var(--text-secondary);
  font-family: var(--font-heading);
  font-size: 0.8rem;
  font-weight: 500;
  cursor: pointer;
  transition: all 0.25s ease;
  white-space: nowrap;
}

.filter-chip:hover {
  border-color: var(--border-hover);
  color: var(--text-primary);
  background: rgba(99, 102, 241, 0.05);
}

.filter-chip.active {
  border-color: var(--accent);
  color: var(--text-primary);
  background: var(--accent-glow);
  box-shadow: 0 0 20px rgba(99, 102, 241, 0.1);
}

.filter-chip .dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
}

.filter-separator {
  width: 1px;
  height: 24px;
  background: var(--border-subtle);
  margin: 0 8px;
}

.sort-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  padding: 7px 14px;
  border-radius: 100px;
  border: 1px solid var(--border-subtle);
  background: transparent;
  color: var(--text-secondary);
  font-family: var(--font-mono);
  font-size: 0.75rem;
  cursor: pointer;
  transition: all 0.25s ease;
}

.sort-btn:hover {
  border-color: var(--border-hover);
  color: var(--text-primary);
}

.sort-btn.active {
  color: var(--accent-soft);
  border-color: rgba(99, 102, 241, 0.15);
}

.sort-btn svg { width: 14px; height: 14px; opacity: 0.6; }

/* Video Grid */
.video-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(320px, 1fr));
  gap: 20px;
  padding-bottom: 80px;
}

.video-card {
  background: var(--bg-card);
  border: 1px solid var(--border-subtle);
  border-radius: var(--radius);
  overflow: hidden;
  cursor: pointer;
  transition: all 0.35s cubic-bezier(0.23, 1, 0.32, 1);
  text-decoration: none;
  color: inherit;
  display: block;
}

.video-card:hover {
  background: var(--bg-card-hover);
  border-color: var(--border-hover);
  transform: translateY(-4px);
  box-shadow:
    0 20px 40px rgba(0, 0, 0, 0.3),
    0 0 60px rgba(99, 102, 241, 0.06);
}

.card-thumb {
  position: relative;
  width: 100%;
  padding-top: 56.25%;
  background: var(--bg-surface);
  overflow: hidden;
}

.card-thumb img {
  position: absolute;
  top: 0; left: 0;
  width: 100%; height: 100%;
  object-fit: cover;
  transition: transform 0.5s cubic-bezier(0.23, 1, 0.32, 1);
}

.video-card:hover .card-thumb img { transform: scale(1.04); }

.card-thumb .platform-badge {
  position: absolute;
  top: 10px; left: 10px;
  display: flex;
  align-items: center;
  gap: 5px;
  padding: 4px 10px;
  border-radius: 6px;
  background: rgba(0, 0, 0, 0.7);
  backdrop-filter: blur(8px);
  font-family: var(--font-mono);
  font-size: 0.65rem;
  font-weight: 500;
  color: #fff;
  letter-spacing: 0.04em;
  text-transform: uppercase;
}

.card-thumb .platform-badge .p-dot {
  width: 6px; height: 6px;
  border-radius: 50%;
}

.card-thumb .duration-badge {
  position: absolute;
  bottom: 10px; right: 10px;
  padding: 3px 8px;
  border-radius: 4px;
  background: rgba(0, 0, 0, 0.75);
  backdrop-filter: blur(8px);
  font-family: var(--font-mono);
  font-size: 0.7rem;
  color: rgba(255, 255, 255, 0.85);
}

.card-body { padding: 16px 18px 20px; }

.card-title {
  font-family: var(--font-heading);
  font-weight: 700;
  font-size: 0.95rem;
  line-height: 1.4;
  color: var(--text-primary);
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
  margin-bottom: 10px;
}

.card-meta {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-bottom: 8px;
}

.card-score {
  font-family: var(--font-mono);
  font-size: 0.75rem;
  font-weight: 500;
  padding: 2px 8px;
  border-radius: 4px;
  background: var(--accent-glow);
  color: var(--accent-soft);
  border: 1px solid rgba(99, 102, 241, 0.15);
}

.card-date {
  font-family: var(--font-mono);
  font-size: 0.72rem;
  color: var(--text-muted);
}

.card-summary {
  font-size: 0.82rem;
  line-height: 1.55;
  color: var(--text-secondary);
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

/* Empty State */
.empty-state {
  text-align: center;
  padding: 80px 20px;
  color: var(--text-muted);
  font-size: 0.9rem;
  grid-column: 1 / -1;
}

/* Footer */
.footer {
  padding: 40px 0;
  text-align: center;
  border-top: 1px solid var(--border-subtle);
  font-family: var(--font-mono);
  font-size: 0.72rem;
  color: var(--text-muted);
  letter-spacing: 0.03em;
}

/* Shimmer loading */
.card-thumb.loading {
  background: linear-gradient(110deg, var(--bg-surface) 8%, #1a1a28 18%, var(--bg-surface) 33%);
  background-size: 200% 100%;
  animation: shimmer 1.5s infinite linear;
}

@keyframes shimmer { to { background-position-x: -200%; } }

/* Animations */
@keyframes fadeInUp {
  from { opacity: 0; transform: translateY(20px); }
  to { opacity: 1; transform: translateY(0); }
}

.video-card { animation: fadeInUp 0.5s ease both; }
.video-card:nth-child(1) { animation-delay: 0.05s; }
.video-card:nth-child(2) { animation-delay: 0.1s; }
.video-card:nth-child(3) { animation-delay: 0.15s; }
.video-card:nth-child(4) { animation-delay: 0.2s; }
.video-card:nth-child(5) { animation-delay: 0.25s; }
.video-card:nth-child(6) { animation-delay: 0.3s; }

/* Responsive */
@media (max-width: 768px) {
  .container { padding: 0 16px; }
  .header { padding: 48px 0 24px; }
  .video-grid { grid-template-columns: 1fr; gap: 16px; }
  .filter-separator { display: none; }
  .filter-bar { gap: 8px; }
}
</style>
</head>
<body>

<div class="container">
  <header class="header">
    <h1>Learning <span>Archive</span></h1>
    <p class="subtitle">// <span class="count" id="videoCount">0</span> videos indexed</p>
  </header>

  <div class="filter-bar">
    <div class="filter-group" id="platformFilters">
      <button class="filter-chip active" data-platform="all">All</button>
      <button class="filter-chip" data-platform="bilibili">
        <span class="dot" style="background: var(--bili)"></span>Bilibili
      </button>
      <button class="filter-chip" data-platform="youtube">
        <span class="dot" style="background: var(--yt)"></span>YouTube
      </button>
      <button class="filter-chip" data-platform="xiaohongshu">
        <span class="dot" style="background: var(--xhs)"></span>Xiaohongshu
      </button>
      <button class="filter-chip" data-platform="douyin">
        <span class="dot" style="background: var(--dy)"></span>Douyin
      </button>
    </div>
    <div class="filter-separator"></div>
    <button class="sort-btn active" id="sortLatest" data-sort="date">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 5v14M5 12l7 7 7-7"/></svg>
      Latest
    </button>
    <button class="sort-btn" id="sortScore" data-sort="score">
      <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M12 2l3.09 6.26L22 9.27l-5 4.87L18.18 22 12 18.56 5.82 22 7 14.14 2 9.27l6.91-1.01L12 2z"/></svg>
      Score
    </button>
  </div>

  <div class="video-grid" id="videoGrid">
    <div class="empty-state">Loading archive...</div>
  </div>
</div>

<footer class="footer">
  <div class="container">powered by video-learn</div>
</footer>

<script>
const PLATFORM_COLORS = {
  bilibili: '#00A1D6',
  youtube: '#FF0000',
  xiaohongshu: '#FE2C55',
  douyin: '#FFFFFF',
  unknown: '#6366F1'
};

const PLATFORM_LABELS = {
  bilibili: 'BILI',
  youtube: 'YT',
  xiaohongshu: 'XHS',
  douyin: 'DY',
  unknown: '--'
};

let allVideos = [];
let currentPlatform = 'all';
let currentSort = 'date';

function formatDuration(seconds) {
  if (!seconds) return '';
  const m = Math.floor(seconds / 60);
  const s = Math.floor(seconds % 60);
  return m + ':' + String(s).padStart(2, '0');
}

function detectPlatform(v) {
  if (v.platform) return v.platform.toLowerCase();
  const url = v.source_url || '';
  if (url.includes('bilibili')) return 'bilibili';
  if (url.includes('youtube') || url.includes('youtu.be')) return 'youtube';
  if (url.includes('xiaohongshu') || url.includes('xhslink')) return 'xiaohongshu';
  if (url.includes('douyin')) return 'douyin';
  return 'unknown';
}

function getScore(v) {
  return v.learning_rating || v.score || v.overall_score || 0;
}

function getThumbUrl(v) {
  if (v.thumbnail && (v.thumbnail.startsWith('http') || v.thumbnail.startsWith('data:'))) return v.thumbnail;
  if (v.thumbnail) return v.thumbnail;
  if (v.slug) return './data/videos/' + v.slug + '/thumbnail.jpg';
  return '';
}

function escapeHtml(str) {
  const div = document.createElement('div');
  div.textContent = str;
  return div.innerHTML;
}

function renderCards(videos) {
  const grid = document.getElementById('videoGrid');
  if (!videos.length) {
    grid.innerHTML = '<div class="empty-state">No videos found</div>';
    return;
  }
  grid.innerHTML = videos.map((v, i) => {
    const platform = detectPlatform(v);
    const color = PLATFORM_COLORS[platform] || PLATFORM_COLORS.unknown;
    const label = PLATFORM_LABELS[platform] || '--';
    const score = getScore(v);
    const thumb = getThumbUrl(v);
    const duration = formatDuration(v.duration);
    const reportUrl = v.report || '#';
    const date = v.date || '';
    return `
      <a class="video-card" href="${reportUrl}" style="animation-delay:${Math.min(i * 0.05, 0.3)}s">
        <div class="card-thumb${thumb ? '' : ' loading'}">
          ${thumb ? `<img src="${thumb}" alt="" loading="lazy" onerror="this.parentElement.classList.add('loading');this.remove()">` : ''}
          <div class="platform-badge"><span class="p-dot" style="background:${color}"></span>${label}</div>
          ${duration ? `<div class="duration-badge">${duration}</div>` : ''}
        </div>
        <div class="card-body">
          <div class="card-title">${escapeHtml(v.title || 'Untitled')}</div>
          <div class="card-meta">
            ${score ? `<span class="card-score">${Number(score).toFixed(1)}</span>` : ''}
            <span class="card-date">${date}</span>
          </div>
          ${v.summary ? `<div class="card-summary">${escapeHtml(v.summary)}</div>` : ''}
        </div>
      </a>
    `;
  }).join('');
}

function filterAndSort() {
  let filtered = currentPlatform === 'all'
    ? [...allVideos]
    : allVideos.filter(v => detectPlatform(v) === currentPlatform);

  if (currentSort === 'score') {
    filtered.sort((a, b) => getScore(b) - getScore(a));
  } else {
    filtered.sort((a, b) => (b.date || '').localeCompare(a.date || ''));
  }
  renderCards(filtered);
}

// Platform filter
document.getElementById('platformFilters').addEventListener('click', e => {
  const chip = e.target.closest('.filter-chip');
  if (!chip) return;
  document.querySelectorAll('.filter-chip').forEach(c => c.classList.remove('active'));
  chip.classList.add('active');
  currentPlatform = chip.dataset.platform;
  filterAndSort();
});

// Sort
document.querySelectorAll('.sort-btn').forEach(btn => {
  btn.addEventListener('click', () => {
    document.querySelectorAll('.sort-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    currentSort = btn.dataset.sort;
    filterAndSort();
  });
});

// Load data
fetch('./data/catalog.json')
  .then(r => r.json())
  .then(data => {
    allVideos = data.videos || [];
    document.getElementById('videoCount').textContent = allVideos.length;
    filterAndSort();
  })
  .catch(() => {
    document.getElementById('videoGrid').innerHTML =
      '<div class="empty-state">Archive empty. Analyze your first video to get started.</div>';
  });
</script>
</body>
</html>'''


def generate_readme(owner, repo_name):
    return f'''# Learning Archive

Auto-updated video learning archive powered by Claude Code video-learn skill.

## How it works

1. Learn from videos with `/video-learn <URL>` -- generates structured learning notes
2. Results are automatically synced to this repo
3. Dashboard: https://{owner}.github.io/{repo_name}/

## Supported Platforms

- Bilibili / YouTube / Xiaohongshu / Douyin
'''


if __name__ == "__main__":
    print(generate_dashboard_html()[:200])
