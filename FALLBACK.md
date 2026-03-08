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

### 重要：YouTube 已内置多策略下载

`download_video()` 对 YouTube 有 5 种自动重试策略，通常无需手动干预：

1. **node-720p**: 使用 Node.js 解密签名，下载 720p
2. **node-480p**: 降级到 480p
3. **combined-360p**: 使用 format 18 (360p 合并格式)
4. **mweb-client**: 切换到 mweb player client
5. **android-vr-fallback**: 无 JS runtime 兜底，使用 android vr API

所有策略均使用 `--js-runtimes node` 启用 Node.js 进行 YouTube 签名解密（yt-dlp 默认只启用 deno）。

### 如果所有策略仍然失败（exit code 2）

1. 检查 yt-dlp 版本是否最新：
```bash
export PATH="/home/node/.local/bin:$PATH"
pip install --upgrade --break-system-packages yt-dlp
```

2. 手动尝试下载：
```bash
export PATH="/home/node/.local/bin:$PATH"
yt-dlp --js-runtimes node -f 18 -o /tmp/yt_video.mp4 --no-playlist "<YouTube URL>"
```

3. 如果报错 "Sign in to confirm your age"，该视频有年龄限制，无法无登录下载。

### 注意事项
- 浏览器方案不可用（signatureCipher 加密），不要尝试从浏览器提取 URL
- `--js-runtimes node` 是关键参数，yt-dlp 默认不启用 Node.js
- YouTube 的 SABR (Server ABR) 需要签名解密，没有 JS runtime 会导致大部分格式不可用

---

## 小红书 (xiaohongshu.com)

### 流程（不使用 yt-dlp，直接浏览器方案）

1. **打开页面**：

> **重要**：小红书帖子页需要 `xsec_token` 参数才能正确加载。
> 如果用户提供的链接不含此参数，先导航到 explore 页面获取带 token 的链接。

如果链接已包含 `xsec_token`，直接打开：
```bash
browser navigate "https://www.xiaohongshu.com/explore/xxxxxxx?xsec_token=xxx&xsec_source="
```

如果链接不含 `xsec_token`，先获取带 token 的链接：
```bash
# 先访问 explore 页关闭登录弹窗
browser navigate "https://www.xiaohongshu.com/explore"
browser act "Click the X close button on the login popup"
# 从页面中提取带 token 的链接
browser console exec "Array.from(document.querySelectorAll('a[href*=\"/explore/\"]')).find(a => a.href.includes('xsec_token'))?.href || 'NOT_FOUND'"
```

或者处理短链接（会自动重定向）：
```bash
browser navigate "https://xhslink.com/xxxxxx"
```

2. **关闭登录弹窗**（页面加载后通常会弹出）：
```bash
browser act "Click the X close button on the login popup"
```

3. **提取视频地址**（分步执行，避免 IIFE 语法问题）：
```bash
# 先获取 note ID
browser console exec "Object.keys(window.__INITIAL_STATE__.note.noteDetailMap)[0]"
# 假设返回 ID 为 xxx，检查是否为视频
browser console exec "window.__INITIAL_STATE__.note.noteDetailMap['<NOTE_ID>'].note.type"
# 如果 type 为 'video'，提取 masterUrl
browser console exec "window.__INITIAL_STATE__.note.noteDetailMap['<NOTE_ID>'].note.video.media.stream.h264[0].masterUrl"
```

4. **下载**（CDN 完全公开，无需认证头）：
```bash
curl -L -o /tmp/xhs_video.mp4 "<masterUrl>"
```

### 注意事项
- 小红书 CDN 是完全公开的，curl 直接下载即可，**无需 Referer 或其他认证头**
- 音视频是合一的 MP4，**不需要 ffmpeg 合并**
- `__INITIAL_STATE__` 在 SSR 页面中始终存在
- 如果是图文笔记（无视频），`note.type` 为 `normal` 而非 `video`，需提示用户
- 短链接 `xhslink.com` 会自动重定向到完整 URL
- **避免使用 IIFE `(() => {...})()` 语法**，browser console exec 对此处理不稳定，改用分步查询

---

## 抖音 (douyin.com)

### 流程（不使用 yt-dlp，直接浏览器方案）

1. **打开页面**（获取 cookie 和上下文）：
```bash
browser navigate "https://www.douyin.com/video/xxxxxxxxxxxxxxxxx"
```

> **注意**：抖音可能会将视频页重定向到首页推荐流。无论是否重定向，只要能获取到 cookie 即可继续。
> 如果重定向了，视频 ID 可能在 URL 参数 `vid` 中：`?vid=xxx`

2. **提取视频 ID**：
```bash
browser console exec "window.location.pathname.match(/video\\/(\\d+)/)?.[1] || new URLSearchParams(window.location.search).get('vid') || window.location.href.match(/(\\d{19})/)?.[1]"
```

3. **调用抖音内部 API 获取视频信息**（异步，分两步）：

> **关键**：`browser console exec` 无法直接返回 Promise 结果。必须先将结果存到 `window` 变量，等待 3 秒后再读取。

Step 3a - 发起请求并存储结果：
```bash
browser console exec "fetch('/aweme/v1/web/aweme/detail/?aweme_id=<VIDEO_ID>&aid=6383&cookie_enabled=true', { headers: { 'Referer': 'https://www.douyin.com/' } }).then(r => r.text()).then(t => { window.__dy_result = t; console.log('DONE'); })"
```

Step 3b - 等待 3 秒后读取结果：
```bash
# 等待 3 秒
sleep 3
browser console exec "JSON.parse(window.__dy_result).aweme_detail.video.play_addr.url_list[0]"
```

4. **下载**（需要 Referer）：
```bash
curl -L -o /tmp/douyin_video.mp4 \
  -H "Referer: https://www.douyin.com/" \
  -H "User-Agent: Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36" \
  "<play_addr.url_list中的第一个URL>"
```

### 备选方案：RENDER_DATA

如果 API 调用失败，尝试从页面渲染数据提取（仅在视频详情页有效，推荐流首页不可用）：
```bash
browser console exec "document.querySelectorAll('script[id=RENDER_DATA]').length"
# 如果为 1，继续：
browser console exec "Object.keys(JSON.parse(decodeURIComponent(document.querySelector('script[id=RENDER_DATA]').textContent)).app).includes('videoDetail') ? 'has_detail' : 'no_detail'"
```

### 注意事项
- curl 必须带 `Referer: https://www.douyin.com/`，否则 403
- 音视频是合一的 MP4，**不需要 ffmpeg 合并**
- 抖音反爬较严格，如果 API 返回空或错误，可能需要等待页面完全加载
- `play_addr.url_list` 通常有多个 CDN 地址，第一个就行
- 视频 ID 通常是 19 位数字
- **异步 fetch 必须分两步**：先存到 window 变量，sleep 后再读取

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
