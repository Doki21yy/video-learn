#!/usr/bin/env python3
"""
video_learner.py - 视频深度学习总结引擎
功能：下载 -> 压缩 -> 豆包大模型原生视频理解 -> 内容分析+场景细拆 -> 生成学习报告
"""

import argparse
import json
import os
import shutil
import sys
import tempfile
from datetime import datetime
from pathlib import Path

# ─── 模块路径 ─────────────────────────────────────────────────────────────────
SCRIPT_DIR = Path(__file__).resolve().parent
SKILL_DIR = SCRIPT_DIR.parent

from video_analyzer import (
    download_video,
    compress_video,
    extract_frames,
    call_doubao_api,
    extract_json_from_text,
    file_to_base64,
    get_video_duration,
    get_file_size,
    slugify,
    log,
    run_cmd,
    detect_platform,
    base64_size,
    MAX_BASE64_BYTES,
)


# ─── 学习分析 Prompt ─────────────────────────────────────────────────────────

def build_learning_prompt():
    """构建深度学习指南分析 prompt"""
    return """你是一位顶级技术文档撰写者和学习指南设计师。请深度分析这段视频，生成一份**全面、实用、可直接用来学习**的深度知识文档。

你的目标不是简单总结"视频讲了什么"，而是创建一份**让没看过视频的人也能完全掌握核心知识**的学习指南。就像一位优秀的学生写了非常详细的课堂笔记分享给同学。

请输出严格的 JSON（不要有多余文字），格式如下：

{
  "title_cn": "<视频标题的中文翻译/解释版本（如果是中文视频就保持原标题）>",
  "topic": "<视频主题，简短概括>",
  "category": "<分类标签，如：AI工具/编程/3D动画/设计/商业/科学/...>",
  "tags": ["<关键词标签1>", "<标签2>", "<标签3>"],
  "difficulty": "<beginner|intermediate|advanced>",
  "learning_rating": <float 1-10, 内容的学习价值评分>,
  "speaker": "<讲者/UP主/频道名称>",
  "language": "<视频语言，如 中文/英文/日文>",
  "video_info": {
    "publish_date": "<如能识别发布日期>",
    "views_estimate": "<如能识别大概观看量>"
  },
  "overview": "<300-500字的核心内容概述。要用流畅的中文叙述视频的核心主题、解决了什么问题、核心方法/技术是什么、最终效果如何。要让读者看完概述就能理解这个视频到底在讲什么。如果是英文视频，概述必须用中文写。>",
  "sections": [
    {
      "title": "<知识板块标题，按主题组织而非时间线>",
      "content": "<该板块的详细内容，用中文 Markdown 格式撰写。要求：\n1. 每个板块 200-800 字\n2. 深入解释核心原理和概念，不要停留在表面\n3. 如果涉及操作步骤，用编号列表详细写出\n4. 如果涉及工具/模型/软件，说明名称、用途和关键参数\n5. 如果涉及对比/选择，用表格或列表对比\n6. 保留重要的英文术语（首次出现时在括号中标注英文原文）\n7. 遇到代码、命令行、提示词时用 ``` 代码块格式>",
      "subsections": [
        {
          "title": "<子标题>",
          "content": "<子板块详细内容，Markdown 格式>"
        }
      ]
    }
  ],
  "resources": [
    {
      "name": "<工具/模型/网站名称>",
      "url": "<如果视频中提到了链接>",
      "description": "<简短描述用途>",
      "type": "<tool|model|website|tutorial|template|other>"
    }
  ],
  "key_tips": [
    "<实用技巧/最佳实践1：要具体，不要泛泛而谈>",
    "<技巧2>",
    "<技巧3>"
  ],
  "faq": [
    {
      "question": "<常见问题或容易踩的坑>",
      "answer": "<解决方法或建议>"
    }
  ],
  "hardware_requirements": "<如果视频涉及软件/模型，说明硬件需求，否则为空字符串>",
  "target_audience": ["<适合人群1>", "<适合人群2>"],
  "summary": "<200-300字的总结，概括核心价值、最大亮点、关键结论。写出看完之后最应该记住的东西。>",
  "related_links": [
    {
      "label": "<链接描述>",
      "url": "<链接地址>"
    }
  ]
}

**核心要求：**

1. **深度 > 广度**：每个 section 要深入讲透，不要蜻蜓点水。一个知识点宁可写300字讲清楚，也不要10个知识点每个只写一句话。

2. **按知识主题组织，不是按时间线**：sections 按照"核心技术原理"、"详细步骤"、"高级用法"、"注意事项"这样的知识结构组织，而不是"第一分钟讲了什么、第二分钟讲了什么"。

3. **提取所有资源和链接**：视频中提到的每一个工具名、模型名、网站链接、下载地址、GitHub 仓库都要提取到 resources 中。

4. **中文撰写**：即使是英文视频，所有内容必须用中文撰写。重要英文术语保留原文。

5. **实用导向**：key_tips 和 faq 要是真正实用的信息，不是空话。比如"GPU显存不够时可以用XX版本模型"而不是"需要好的硬件"。

6. **sections 数量**：通常 3-8 个 section，视频越长/内容越丰富 section 越多。每个 section 可以有 0-5 个 subsections。

7. **learning_rating 评分标准**：
   - 1-3: 内容浅薄、广告性质
   - 4-5: 有一定信息量但不深入
   - 6-7: 内容充实，有实用价值
   - 8-9: 非常优质，系统性强
   - 10: 顶级教程，完整且深入

8. 输出纯 JSON，不要包裹在代码块中"""


def build_scene_learning_prompt(sections):
    """构建场景细拆 prompt（保留用于视频播放器场景同步）"""
    return """你是一位视频内容时间线分析师。请将这段视频按时间顺序拆分为多个场景片段，每个片段约 20-40 秒。

请输出严格的 JSON（不要有额外文字），格式如下：

{
  "chapters": [
    {
      "chapter": "<该时间段的主题>",
      "start": "<起始时间>",
      "end": "<结束时间>",
      "scenes": [
        {
          "scene_id": "<章节序号-场景序号，如 1-1>",
          "start": "<起始时间>",
          "end": "<结束时间>",
          "visual": "<画面描述>",
          "narration": "<讲者说了什么（中文概括）>",
          "core_concept": "<核心知识点>",
          "teaching_method": "<类比/演示/举例/理论/实操/对比>",
          "clarity": "<high/medium/low>",
          "note": "<一句话关键笔记>"
        }
      ]
    }
  ]
}

要求：
1. 场景时间段必须连续覆盖整个视频，不要有间隙
2. 每个场景的 narration 用中文概括讲者在说什么
3. core_concept 提炼该场景最重要的一个知识点
4. 输出纯 JSON"""


# ─── 分析流程 ─────────────────────────────────────────────────────────────────

def analyze_video(video_path, title="", source_url=""):
    """
    执行学习内容分析（两阶段 API 调用）
    返回分析 JSON
    """
    log("读取视频并编码为 base64...")
    video_b64 = file_to_base64(video_path)
    b64_mb = len(video_b64) / 1024 / 1024
    log(f"Base64 大小: {b64_mb:.1f}MB")

    if len(video_b64) > MAX_BASE64_BYTES:
        raise RuntimeError(f"视频 base64 ({b64_mb:.1f}MB) 超过 API 限制 (50MB)")

    # Stage 1: 内容学习分析
    log("=" * 60)
    log("Stage 1: 内容学习分析")
    log("=" * 60)

    learning_prompt = build_learning_prompt()
    analysis_text = call_doubao_api(video_b64, learning_prompt)
    analysis = extract_json_from_text(analysis_text)

    if analysis is None:
        log("JSON 解析失败，保存原始响应", "ERROR")
        analysis = {"_raw_response": analysis_text, "learning_rating": 0}

    log(f"分析完成，learning_rating = {analysis.get('learning_rating', 'N/A')}")

    # Stage 2: 场景细拆（学习版）
    log("=" * 60)
    log("Stage 2: 场景细拆")
    log("=" * 60)

    chapters = analysis.get("chapters", [])

    if not chapters:
        # 按时长均匀分段
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
                    "title": f"段落{idx}",
                    "summary": "",
                    "key_points": []
                })
                t = end_t
                idx += 1

    if chapters:
        scene_prompt = build_scene_learning_prompt(chapters)
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

    # 抽帧截图（用于封面和时间线）
    log("抽取视频帧截图...")
    tmp_frame_dir = tempfile.mkdtemp(prefix="vlearn_frames_")
    frames = extract_frames(video_path, tmp_frame_dir)
    if frames:
        analysis["_frames"] = frames
        log(f"抽帧完成: {len(frames)} 帧")
    else:
        log("抽帧失败，报告将不包含截图", "WARN")

    # 添加元数据
    analysis["_meta"] = {
        "title": title,
        "type": "learning",
        "analyzed_at": datetime.now().isoformat(),
        "video_duration": get_video_duration(video_path),
        "video_size_mb": round(get_file_size(video_path) / 1024 / 1024, 1),
        "source_url": source_url,
    }

    return analysis


# ─── 报告生成 ─────────────────────────────────────────────────────────────────

def generate_report(analysis_data, video_path, title, archive_dir):
    """调用 learn_report.py 生成 HTML 报告（无需视频 base64，使用平台内嵌播放器）"""
    # 创建归档目录
    date_str = datetime.now().strftime("%Y%m%d")
    slug = slugify(title)
    report_dir = os.path.join(archive_dir, f"{date_str}_{slug}")
    os.makedirs(report_dir, exist_ok=True)

    # 保存分析 JSON（保留 _frames 用于封面提取，排除 _video_base64）
    json_path = os.path.join(report_dir, "analysis.json")
    save_data = {k: v for k, v in analysis_data.items()
                 if not k.startswith("_video_base64")}
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(save_data, f, ensure_ascii=False, indent=2)

    # 调用 learn_report.py 生成 HTML（不再传 video-base64-path）
    report_gen = os.path.join(SCRIPT_DIR, "learn_report.py")
    cmd = [
        sys.executable, report_gen,
        "--analysis-json", json_path,
        "--title", title,
        "--output-dir", report_dir,
    ]
    run_cmd(cmd)

    log(f"报告已生成: {report_dir}/")
    return report_dir


# ─── 完整流水线 ───────────────────────────────────────────────────────────────

def run_pipeline(source, title="", archive_dir="./outputs/learning"):
    """运行完整的学习总结流水线"""
    archive_dir = os.path.abspath(archive_dir)
    os.makedirs(archive_dir, exist_ok=True)

    if not title:
        if os.path.isfile(source):
            title = Path(source).stem
        else:
            title = "视频学习笔记"

    tmp_dir = tempfile.mkdtemp(prefix="video_learn_")

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

    # Step 3: 分析
    source_url = source if not os.path.isfile(source) else ""
    analysis = analyze_video(compressed_path, title, source_url)

    # Step 4: 生成报告
    log("=" * 60)
    log("Step 4: 生成学习报告")
    log("=" * 60)
    report_dir = generate_report(analysis, compressed_path, title, archive_dir)

    report_html = os.path.join(report_dir, "report.html")
    report_lite = os.path.join(report_dir, "report-lite.html")

    log("=" * 60)
    log("流水线完成!")
    log(f"完整报告: {report_html}")
    log(f"轻量报告: {report_lite}")
    log(f"归档目录: {report_dir}")
    log("=" * 60)

    # Auto-sync to GitHub
    try:
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


# ─── CLI ──────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(
        description="视频深度学习总结工具",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    subparsers = parser.add_subparsers(dest="command", help="子命令")

    # run
    p_run = subparsers.add_parser("run", help="运行完整流水线")
    p_run.add_argument("source", help="视频URL或本地路径")
    p_run.add_argument("--title", default="", help="视频标题")
    p_run.add_argument("--archive-dir", default="./outputs/learning", help="报告归档目录")

    # download
    p_dl = subparsers.add_parser("download", help="仅下载视频")
    p_dl.add_argument("url", help="视频URL")
    p_dl.add_argument("--output-dir", default=".", help="输出目录")

    # compress
    p_comp = subparsers.add_parser("compress", help="仅压缩视频")
    p_comp.add_argument("input", help="输入视频路径")
    p_comp.add_argument("--output", default=None, help="输出路径")

    # analyze
    p_anal = subparsers.add_parser("analyze", help="仅分析视频")
    p_anal.add_argument("video", help="视频文件路径")
    p_anal.add_argument("--title", default="", help="视频标题")
    p_anal.add_argument("--output-json", default=None, help="输出JSON路径")

    # report
    p_rep = subparsers.add_parser("report", help="从JSON生成报告")
    p_rep.add_argument("json_path", help="分析JSON路径")
    p_rep.add_argument("--video", required=True, help="视频文件路径")
    p_rep.add_argument("--title", default="", help="视频标题")
    p_rep.add_argument("--archive-dir", default="./outputs/learning", help="报告归档目录")

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
            "learning_rating": result["analysis"].get("learning_rating", "N/A")
        }, ensure_ascii=False, indent=2))

    elif args.command == "download":
        path = download_video(args.url, args.output_dir)
        print(f"Downloaded: {path}")

    elif args.command == "compress":
        from video_analyzer import TARGET_FILE_SIZE
        path = compress_video(args.input, args.output, TARGET_FILE_SIZE)
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
