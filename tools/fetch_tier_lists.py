#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
职业天梯抓取：Wowhead guide 页面 → js/data/*-tier-list.js

为什么需要代理/阅读器：
    wowhead.com 对部分地区出口直接返回 403（CloudFront 地区拦截），
    实测本机直连与香港出口均为 403。脚本提供三种取页方式：

        auto    先直连，非 200 时自动退回 r.jina.ai 阅读器（默认）
        direct  只直连（美国出口的 CI/Netlify 构建机可用）
        reader  只走 r.jina.ai 阅读器（本机可用，需要能访问 r.jina.ai）

解析口径：
    1. 优先取正文里的编号排名列表 “1.   Arms Warrior (A Tier)”——它是页面唯一明确的排名；
    2. 没有编号列表时，退回 “### A-Tier Specs …” + “#### 专精名” 的分节结构；
    3. 两种方式都只认 SPEC_BY_EN 里的英文专精名，遇到没登记的专精直接失败，
       避免“页面新增专精 → 站点静默少一格”。

用法：
    python tools/fetch_tier_lists.py                     # 抓取并写入 6 份数据
    python tools/fetch_tier_lists.py --check             # 只比对，有差异时退出码 1
    python tools/fetch_tier_lists.py --reader            # 强制走阅读器
    python tools/fetch_tier_lists.py --offline           # 只用 .cache/tier-lists 里的原文
    python tools/fetch_tier_lists.py --proxy http://127.0.0.1:15236

    # 本机典型用法（直连 403，系统代理在国内可用）
    python tools/fetch_tier_lists.py --reader --proxy http://127.0.0.1:15236
"""

from __future__ import annotations

import argparse
import json
import logging
import os
import re
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Callable, Dict, List, Optional

import requests

sys.path.insert(0, str(Path(__file__).resolve().parent))
from paths import REPO_ROOT  # noqa: E402
from wow_terms import SPEC_BY_EN  # noqa: E402

DATA_DIR = REPO_ROOT / "js" / "data"
SPECS_JS = DATA_DIR / "specs.js"
CACHE_DIR = REPO_ROOT / ".cache" / "tier-lists"

BEIJING = timezone(timedelta(hours=8))
USER_AGENT = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36"
)
READER_PREFIX = "https://r.jina.ai/"

# 阅读器取不到页面时也回 HTTP 200，并在正文前的元数据里留一行 Warning
# （“This page maybe not yet fully loaded, consider explicitly specify a timeout.”）。
READER_WARNING_MARKER = "warning:"

# 抓取 + 解析算一轮。限流、页面没渲染出来都是临时故障，重试几轮再判死。
PARSE_ATTEMPTS = 3
RETRY_SLEEP = 5

TIER_ORDER = ["S", "A+", "A", "B", "C", "D", "F"]

# 天梯条目 → 输出文件 / 变量名 / wowhead guide 地址
GUIDES: List["Guide"] = []


@dataclass(frozen=True)
class Guide:
    key: str
    label: str
    out_file: str
    var: str
    url: str


GUIDES.extend(
    [
        Guide("raid-dps", "团本 DPS 天梯（排名数据）", "dps-tier-list.js", "dpsTierList",
              "https://www.wowhead.com/cn/guide/classes/tier-lists/dps-rankings-raids"),
        Guide("raid-healer", "团本治疗天梯（排名数据）", "healer-tier-list.js", "healerTierList",
              "https://www.wowhead.com/cn/guide/classes/tier-lists/healer-rankings-raids"),
        Guide("raid-tank", "团本坦克天梯（排名数据）", "tank-tier-list.js", "tankTierList",
              "https://www.wowhead.com/cn/guide/classes/tier-lists/tank-rankings-raids"),
        Guide("mplus-dps", "大秘境 DPS 天梯（排名数据）", "mplus-dps-tier-list.js", "mplusDpsTierList",
              "https://www.wowhead.com/cn/guide/classes/tier-lists/dps-rankings-mythic-plus"),
        Guide("mplus-healer", "大秘境治疗天梯（排名数据）", "mplus-healer-tier-list.js",
              "mplusHealerTierList",
              "https://www.wowhead.com/cn/guide/classes/tier-lists/healer-rankings-mythic-plus"),
        Guide("mplus-tank", "大秘境坦克天梯（排名数据）", "mplus-tank-tier-list.js", "mplusTankTierList",
              "https://www.wowhead.com/cn/guide/classes/tier-lists/tank-rankings-mythic-plus"),
    ]
)

# 英文专精名 → specs.js 的 id 那张表在 tools/wow_terms.py（天梯与公会成员统计共用）。


# 分节结构里这些 #### 标题不是专精，出现即表示当前层级区间结束
SECTION_STOP = {
    "changelog",
    "about the author",
    "filter buttons",
    "overall ranking",
}

NUMBERED_RE = re.compile(
    r"(?m)^[ \t]{0,3}(\d{1,3})\.\s+([A-Za-z' \-]{3,40}?)\s*\(([SABCDF]\+?)\s*Tier\)\s*$"
)
HEADING_RE = re.compile(r"(?m)^(#{2,4})[ \t]+(.+?)[ \t]*$")
TIER_HEADING_RE = re.compile(r"\b([SABCDF])\s*(\+)?\s*-?\s*Tier\b", re.IGNORECASE)
TITLE_RE = re.compile(r"(?m)^Title:\s*(.+?)\s*$")
UPDATED_RE = re.compile(r"已更新[：:]\s*(\d{4})/(\d{1,2})/(\d{1,2})")
AUTHOR_BYLINE_RE = re.compile(r"\[来自\s*([^\]]+?)\s*\]")
AUTHOR_MAINTAINED_RE = re.compile(r"maintained by\s+([A-Z][A-Za-z0-9_]+)")
AUTHOR_IM_RE = re.compile(r"I'm\s+([A-Z][A-Za-z0-9_]+)")
DATE_LINE_RE = re.compile(r'^\s*"(?:lastUpdated|fetchedAt)":.*$', re.MULTILINE)

LOG = logging.getLogger("tier-lists")


class FetchError(RuntimeError):
    """取页失败（三种方式都没拿到内容）。"""


class BadPayloadError(FetchError):
    """取回了内容，但不是真正文（错误页 / 404 页 / 没渲染完）。

    文本随异常带出去，落成 .cache/tier-lists/<key>.failed.md，失败时由 CI 上传成
    artifact —— 没有这份原文，只能看到“解析出 0 个专精”，查不出是页面变了还是没抓到。
    """

    def __init__(self, message: str, text: str = "") -> None:
        super().__init__(message)
        self.text = text


@dataclass
class ParsedPage:
    title: str
    source: str
    last_updated: str
    fetched_at: str
    tiers: Dict[str, List[str]]
    unknowns: List[str]


def clean_name(raw: str) -> str:
    """去掉 markdown 强调符 / 结尾标点，压平空白。"""
    name = raw.replace("**", "").replace("*", "").replace("`", "")
    name = re.sub(r"\s+", " ", name).strip(" .:")
    return name


def load_spec_ids() -> set:
    """从 specs.js 里读出已登记的专精 id。"""
    text = SPECS_JS.read_text(encoding="utf-8")
    return set(re.findall(r"^\s*'([a-z-]+\|[^']+)':\s*\{", text, re.MULTILINE))


def today_shanghai() -> str:
    return datetime.now(BEIJING).strftime("%Y/%m/%d")


def system_proxy() -> Optional[str]:
    """Windows 系统代理（HKCU Internet Settings），非 Windows 或未开启时返回 None。"""
    if sys.platform != "win32":
        return None
    try:
        import winreg

        with winreg.OpenKey(
            winreg.HKEY_CURRENT_USER,
            r"Software\Microsoft\Windows\CurrentVersion\Internet Settings",
        ) as key:
            enabled = winreg.QueryValueEx(key, "ProxyEnable")[0]
            server = winreg.QueryValueEx(key, "ProxyServer")[0]
    except OSError:
        return None
    if not enabled or not server:
        return None
    server = str(server)
    if "=" not in server:
        return f"http://{server}"
    for part in server.split(";"):
        if part.lower().startswith("https="):
            return f"http://{part.split('=', 1)[1]}"
    return None


def build_session(proxy: Optional[str]) -> requests.Session:
    session = requests.Session()
    session.headers.update({"User-Agent": USER_AGENT, "Accept-Language": "zh-CN,zh;q=0.9"})
    explicit = proxy or os.environ.get("HTTPS_PROXY") or os.environ.get("https_proxy")
    explicit = explicit or system_proxy()
    if explicit:
        session.proxies.update({"http": explicit, "https": explicit})
        LOG.info("代理: %s", explicit)
    return session


def http_get(session: requests.Session, url: str, timeout: int) -> str:
    """带重试的 GET，返回正文文本；失败抛 FetchError。"""
    last_error = "未知错误"
    for attempt in range(1, 4):
        try:
            response = session.get(url, timeout=timeout)
        except requests.RequestException as exc:  # 网络层失败，重试
            last_error = f"{type(exc).__name__}: {exc}"
        else:
            if response.status_code == 200 and response.text.strip():
                return response.text
            last_error = f"HTTP {response.status_code}"
            if response.status_code in (403, 404):
                break
        time.sleep(attempt * 2)
    raise FetchError(f"{url} → {last_error}")


def validate_reader_payload(text: str, guide: Guide) -> None:
    """确认阅读器拿回来的是真正的 guide 正文，不是它的空壳页 / 404 页。

    只认阅读器写在元数据头里的 Warning 和标题：正文里出现 wowhead 的“举报广告”弹窗是
    正常的（每个页面都带这个隐藏弹窗，实测 50KB 的正常页面里也有这段文字），
    所以不能按正文里的字样判死 —— 没抓到正文的情况交给 parse_page 的“0 个专精”判定加整体重试。
    """
    marker = "Markdown Content:"
    if marker not in text:
        raise BadPayloadError(f"阅读器返回内容不含正文: {guide.url}", text)
    header = text[: text.find(marker)]
    for line in header.splitlines():
        if line.strip().lower().startswith(READER_WARNING_MARKER):
            raise BadPayloadError(f"阅读器报告取页失败（{line.strip()}）: {guide.url}", text)
    title_match = TITLE_RE.search(header)
    title = title_match.group(1).strip() if title_match else ""
    if not title:
        raise BadPayloadError(f"阅读器没回标题（页面没渲染出来）: {guide.url}", text)
    if "page not found" in title.lower():
        raise BadPayloadError(f"阅读器返回的是 404 页: {guide.url}", text)


def fetch_guide(session: requests.Session, guide: Guide, route: str, timeout: int) -> str:
    """按 route 取页面原文；reader 模式拿到的是 r.jina.ai 的 markdown。"""
    if route in ("auto", "direct"):
        try:
            return http_get(session, guide.url, timeout)
        except FetchError as exc:
            if route == "direct":
                raise
            LOG.warning("直连失败（%s），改走阅读器", exc)
    text = http_get(session, READER_PREFIX + guide.url, timeout)
    validate_reader_payload(text, guide)
    return text


def body_after_content(text: str) -> str:
    marker = text.find("Markdown Content:")
    return text[marker + len("Markdown Content:") :] if marker >= 0 else text


def extract_author(text: str) -> str:
    """作者：优先用 wowhead 的“来自 X”署名，其次只看 About the Author 段落。

    不能全页搜 “maintained by / I'm”——正文里出现 “I'm not sure” 这类句子会把作者抓成 not。
    """
    match = AUTHOR_BYLINE_RE.search(text)
    if match:
        return clean_name(match.group(1))

    index = text.lower().find("about the author")
    scope = text[index: index + 2000] if index >= 0 else ""
    for pattern in (AUTHOR_MAINTAINED_RE, AUTHOR_IM_RE):
        match = pattern.search(scope)
        if match:
            return match.group(1)
    return "Wowhead"


def extract_meta(text: str) -> tuple:
    """标题 / 作者 / 页面自带更新日期。"""
    title_match = TITLE_RE.search(text)
    title = clean_name(title_match.group(1)) if title_match else ""
    author = extract_author(text)

    updated = today_shanghai()
    match = UPDATED_RE.search(text)
    if match:
        year, month, day = (int(part) for part in match.groups())
        updated = f"{year:04d}/{month:02d}/{day:02d}"
    return title, author, updated


def tiers_from_numbered(body: str, unknowns: List[str]) -> Dict[str, List[str]]:
    tiers: Dict[str, List[str]] = {}
    for match in NUMBERED_RE.finditer(body):
        name = clean_name(match.group(2))
        tier = match.group(3).upper()
        spec_id = SPEC_BY_EN.get(name)
        if not spec_id:
            unknowns.append(f"编号列表: {name}（{tier}）")
            continue
        bucket = tiers.setdefault(tier, [])
        if spec_id not in bucket:
            bucket.append(spec_id)
    return tiers


def tiers_from_headings(body: str, unknowns: List[str]) -> Dict[str, List[str]]:
    tiers: Dict[str, List[str]] = {}
    current: Optional[str] = None
    for match in HEADING_RE.finditer(body):
        level = len(match.group(1))
        text = clean_name(match.group(2))
        if level <= 3:
            tier_match = TIER_HEADING_RE.search(text)
            if tier_match:
                current = tier_match.group(1).upper() + ("+" if tier_match.group(2) else "")
            elif "lower tier" in text.lower():
                current = "LOWER"
            continue
        if text.lower() in SECTION_STOP:
            current = None
            continue
        if current is None:
            continue
        spec_id = SPEC_BY_EN.get(text)
        if not spec_id:
            unknowns.append(f"分节标题: {text}（{current}）")
            continue
        if current == "LOWER":
            # wowhead 的 “Lower Tier” 不会说明是 D 还是 F，先按未定级处理，交人工判断
            unknowns.append(f"未定级段落: {text}（Lower Tier）")
            continue
        bucket = tiers.setdefault(current, [])
        if spec_id not in bucket:
            bucket.append(spec_id)
    return tiers


def parse_page(text: str, guide: Guide) -> ParsedPage:
    title, source, last_updated = extract_meta(text)
    body = body_after_content(text)

    unknowns: List[str] = []
    numbered_unknowns: List[str] = []
    tiers = tiers_from_numbered(body, numbered_unknowns)
    if sum(len(items) for items in tiers.values()) < 3:
        tiers = tiers_from_headings(body, unknowns)
    unknowns = numbered_unknowns + [item for item in unknowns if item not in numbered_unknowns]

    tiers = {key: value for key, value in tiers.items() if key in TIER_ORDER}
    if not any(tiers.values()):
        raise ValueError(f"{guide.key}: 没解析出任何专精，可能是没抓到正文，也可能页面结构变了")
    if not title:
        title = guide.label

    return ParsedPage(
        title=title,
        source=source,
        last_updated=last_updated,
        fetched_at=today_shanghai(),
        tiers=tiers,
        unknowns=unknowns,
    )


def fetch_and_parse(
    guide: Guide,
    fetch_text: Callable[[], str],
    attempts: int = PARSE_ATTEMPTS,
    sleep: int = RETRY_SLEEP,
    dump_path: Optional[Path] = None,
) -> tuple:
    """抓一轮 + 解析一轮；失败重试，全失败才抛。

    为什么重试：2026-11-09 的定时任务里 6 个页面有 5 个正常，坦克那页解析出 0 个专精，
    整个作业 exit 3 失败。阅读器偶尔会回没渲染完的空壳页（正文前留一行 Warning），
    重抓一次多半就好；真有页面改版，重试几轮后照样失败报警。
    """
    last_error: Exception = ValueError(f"{guide.key}: 没有任何结果")
    for attempt in range(1, attempts + 1):
        text = ""
        try:
            text = fetch_text()
            return parse_page(text, guide), text
        except (FetchError, ValueError) as exc:
            last_error = exc
            # 取页失败时异常自带原文；解析失败时用这一轮抓到的正文
            payload = getattr(exc, "text", "") or text
            if dump_path is not None and payload:
                dump_path.write_text(payload, encoding="utf-8")
            if attempt < attempts:
                LOG.warning(
                    "%s: 第 %d/%d 轮失败（%s），%d 秒后重试", guide.key, attempt, attempts, exc, sleep
                )
                time.sleep(sleep)
    raise FetchError(f"{guide.key}: {last_error}")


def render_js(guide: Guide, page: ParsedPage) -> str:
    payload = {
        "title": page.title,
        "source": page.source,
        "lastUpdated": page.last_updated,
        "fetchedAt": page.fetched_at,
        "sourceUrl": guide.url,
        "tiers": {
            tier: {"name": tier, "description": "", "specs": page.tiers.get(tier, [])}
            for tier in TIER_ORDER
        },
    }
    body = json.dumps(payload, ensure_ascii=False, indent=2)
    header = (
        "/**\n"
        f" * {guide.label}\n"
        " *\n"
        " * 专精图标与职业信息统一见 specs.js，此处只保留层级与元数据。\n"
        f" * 来源: {guide.url}\n"
        f" * 更新: {page.last_updated}\n"
        " *\n"
        " * 由 tools/fetch_tier_lists.py 自动生成，请勿手改。\n"
        " */\n\n"
    )
    return f"{header}const {guide.var} = {body};\n\nexport default {guide.var};\n"


def summarize(guide: Guide, page: ParsedPage) -> str:
    counts = " ".join(
        f"{tier}:{len(page.tiers.get(tier, []))}" for tier in TIER_ORDER if page.tiers.get(tier)
    )
    return f"{guide.out_file:<26} {counts}"


def main(argv: Optional[List[str]] = None) -> int:
    # 输出被重定向（CI / 管道）时固定用 UTF-8，避免中文日志按 GBK 编码后花屏；
    # 交互式控制台保持系统默认，不改用户原有显示。
    for stream in (sys.stdout, sys.stderr):
        if not stream.isatty() and hasattr(stream, "reconfigure"):
            stream.reconfigure(encoding="utf-8", errors="replace")

    parser = argparse.ArgumentParser(description="抓取 Wowhead 职业天梯并生成 js/data 数据文件")
    parser.add_argument("--check", action="store_true", help="只比对差异，不写文件；有差异时退出码 1")
    parser.add_argument("--route", choices=["auto", "direct", "reader"], default="auto")
    parser.add_argument("--offline", action="store_true", help="不联网，只用 --cache-dir 里的原文")
    parser.add_argument("--cache-dir", type=Path, default=CACHE_DIR)
    parser.add_argument("--proxy", default=None, help="HTTP(S) 代理，例如 http://127.0.0.1:15236")
    parser.add_argument("--timeout", type=int, default=60)
    parser.add_argument("--only", default=None, help="只处理某个 key，例如 mplus-dps")
    args = parser.parse_args(argv)

    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    args.cache_dir.mkdir(parents=True, exist_ok=True)

    spec_ids = load_spec_ids()
    known_map_diff = sorted({sid for sid in SPEC_BY_EN.values() if sid not in spec_ids})
    if known_map_diff:
        LOG.error("specs.js 里缺少这些专精，先补注册表再跑：%s", ", ".join(known_map_diff))
        return 2

    session = None if args.offline else build_session(args.proxy)
    # 两段式：先把 6 个页面全抓全解析，全都通过才落盘 —— 一个页面抓坏就不写半套数据，
    # 也免得 CI 里检查一遍、生成时再抓一遍（阅读器免费额度就那么多）。
    rendered = []  # [(guide, content, target, old)]
    failed = 0

    for guide in GUIDES:
        if args.only and guide.key != args.only:
            continue
        cache_file = args.cache_dir / f"{guide.key}.md"
        failed_file = args.cache_dir / f"{guide.key}.failed.md"

        def fetch_text(guide: Guide = guide, cache_file: Path = cache_file) -> str:
            if args.offline:
                if not cache_file.exists():
                    raise FetchError(f"离线模式缺少缓存: {cache_file}")
                return cache_file.read_text(encoding="utf-8")
            assert session is not None
            text = fetch_guide(session, guide, args.route, args.timeout)
            time.sleep(1.5)  # 阅读器免费额度限速，顺序请求留点间隔
            return text

        try:
            page, text = fetch_and_parse(
                guide,
                fetch_text,
                attempts=1 if args.offline else PARSE_ATTEMPTS,
                dump_path=None if args.offline else failed_file,
            )
        except FetchError as exc:
            LOG.error("%s", exc)
            failed += 1
            continue

        # 解析通过才写缓存：坏页面不能顶掉可离线重跑的原文（它另存为 .failed.md）。
        if not args.offline:
            cache_file.write_text(text, encoding="utf-8")
            if failed_file.exists():
                failed_file.unlink()

        for unknown in page.unknowns:
            LOG.warning("%s: 未登记专精 —— %s", guide.key, unknown)
        LOG.info("%s", summarize(guide, page))

        target = DATA_DIR / guide.out_file
        old = target.read_text(encoding="utf-8") if target.exists() else ""
        rendered.append((guide, render_js(guide, page), target, old))

    if failed:
        LOG.error("有 %d 个天梯没抓到，本次不写任何文件（原文见 .cache/tier-lists/*.failed.md）", failed)
        return 3
    if not rendered:
        LOG.error("没有任何数据生成")
        return 3

    exit_code = 0
    for guide, content, target, old in rendered:
        if args.check:
            same = DATE_LINE_RE.sub("", old) == DATE_LINE_RE.sub("", content)
            LOG.info("  %s: %s", guide.out_file, "一致" if same else "有差异")
            if not same:
                exit_code = max(exit_code, 1)
        elif old != content:
            target.write_text(content, encoding="utf-8")
            LOG.info("  %s: 已更新", guide.out_file)
        else:
            LOG.info("  %s: 无变化", guide.out_file)
    return exit_code


if __name__ == "__main__":
    sys.exit(main())
