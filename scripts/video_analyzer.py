#!/usr/bin/env python3
"""
video_analyzer.py - 爆款视频拆解核心引擎
功能：下载 → 压缩 → 豆包大模型原生视频理解 → 8维度+5模块分析 → 逐场景细拆 → 生成报告
"""

import argparse
import base64
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import time
import urllib.request
import urllib.error
from datetime import datetime
from pathlib import Path

# ─── API 配置 ───────────────────────────────────────────────────────────────
API_ENDPOINT = "https://ark.cn-beijing.volces.com/api/v3/responses"
API_MODEL = "doubao-seed-2-0-pro-260215"
MAX_BASE64_BYTES = 50 * 1024 * 1024  # 50MB API limit
TARGET_FILE_SIZE = 35 * 1024 * 1024  # 35MB target (base64 ≈ 47MB < 50MB)
MAX_RETRIES = 3

SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPT_DIR.parent

# ─── API Key 加载（优先级：环境变量 > 配置文件）─────────────────────────────
_API_CONFIG_PATH = SKILL_DIR / ".api_config.json"

def _load_api_key():
    """加载豆包 API Key：优先环境变量 DOUBAO_API_KEY，其次配置文件"""
    key = os.environ.get("DOUBAO_API_KEY", "")
    if key:
        return key
    if _API_CONFIG_PATH.is_file():
        try:
            with open(_API_CONFIG_PATH) as f:
                cfg = json.load(f)
            return cfg.get("api_key", "")
        except Exception:
            pass
    return ""

API_KEY = _load_api_key()

# 确保 ~/.local/bin 在 PATH 中（ffmpeg/ffprobe/yt-dlp 可能安装在此处）
_LOCAL_BIN = os.path.expanduser("~/.local/bin")
if _LOCAL_BIN not in os.environ.get("PATH", ""):
    os.environ["PATH"] = _LOCAL_BIN + os.pathsep + os.environ.get("PATH", "")


# ─── 工具函数 ───────────────────────────────────────────────────────────────

def log(msg, level="INFO"):
    ts = datetime.now().strftime("%H:%M:%S")
    print(f"[{ts}] [{level}] {msg}", flush=True)


def run_cmd(cmd, check=True, capture=True):
    """运行外部命令"""
    log(f"CMD: {' '.join(cmd) if isinstance(cmd, list) else cmd}")
    result = subprocess.run(
        cmd, shell=isinstance(cmd, str),
        capture_output=capture, text=True
    )
    if check and result.returncode != 0:
        stderr = result.stderr if capture else ""
        raise RuntimeError(f"Command failed (exit {result.returncode}): {stderr}")
    return result


def detect_platform(url):
    """检测视频平台"""
    url_lower = url.lower()
    if "bilibili.com" in url_lower or "b23.tv" in url_lower:
        return "bilibili"
    elif "youtube.com" in url_lower or "youtu.be" in url_lower:
        return "youtube"
    elif "xiaohongshu.com" in url_lower or "xhslink.com" in url_lower:
        return "xiaohongshu"
    elif "douyin.com" in url_lower or "tiktok.com" in url_lower:
        return "douyin"
    return "unknown"


def get_video_duration(filepath):
    """用 ffprobe 获取视频时长（秒）"""
    result = run_cmd([
        "ffprobe", "-v", "error",
        "-show_entries", "format=duration",
        "-of", "default=noprint_wrappers=1:nokey=1",
        filepath
    ])
    try:
        return float(result.stdout.strip())
    except ValueError:
        return 0.0


def get_file_size(filepath):
    return os.path.getsize(filepath)


def file_to_base64(filepath):
    with open(filepath, "rb") as f:
        return base64.b64encode(f.read()).decode("utf-8")


def base64_size(filepath):
    """估算 base64 编码后大小"""
    fsize = get_file_size(filepath)
    return int(fsize * 4 / 3) + 100


def slugify(title):
    """生成 ASCII 安全的目录名"""
    ascii_part = re.sub(r'[^a-zA-Z0-9\s\-]', '', title).strip()
    if ascii_part:
        return re.sub(r'\s+', '-', ascii_part).lower()[:60]
    return hashlib.md5(title.encode()).hexdigest()[:12]


def extract_json_from_text(text):
    """从文本中提取 JSON，兼容 markdown 代码块包裹"""
    # 尝试从 ```json ... ``` 代码块提取
    m = re.search(r'```(?:json)?\s*\n?(.*?)\n?\s*```', text, re.DOTALL)
    if m:
        text = m.group(1).strip()

    # 大括号匹配法：找最外层 JSON object
    depth = 0
    start = -1
    for i, ch in enumerate(text):
        if ch == '{':
            if depth == 0:
                start = i
            depth += 1
        elif ch == '}':
            depth -= 1
            if depth == 0 and start >= 0:
                try:
                    return json.loads(text[start:i + 1])
                except json.JSONDecodeError:
                    start = -1
                    continue

    # 尝试找 JSON array
    depth = 0
    start = -1
    for i, ch in enumerate(text):
        if ch == '[':
            if depth == 0:
                start = i
            depth += 1
        elif ch == ']':
            depth -= 1
            if depth == 0 and start >= 0:
                try:
                    return json.loads(text[start:i + 1])
                except json.JSONDecodeError:
                    start = -1
                    continue

    # 最后尝试直接 parse
    try:
        return json.loads(text)
    except json.JSONDecodeError:
        return None


# ─── Step 1: 下载 ────────────────────────────────────────────────────────────

def download_video(url, output_dir=None):
    """下载视频，返回本地文件路径"""
    if os.path.isfile(url):
        log(f"本地文件: {url}")
        return os.path.abspath(url)

    platform = detect_platform(url)
    log(f"检测到平台: {platform}")

    if platform in ("xiaohongshu", "douyin"):
        log(f"{platform} 不支持 yt-dlp，需使用浏览器 fallback", "WARN")
        sys.exit(2)

    if output_dir is None:
        output_dir = tempfile.mkdtemp(prefix="video_analyze_")

    output_path = os.path.join(output_dir, "downloaded_video.mp4")

    # 检查 yt-dlp 是否可用
    try:
        run_cmd(["yt-dlp", "--version"])
    except (FileNotFoundError, RuntimeError):
        log("yt-dlp 未安装，尝试安装...", "WARN")
        run_cmd([sys.executable, "-m", "pip", "install", "yt-dlp"], check=False)

    cmd = [
        "yt-dlp",
        "-f", "bestvideo[height<=720]+bestaudio/best[height<=720]/best",
        "--merge-output-format", "mp4",
        "-o", output_path,
        "--no-playlist",
        "--socket-timeout", "30",
        url
    ]

    try:
        result = run_cmd(cmd, check=False)
        if result.returncode != 0:
            stderr = result.stderr or ""
            if "412" in stderr or "403" in stderr or "HTTP Error" in stderr:
                log(f"yt-dlp 被反爬 (可能412/403)，需使用浏览器 fallback", "WARN")
                sys.exit(2)
            raise RuntimeError(f"yt-dlp 下载失败: {stderr}")
    except FileNotFoundError:
        log("yt-dlp 不可用，需使用浏览器 fallback", "WARN")
        sys.exit(2)

    # yt-dlp 可能改变扩展名，查找实际文件
    if not os.path.exists(output_path):
        for f in os.listdir(output_dir):
            if f.startswith("downloaded_video"):
                output_path = os.path.join(output_dir, f)
                break

    if not os.path.exists(output_path):
        raise RuntimeError("下载完成但找不到输出文件")

    log(f"下载完成: {output_path} ({get_file_size(output_path) / 1024 / 1024:.1f}MB)")
    return output_path


# ─── Step 2: 压缩 ────────────────────────────────────────────────────────────

def compress_video(input_path, output_path=None, target_size=TARGET_FILE_SIZE):
    """
    压缩视频到目标大小。
    如果原始文件已够小，只做 faststart 处理。
    """
    if output_path is None:
        dirname = os.path.dirname(input_path)
        output_path = os.path.join(dirname, "compressed_video.mp4")

    fsize = get_file_size(input_path)
    b64size = base64_size(input_path)

    if fsize <= target_size and b64size <= MAX_BASE64_BYTES:
        log(f"文件已足够小 ({fsize / 1024 / 1024:.1f}MB)，仅做 faststart 处理")
        faststart_path = output_path + ".faststart.mp4"
        run_cmd([
            "ffmpeg", "-y", "-i", input_path,
            "-c", "copy", "-movflags", "+faststart",
            faststart_path
        ])
        os.rename(faststart_path, output_path)
        log(f"Faststart 完成: {output_path}")
        return output_path

    duration = get_video_duration(input_path)
    if duration <= 0:
        duration = 60.0
        log("无法获取时长，假设 60 秒", "WARN")

    def do_compress(tgt_size):
        target_bitrate_kbps = int((tgt_size * 8) / duration / 1024 * 0.9)
        target_bitrate_kbps = max(target_bitrate_kbps, 200)
        audio_bitrate = 96
        video_bitrate = target_bitrate_kbps - audio_bitrate

        log(f"目标码率: {video_bitrate}k video + {audio_bitrate}k audio (时长 {duration:.0f}s)")

        tmp_out = output_path + ".tmp.mp4"
        cmd = [
            "ffmpeg", "-y", "-i", input_path,
            "-c:v", "libx264", "-preset", "fast", "-crf", "28",
            "-b:v", f"{video_bitrate}k", "-maxrate", f"{int(video_bitrate * 1.5)}k",
            "-bufsize", f"{video_bitrate * 2}k",
            "-vf", "scale='min(1280,iw)':min'(720,ih)':force_original_aspect_ratio=decrease",
            "-c:a", "aac", "-b:a", f"{audio_bitrate}k",
            "-movflags", "+faststart",
            tmp_out
        ]
        run_cmd(cmd)
        os.rename(tmp_out, output_path)
        return output_path

    # 第一次压缩
    do_compress(target_size)
    result_b64_size = base64_size(output_path)
    result_fsize = get_file_size(output_path)
    log(f"压缩结果: {result_fsize / 1024 / 1024:.1f}MB (base64 ≈ {result_b64_size / 1024 / 1024:.1f}MB)")

    # 如果仍超限，二次压缩
    if result_b64_size > MAX_BASE64_BYTES:
        log("base64 仍超限，执行二次压缩", "WARN")
        second_target = int(target_size * 0.6)
        backup = input_path
        input_path = output_path
        do_compress(second_target)
        result_b64_size = base64_size(output_path)
        result_fsize = get_file_size(output_path)
        log(f"二次压缩结果: {result_fsize / 1024 / 1024:.1f}MB (base64 ≈ {result_b64_size / 1024 / 1024:.1f}MB)")

        if result_b64_size > MAX_BASE64_BYTES:
            log("二次压缩后仍超限，视频可能过长", "ERROR")

    return output_path


# ─── Step 3 & 4: API 分析 ─────────────────────────────────────────────────────

def call_doubao_api(video_base64, prompt_text, retry=MAX_RETRIES):
    """调用豆包大模型 API（原生视频理解）"""
    if not API_KEY:
        raise RuntimeError(
            "豆包 API Key 未配置。请先运行首次设置：\n"
            "  方法1: 设置环境变量 DOUBAO_API_KEY=<your-key>\n"
            "  方法2: 编辑 ~/.claude/skills/video-learn/.api_config.json"
        )
    payload = {
        "model": API_MODEL,
        "input": [{
            "role": "user",
            "content": [
                {
                    "type": "input_video",
                    "video_url": f"data:video/mp4;base64,{video_base64}"
                },
                {
                    "type": "input_text",
                    "text": prompt_text
                }
            ]
        }]
    }

    data = json.dumps(payload, ensure_ascii=False).encode("utf-8")
    headers = {
        "Content-Type": "application/json",
        "Authorization": f"Bearer {API_KEY}"
    }

    req = urllib.request.Request(API_ENDPOINT, data=data, headers=headers, method="POST")

    for attempt in range(1, retry + 1):
        try:
            log(f"API 调用 (尝试 {attempt}/{retry})...")
            with urllib.request.urlopen(req, timeout=300) as resp:
                body = resp.read().decode("utf-8")
                result = json.loads(body)
                return parse_api_response(result)
        except urllib.error.HTTPError as e:
            body = e.read().decode("utf-8", errors="replace")
            log(f"API HTTP 错误 {e.code}: {body[:500]}", "ERROR")
            if attempt < retry:
                time.sleep(5 * attempt)
        except urllib.error.URLError as e:
            log(f"API 网络错误: {e}", "ERROR")
            if attempt < retry:
                time.sleep(5 * attempt)
        except Exception as e:
            log(f"API 未知错误: {e}", "ERROR")
            if attempt < retry:
                time.sleep(5 * attempt)

    raise RuntimeError(f"API 调用在 {retry} 次重试后失败")


def parse_api_response(result):
    """
    解析豆包 API 返回，兼容多种格式：
    1. responses API: output 为列表 [{type:"message", content:[{type:"output_text", text:...}]}]
    2. output 为 dict
    3. chat completions: choices[0].message.content
    """
    text = None

    # 格式1: responses API (output 是列表)
    if "output" in result and isinstance(result["output"], list):
        for item in result["output"]:
            if isinstance(item, dict) and item.get("type") == "message":
                for c in item.get("content", []):
                    if isinstance(c, dict) and c.get("type") == "output_text":
                        text = c.get("text", "")
                        break
            if text:
                break
        if not text:
            # output 列表中直接是字符串
            for item in result["output"]:
                if isinstance(item, str):
                    text = item
                    break

    # 格式2: output 为 dict
    if not text and "output" in result and isinstance(result["output"], dict):
        text = result["output"].get("text", "")
        if not text:
            content = result["output"].get("content", "")
            if isinstance(content, str):
                text = content
            elif isinstance(content, list):
                for c in content:
                    if isinstance(c, dict):
                        text = c.get("text", "")
                        if text:
                            break

    # 格式3: chat completions
    if not text and "choices" in result:
        choices = result["choices"]
        if choices and isinstance(choices, list):
            msg = choices[0].get("message", {})
            text = msg.get("content", "")

    if not text:
        # 尝试直接从顶层取
        text = result.get("text", "") or result.get("content", "")

    if not text:
        log(f"无法解析 API 响应: {json.dumps(result, ensure_ascii=False)[:500]}", "ERROR")
        raise RuntimeError("无法从 API 响应中提取文本")

    return text


def build_analysis_prompt():
    """构建第一次 API 调用的分析 prompt（8维度 + 5进阶模块）"""
    return """你是一位资深短视频爆款分析师。请对这段视频进行全面深度拆解。

你必须基于视频的实际质量独立评分，不要受到示例格式中任何数字的影响。评分应有明显区分度：
- 1-3分：差，明显不足，业余水平
- 4-5分：一般，有基本功但缺乏亮点
- 6-7分：良好，有一定专业度和创意
- 8-9分：优秀，接近头部水平
- 10分：顶级，教科书级别（极少给出）

overall_score 应该是8个维度评分的加权平均（hook和narrative权重更高），不要简单给一个笼统的高分。
差的视频就应该给低分（3-5分），一般的给中间分（5-7分），只有真正优秀的才给8分以上。

请输出严格的 JSON（不要有多余文字），格式如下：

{
  "overall_score": <float 1-10>,
  "summary": "<200字以内的总体评价>",
  "hook": {
    "score": <int 1-10>,
    "description": "<黄金3秒分析>",
    "formula": "<开头公式，如：悬念+视觉冲击>",
    "template": "<可复用的开头模板>"
  },
  "narrative": {
    "score": <int 1-10>,
    "type": "<叙事类型，如：三幕式/倒叙/平铺>",
    "description": "<叙事结构分析>",
    "timeline": [
      {"start": "0:00", "end": "0:30", "chapter": "<章节名>", "description": "<内容>"}
    ],
    "template": "<叙事结构模板>"
  },
  "pacing": {
    "score": <int 1-10>,
    "description": "<节奏分析>",
    "cut_points": ["<关键剪辑点时间戳>"],
    "pattern": "<节奏模式>"
  },
  "visual": {
    "score": <int 1-10>,
    "description": "<视觉分析>",
    "shots": [{"time": "<时间>", "type": "<镜头类型>", "description": "<描述>"}],
    "color_style": "<色彩风格>",
    "effects": ["<特效列表>"]
  },
  "text_overlay": {
    "score": <int 1-10>,
    "description": "<字幕设计分析>",
    "has_text": <bool>,
    "style": "<字幕风格>",
    "highlights": ["<重点字幕>"]
  },
  "audio": {
    "score": <int 1-10>,
    "description": "<音频分析>",
    "estimated_bpm": <int>,
    "sync_evidence": "<音画同步证据>",
    "voice_style": "<解说/配音风格>"
  },
  "cta": {
    "score": <int 1-10>,
    "description": "<互动引导分析>",
    "has_cta": <bool>,
    "cta_time": "<出现时间>",
    "cta_type": "<引导类型>"
  },
  "ending": {
    "score": <int 1-10>,
    "description": "<结尾分析>",
    "is_loopable": <bool>,
    "has_series_hook": <bool>,
    "ending_type": "<结尾类型>"
  },
  "emotional_arc": {
    "arc_type": "<情绪弧线类型>",
    "arc_description": "<弧线描述>",
    "curve_points": [
      {"time": "0:00", "valence": <float -5到5>, "arousal": <float 0到10>, "label": "<情绪标签>"}
    ],
    "turning_points": [
      {"time": "<时间>", "type": "<转折类型>", "description": "<描述>"}
    ]
  },
  "retention_prediction": {
    "hook_rate_3s": <float 0-1>,
    "retention_30s": <float 0-1>,
    "midpoint_retention": <float 0-1>,
    "completion_rate": <float 0-1>,
    "risk_segments": [
      {"time": "<时间段>", "risk": "<low/medium/high>", "label": "<标签>", "reason": "<原因>", "fix": "<修复建议>"}
    ]
  },
  "viral_formulas": {
    "script_formula": {
      "steps": ["<步骤1>", "<步骤2>"],
      "fill_template": "<可填空的脚本模板>"
    },
    "emotion_formula": {
      "nodes": ["<情绪节点1>", "<情绪节点2>"],
      "key_principles": ["<核心原则>"]
    },
    "algorithm_formula": {
      "drivers": ["<算法驱动因素>"],
      "weight_tips": ["<权重技巧>"]
    }
  },
  "algorithm_fitness": {
    "metrics": {
      "completion_rate": <float 0-1>,
      "interaction_rate": <float 0-1>,
      "share_rate": <float 0-1>,
      "save_rate": <float 0-1>
    },
    "platform_fit": [
      {"platform": "<平台名>", "score": <int 1-10>, "reason": "<原因>", "recommended": <bool>}
    ]
  },
  "learning_path": [
    {
      "rank": 1,
      "technique": "<技巧名称>",
      "difficulty": "<入门/进阶/高阶>",
      "why": "<为什么学这个>",
      "exercises": ["<练习任务>"],
      "reference": "<参考案例>"
    }
  ],
  "replicable_template": {
    "structure": "<结构公式>",
    "shot_list": [{"order": 1, "shot": "<镜头>", "duration": "<时长>", "note": "<备注>"}],
    "script_template": "<文案模板>"
  },
  "top3_strengths": ["<亮点1>", "<亮点2>", "<亮点3>"],
  "top3_improvements": ["<改进1>", "<改进2>", "<改进3>"]
}

重要提示：
1. 所有时间戳请使用 "分:秒" 格式（如 "1:30"）
2. timeline 必须覆盖视频全部时长，不要遗漏
3. curve_points 至少每30秒一个采样点
4. risk_segments 认真评估，不要全部填 low
5. 输出纯 JSON，不要包裹在代码块中，不要有额外文字"""


def build_scene_prompt(chapters):
    """构建第二次 API 调用的场景细拆 prompt"""
    chapters_text = json.dumps(chapters, ensure_ascii=False, indent=2)
    return f"""你是一位资深短视频拆解专家。上一轮分析已经将视频分为以下章节：

{chapters_text}

现在请对每个章节进行更细粒度的拆解。将每个章节拆分为 2-5 个 scene（每个 scene 约 15-25 秒），提供详细的逐场景分析。

留存风险 (retention_risk) 判断标准：
- 画面单一超过15秒 = medium
- 纯文字无变化超过20秒 = high
- 抽象概念无类比 = medium
- 节奏拖沓、信息密度低 = medium
- 高度重复内容 = high

techniques 的 category 可选：Hook / 留存 / 节奏 / 情绪 / 信任 / 互动 / 视觉

请输出严格的 JSON（不要有额外文字），格式如下：

{{
  "chapters": [
    {{
      "chapter": "<章节名，与输入对应>",
      "start": "<起始时间>",
      "end": "<结束时间>",
      "scenes": [
        {{
          "scene_id": "<章节序号-场景序号，如 1-1>",
          "start": "<起始时间>",
          "end": "<结束时间>",
          "visual": "<画面描述>",
          "audio": "<音频描述>",
          "emotion": "<情绪描述>",
          "emotion_valence": <float -5到5>,
          "emotion_arousal": <float 0到10>,
          "retention_risk": "<low/medium/high>",
          "risk_reason": "<风险原因，如果是low可以写无>",
          "risk_fix": "<修复建议，如果是low可以写无需修复>",
          "quote": "<该场景的核心台词/旁白>",
          "techniques": [
            {{"name": "<手法名称>", "category": "<类别>", "why": "<为什么有效>"}}
          ]
        }}
      ]
    }}
  ]
}}

重要：
1. scene 的时间段必须连续覆盖整个章节，不要有间隙
2. 每个 scene 约 15-25 秒，不要太长也不要太短
3. retention_risk 要诚实评估，不要全填 low
4. techniques 至少列 1 个，突出的场景可以列 2-3 个
5. quote 如果听不清可以写"（无法辨识）"
6. 输出纯 JSON"""


def extract_frames(video_path, output_dir, interval=20):
    """用 ffmpeg 抽帧截图，返回 [(时间秒, base64)] 列表"""
    duration = get_video_duration(video_path)
    frames = []
    frame_dir = os.path.join(output_dir, "frames")
    os.makedirs(frame_dir, exist_ok=True)

    # 计算帧间隔
    if duration <= 60:
        interval = 15
    elif duration <= 180:
        interval = 20
    else:
        interval = 30

    t = 0
    idx = 0
    while t < duration:
        frame_path = os.path.join(frame_dir, f"frame_{idx:04d}.jpg")
        cmd = [
            "ffmpeg", "-y", "-ss", str(t),
            "-i", video_path,
            "-frames:v", "1",
            "-q:v", "5",
            "-vf", "scale=480:-1",
            frame_path
        ]
        try:
            run_cmd(cmd, check=True)
            if os.path.exists(frame_path):
                b64 = file_to_base64(frame_path)
                frames.append({"time": t, "base64": b64})
        except Exception as e:
            log(f"抽帧失败 t={t}: {e}", "WARN")
        t += interval
        idx += 1

    log(f"抽帧完成: {len(frames)} 帧")
    return frames


def analyze_video(video_path, title="", source_url=""):
    """
    执行完整分析流程（Step 3 + Step 4）
    返回合并后的分析 JSON
    """
    log("读取视频并编码为 base64...")
    video_b64 = file_to_base64(video_path)
    b64_mb = len(video_b64) / 1024 / 1024
    log(f"Base64 大小: {b64_mb:.1f}MB")

    if len(video_b64) > MAX_BASE64_BYTES:
        raise RuntimeError(f"视频 base64 ({b64_mb:.1f}MB) 超过 API 限制 (50MB)")

    # Step 3: 8维度 + 5模块 分析
    log("=" * 60)
    log("Step 3: 8维度 + 5进阶模块分析")
    log("=" * 60)

    analysis_prompt = build_analysis_prompt()
    analysis_text = call_doubao_api(video_b64, analysis_prompt)
    analysis = extract_json_from_text(analysis_text)

    if analysis is None:
        log("JSON 解析失败，保存原始响应", "ERROR")
        analysis = {"_raw_response": analysis_text, "overall_score": 0}

    log(f"分析完成，overall_score = {analysis.get('overall_score', 'N/A')}")

    # Step 4: 逐场景细拆
    log("=" * 60)
    log("Step 4: 逐场景细拆")
    log("=" * 60)

    chapters = []
    narrative = analysis.get("narrative", {})
    timeline = narrative.get("timeline", [])

    if timeline:
        chapters = timeline
    else:
        # 如果没有 timeline，按视频时长均匀分段
        duration = get_video_duration(video_path)
        if duration > 0:
            segment_length = min(60, duration / 3)
            t = 0
            idx = 1
            while t < duration:
                end_t = min(t + segment_length, duration)
                chapters.append({
                    "start": f"{int(t // 60)}:{int(t % 60):02d}",
                    "end": f"{int(end_t // 60)}:{int(end_t % 60):02d}",
                    "chapter": f"段落{idx}",
                    "description": ""
                })
                t = end_t
                idx += 1

    if chapters:
        scene_prompt = build_scene_prompt(chapters)
        scene_text = call_doubao_api(video_b64, scene_prompt)
        scenes_data = extract_json_from_text(scene_text)

        if scenes_data:
            analysis["scene_breakdown"] = scenes_data
            scene_count = sum(
                len(ch.get("scenes", []))
                for ch in scenes_data.get("chapters", [])
            )
            log(f"场景细拆完成: {scene_count} 个场景")
        else:
            log("场景细拆 JSON 解析失败", "WARN")
            analysis["scene_breakdown"] = {"_raw_response": scene_text}
    else:
        log("无法获取章节信息，跳过场景细拆", "WARN")

    # 添加元数据
    analysis["_meta"] = {
        "title": title,
        "analyzed_at": datetime.now().isoformat(),
        "video_duration": get_video_duration(video_path),
        "video_size_mb": round(get_file_size(video_path) / 1024 / 1024, 1),
        "source_url": source_url,
    }

    return analysis


# ─── Step 5: 生成报告 ──────────────────────────────────────────────────────────

def generate_report(analysis_data, video_path, title, archive_dir):
    """调用 report_generator.py 生成 HTML 报告"""
    # 抽帧
    tmp_dir = tempfile.mkdtemp(prefix="report_")
    frames = extract_frames(video_path, tmp_dir)
    analysis_data["_frames"] = frames

    # 视频 base64 (for self-contained report)
    analysis_data["_video_base64"] = file_to_base64(video_path)
    analysis_data["_video_path"] = video_path

    # 创建归档目录
    date_str = datetime.now().strftime("%Y%m%d")
    slug = slugify(title)
    report_dir = os.path.join(archive_dir, f"{date_str}_{slug}")
    os.makedirs(report_dir, exist_ok=True)

    # 保存分析 JSON
    json_path = os.path.join(report_dir, "analysis.json")
    # 不保存 base64 视频到 JSON（太大）
    save_data = {k: v for k, v in analysis_data.items() if k != "_video_base64"}
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(save_data, f, ensure_ascii=False, indent=2)

    # 复制视频到归档目录
    import shutil
    video_dest = os.path.join(report_dir, "video.mp4")
    shutil.copy2(video_path, video_dest)

    # 调用 report_generator.py
    report_gen = os.path.join(SCRIPT_DIR, "report_generator.py")
    cmd = [
        sys.executable, report_gen,
        "--analysis-json", json_path,
        "--video-path", video_path,
        "--title", title,
        "--output-dir", report_dir,
        "--video-base64-path", video_path
    ]
    run_cmd(cmd)

    log(f"报告已生成: {report_dir}/")
    return report_dir


# ─── 完整流水线 ────────────────────────────────────────────────────────────────

def run_pipeline(source, title="", archive_dir="./outputs/reports"):
    """运行完整的5步流水线"""
    archive_dir = os.path.abspath(archive_dir)
    os.makedirs(archive_dir, exist_ok=True)

    if not title:
        if os.path.isfile(source):
            title = Path(source).stem
        else:
            title = "视频分析"

    tmp_dir = tempfile.mkdtemp(prefix="video_pipeline_")

    # Step 1: 下载
    log("=" * 60)
    log("Step 1: 下载视频")
    log("=" * 60)
    video_path = download_video(source, tmp_dir)

    # Step 2: 压缩
    log("=" * 60)
    log("Step 2: 压缩视频")
    log("=" * 60)
    compressed_path = os.path.join(tmp_dir, "compressed.mp4")
    compressed_path = compress_video(video_path, compressed_path)

    # Step 3 & 4: 分析
    source_url = source if not os.path.isfile(source) else ""
    analysis = analyze_video(compressed_path, title, source_url)

    # Step 5: 生成报告
    log("=" * 60)
    log("Step 5: 生成 HTML 报告")
    log("=" * 60)
    report_dir = generate_report(analysis, compressed_path, title, archive_dir)

    # 输出结果路径
    report_html = os.path.join(report_dir, "report.html")
    report_lite = os.path.join(report_dir, "report-lite.html")

    log("=" * 60)
    log("流水线完成!")
    log(f"完整报告: {report_html}")
    log(f"轻量报告: {report_lite}")
    log(f"归档目录: {report_dir}")
    log("=" * 60)

    # Auto-sync to GitHub if configured
    try:
        sys.path.insert(0, SCRIPT_DIR)
        from github_sync import auto_sync
        auto_sync(report_dir)
    except Exception as e:
        log(f"GitHub sync skipped: {e}")

    return {
        "report_dir": report_dir,
        "report_html": report_html,
        "report_lite": report_lite,
        "analysis": analysis
    }


# ─── CLI ────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="爆款视频拆解与优化工具",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    subparsers = parser.add_subparsers(dest="command", help="子命令")

    # run - 完整流水线
    p_run = subparsers.add_parser("run", help="运行完整流水线")
    p_run.add_argument("source", help="视频URL或本地路径")
    p_run.add_argument("--title", default="", help="视频标题")
    p_run.add_argument("--archive-dir", default="./outputs/reports", help="报告归档目录")

    # download - 仅下载
    p_dl = subparsers.add_parser("download", help="仅下载视频")
    p_dl.add_argument("url", help="视频URL")
    p_dl.add_argument("--output-dir", default=".", help="输出目录")

    # compress - 仅压缩
    p_comp = subparsers.add_parser("compress", help="仅压缩视频")
    p_comp.add_argument("input", help="输入视频路径")
    p_comp.add_argument("--output", default=None, help="输出路径")
    p_comp.add_argument("--target-size", type=int, default=TARGET_FILE_SIZE, help="目标大小(字节)")

    # analyze - 仅分析
    p_anal = subparsers.add_parser("analyze", help="仅分析视频（无报告）")
    p_anal.add_argument("video", help="视频文件路径")
    p_anal.add_argument("--title", default="", help="视频标题")
    p_anal.add_argument("--output-json", default=None, help="输出JSON路径")

    # report - 从JSON生成报告
    p_rep = subparsers.add_parser("report", help="从分析JSON生成HTML报告")
    p_rep.add_argument("json_path", help="分析JSON路径")
    p_rep.add_argument("--video", required=True, help="视频文件路径")
    p_rep.add_argument("--title", default="", help="视频标题")
    p_rep.add_argument("--archive-dir", default="./outputs/reports", help="报告归档目录")

    args = parser.parse_args()

    if args.command is None:
        parser.print_help()
        sys.exit(1)

    if args.command == "run":
        result = run_pipeline(args.source, args.title, args.archive_dir)
        print(json.dumps({
            "report_dir": result["report_dir"],
            "report_html": result["report_html"],
            "report_lite": result["report_lite"],
            "overall_score": result["analysis"].get("overall_score", "N/A")
        }, ensure_ascii=False, indent=2))

    elif args.command == "download":
        path = download_video(args.url, args.output_dir)
        print(f"Downloaded: {path}")

    elif args.command == "compress":
        path = compress_video(args.input, args.output, args.target_size)
        print(f"Compressed: {path}")

    elif args.command == "analyze":
        analysis = analyze_video(args.video, args.title)
        out = args.output_json or "analysis.json"
        with open(out, "w", encoding="utf-8") as f:
            json.dump(analysis, f, ensure_ascii=False, indent=2)
        print(f"Analysis saved: {out}")

    elif args.command == "report":
        with open(args.json_path, "r", encoding="utf-8") as f:
            data = json.load(f)
        report_dir = generate_report(data, args.video, args.title, args.archive_dir)
        print(f"Report: {report_dir}")


if __name__ == "__main__":
    main()
