#!/usr/bin/env python3
"""
从上海高考真题作文 DOCX 中提取所有独立作文，保存为独立文本文件。

解析规则：
- 以年份/题目标记识别作文边界
- 去除分数、编号前缀等元数据
- 保存为 samples/ 目录下的独立 .txt
"""

import xml.etree.ElementTree as ET
import re
import json
from pathlib import Path
from dataclasses import dataclass, field


@dataclass
class Essay:
    title: str
    year: str
    grade: str = ""
    topic: str = ""
    body: list[str] = field(default_factory=list)
    filename: str = ""

    @property
    def full_text(self) -> str:
        return "\n\n".join(self.body)

    @property
    def word_count(self) -> int:
        return len(self.full_text.replace("\n", ""))

    @property
    def paragraph_count(self) -> int:
        return len(self.body)


def parse_paragraphs(filepath: str) -> list[str]:
    """提取所有段落文本"""
    tree = ET.parse(filepath)
    paragraphs = []
    for p in tree.iter('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}p'):
        texts = []
        for t in p.iter('{http://schemas.openxmlformats.org/wordprocessingml/2006/main}t'):
            if t.text:
                texts.append(t.text)
        line = ''.join(texts).strip()
        if line:
            paragraphs.append(line)
    return paragraphs


def clean_body_line(line: str) -> str:
    """清理段落编号前缀（如 '1.' '①' 等），保留正文内容"""
    # 移除编号前缀: "1." "2．" "①" "1、" 等
    cleaned = re.sub(r'^[\d]+[\.\．\、\s]+', '', line).strip()
    cleaned = re.sub(r'^[①②③④⑤⑥⑦⑧⑨⑩]', '', cleaned).strip()
    return cleaned


def extract_essays(paragraphs: list[str]) -> list[Essay]:
    """从段落列表中识别并提取所有作文"""
    essays = []
    current_essay = None
    current_year = ""
    current_topic = ""
    in_essay_body = False
    saw_title_after_grade = False

    # 年份标记模式
    year_pattern = re.compile(r'(\d{4})年|【(\d{4}).*作文】')

    # 分数标记
    grade_pattern = re.compile(r'[一二三]类[上中下]?\s*\d+分')

    i = 0
    while i < len(paragraphs):
        p = paragraphs[i]

        # 检测年份
        ym = year_pattern.search(p)
        if ym:
            current_year = ym.group(1) or ym.group(2)
            # 如果下一行是作文题目
            if i + 1 < len(paragraphs):
                current_topic = paragraphs[i + 1]
            i += 1
            continue

        # 检测分数/等级行
        if grade_pattern.search(p) and current_essay is None:
            # 前一行是标题
            i += 1
            continue

        # 检测"要求"行 -> 跳过
        if '要求' in p and ('不少于800字' in p or '自拟题目' in p or '(1)自拟' in p):
            i += 1
            continue

        # 检测作文题目行 (以"作文。"结尾或"写作"开头)
        if ('作文' in p and re.search(r'\d+分', p)) or p.startswith('三、写作'):
            i += 1
            continue

        # 检测"X、作文"行
        if re.match(r'\d+[\.\、]\s*作文', p):
            # 下一行是题目
            if i + 1 < len(paragraphs):
                current_topic = paragraphs[i + 1]
                i += 2
            else:
                i += 1
            continue

        # --- 作文边界检测 ---
        # 如果前一行是分数/等级，当前行很可能是新作文的第一段
        prev_is_grade = (i > 0 and grade_pattern.search(paragraphs[i - 1]))
        # 如果前两行是标题+等级
        prev_2_is_grade = (i > 1 and grade_pattern.search(paragraphs[i - 1]))
        prev_1_is_title = (i > 0 and len(paragraphs[i - 1]) < 30 and not grade_pattern.search(paragraphs[i - 1]))

        # 新作文的开始：上一行是标题且之前是等级
        if prev_2_is_grade and prev_1_is_title and len(p) > 30 and re.match(r'^[\d①②]', p):
            if current_essay:
                essays.append(current_essay)
            title = paragraphs[i-1]
            grade = paragraphs[i-2]
            body_text = clean_body_line(p)
            current_essay = Essay(
                title=title, year=current_year, grade=grade,
                body=[body_text], topic=current_topic,
            )
            i += 1
            continue

        # 简化的边界检测：上一行含分数，当前行以数字或①开头
        if prev_is_grade and re.match(r'^[\d①②]', p) and len(p) > 30:
            if current_essay:
                essays.append(current_essay)
            # 标题可能在两个元素之前
            title = paragraphs[i-2] if i >= 2 and len(paragraphs[i-2]) < 30 else ""
            grade = paragraphs[i-1]
            body_text = clean_body_line(p)
            current_essay = Essay(
                title=title, year=current_year, grade=grade,
                body=[body_text], topic=current_topic,
            )
            i += 1
            continue

        # 检测无编号开头的作文（如2018的那篇）
        # 标题后直接跟正文（正文不以数字开头）
        if current_essay is None and len(p) > 50 and not re.match(r'^\d', p):
            # 检查前面是否刚见过年份+题目+标题模式
            # 对于2018作文：标题是 "请理性看待'被需要'"，下一行就是正文
            if i > 0 and len(paragraphs[i-1]) < 30:
                title = paragraphs[i-1]
                current_essay = Essay(
                    title=title, year=current_year, grade="",
                    body=[p], topic=current_topic,
                )
                i += 1
                continue

        # 在作文体内：继续收集段落
        if current_essay is not None:
            # 检测新的作文标题（下一行是分数 + 再后面以数字开头）
            if (i + 1 < len(paragraphs) and grade_pattern.search(paragraphs[i])
                and i + 2 < len(paragraphs) and re.match(r'^[\d①②]', paragraphs[i+2])):
                essays.append(current_essay)
                current_essay = None
                i += 1
                continue

            # 检测年份切换
            if year_pattern.search(p) or '【2025' in p:
                essays.append(current_essay)
                current_essay = None
                # 更新年份
                ym = year_pattern.search(p)
                if ym:
                    current_year = ym.group(1) or ym.group(2)
                if '【2025' in p:
                    current_year = '2025'
                i += 1
                continue

            # 正常段落
            cleaned = clean_body_line(p)
            if cleaned:
                current_essay.body.append(cleaned)
            i += 1
            continue

        i += 1

    # 保存最后一篇
    if current_essay and current_essay.body:
        essays.append(current_essay)

    return essays


def main():
    docx_path = Path("/Users/tangmingde/Desktop/副本往年上海高考真题作文习作.docx")
    unpacked_xml = Path("/Users/tangmingde/Downloads/lab5/unpacked_zuowen2/word/document.xml")
    output_dir = Path("/Users/tangmingde/Downloads/lab5/arggraph_agent/samples/sh_gaokao")
    output_dir.mkdir(parents=True, exist_ok=True)

    paragraphs = parse_paragraphs(str(unpacked_xml))
    print(f"共提取 {len(paragraphs)} 个段落")

    essays = extract_essays(paragraphs)

    print(f"\n识别到 {len(essays)} 篇作文:\n")
    for i, e in enumerate(essays):
        safe_title = re.sub(r'[^\w\u4e00-\u9fff]', '_', e.title)[:30]
        e.filename = f"{e.year}_{e.grade.replace(' ','')}_{safe_title}.txt"
        e.filename = e.filename.strip('_')

        out_path = output_dir / e.filename
        out_path.write_text(e.full_text, encoding='utf-8')

        print(f"{i+1:2d}. [{e.year}] {e.title}")
        print(f"    等级: {e.grade if e.grade else '未标注'}")
        print(f"    段数: {e.paragraph_count}, 字数: {e.word_count}")
        print(f"    文件: {e.filename}")
        print()

    # 保存 JSON 清单
    manifest = []
    for e in essays:
        manifest.append({
            "title": e.title,
            "year": e.year,
            "grade": e.grade,
            "topic": e.topic,
            "filename": e.filename,
            "paragraphs": e.paragraph_count,
            "word_count": e.word_count,
        })

    manifest_path = output_dir / "manifest.json"
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2), encoding='utf-8')
    print(f"清单已保存: {manifest_path}")

    return essays


if __name__ == "__main__":
    main()
