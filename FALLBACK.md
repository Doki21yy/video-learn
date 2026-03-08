# 浏览器 Fallback 下载方案

当 yt-dlp 被反爬（412/403）或平台不支持 yt-dlp 时，使用浏览器自动化方案下载视频。

---

## B站 (bilibili.com)

### 流程

1. **打开页面**（可能需要两次以通过验证）：
```bash
browser navigate "https://www.bilibili.com/video/BVxxxxxxx"
```

如果遇到验证页面，等待几秒后重新导航：
```bash
browser navigate "https://www.bilibili.com/video/BVxxxxxxx"
```

2. **提取视频/音频流地址**：
```bash
browser console exec "JSON.stringify(window.__playinfo__.data.dash)"
```

从返回的 JSON 中提取：
- 视频流: `dash.video[0].baseUrl` 或 `dash.video[0].backupUrl[0]`
- 音频流: `dash.audio[0].baseUrl` 或 `dash.audio[0].backupUrl[0]`

选择视频流时优先选 720p（`height: 720` 或 `id: 64`）。

3. **下载视频和音频**（必须带 Referer）：
```bash
curl -o /tmp/bili_video.m4s -H "Referer: https://www.bilibili.com" -H "User-Agent: Mozilla/5.0" "<视频流URL>"
curl -o /tmp/bili_audio.m4s -H "Referer: https://www.bilibili.com" -H "User-Agent: Mozilla/5.0" "<音频流URL>"
```

4. **ffmpeg 合并**：
```bash
ffmpeg -y -i /tmp/bili_video.m4s -i /tmp/bili_audio.m4s -c copy -movflags +faststart /tmp/bili_merged.mp4
```

### 注意事项
- curl 必须带 `Referer: https://www.bilibili.com`，否则 403
- 如果 `__playinfo__` 不存在，可能需要登录或页面未完全加载，等待后重试
- B站 dash 流是视频/音频分离的，必须用 ffmpeg 合并

---

## YouTube (youtube.com)

### 流程

1. **打开页面**：
```bash
browser navigate "https://www.youtube.com/watch?v=xxxxxxxxxxx"
```

2. **提取流地址**：
```bash
browser console exec "JSON.stringify(ytInitialPlayerResponse.streamingData)"
```

从返回的 JSON 中提取：
- 优先使用 `formats`（视频+音频合一流）：
  - 找 `qualityLabel` 为 "720p" 或 "360p" 的条目
  - 取其 `url` 字段
- 如果 `formats` 没有可用的，使用 `adaptiveFormats`：
  - 视频: `mimeType` 含 "video/mp4"，选 720p
  - 音频: `mimeType` 含 "audio/mp4"，选码率最高的
  - 分别下载后 ffmpeg 合并

3. **下载**：

合一流（formats 有 url）：
```bash
curl -L -o /tmp/yt_video.mp4 "<url>"
```

分离流（adaptiveFormats）：
```bash
curl -L -o /tmp/yt_video.mp4 "<video_url>"
curl -L -o /tmp/yt_audio.m4a "<audio_url>"
ffmpeg -y -i /tmp/yt_video.mp4 -i /tmp/yt_audio.m4a -c copy -movflags +faststart /tmp/yt_merged.mp4
```

### 注意事项
- YouTube 的 `formats` URL 可能包含 `&` 需要正确转义
- 如果 `ytInitialPlayerResponse` 不存在，页面可能通过 AJAX 加载，尝试：
  ```bash
  browser console exec "document.querySelector('script:not([src])').textContent.match(/ytInitialPlayerResponse\\s*=\\s*(\\{.*?\\});/)?.[1]"
  ```
- 某些视频可能需要年龄验证或登录

---

## 小红书 (xiaohongshu.com)

### 流程（不使用 yt-dlp，直接浏览器方案）

1. **打开页面**：
```bash
browser navigate "https://www.xiaohongshu.com/explore/xxxxxxx"
```

或者处理短链接：
```bash
browser navigate "https://xhslink.com/xxxxxx"
```

2. **提取视频地址**：
```bash
browser console exec "(() => { const state = window.__INITIAL_STATE__; const noteMap = state.note.noteDetailMap; const key = Object.keys(noteMap)[0]; const note = noteMap[key].note; const video = note.video; if (video && video.media && video.media.stream) { const streams = video.media.stream.h264 || video.media.stream.h265 || video.media.stream.av1; return streams[0].masterUrl; } return 'NO_VIDEO_FOUND'; })()"
```

3. **下载**（CDN 完全公开，无需认证头）：
```bash
curl -L -o /tmp/xhs_video.mp4 "<masterUrl>"
```

### 注意事项
- 小红书 CDN 是完全公开的，curl 直接下载即可，**无需 Referer 或其他认证头**
- 音视频是合一的 MP4，**不需要 ffmpeg 合并**
- `__INITIAL_STATE__` 在 SSR 页面中始终存在
- 如果是图文笔记（无视频），`video` 字段会为空，需提示用户
- 短链接 `xhslink.com` 会自动重定向到完整 URL

---

## 抖音 (douyin.com)

### 流程（不使用 yt-dlp，直接浏览器方案）

1. **打开页面**（获取 cookie 和上下文）：
```bash
browser navigate "https://www.douyin.com/video/xxxxxxxxxxxxxxxxx"
```

2. **提取视频 ID**：
```bash
browser console exec "window.location.pathname.match(/video\\/(\\d+)/)?.[1] || window.location.href.match(/(\\d{19})/)?.[1]"
```

3. **调用抖音内部 API 获取视频信息**：
```bash
browser console exec "fetch('/aweme/v1/web/aweme/detail/?aweme_id=<VIDEO_ID>&aid=6383&cookie_enabled=true&browser_language=zh-CN&browser_platform=MacIntel&browser_name=Chrome&browser_version=120', { headers: { 'Referer': 'https://www.douyin.com/' } }).then(r => r.json()).then(d => JSON.stringify(d.aweme_detail.video.play_addr.url_list))"
```

4. **下载**（需要 Referer）：
```bash
curl -L -o /tmp/douyin_video.mp4 \
  -H "Referer: https://www.douyin.com/" \
  -H "User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36" \
  "<play_addr.url_list中的第一个URL>"
```

### 备选方案

如果 API 调用失败，尝试从页面渲染数据提取：
```bash
browser console exec "(() => { const scripts = document.querySelectorAll('script[id=RENDER_DATA]'); if (scripts.length) { const data = JSON.parse(decodeURIComponent(scripts[0].textContent)); const keys = Object.keys(data); for (const key of keys) { const item = data[key]; if (item && item.awemeDetail && item.awemeDetail.video) { return JSON.stringify(item.awemeDetail.video.playAddr || item.awemeDetail.video.play_addr); } } } return 'NOT_FOUND'; })()"
```

### 注意事项
- curl 必须带 `Referer: https://www.douyin.com/`，否则 403
- 音视频是合一的 MP4，**不需要 ffmpeg 合并**
- 抖音反爬较严格，如果 API 返回空或错误，可能需要等待页面完全加载
- `play_addr.url_list` 通常有多个 CDN 地址，第一个就行
- 视频 ID 通常是 19 位数字

---

## 通用后续步骤

无论哪个平台，下载完成后执行：

```bash
# 1. 压缩视频
python3 ~/.claude/skills/video-learn/scripts/video_learner.py compress /tmp/downloaded_video.mp4 --output /tmp/compressed.mp4

# 2. 分析
python3 ~/.claude/skills/video-learn/scripts/video_learner.py analyze /tmp/compressed.mp4 --title "视频标题" --output-json /tmp/analysis.json

# 3. 生成报告
python3 ~/.claude/skills/video-learn/scripts/video_learner.py report /tmp/analysis.json --video /tmp/compressed.mp4 --title "视频标题" --archive-dir ./outputs/reports
```

或者直接用 `run` 命令处理本地文件：
```bash
python3 ~/.claude/skills/video-learn/scripts/video_learner.py run /tmp/downloaded_video.mp4 --title "视频标题" --archive-dir ./outputs/reports
```
