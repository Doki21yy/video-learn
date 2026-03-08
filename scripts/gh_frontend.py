#!/usr/bin/env python3
"""Frontend generator for Video Learning Library on GitHub Pages.
   Warm editorial notebook style matching the video-learn report design.
"""


def generate_dashboard_html():
    return '''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Video Learning Library</title>
<link rel="preconnect" href="https://fonts.googleapis.com">
<link href="https://fonts.googleapis.com/css2?family=Noto+Serif+SC:wght@400;600;700&family=DM+Sans:ital,opsz,wght@0,9..40,300;0,9..40,400;0,9..40,500;0,9..40,600;0,9..40,700;1,9..40,400&family=JetBrains+Mono:wght@400;500&display=swap" rel="stylesheet">
<link rel="stylesheet" href="assets/styles.css">
</head>
<body>

<header class="site-header">
  <div class="header-inner">
    <span class="site-logo">VIDEO LEARNING LIBRARY</span>
    <h1 class="site-title">&#x89C6;&#x9891;&#x5B66;&#x4E60;&#x77E5;&#x8BC6;&#x5E93;</h1>
    <p class="site-subtitle">&#x6DF1;&#x5EA6;&#x5B66;&#x4E60;&#x3001;&#x7ED3;&#x6784;&#x5316;&#x603B;&#x7ED3;&#x3001;&#x77E5;&#x8BC6;&#x6C89;&#x6DC0; &mdash; &#x8BA9;&#x6BCF;&#x4E00;&#x6B21;&#x89C2;&#x770B;&#x90FD;&#x6709;&#x4EF7;&#x503C;</p>
  </div>
</header>

<div class="stats-bar" id="statsBar">
  <div class="stat-card">
    <div class="stat-icon si-ink">
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M23 7l-7 5 7 5V7z"/><rect x="1" y="5" width="15" height="14" rx="2"/></svg>
    </div>
    <span class="stat-value" id="statTotal">--</span>
    <span class="stat-label">&#x5DF2;&#x5206;&#x6790;&#x89C6;&#x9891;</span>
  </div>
  <div class="stat-card">
    <div class="stat-icon si-ink">
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"/></svg>
    </div>
    <span class="stat-value" id="statAvgScore">--</span>
    <span class="stat-label">&#x5E73;&#x5747;&#x8BC4;&#x5206;</span>
  </div>
  <div class="stat-card">
    <div class="stat-icon si-teal">
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"/><path d="M12 6v6l4 2"/></svg>
    </div>
    <span class="stat-value" id="statWatchTime">--</span>
    <span class="stat-label">&#x603B;&#x65F6;&#x957F;</span>
  </div>
  <div class="stat-card">
    <div class="stat-icon si-green">
      <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="3" y="4" width="18" height="18" rx="2"/><line x1="16" y1="2" x2="16" y2="6"/><line x1="8" y1="2" x2="8" y2="6"/><line x1="3" y1="10" x2="21" y2="10"/></svg>
    </div>
    <span class="stat-value" id="statLatest">--</span>
    <span class="stat-label">&#x6700;&#x8FD1;&#x66F4;&#x65B0;</span>
  </div>
</div>

<div class="container">
  <div class="tab-row" id="platformTabs">
    <button class="tab-btn active" data-platform="">All</button>
  </div>

  <div class="toolbar">
    <div class="search-box">
      <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="8"/><line x1="21" y1="21" x2="16.65" y2="16.65"/></svg>
      <input type="text" id="searchInput" placeholder="&#x641C;&#x7D22;&#x89C6;&#x9891;&#x6807;&#x9898;&#x6216;&#x5185;&#x5BB9;..." />
    </div>
    <select id="sortSelect" class="sort-select">
      <option value="date-desc">&#x6700;&#x65B0;&#x4F18;&#x5148;</option>
      <option value="date-asc">&#x6700;&#x65E9;&#x4F18;&#x5148;</option>
      <option value="score-desc">&#x8BC4;&#x5206;&#x6700;&#x9AD8;</option>
      <option value="score-asc">&#x8BC4;&#x5206;&#x6700;&#x4F4E;</option>
    </select>
  </div>

  <div class="video-grid" id="videoGrid">
    <div class="loading-state"><div class="spinner"></div>Loading catalog...</div>
  </div>

  <div class="empty-state" id="emptyState" style="display:none">
    <p class="empty-title">&#x6CA1;&#x6709;&#x627E;&#x5230;&#x5339;&#x914D;&#x7684;&#x89C6;&#x9891;</p>
    <p class="empty-hint">&#x8BD5;&#x8BD5;&#x5176;&#x4ED6;&#x641C;&#x7D22;&#x5173;&#x952E;&#x8BCD;&#x6216;&#x5207;&#x6362;&#x5206;&#x7C7B;&#x6807;&#x7B7E;</p>
  </div>
</div>

<footer class="site-footer">
  <p>Powered by <a href="https://github.com/anthropics/claude-code" target="_blank">Claude Code</a> video-learn skill</p>
</footer>

<script>
let allVideos = [];
let activePlatform = '';

async function loadCatalog() {
    try {
        const resp = await fetch('data/catalog.json');
        if (!resp.ok) throw new Error('Catalog not found');
        const catalog = await resp.json();
        allVideos = catalog.videos || [];
        updateStats(catalog);
        buildPlatformTabs();
        renderVideos();
    } catch (e) {
        document.getElementById('videoGrid').innerHTML =
            '<div class="loading-state">&#x8FD8;&#x6CA1;&#x6709;&#x89C6;&#x9891;&#xFF0C;&#x8FD0;&#x884C; /video-learn &#x6DFB;&#x52A0;&#x7B2C;&#x4E00;&#x4E2A;&#x5206;&#x6790;&#x3002;</div>';
    }
}

function updateStats(catalog) {
    document.getElementById('statTotal').textContent = catalog.total_videos || 0;
    const videos = catalog.videos || [];
    if (videos.length > 0) {
        const avg = videos.reduce((s, v) => s + (v.score || 0), 0) / videos.length;
        document.getElementById('statAvgScore').textContent = avg.toFixed(1);
        const totalSec = videos.reduce((s, v) => s + (v.duration || 0), 0);
        const hours = Math.floor(totalSec / 3600);
        const mins = Math.floor((totalSec % 3600) / 60);
        document.getElementById('statWatchTime').textContent =
            hours > 0 ? hours + 'h ' + mins + 'm' : mins + 'm';
        document.getElementById('statLatest').textContent = videos[0].date || '--';
    }
}

function buildPlatformTabs() {
    const container = document.getElementById('platformTabs');
    const learningCount = allVideos.filter(v => v.type === 'learning').length;
    const optimizeCount = allVideos.filter(v => v.type !== 'learning').length;
    const platforms = [...new Set(allVideos.filter(v => v.type !== 'learning').map(v => v.platform).filter(Boolean))];
    const counts = {};
    allVideos.filter(v => v.type !== 'learning').forEach(v => { counts[v.platform] = (counts[v.platform] || 0) + 1; });

    container.querySelector('[data-platform=""]').textContent = '\\u5168\\u90E8 (' + allVideos.length + ')';

    if (learningCount > 0) {
        const btn = document.createElement('button');
        btn.className = 'tab-btn tab-learning';
        btn.dataset.platform = '__learning__';
        btn.textContent = '\\u5B66\\u4E60\\u7B14\\u8BB0 (' + learningCount + ')';
        btn.addEventListener('click', () => { setTab(btn, '__learning__'); });
        container.appendChild(btn);
    }
    if (learningCount > 0 && optimizeCount > 0) {
        const btn = document.createElement('button');
        btn.className = 'tab-btn';
        btn.dataset.platform = '__optimize__';
        btn.textContent = '\\u7206\\u6B3E\\u5206\\u6790 (' + optimizeCount + ')';
        btn.addEventListener('click', () => { setTab(btn, '__optimize__'); });
        container.appendChild(btn);
    }
    platforms.forEach(p => {
        const btn = document.createElement('button');
        btn.className = 'tab-btn';
        btn.dataset.platform = p;
        btn.textContent = p + ' (' + (counts[p] || 0) + ')';
        btn.addEventListener('click', () => { setTab(btn, p); });
        container.appendChild(btn);
    });
    container.querySelector('[data-platform=""]').addEventListener('click', function() { setTab(this, ''); });
}

function setTab(btn, platform) {
    document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
    btn.classList.add('active');
    activePlatform = platform;
    renderVideos();
}

function getFilteredVideos() {
    const query = document.getElementById('searchInput').value.toLowerCase();
    const platform = activePlatform;
    const sort = document.getElementById('sortSelect').value;
    let filtered = allVideos.filter(v => {
        if (query && !v.title.toLowerCase().includes(query) &&
            !(v.summary || '').toLowerCase().includes(query)) return false;
        if (platform === '__learning__' && v.type !== 'learning') return false;
        if (platform === '__optimize__' && v.type === 'learning') return false;
        if (platform && platform !== '__learning__' && platform !== '__optimize__' && v.platform !== platform) return false;
        return true;
    });
    filtered.sort((a, b) => {
        switch (sort) {
            case 'date-desc': return (b.date || '').localeCompare(a.date || '');
            case 'date-asc': return (a.date || '').localeCompare(b.date || '');
            case 'score-desc': return (b.score || 0) - (a.score || 0);
            case 'score-asc': return (a.score || 0) - (b.score || 0);
            default: return 0;
        }
    });
    return filtered;
}

function formatDuration(seconds) {
    if (!seconds) return '--';
    const m = Math.floor(seconds / 60);
    const s = Math.floor(seconds % 60);
    return m + ':' + String(s).padStart(2, '0');
}

function scoreRingSvg(score, strokeColor) {
    const circ = 125.7;
    const offset = circ - (score / 10.0) * circ;
    return '<svg width="44" height="44" viewBox="0 0 52 52">' +
      '<circle cx="26" cy="26" r="20" fill="none" stroke="#EDEBE4" stroke-width="3.5"/>' +
      '<circle cx="26" cy="26" r="20" fill="none" stroke="' + strokeColor + '" stroke-width="3.5" ' +
      'stroke-dasharray="' + circ.toFixed(1) + '" stroke-dashoffset="' + offset.toFixed(1) + '" stroke-linecap="round"/>' +
      '</svg>';
}

function scoreStrokeColor(score) {
    if (score >= 8) return '#16A34A';
    if (score >= 6) return '#D97706';
    return '#E11D48';
}

function scoreTextClass(score) {
    if (score >= 8) return 'ring-num-green';
    if (score >= 6) return 'ring-num-amber';
    return 'ring-num-rose';
}

function platformIcon(platform) {
    return {'YouTube':'YT','Bilibili':'B','Douyin':'DY','Xiaohongshu':'XHS','TikTok':'TT'}[platform] || '?';
}

function platformBadgeClass(platform) {
    return {'YouTube':'badge-yt','Bilibili':'badge-bili','Douyin':'badge-dy',
            'Xiaohongshu':'badge-xhs','TikTok':'badge-tt'}[platform] || 'badge-default';
}

function renderVideos() {
    const grid = document.getElementById('videoGrid');
    const empty = document.getElementById('emptyState');
    const videos = getFilteredVideos();
    if (videos.length === 0) { grid.innerHTML = ''; empty.style.display = 'block'; return; }
    empty.style.display = 'none';

    grid.innerHTML = videos.map(v => {
        const score = v.learning_rating || v.score || 0;
        const isLearning = v.type === 'learning';

        if (isLearning) {
            const diffMap = {'beginner':['\\u521D\\u7EA7','pill-diff-b'],'intermediate':['\\u4E2D\\u7EA7','pill-diff-i'],'advanced':['\\u9AD8\\u7EA7','pill-diff-a']};
            const [diffLabel, diffClass] = diffMap[v.difficulty] || diffMap['intermediate'];
            return `
            <a class="video-card" href="${v.report || '#'}">
              <div class="card-thumb">
                <img src="${v.thumbnail || ''}" alt="" loading="lazy" onerror="this.style.display='none'" />
                <span class="card-duration">${formatDuration(v.duration)}</span>
                <span class="card-badge badge-learn">LEARN</span>
              </div>
              <div class="card-body">
                <div class="card-head">
                  <div class="card-ring">
                    ${scoreRingSvg(score, '#6C63FF')}
                    <span class="ring-num ring-num-ink">${score}</span>
                  </div>
                  <div class="card-info">
                    <h3 class="card-title">${escapeHtml(v.title || 'Untitled')}</h3>
                    <div class="card-tags">
                      <span class="card-pill ${diffClass}">${diffLabel}</span>
                      ${v.category ? '<span class="card-pill pill-cat">' + escapeHtml(v.category) + '</span>' : ''}
                      <span class="card-date">${v.date || ''}</span>
                    </div>
                  </div>
                </div>
                <p class="card-summary">${escapeHtml((v.summary || '').substring(0, 120))}${(v.summary || '').length > 120 ? '...' : ''}</p>
              </div>
            </a>`;
        }

        const strokeColor = scoreStrokeColor(score);
        const textClass = scoreTextClass(score);
        const badgeCls = platformBadgeClass(v.platform);
        return `
        <a class="video-card" href="${v.report || '#'}">
          <div class="card-thumb">
            <img src="${v.thumbnail || ''}" alt="" loading="lazy" onerror="this.style.display='none'" />
            <span class="card-duration">${formatDuration(v.duration)}</span>
            <span class="card-badge ${badgeCls}">${platformIcon(v.platform)}</span>
          </div>
          <div class="card-body">
            <div class="card-head">
              <div class="card-ring">
                ${scoreRingSvg(score, strokeColor)}
                <span class="ring-num ${textClass}">${score}</span>
              </div>
              <div class="card-info">
                <h3 class="card-title">${escapeHtml(v.title || 'Untitled')}</h3>
                <div class="card-tags">
                  <span class="card-pill pill-platform">${v.platform || ''}</span>
                  <span class="card-date">${v.date || ''}</span>
                </div>
              </div>
            </div>
            <p class="card-summary">${escapeHtml((v.summary || '').substring(0, 120))}${(v.summary || '').length > 120 ? '...' : ''}</p>
          </div>
        </a>`;
    }).join('');
}

function escapeHtml(str) {
    const div = document.createElement('div');
    div.textContent = str;
    return div.innerHTML;
}

document.getElementById('searchInput').addEventListener('input', renderVideos);
document.getElementById('sortSelect').addEventListener('change', renderVideos);
loadCatalog();
</script>

</body>
</html>'''


def generate_styles_css():
    return '''/* Video Learning Library - Editorial Notebook Style */
*{margin:0;padding:0;box-sizing:border-box}
:root{
  --bg:#F6F5F0;--bg-warm:#FAF9F5;--card:#FFFFFF;--card-alt:#FAFAF7;
  --border:#E2E0D8;--border-light:#EDEBE4;
  --text:#1A1816;--text-2:#4A4640;--text-3:#8A857D;--text-4:#B5B0A6;
  --ink:#6C63FF;--ink-light:#EEEDFF;--ink-mid:#C5C1FF;--ink-deep:#4F46E5;
  --teal:#0D9488;--teal-bg:#F0FDFA;--amber:#D97706;--amber-bg:#FFFBEB;
  --rose:#E11D48;--rose-bg:#FFF1F2;--green:#16A34A;--green-bg:#F0FDF4;
  --serif:'Noto Serif SC',Georgia,serif;
  --sans:'DM Sans',-apple-system,BlinkMacSystemFont,'Noto Sans SC',sans-serif;
  --mono:'JetBrains Mono',monospace;
  --r:14px;--r-sm:8px;
  --sh:0 1px 2px rgba(26,24,22,.04),0 2px 8px rgba(26,24,22,.04);
  --sh-md:0 2px 8px rgba(26,24,22,.06),0 8px 24px rgba(26,24,22,.06);
  --sh-lg:0 4px 12px rgba(26,24,22,.06),0 16px 40px rgba(26,24,22,.08);
}
html{scroll-behavior:smooth}
body{font-family:var(--sans);background:var(--bg);color:var(--text);line-height:1.7;-webkit-font-smoothing:antialiased;font-size:15px}

/* Header */
.site-header{
  background:var(--card);border-bottom:1px solid var(--border);
  padding:40px 28px 36px;text-align:center;position:relative;overflow:hidden;
}
.site-header::before{
  content:'';position:absolute;top:-50%;left:-10%;width:120%;height:200%;
  background:radial-gradient(ellipse at 30% 20%,rgba(108,99,255,.05) 0%,transparent 60%),
             radial-gradient(ellipse at 70% 80%,rgba(13,148,136,.04) 0%,transparent 50%);
  pointer-events:none;
}
.header-inner{max-width:800px;margin:0 auto;position:relative}
.site-logo{
  font-family:var(--mono);font-size:.72rem;color:var(--ink);background:var(--ink-light);
  padding:4px 14px;border-radius:20px;display:inline-block;margin-bottom:16px;
  letter-spacing:.06em;font-weight:500;
}
.site-title{
  font-family:var(--serif);font-size:clamp(1.5rem,3.5vw,2.1rem);font-weight:700;
  letter-spacing:-.02em;color:var(--text);margin-bottom:8px;line-height:1.3;
}
.site-subtitle{font-size:.92rem;color:var(--text-3);font-weight:400;max-width:44ch;margin:0 auto}

/* Stats */
.stats-bar{
  display:grid;grid-template-columns:repeat(4,1fr);gap:16px;
  max-width:1200px;margin:-28px auto 0;padding:0 28px;position:relative;z-index:1;
}
.stat-card{
  background:var(--card);border:1px solid var(--border);border-radius:var(--r);
  padding:20px 24px;text-align:center;box-shadow:var(--sh);
  transition:box-shadow .2s,transform .2s;
}
.stat-card:hover{box-shadow:var(--sh-md);transform:translateY(-2px)}
.stat-icon{
  width:36px;height:36px;border-radius:var(--r-sm);
  display:inline-flex;align-items:center;justify-content:center;margin-bottom:10px;
}
.si-ink{background:var(--ink-light);color:var(--ink)}
.si-teal{background:var(--teal-bg);color:var(--teal)}
.si-green{background:var(--green-bg);color:var(--green)}
.stat-value{
  display:block;font-family:var(--mono);font-size:1.5rem;font-weight:700;
  color:var(--text);letter-spacing:-.02em;
}
.stat-label{display:block;font-size:.78rem;color:var(--text-3);margin-top:2px;font-weight:400}

/* Container */
.container{max-width:1200px;margin:0 auto;padding:32px 28px 64px}

/* Tabs */
.tab-row{
  display:flex;align-items:center;gap:8px;margin-bottom:20px;
  padding-bottom:16px;border-bottom:1px solid var(--border-light);flex-wrap:wrap;
}
.tab-btn{
  padding:7px 18px;border-radius:20px;border:1px solid var(--border);
  background:transparent;color:var(--text-3);font-size:.84rem;font-weight:500;
  cursor:pointer;transition:all .2s;font-family:var(--sans);
}
.tab-btn:hover{border-color:var(--ink-mid);color:var(--ink);background:var(--ink-light)}
.tab-btn.active{background:var(--ink);color:#fff;border-color:var(--ink);font-weight:600}
.tab-btn.tab-learning.active{background:linear-gradient(135deg,var(--ink),var(--ink-deep));border-color:var(--ink-deep)}

/* Toolbar */
.toolbar{display:flex;gap:12px;margin-bottom:24px;flex-wrap:wrap}
.search-box{flex:1;min-width:220px;position:relative}
.search-box input{
  width:100%;padding:10px 16px 10px 40px;border-radius:var(--r);
  border:1px solid var(--border);background:var(--card);color:var(--text);
  font-size:.9rem;font-family:var(--sans);outline:none;transition:all .2s;
}
.search-box input:focus{border-color:var(--ink);box-shadow:0 0 0 3px rgba(108,99,255,.08)}
.search-box input::placeholder{color:var(--text-4)}
.search-box svg{position:absolute;left:14px;top:50%;transform:translateY(-50%);color:var(--text-4)}
.sort-select{
  padding:10px 32px 10px 14px;border-radius:var(--r);border:1px solid var(--border);
  background:var(--card);color:var(--text-2);font-size:.84rem;font-family:var(--sans);
  cursor:pointer;outline:none;appearance:none;
  background-image:url("data:image/svg+xml,%3Csvg xmlns='http://www.w3.org/2000/svg' width='12' height='12' viewBox='0 0 24 24' fill='%238A857D'%3E%3Cpath d='M7 10l5 5 5-5z'/%3E%3C/svg%3E");
  background-repeat:no-repeat;background-position:right 10px center;
}
.sort-select:focus{border-color:var(--ink)}

/* Grid */
.video-grid{display:grid;grid-template-columns:repeat(auto-fill,minmax(320px,1fr));gap:20px}

/* Card */
.video-card{
  background:var(--card);border:1px solid var(--border);border-radius:var(--r);
  overflow:hidden;text-decoration:none;color:inherit;
  transition:all .25s;box-shadow:var(--sh);display:block;
}
.video-card:hover{box-shadow:var(--sh-lg);transform:translateY(-4px)}

.card-thumb{
  position:relative;width:100%;padding-top:56.25%;background:var(--card-alt);
  overflow:hidden;border-bottom:1px solid var(--border-light);
}
.card-thumb img{position:absolute;top:0;left:0;width:100%;height:100%;object-fit:cover;transition:transform .3s}
.video-card:hover .card-thumb img{transform:scale(1.03)}
.card-duration{
  position:absolute;bottom:10px;right:10px;
  background:rgba(26,24,22,.82);backdrop-filter:blur(4px);
  color:#fff;padding:3px 8px;border-radius:6px;
  font-family:var(--mono);font-size:.72rem;font-weight:500;
}
.card-badge{
  position:absolute;top:10px;left:10px;
  padding:3px 10px;border-radius:6px;
  font-size:.68rem;font-weight:600;color:#fff;letter-spacing:.04em;
}
.badge-learn{background:linear-gradient(135deg,var(--ink),var(--ink-deep))}
.badge-yt{background:#ff0000cc}.badge-bili{background:#00a1d6cc}
.badge-dy{background:rgba(22,24,35,.85)}.badge-xhs{background:#ff2442cc}
.badge-tt{background:rgba(1,1,1,.85)}.badge-default{background:rgba(26,24,22,.6)}

.card-body{padding:18px 20px 20px}
.card-head{display:flex;align-items:flex-start;gap:14px;margin-bottom:12px}
.card-ring{position:relative;width:44px;height:44px;flex-shrink:0}
.card-ring svg{transform:rotate(-90deg)}
.ring-num{
  position:absolute;inset:0;display:flex;align-items:center;justify-content:center;
  font-family:var(--mono);font-weight:700;font-size:.88rem;
}
.ring-num-ink{color:var(--ink-deep)}
.ring-num-green{color:var(--green)}
.ring-num-amber{color:var(--amber)}
.ring-num-rose{color:var(--rose)}

.card-info{flex:1;min-width:0}
.card-title{
  font-size:.95rem;font-weight:600;color:var(--text);line-height:1.4;
  display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden;
  margin-bottom:6px;
}
.card-tags{display:flex;align-items:center;gap:6px;flex-wrap:wrap}
.card-pill{
  display:inline-flex;align-items:center;
  font-size:.7rem;padding:2px 10px;border-radius:12px;font-weight:500;
}
.pill-diff-b{background:var(--green-bg);color:var(--green)}
.pill-diff-i{background:var(--amber-bg);color:var(--amber)}
.pill-diff-a{background:var(--rose-bg);color:var(--rose)}
.pill-cat{background:var(--ink-light);color:var(--ink-deep)}
.pill-platform{background:var(--card-alt);border:1px solid var(--border-light);color:var(--text-3)}
.card-date{font-family:var(--mono);font-size:.72rem;color:var(--text-4)}
.card-summary{font-size:.84rem;color:var(--text-3);line-height:1.6;display:-webkit-box;-webkit-line-clamp:2;-webkit-box-orient:vertical;overflow:hidden}

/* Loading & Empty */
.loading-state,.empty-state{text-align:center;padding:80px 20px;color:var(--text-3)}
.loading-state .spinner{
  width:32px;height:32px;border:3px solid var(--border);border-top-color:var(--ink);
  border-radius:50%;animation:spin .8s linear infinite;margin:0 auto 16px;
}
@keyframes spin{to{transform:rotate(360deg)}}
.empty-title{font-size:1rem;margin-bottom:6px;color:var(--text-2)}
.empty-hint{font-size:.84rem;color:var(--text-4)}

/* Footer */
.site-footer{
  text-align:center;padding:28px 20px;
  border-top:1px solid var(--border-light);font-size:.78rem;color:var(--text-4);
}
.site-footer a{color:var(--ink);text-decoration:none}

/* Responsive */
@media(max-width:768px){
  .stats-bar{grid-template-columns:repeat(2,1fr);gap:10px;margin-top:-20px;padding:0 16px}
  .stat-card{padding:14px 16px}
  .stat-value{font-size:1.2rem}
  .video-grid{grid-template-columns:1fr}
  .container{padding:24px 16px 48px}
  .site-header{padding:28px 16px 24px}
  .toolbar{flex-direction:column}
  .sort-select{width:100%}
}
@media(max-width:480px){
  .stats-bar{grid-template-columns:1fr 1fr}
}
'''


def generate_readme(owner, repo_name):
    return f'''# Video Learning Library

Auto-updated video learning & analysis dashboard powered by Claude Code.

## How it works

1. Learn from videos with `/video-learn <URL>` - generates structured learning notes
2. All analyses are accessible via `/video-learn <URL>`
3. Results are automatically synced to this repo
4. Dashboard updates at: https://{owner}.github.io/{repo_name}/

## Features

- **Learning Notes**: Structured chapter breakdowns, knowledge timelines, key quotes, action items
- **Viral Analysis**: 8-dimension scoring, emotional arc mapping, retention prediction, viral formula extraction

## Supported Platforms

- YouTube / Bilibili / Xiaohongshu / Douyin / TikTok
'''


if __name__ == "__main__":
    print(generate_dashboard_html()[:200])
    print("---")
    print(generate_styles_css()[:200])
