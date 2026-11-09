#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
天梯抓取解析测试：编号列表优先、分节结构回退、未知专精必须显式报错。

这里只测纯解析与渲染，不走网络——抓取逻辑由 .github/workflows/tier-list-refresh.yml 兜。
"""

import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
sys.path.insert(0, str(ROOT / "tools"))

import fetch_tier_lists as ftl  # noqa: E402

# 重试用例会打一堆预期内的 WARNING，测试输出里不用看见
ftl.LOG.setLevel(50)

GUIDE = ftl.GUIDES[0]

NUMBERED_PAGE = """Title: DPS Raid Rankings - Test
URL Source: https://example.com/guide
Markdown Content:
## Patch 12.1 DPS Tier List

### Filter Buttons

S

A

1.   Arms Warrior (A Tier)

2.   Devourer Demon Hunter (A+ Tier)

3.   Affliction Warlock (B Tier)
"""

HEADING_PAGE = """Title: Tank Tier List - Test
Markdown Content:
### **S-Tier Specs**
#### Blood Death Knight
### A-Tier Specs
#### Guardian Druid
#### Changelog
*   nothing to see here
### B-Tier Specs
#### Brewmaster Monk
"""

UNKNOWN_PAGE = """Title: 未知专精页
Markdown Content:
1.   Pirate Rogue (S Tier)
2.   Frost Mage (A Tier)
3.   Fire Mage (A Tier)
4.   Arcane Mage (A Tier)
"""

AUTHOR_PAGE = """Title: x
Markdown Content:
I'm not sure this is a good idea.

#### About the Author

Hi, I'm YoDa. I have been tanking since Shadowlands.
"""

# 阅读器取不到页面时的产物：正文前带 Warning 的空壳页、404 页、没有正文。
# 注意：“Why are you reporting this ad?” 是 wowhead 每个页面都带的隐藏弹窗，不是错误标志。
LAZY_PAGE = """Title: Tank Raid Rankings - Test
URL Source: https://example.com/guide
Warning: This page maybe not yet fully loaded, consider explicitly specify a timeout.

Markdown Content:

"""

NO_TITLE_PAGE = """URL Source: https://example.com/guide
Markdown Content:

"""

NOT_FOUND_PAGE = """Title: Page Not Found
URL Source: https://example.com/guide
Markdown Content:
Sorry, we couldn't find that page.
"""


class NumberedListTest(unittest.TestCase):
    def test_编号列表优先且支持A_加档(self):
        page = ftl.parse_page(NUMBERED_PAGE, GUIDE)
        self.assertEqual(page.title, "DPS Raid Rankings - Test")
        self.assertEqual(page.tiers["A"], ["warrior|武器"])
        self.assertEqual(page.tiers["A+"], ["demon-hunter|噬灭"])
        self.assertEqual(page.tiers["B"], ["warlock|痛苦"])
        self.assertNotIn("S", page.tiers)

    def test_过滤按钮里的裸字母不会被当成层级(self):
        page = ftl.parse_page(NUMBERED_PAGE, GUIDE)
        self.assertEqual(sum(len(v) for v in page.tiers.values()), 3)


class HeadingFallbackTest(unittest.TestCase):
    def test_没有编号列表时按分节标题取(self):
        page = ftl.parse_page(HEADING_PAGE, GUIDE)
        self.assertEqual(page.tiers["S"], ["death-knight|鲜血"])
        self.assertEqual(page.tiers["A"], ["druid|守护"])
        self.assertEqual(page.tiers["B"], ["monk|酒仙"])

    def test_bold标题也能识别(self):
        page = ftl.parse_page(HEADING_PAGE, GUIDE)
        self.assertIn("S", page.tiers)


class UnknownSpecTest(unittest.TestCase):
    def test_未登记专精要报出来而不是静默丢弃(self):
        page = ftl.parse_page(UNKNOWN_PAGE, GUIDE)
        self.assertTrue(any("Pirate Rogue" in item for item in page.unknowns))
        self.assertEqual(page.tiers["A"], ["mage|冰霜", "mage|火焰", "mage|奥术"])

    def test_一条专精都解析不出时直接失败(self):
        with self.assertRaises(ValueError):
            ftl.parse_page("Title: x\nMarkdown Content:\n没有排名内容\n", GUIDE)


class AuthorTest(unittest.TestCase):
    def test_作者只在About段落里取(self):
        self.assertEqual(ftl.extract_author(AUTHOR_PAGE), "YoDa")

    def test_正文里的I_m不会被当成作者(self):
        self.assertEqual(ftl.extract_author("Markdown Content:\nI'm not sure.\n"), "Wowhead")

    def test_中文署名优先(self):
        text = "Markdown Content:\n[来自 AutomaticJak](https://x) 已更新：  2026/10/13"
        self.assertEqual(ftl.extract_author(text), "AutomaticJak")


class RenderTest(unittest.TestCase):
    def test_渲染出七个层级且导出默认变量(self):
        page = ftl.parse_page(NUMBERED_PAGE, GUIDE)
        content = ftl.render_js(GUIDE, page)
        for tier in ftl.TIER_ORDER:
            self.assertIn(f'"{tier}": {{', content)
        self.assertIn("export default dpsTierList;", content)
        self.assertIn('"sourceUrl": "https://www.wowhead.com/cn/guide/classes/tier-lists/'
                      'dps-rankings-raids"', content)


class ReaderPayloadTest(unittest.TestCase):
    """阅读器失败时也回 200（正文前留一行 Warning 或干脆是 404 页），得认出这类“假正文”。"""

    def test_正常正文通过(self):
        ftl.validate_reader_payload(NUMBERED_PAGE, GUIDE)

    def test_没有正文标记要报错(self):
        with self.assertRaises(ftl.BadPayloadError):
            ftl.validate_reader_payload("Title: x\n没有任何正文\n", GUIDE)

    def test_渲染未完成的Warning当成取页失败(self):
        with self.assertRaises(ftl.BadPayloadError) as ctx:
            ftl.validate_reader_payload(LAZY_PAGE, GUIDE)
        # 原文跟着异常走，失败时要能落盘排查
        self.assertIn("Warning: This page maybe not yet fully loaded", ctx.exception.text)

    def test_没有标题当成取页失败(self):
        with self.assertRaises(ftl.BadPayloadError):
            ftl.validate_reader_payload(NO_TITLE_PAGE, GUIDE)

    def test_404页当成取页失败(self):
        with self.assertRaises(ftl.BadPayloadError):
            ftl.validate_reader_payload(NOT_FOUND_PAGE, GUIDE)

    def test_正文里的举报广告弹窗不算错误页(self):
        # 实测正常页面 50KB 也含这段文字，按字样判死会把好页面全判成失败
        text = NUMBERED_PAGE + "\n## Why are you reporting this ad?\n\nPlease make a selection.\n"
        ftl.validate_reader_payload(text, GUIDE)
        self.assertEqual(len(ftl.parse_page(text, GUIDE).tiers["B"]), 1)


class RetryTest(unittest.TestCase):
    """限流 / 没渲染出来是临时故障：重试到用尽次数才判死。"""

    def test_取页错误后重试成功(self):
        calls = []

        def fetch():
            calls.append(1)
            if len(calls) == 1:
                raise ftl.BadPayloadError("空壳页", LAZY_PAGE)
            return NUMBERED_PAGE

        page, text = ftl.fetch_and_parse(GUIDE, fetch, attempts=3, sleep=0)
        self.assertEqual(len(calls), 2)
        self.assertEqual(text, NUMBERED_PAGE)
        self.assertEqual(page.tiers["A"], ["warrior|武器"])

    def test_重试次数用尽才抛出(self):
        calls = []

        def fetch():
            calls.append(1)
            return "Title: x\nMarkdown Content:\n没有排名内容\n"

        with self.assertRaises(ftl.FetchError):
            ftl.fetch_and_parse(GUIDE, fetch, attempts=3, sleep=0)
        self.assertEqual(len(calls), 3)

    def test_全轮失败留下抓到的原文(self):
        with tempfile.TemporaryDirectory() as tmp:
            dump = Path(tmp) / "raid-tank.failed.md"
            with self.assertRaises(ftl.FetchError):
                ftl.fetch_and_parse(GUIDE, lambda: LAZY_PAGE, attempts=2, sleep=0, dump_path=dump)
            self.assertTrue(dump.exists())
            self.assertIn("Warning: This page maybe not yet fully loaded", dump.read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
