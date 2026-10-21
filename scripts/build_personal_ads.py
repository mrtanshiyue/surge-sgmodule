#!/usr/bin/env python3
"""Build the screenshot-scoped Surge module from Wool Scripts' upstream module."""

import argparse
import hashlib
import json
import re
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

# These upstream headings map to Apps visible in the user's screenshots.
# Broader ad-network groups and headings for other Apps are deliberately excluded.
ALLOWED_GROUPS = {
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
    "番茄小说",
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
    "小红书",
}

SECTIONS = ("Rule", "Header Rewrite", "URL Rewrite", "Body Rewrite", "Map Local", "Script")
SKIP_RULES = {"DOMAIN,dig.bdurl.net,REJECT"}


def read_upstream(source_path):
    if source_path:
        text = Path(source_path).read_text(encoding="utf-8")
        return text, "local-source"

    request = urllib.request.Request(UPSTREAM_API, headers={"User-Agent": "surge-sgmodule-sync"})
    with urllib.request.urlopen(request, timeout=30) as response:
        commits = json.load(response)
    if not commits:
        raise RuntimeError("Upstream has no commit for blockAds.module")
    commit = commits[0]["sha"]
    request = urllib.request.Request(RAW_URL.format(commit=commit), headers={"User-Agent": "surge-sgmodule-sync"})
    with urllib.request.urlopen(request, timeout=30) as response:
        return response.read().decode("utf-8"), commit


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
        "#!name=截图 App 去广告（Wool 上游精选）",
        "#!desc=只保留截图中有对应上游去广告分组的规则；规则来自 fmz200/wool_scripts。",
        "#!author=mrtanshiyue（上游规则：fmz200）",
        "#!category=个人模块",
        "#!homepage=https://github.com/mrtanshiyue/surge-sgmodule",
        f"#!raw-url={MODULE_URL}",
        "#!tag=去广告,截图App,Wool",
        "#!system=ios",
        f"#!date={upstream_date}",
        "#!remark=筛选自上游 blockAds.module；未纳入通用广告联盟组。dig.bdurl.net 已排除，以免影响抖音精选视频播放。",
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

    module = "\n".join(output).rstrip() + "\n"
    manifest = {
        "upstream_repository": f"https://github.com/{UPSTREAM_REPO}",
        "upstream_path": UPSTREAM_PATH,
        "upstream_commit": commit,
        "upstream_sha256": hashlib.sha256(source.encode()).hexdigest(),
        "upstream_date": upstream_date,
        "selected_groups": {section: [name for name, _ in blocks] for section, blocks in groups.items()},
        "excluded_rules": sorted(SKIP_RULES),
        "module_sha256": hashlib.sha256(module.encode()).hexdigest(),
    }
    if "# > 广告联盟" in module or any(line.strip() in SKIP_RULES for line in module.splitlines()):
        raise RuntimeError("Filtered module contains a forbidden group or playback-breaking host")
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
