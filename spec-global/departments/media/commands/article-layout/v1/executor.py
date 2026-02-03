#!/usr/bin/env python3
"""
Article Layout Splash Command Executor
文章排版命令执行器

执行 /layout 命令，将文章转换为格式化的平台就绪内容。

Usage:
    python article_layout_command.py <file_path> [options]

Options:
    --theme <theme>         主题选择 (wechat_red_safe, blue, minimal)
    --platform <platform>   目标平台 (wechat, xhs, notion, feishu, generic)
    --format <format>       输出格式 (md, html, both)
    --no-proofread          跳过自动校对
"""

import argparse
import json
import os
import sys
from pathlib import Path
from datetime import datetime

# 添加项目根目录到 Python 路径
project_root = Path(__file__).parent.parent.parent.parent.parent
spec_global_root = Path(__file__).parent.parent.parent.parent
sys.path.insert(0, str(project_root))


class ArticleLayoutCommand:
    """文章排版命令执行器"""

    def __init__(self, file_path: str, theme: str = "wechat_red_safe",
                 platform: str = "wechat", output_format: str = "both",
                 proofread: bool = True):
        self.file_path = Path(file_path)
        self.theme = theme
        self.platform = platform
        self.output_format = output_format
        self.proofread = proofread

        # 输出目录
        self.output_dir = self.file_path.parent / "output"
        self.output_dir.mkdir(exist_ok=True)

        # 输出文件名
        base_name = self.file_path.stem
        self.output_md = self.output_dir / f"{base_name}_final.md"
        self.output_html = self.output_dir / f"{base_name}_final.html"
        self.report_file = self.output_dir / f"{base_name}_report.json"

    def validate_input(self):
        """验证输入文件"""
        if not self.file_path.exists():
            raise FileNotFoundError(f"找不到文件：{self.file_path}")

        # 支持的文件格式
        supported_extensions = {".md", ".txt", ".markdown"}
        if self.file_path.suffix.lower() not in supported_extensions:
            raise ValueError(
                f"不支持的文件格式：{self.file_path.suffix}。"
                f"支持的格式：{', '.join(supported_extensions)}"
            )

    def load_theme_config(self):
        """加载主题配置"""
        # 尝试多个可能的路径
        theme_names = [self.theme, "wechat-red-theme", "red-theme"]
        base_paths = [
            spec_global_root / "departments" / "media" / "themes",
            spec_global_root / "themes",
        ]

        for base_path in base_paths:
            for theme_name in theme_names:
                theme_path = base_path / theme_name / "v1" / "theme.yaml"
                if theme_path.exists():
                    import yaml
                    with open(theme_path, "r", encoding="utf-8") as f:
                        config = yaml.safe_load(f)
                        print(f"   加载主题: {theme_name}")
                        return config

        # 如果都没找到，使用默认配置
        print(f"   ⚠ 主题配置未找到，使用默认配置")
        return {
            "colors": {
                "red_primary": "#ff4d4f",
                "red_dark": "#cf1322",
                "red_bg": "#fff1f0",
                "text_main": "#555555",
                "text_muted": "#666666",
                "text_deep": "#4a4a4a",
            }
        }

    def read_article(self):
        """读取文章内容"""
        with open(self.file_path, "r", encoding="utf-8") as f:
            return f.read()

    def apply_layout(self, article_content: str, theme_config: dict) -> str:
        """
        应用排版样式

        这是一个简化的实现，实际应该调用 agent.media.readable_color_layout
        """
        # 读取颜色配置
        colors = theme_config.get("colors", {})

        # 替换标题
        lines = article_content.split("\n")
        result = []

        for line in lines:
            # H1 标题
            if line.startswith("# "):
                line = line.replace(
                    "# ",
                    f'<h1 style="color:{colors.get("red_primary", "#ff4d4f")};font-weight:700;">',
                    1
                ).replace("\n", "</h1>\n")

            # H2 标题
            elif line.startswith("## "):
                line = line.replace(
                    "## ",
                    f'<h2 style="color:{colors.get("red_dark", "#cf1322")};font-weight:600;">',
                    1
                ).replace("\n", "</h2>\n")

            # H3 标题
            elif line.startswith("### "):
                line = line.replace(
                    "### ",
                    f'<h3 style="color:{colors.get("red_dark", "#cf1322")};font-weight:600;">',
                    1
                ).replace("\n", "</h3>\n")

            result.append(line)

        return "\n".join(result)

    def proofread_content(self, content: str) -> tuple:
        """
        校对内容，修复暗色文字

        Returns:
            (proofread_content, issues_found)
        """
        issues_found = []

        # 检查并替换暗色
        dark_colors = {
            "#262626": "#4a4a4a",
            "#333333": "#555555",
            "#8c8c8c": "#666666",
        }

        for dark, light in dark_colors.items():
            if dark in content:
                count = content.count(dark)
                issues_found.append({
                    "type": "dark_text",
                    "color": dark,
                    "replacement": light,
                    "count": count
                })
                content = content.replace(dark, light)

        # 检查引用块颜色
        if '<blockquote style="color:#666666;">' in content:
            content = content.replace(
                '<blockquote style="color:#666666;">',
                '<blockquote style="color:#4a4a4a;">'
            )
            issues_found.append({
                "type": "quote_block_color",
                "original": "#666666",
                "replacement": "#4a4a4a",
                "reason": "引用块使用更深的颜色确保对比度"
            })

        return content, issues_found

    def generate_html(self, markdown_content: str) -> str:
        """生成独立的 HTML 文件"""
        return f"""<!DOCTYPE html>
<html lang="zh-CN">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{self.file_path.stem}</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, "Segoe UI", Roboto, "Helvetica Neue", Arial, sans-serif;
            line-height: 1.8;
            color: #555555;
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
            background: #fff;
        }}
        h1 {{
            color: #ff4d4f;
            font-weight: 700;
            font-size: 24px;
            margin-top: 20px;
            margin-bottom: 20px;
        }}
        h2 {{
            color: #cf1322;
            font-weight: 600;
            font-size: 18px;
            margin-top: 24px;
            margin-bottom: 12px;
            padding-bottom: 8px;
            border-bottom: 2px solid #ff4d4f;
        }}
        h3 {{
            color: #cf1322;
            font-weight: 600;
            font-size: 16px;
            margin-top: 16px;
            margin-bottom: 8px;
        }}
        p {{
            color: #555555;
            font-size: 15px;
            margin: 8px 0;
            line-height: 1.8;
        }}
        blockquote {{
            color: #4a4a4a;
            padding: 12px 16px;
            margin: 16px 0;
            border-left: 4px solid #d9d9d9;
            background: #f5f5f5;
        }}
        blockquote.highlight {{
            background: #fff1f0;
            border-left: 4px solid #ff4d4f;
        }}
        strong {{
            font-weight: 600;
        }}
        ul {{
            padding-left: 20px;
        }}
        li {{
            margin: 4px 0;
        }}
        span.emphasis {{
            color: #ff4d4f;
            font-weight: 600;
        }}
        span.text {{
            color: #555555;
        }}
        hr {{
            border: none;
            border-top: 1px solid #e8e8e8;
            margin: 20px 0;
        }}
        pre {{
            background: #f5f5f5;
            padding: 12px;
            border-radius: 4px;
            overflow-x: auto;
        }}
        code {{
            font-family: "Consolas", "Monaco", monospace;
            font-size: 14px;
        }}
    </style>
</head>
<body>
{markdown_content}
</body>
</html>"""

    def run(self):
        """执行排版命令"""
        print(f"📝 文章排版命令执行器")
        print(f"=" * 50)
        print(f"输入文件: {self.file_path}")
        print(f"主题: {self.theme}")
        print(f"平台: {self.platform}")
        print(f"输出格式: {self.output_format}")
        print(f"自动校对: {'是' if self.proofread else '否'}")
        print()

        # 验证输入
        self.validate_input()

        # 读取文章
        print("📖 读取文章...")
        article_content = self.read_article()

        # 加载主题配置
        print("🎨 加载主题配置...")
        theme_config = self.load_theme_config()

        # 应用排版
        print("✨ 应用排版样式...")
        formatted_content = self.apply_layout(article_content, theme_config)

        # 校对
        proofread_issues = []
        if self.proofread:
            print("🔍 自动校对...")
            formatted_content, proofread_issues = self.proofread_content(formatted_content)
            if proofread_issues:
                print(f"   发现 {len(proofread_issues)} 个问题，已自动修复")

        # 生成报告
        report = {
            "timestamp": datetime.now().isoformat(),
            "input_file": str(self.file_path),
            "theme": self.theme,
            "platform": self.platform,
            "output_format": self.output_format,
            "proofread_issues": proofread_issues,
            "output_files": []
        }

        # 保存输出
        print("💾 保存输出文件...")

        if self.output_format in ["md", "both"]:
            with open(self.output_md, "w", encoding="utf-8") as f:
                f.write(formatted_content)
            report["output_files"].append(str(self.output_md))
            print(f"   ✓ {self.output_md}")

        if self.output_format in ["html", "both"]:
            html_content = self.generate_html(formatted_content)
            with open(self.output_html, "w", encoding="utf-8") as f:
                f.write(html_content)
            report["output_files"].append(str(self.output_html))
            print(f"   ✓ {self.output_html}")

        # 保存报告
        with open(self.report_file, "w", encoding="utf-8") as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        print(f"   ✓ {self.report_file}")

        print()
        print("✅ 排版完成！")
        print(f"📂 输出目录: {self.output_dir}")

        return report


def main():
    """主函数"""
    parser = argparse.ArgumentParser(
        description="文章排版命令 - 将文章转换为格式化的平台就绪内容",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  %(prog)s articles/my-post.md
  %(prog)s articles/my-post.md --theme blue
  %(prog)s articles/my-post.md --platform xhs --format html
  %(prog)s articles/my-post.md --theme minimal --platform notion
        """
    )

    parser.add_argument(
        "file_path",
        help="输入文章的文件路径（.md 或 .txt）"
    )

    parser.add_argument(
        "--theme",
        choices=["wechat_red_safe", "blue", "minimal"],
        default="wechat_red_safe",
        help="排版主题（默认: wechat_red_safe）"
    )

    parser.add_argument(
        "--platform",
        choices=["wechat", "xhs", "notion", "feishu", "generic"],
        default="wechat",
        help="目标平台（默认: wechat）"
    )

    parser.add_argument(
        "--format",
        choices=["md", "html", "both"],
        default="both",
        help="输出格式（默认: both）"
    )

    parser.add_argument(
        "--no-proofread",
        action="store_true",
        help="跳过自动校对"
    )

    args = parser.parse_args()

    # 执行排版
    try:
        command = ArticleLayoutCommand(
            file_path=args.file_path,
            theme=args.theme,
            platform=args.platform,
            output_format=args.format,
            proofread=not args.no_proofread
        )
        command.run()

    except FileNotFoundError as e:
        print(f"❌ {e}", file=sys.stderr)
        print("请检查文件路径是否正确", file=sys.stderr)
        sys.exit(1)

    except ValueError as e:
        print(f"❌ {e}", file=sys.stderr)
        sys.exit(1)

    except Exception as e:
        print(f"❌ 执行出错: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
