#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import argparse
import csv
import os
import re
from typing import Optional, Tuple

from mutagen.id3 import ID3, ID3NoHeaderError, ID3BadUnsynchData, TIT2, TPE1, TALB
from mutagen.id3._frames import TextFrame
from mutagen import MutagenError
from pypinyin import pinyin, Style

_CHINESE_RE = re.compile(r'[\u4e00-\u9fff]')

def contains_chinese(s: str) -> bool:
    return bool(_CHINESE_RE.search(s or ""))

def to_pinyin(text: str, with_tone: bool = False) -> str:
    """
    将中文转为 CamelCase 拼音（每个音节首字母大写并连写），非中文原样保留。
    例：挂号费 -> GuaHaoFei； --tone 时 -> Gua1Hao4Fei4
    """
    if not text:
        return text

    parts = []
    i = 0
    n = len(text)

    while i < n:
        if _CHINESE_RE.match(text[i]):
            # 收集连续中文块
            j = i + 1
            while j < n and _CHINESE_RE.match(text[j]):
                j += 1
            chinese_chunk = text[i:j]

            # 选择拼音风格：无声调 or 数字声调
            style = Style.TONE3 if with_tone else Style.NORMAL
            py_list = pinyin(chinese_chunk, style=style, heteronym=False)

            # py_list 是二维列表，展平成音节序列
            syllables = [syll[0] for syll in py_list if syll]

            def camelize_syllable(s: str) -> str:
                # 处理如 "zhong1"：首字母大写，其余保持（数字声调保留在末尾）
                # 找到首个字母部分与后续（可能包含数字）
                m = re.match(r"([a-zA-Z]+)(.*)", s)
                if not m:
                    return s  # 理论上不会发生
                head, tail = m.group(1), m.group(2)
                return head[:1].upper() + head[1:].lower() + tail

            camel = "".join(camelize_syllable(s) for s in syllables)
            parts.append(camel)
            i = j
        else:
            # 非中文字符原样逐字加入（包含空格/标点/英文等）
            parts.append(text[i])
            i += 1

    # 合并
    result = "".join(parts)
    # 压缩可能的多余空格
    result = re.sub(r'\s{2,}', ' ', result).strip()
    return result

def read_text(frame: Optional[TextFrame]) -> Optional[str]:
    if not frame:
        return None
    try:
        if isinstance(frame.text, list):
            return frame.text[0] if frame.text else ""
        return str(frame.text)
    except Exception:
        return None

def set_text(tags: ID3, frame_cls, value: str):
    key = frame_cls.__name__
    old_frame = tags.getall(key)
    encoding = old_frame[0].encoding if old_frame else 3  # 3=UTF-8
    tags.setall(key, [])
    tags.add(frame_cls(encoding=encoding, text=value))

def convert_tag_value(value: Optional[str], with_tone: bool) -> Tuple[Optional[str], bool]:
    if not value:
        return value, False
    if contains_chinese(value):
        return to_pinyin(value, with_tone=with_tone), True
    return value, False

def process_file(path: str, with_tone: bool, dry_run: bool) -> dict:
    result = {
        "file": path,
        "changed": False,
        "title_before": None, "title_after": None,
        "artist_before": None, "artist_after": None,
        "album_before": None, "album_after": None,
        "error": None,
    }
    try:
        try:
            tags = ID3(path)
        except ID3NoHeaderError:
            tags = ID3()
            tags.save(path)

        title = read_text(tags.get("TIT2"))
        artist = read_text(tags.get("TPE1"))
        album = read_text(tags.get("TALB"))

        result["title_before"] = title
        result["artist_before"] = artist
        result["album_before"] = album

        new_title, title_changed = convert_tag_value(title, with_tone)
        new_artist, artist_changed = convert_tag_value(artist, with_tone)
        new_album, album_changed = convert_tag_value(album, with_tone)

        result["title_after"] = new_title
        result["artist_after"] = new_artist
        result["album_after"] = new_album

        if title_changed or artist_changed or album_changed:
            result["changed"] = True
            if not dry_run:
                if title_changed:
                    set_text(tags, TIT2, new_title)
                if artist_changed:
                    set_text(tags, TPE1, new_artist)
                if album_changed:
                    set_text(tags, TALB, new_album)
                try:
                    tags.save(path, v2_version=3)
                except (ID3BadUnsynchData, MutagenError):
                    tags.save(path)

    except (MutagenError, Exception) as e:
        result["error"] = str(e)

    return result

def is_mp3(filename: str) -> bool:
    return filename.lower().endswith(".mp3")

def main():
    parser = argparse.ArgumentParser(
        description="将MP3的 Artist/Album/Title 中的中文转为拼音（保留非中文）"
    )
    parser.add_argument("folder", help="包含MP3文件的文件夹路径")
    parser.add_argument("--tone", action="store_true", help="使用带声调拼音（默认不带声调）")
    parser.add_argument("--dry-run", action="store_true", help="仅预览更改，不写回文件")
    parser.add_argument("--recursive", action="store_true", help="递归处理子目录")
    parser.add_argument("--backup", default="backup_tags.csv", help="备份CSV文件名（默认：backup_tags.csv）")
    args = parser.parse_args()

    folder = os.path.abspath(os.path.expanduser(args.folder))
    if not os.path.isdir(folder):
        print(f"[错误] 路径不是文件夹：{folder}")
        return

    rows = []
    total = 0
    changed = 0
    errors = 0

    if args.recursive:
        walker = ((root, files) for root, _, files in os.walk(folder))
    else:
        walker = ((folder, os.listdir(folder)) ,)

    for root, files in walker:
        for name in files:
            if not is_mp3(name):
                continue
            path = os.path.join(root, name)
            total += 1
            info = process_file(path, with_tone=args.tone, dry_run=args.dry_run)
            rows.append(info)
            if info["error"]:
                errors += 1
                print(f"[失败] {path} -> {info['error']}")
            elif info["changed"]:
                changed += 1
                print(f"[变更] {path}")
                print(f"       Title : {info['title_before']} -> {info['title_after']}")
                print(f"       Artist: {info['artist_before']} -> {info['artist_after']}")
                print(f"       Album : {info['album_before']} -> {info['album_after']}")
            else:
                print(f"[跳过] {path}（无中文或无需更改）")

    backup_path = os.path.join(folder, args.backup)
    try:
        with open(backup_path, "w", newline="", encoding="utf-8") as f:
            writer = csv.DictWriter(
                f,
                fieldnames=[
                    "file",
                    "title_before", "title_after",
                    "artist_before", "artist_after",
                    "album_before", "album_after",
                    "changed", "error"
                ]
            )
            writer.writeheader()
            for r in rows:
                writer.writerow(r)
        print(f"\n已写入备份：{backup_path}")
    except Exception as e:
        print(f"[警告] 备份写入失败：{e}")

    mode = "预览" if args.dry_run else "写入"
    print(f"\n处理完成（{mode}）：共 {total} 个MP3，变更 {changed} 个，失败 {errors} 个。")

if __name__ == "__main__":
    main()

#pip install mutagen pypinyin
#python yuyang\mp3Chinese.py "C:\temp\mp3" 