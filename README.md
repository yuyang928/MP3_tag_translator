# MP3_tag_translator
Translate MP3 metadata from Chinese characters to Pinyin
A small script I wrote to convert Chinese MP3 tags into Pinyin.

It scans the Artist, Album and Title fields in MP3 ID3 tags and replaces any Chinese characters with CamelCase Pinyin.

Example:

```
周杰伦 -> ZhouJieLun
七里香 -> QiLiXiang
挂号费 -> GuaHaoFei
```

With `--tone`:

```
周杰伦 -> Zhou1Jie2Lun2
```

## Why

I have some MP3 players and car audio systems that don't display Chinese properly.

This script converts the metadata to Pinyin so the songs can still be sorted and displayed correctly.

## Requirements

Python 3.x

Install packages:

```bash
pip install mutagen pypinyin
```

## Usage

Basic:

```bash
python mp3Chinese.py "C:\temp\mp3"
```

Preview only:

```bash
python mp3Chinese.py "C:\temp\mp3" --dry-run
```

Include tone numbers:

```bash
python mp3Chinese.py "C:\temp\mp3" --tone
```

Scan subfolders:

```bash
python mp3Chinese.py "C:\temp\mp3" --recursive
```

Custom backup file:

```bash
python mp3Chinese.py "C:\temp\mp3" --backup my_backup.csv
```

## What it changes

The script only updates:

- Title (TIT2)
- Artist (TPE1)
- Album (TALB)

Filenames are not changed.

## Example

Before:

```
Title : 七里香
Artist: 周杰伦
Album : 七里香
```

After:

```
Title : QiLiXiang
Artist: ZhouJieLun
Album : QiLiXiang
```

## Backup

A CSV file is generated in the target folder.

Default name:

```
backup_tags.csv
```

The CSV contains the original values and the converted values, so you can see what was changed.

## Notes

- Only MP3 files are processed.
- Non-Chinese text is left as-is.
- Files without Chinese tags are skipped.
- Existing ID3 data should be preserved.
- Dry-run mode is recommended before doing large batches.

## Example workflow

First run:

```bash
python mp3Chinese.py "D:\Music" --dry-run --recursive
```

If the output looks good:

```bash
python mp3Chinese.py "D:\Music" --recursive
```

