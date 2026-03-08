# video-learn

视频深度学习总结。用户提供视频链接（B站/YouTube/小红书/抖音）或本地视频文件，自动完成：下载 -> AI内容分析 -> 生成学习笔记 -> 推送到 GitHub Pages。

## Trigger

- `/video-learn <链接或本地视频路径>`
- 当用户说"学习视频"、"总结视频"、"视频笔记"、"视频学习"、"帮我看看这个视频讲了什么"并附带链接时触发
- 当用户直接发送视频链接时触发

## 首次设置

使用前需配置两项：

### 1. 豆包 API Key

模型：`doubao-seed-2-0-pro`（火山引擎 Ark 平台）

```bash
python3 -c "
import json, os
path = os.path.expanduser('~/.claude/skills/video-learn/.api_config.json')
os.makedirs(os.path.dirname(path), exist_ok=True)
with open(path, 'w') as f:
    json.dump({'api_key': '<你的API Key>'}, f)
print('Done')
"
```

或设置环境变量：`export DOUBAO_API_KEY="<key>"`

### 2. GitHub Token

```bash
export PATH="/home/node/.local/bin:$PATH"
python3 ~/.claude/skills/video-learn/scripts/github_sync.py setup --token <GITHUB_TOKEN>
```

自动完成：验证Token -> 创建仓库 -> 推送仪表板 -> 启用GitHub Pages -> 保存配置

> 设置完成后，每次发视频链接，报告自动生成并推送到 GitHub Pages 存档。

### 配置文件

| 配置 | 路径 |
|------|------|
| API Key | `~/.claude/skills/video-learn/.api_config.json` |
| GitHub | `~/.claude/skills/video-learn/.sync_config.json` |

## 执行协议

### 核心原则
1. **收到链接直接开始，不反复确认**
2. 始终使用 `--archive-dir ./outputs/learning` 和 `--title` 参数
3. **运行前设置 PATH**：`export PATH="/home/node/.local/bin:$PATH"`
4. 报告使用平台内嵌播放器（Bilibili/YouTube iframe），不上传视频
5. 报告输出为 `<file type="static">` 附件，同时在对话中输出 Markdown 摘要

### 完整流程

```
Step 0: 检查配置
  检查 ~/.claude/skills/video-learn/.api_config.json 和 .sync_config.json
  缺失则提示用户完成首次设置

Step 1: 尝试 yt-dlp 下载
  export PATH="/home/node/.local/bin:$PATH"
  python3 ~/.claude/skills/video-learn/scripts/video_learner.py run \
    "<URL>" --title "视频标题" --archive-dir ./outputs/learning

  成功（exit 0）-> 完成（报告+GitHub自动同步）
  失败（exit 2）-> Step 2

Step 2: 浏览器 fallback
  读取 ~/.claude/skills/video-learn/FALLBACK.md
  按对应平台方案下载视频到 /tmp/

  关键点：
  - B站第一次可能 412，等 5 秒重新 navigate
  - B站用 __playinfo__.data.dash，视频+音频分下载后 ffmpeg 合并
  - YouTube 用 ytInitialPlayerResponse.streamingData
  - 小红书用 __INITIAL_STATE__ 的 masterUrl
  - 抖音用 /aweme/v1/web/aweme/detail/ API

Step 3: 本地文件继续（需注入 source_url）
  # 压缩
  python3 ~/.claude/skills/video-learn/scripts/video_learner.py compress /tmp/视频.mp4

  # 分析
  python3 ~/.claude/skills/video-learn/scripts/video_learner.py analyze /tmp/compressed.mp4 \
    --title "标题" --output-json /tmp/analysis.json

  # 注入 source_url（报告中才有内嵌播放器）
  python3 -c "
  import json
  with open('/tmp/analysis.json') as f: d = json.load(f)
  d.setdefault('_meta', {})['source_url'] = '原始链接'
  with open('/tmp/analysis.json', 'w') as f: json.dump(d, f, ensure_ascii=False, indent=2)
  "

  # 生成报告
  python3 ~/.claude/skills/video-learn/scripts/video_learner.py report /tmp/analysis.json \
    --video /tmp/compressed.mp4 --title "标题" --archive-dir ./outputs/learning

Step 4: GitHub 同步
  # run 命令自动同步；浏览器 fallback 后手动：
  python3 ~/.claude/skills/video-learn/scripts/github_sync.py sync ./outputs/learning/日期_标题

Step 5: 输出
  <file type="static"> 附件 + Markdown 学习摘要
```

### 子命令

| 命令 | 用途 |
|------|------|
| `run` | 完整流水线（下载->压缩->分析->报告->GitHub） |
| `download` | 仅下载 |
| `compress` | 仅压缩 |
| `analyze` | 仅分析（输出JSON） |
| `report` | 从JSON生成报告 |

## 报告特性

### 视频播放
- B站：`<iframe src="//player.bilibili.com/player.html?bvid=xxx">`
- YouTube：`<iframe src="https://www.youtube.com/embed/xxx">`
- 其他：跳转链接按钮

### 内容结构
- 难度/分类/讲者标签 + 300-500字概述
- 按知识主题组织的内容板块（200-800字/板块）
- 工具与资源表格 + 实用技巧 + FAQ
- 适合人群 + 总结 + 相关链接

### 设计风格
- 暖色编辑式（#F6F5F0 底色，#6C63FF 主色）
- Noto Serif SC + DM Sans + JetBrains Mono

## 异常处理

| 情况 | 处理 |
|------|------|
| yt-dlp 被反爬 (412/403) | 自动走 FALLBACK.md 浏览器方案 |
| API 调用失败 | 内置 3 次重试；全部失败检查 Key |
| 视频过大 (>50MB base64) | 自动二次压缩 |

## 依赖

- `python3`（标准库）
- `ffmpeg` / `ffprobe`
- `yt-dlp`（B站/YouTube）

**运行前**：`export PATH="/home/node/.local/bin:$PATH"`
