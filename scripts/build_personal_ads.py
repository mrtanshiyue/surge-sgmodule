#!/usr/bin/env python3
"""Build the screenshot-scoped Surge module from Wool Scripts' upstream module."""

import argparse
import hashlib
import json
import re
import time
import urllib.error
import urllib.request
from pathlib import Path


UPSTREAM_REPO = "fmz200/wool_scripts"
UPSTREAM_PATH = "Surge/module/blockAds.module"
UPSTREAM_API = (
    "https://api.github.com/repos/fmz200/wool_scripts/commits"
    "?path=Surge%2Fmodule%2FblockAds.module&per_page=1"
)
RAW_URL = "https://raw.githubusercontent.com/fmz200/wool_scripts/{commit}/" + UPSTREAM_PATH
MODULE_URL = "https://raw.githubusercontent.com/mrtanshiyue/surge-sgmodule/main/PersonalAds.sgmodule"

# Screenshot app groups plus the requested general ad-alliance rules.
ALLOWED_GROUPS = {
    "广告联盟",
    "12123",
    "Amazon",
    "Apple",
    "Facebook",
    "Google",
    "WPS",
    "YouTube",
    "京东",
    "拼多多",
    "同花顺",
    "杭州市民",
    "喜马拉雅",
    "哔哩哔哩",
    "字节跳动",
    "山姆会员商店",
    "中国电信",
    "阿里巴巴",
    "抖音",
    "高德地图",
    "钉钉",
    "腾讯系",
    "腾讯游戏",
    "淘宝",
    "淘票票",
    "网易云音乐",
    "美团",
    "美团 & 美团外卖",
    "米家",
    "小爱音箱",
    "小米",
    "萤石",
    "优酷",
    "QQ音乐",
}

SECTIONS = ("Rule", "Header Rewrite", "URL Rewrite", "Body Rewrite", "Map Local", "Script")
SKIP_RULES = {"DOMAIN,dig.bdurl.net,REJECT"}
ARGUMENT_DEFAULTS = {
    "DT": "false",
    "FX": "true",
    "MY": "true",
    "logLevel": '"error"',
    "sponsorBlock": "false",
}
ARGUMENT_SOURCES = [
    {"repository": UPSTREAM_REPO, "path": "Surge/module/split/partB/bilibili.sgmodule"},
    {"repository": UPSTREAM_REPO, "path": "Surge/module/split/partW/NetEaseCloudMusic.sgmodule"},
]
DEFERRED_CANDIDATES = {
    "repository": "abclq/home-dns-adblock",
    "path": "config/adblock-fq.conf",
    "commit": "ee9c7c7929c71519728c18f6b5488b25598d92c9",
    "blob_sha": "b866fdaa3238d3e3605183d03762fea78fead6cc",
    "source_date": "2026-10-14",
    "reason": "精确 reading-ad 主机用于看广告解锁章节；等待用户确认后再加入。",
    "rules": [
        "DOMAIN,v11-reading-ad.qznovelvod.com,REJECT",
        "DOMAIN,v13-reading-ad.qznovelvod.com,REJECT",
        "DOMAIN,v26-reading-ad.qznovelvod.com,REJECT",
        "DOMAIN,v5-bd-daily-reading-ad.qznovelvod.com,REJECT",
        "DOMAIN,v5-reading-ad.qznovelvod.com,REJECT",
        "DOMAIN,v5-se-sjy-daily-reading-ad.qznovelvod.com,REJECT",
        "DOMAIN,v6-reading-ad.qznovelvod.com,REJECT",
        "DOMAIN,v9-reading-ad.qznovelvod.com,REJECT",
        "DOMAIN,v96-reading-ad.qznovelvod.com,REJECT",
    ],
}

def fetch_upstream(url):
    request = urllib.request.Request(url, headers={"User-Agent": "surge-sgmodule-sync"})
    for attempt in range(3):
        try:
            with urllib.request.urlopen(request, timeout=30) as response:
                return response.read().decode("utf-8")
        except urllib.error.HTTPError as error:
            if error.code < 500 or attempt == 2:
                raise
        except (TimeoutError, urllib.error.URLError):
            if attempt == 2:
                raise
        time.sleep(attempt + 1)


def read_upstream(source_path):
    if source_path:
        text = Path(source_path).read_text(encoding="utf-8")
        return text, "local-source"

    commits = json.loads(fetch_upstream(UPSTREAM_API))
    if not commits:
        raise RuntimeError("Upstream has no commit for blockAds.module")
    commit = commits[0]["sha"]
    return fetch_upstream(RAW_URL.format(commit=commit)), commit


def parse_module(source):
    lines = source.splitlines()
    metadata = []
    sections = {}
    plain_sections = {}
    current_section = None
    current_group = None
    current_lines = []

    def finish_group():
        if current_section and current_group:
            sections.setdefault(current_section, []).append((current_group, current_lines.copy()))

    for line in lines:
        section_match = re.fullmatch(r"\[([^\]]+)\]", line.strip())
        if section_match:
            finish_group()
            current_section = section_match.group(1)
            plain_sections.setdefault(current_section, [])
            current_group = None
            current_lines = []
            continue
        if current_section is None:
            metadata.append(line)
            continue
        plain_sections[current_section].append(line)
        if line.startswith("# > "):
            finish_group()
            current_group = line[4:].strip()
            current_lines = [line]
        elif current_group:
            current_lines.append(line)
    finish_group()
    return metadata, sections, plain_sections


def selected_groups(sections):
    selected = {}
    for section in SECTIONS:
        blocks = []
        for name, lines in sections.get(section, []):
            if name not in ALLOWED_GROUPS:
                continue
            filtered = [line for line in lines if not line.startswith("# >>>") and line.strip() not in SKIP_RULES]
            if any(line.strip() and not line.lstrip().startswith("#") for line in filtered):
                blocks.append((name, filtered))
        if blocks:
            selected[section] = blocks

    found = {name for blocks in selected.values() for name, _ in blocks}
    missing = sorted(ALLOWED_GROUPS - found)
    if missing:
        raise RuntimeError("Expected upstream app groups missing: " + ", ".join(missing))
    return selected


def source_mitm_hosts(plain_sections):
    for line in plain_sections.get("MITM", []):
        match = re.match(r"\s*hostname\s*=\s*%APPEND%\s*(.*)", line, re.IGNORECASE)
        if match:
            return [host.strip() for host in match.group(1).split(",") if host.strip()]
    raise RuntimeError("Upstream MITM hostname list not found")


def build(source, commit):
    metadata, sections, plain_sections = parse_module(source)
    groups = selected_groups(sections)
    selected_text = "\n".join(line for blocks in groups.values() for _, lines in blocks for line in lines)
    argument_names = sorted(set(re.findall(r"\{\{\{([A-Za-z0-9_]+)\}\}\}", selected_text)))
    missing_arguments = set(argument_names) - ARGUMENT_DEFAULTS.keys()
    if missing_arguments:
        raise RuntimeError("Missing Surge module arguments: " + ", ".join(sorted(missing_arguments)))
    module_arguments = ",".join(f"{name}:{ARGUMENT_DEFAULTS[name]}" for name in argument_names)

    group_hosts = set()
    for blocks in groups.values():
        for _, lines in blocks:
            for line in lines:
                match = re.match(r"\s*#\s*hostname\s*=\s*(.*)", line, re.IGNORECASE)
                if match:
                    group_hosts.update(host.strip() for host in match.group(1).split(",") if host.strip())
    mitm_hosts = [host for host in source_mitm_hosts(plain_sections) if host in group_hosts and host != "dig.bdurl.net"]

    upstream_date = next((line.split("=", 1)[1].strip() for line in metadata if line.startswith("#!date=")), "unknown")
    output = [
        "#!name=才才的去广告集合",
        "#!desc=Surge iOS 6 综合去广告模块，按截图筛选可用上游分组。",
        "#!author=mrtanshiyue（上游规则：fmz200）",
        "#!category=个人模块",
        "#!homepage=https://github.com/mrtanshiyue/surge-sgmodule",
        f"#!raw-url={MODULE_URL}",
        "#!tag=去广告,截图App,广告联盟,Wool",
        "#!system=ios",
        f"#!date={upstream_date}",
        "#!requirement=CORE_VERSION>=20",
        f"#!arguments={module_arguments}",
        "#!arguments-desc=保留 B 站视频内创作者赞助片段；日志级别为 error；网易云音乐选项沿用上游默认值。",
        "#!remark=筛选自 Wool Scripts blockAds.module；dig.bdurl.net 已排除，以免影响抖音精选视频播放。",
    ]

    for section in SECTIONS:
        blocks = groups.get(section)
        if not blocks:
            continue
        output.extend(["", f"[{section}]"])
        for _, lines in blocks:
            output.extend([""] + lines)

    if mitm_hosts:
        output.extend(["", "[MITM]", "hostname = %APPEND% " + ", ".join(mitm_hosts)])

    module = re.sub(r"\n{3,}", "\n\n", "\n".join(output)).rstrip() + "\n"
    manifest = {
        "upstream_repository": f"https://github.com/{UPSTREAM_REPO}",
        "upstream_path": UPSTREAM_PATH,
        "upstream_commit": commit,
        "upstream_sha256": hashlib.sha256(source.encode()).hexdigest(),
        "upstream_date": upstream_date,
        "selected_groups": {section: [name for name, _ in blocks] for section, blocks in groups.items()},
        "module_arguments": {name: ARGUMENT_DEFAULTS[name].strip('"') for name in argument_names},
        "argument_sources": [
            {**source, "commit": commit} for source in ARGUMENT_SOURCES
        ],
        "excluded_rules": sorted(SKIP_RULES),
        "excluded_apps": ["小红书"],
        "deferred_candidates": DEFERRED_CANDIDATES,
        "module_sha256": hashlib.sha256(module.encode()).hexdigest(),
    }
    if any(line.strip() in SKIP_RULES for line in module.splitlines()):
        raise RuntimeError("Filtered module contains the playback-breaking host")
    if re.search(r"(?:xhscdn\.com|xiaohongshu\.com)", module, re.IGNORECASE):
        raise RuntimeError("Filtered module contains Xiaohongshu-specific rules")
    unbound = set(re.findall(r"\{\{\{([A-Za-z0-9_]+)\}\}\}", module)) - set(argument_names)
    if unbound:
        raise RuntimeError("Unbound Surge module arguments: " + ", ".join(sorted(unbound)))
    return module, manifest


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", help="Use a local upstream snapshot instead of fetching the latest commit")
    parser.add_argument("--upstream-commit", help="Record the upstream commit when building from a local snapshot")
    parser.add_argument("--output", default="PersonalAds.sgmodule")
    parser.add_argument("--manifest", default="sources.json")
    args = parser.parse_args()

    source, commit = read_upstream(args.source)
    if args.upstream_commit:
        commit = args.upstream_commit
    module, manifest = build(source, commit)
    Path(args.output).write_text(module, encoding="utf-8")
    Path(args.manifest).write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print(f"Built {args.output}: {len(module.splitlines())} lines, {len(manifest['selected_groups'])} sections, upstream {commit}")


if __name__ == "__main__":
    main()
