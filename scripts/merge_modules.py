#!/usr/bin/env python3
"""Merge the user's filtered Wool module with the Feng upstream module."""

import argparse
import fnmatch
import hashlib
import json
import re
import urllib.request
from pathlib import Path

import build_personal_ads as wool

FENG_REPO = "Feng-Feng1/surge"
FENG_PATH = "AdBlock-AllInOne.sgmodule"
FENG_PREFIX = "https://raw.githubusercontent.com/Feng-Feng1/surge/"
SECTIONS = ("Rule", "Header Rewrite", "URL Rewrite", "Body Rewrite", "Map Local", "Script")
EXCLUDED = re.compile(r"xiaohongshu|xhscdn|(?<![a-z])xhs|rednote\.com|小红书|xiaoantech|spotify\.crack|wyres\.js", re.I)
PROTECTIONS = ("DOMAIN,dig.bdurl.net", "DOMAIN-SUFFIX,xiaohongshu.com",
               "DOMAIN-SUFFIX,xhscdn.com", "DOMAIN-SUFFIX,xhslink.com",
               "DOMAIN-SUFFIX,rednote.com", "DOMAIN-WILDCARD,v*-reading-ad.qznovelvod.com")
PROTECTED_HOSTS = ("dig.bdurl.net", "edith.xiaohongshu.com", "ads-video-al.xhscdn.com",
                   "xhslink.com", "rednote.com") + tuple(
                       rule.split(",")[1] for rule in wool.DEFERRED_CANDIDATES["rules"]
                   )
ARGUMENTS = {**wool.ARGUMENT_DEFAULTS, "per_filter_video_thread": '"0"'}


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "surge-sgmodule-sync"})
    with urllib.request.urlopen(req, timeout=45) as response:
        return response.read().decode("utf-8")


def feng_source(path, revision):
    if path:
        if not revision:
            raise ValueError("--feng-commit is required with --feng-source")
        return Path(path).read_text(encoding="utf-8"), revision
    commits = json.loads(fetch("https://api.github.com/repos/" + FENG_REPO + "/commits?path=" + FENG_PATH + "&per_page=1"))
    if not commits:
        raise RuntimeError("No upstream Feng commit found")
    revision = commits[0]["sha"]
    return fetch(FENG_PREFIX + revision + "/" + FENG_PATH), revision


def sections(text):
    result = {}
    current = None
    for line in text.splitlines():
        match = re.fullmatch(r"\[([^]]+)\]", line.strip())
        if match:
            current = match.group(1)
            if current in result:
                raise ValueError("Duplicate upstream section: " + current)
            result[current] = []
        elif current:
            result[current].append(line)
    return result


def script_key(line):
    kind = re.search(r"\btype\s*=\s*([^,]+)", line)
    pattern = re.search(r"\bpattern\s*=\s*(.*?)(?=,\s*[\w-]+\s*=|$)", line)
    if not kind or not pattern:
        raise ValueError("Unrecognised script: " + line[:100])
    return kind.group(1).strip().lower(), pattern.group(1).strip()


def guard_ruleset(line):
    match = re.fullmatch(r"(AND,\(.*\)),(REJECT(?:-DROP)?)(,pre-matching)?", line)
    if not match:
        raise ValueError("Unrecognised upstream external ruleset: " + line[:100])
    exclusions = ",".join("(NOT,((" + rule + ")))" for rule in PROTECTIONS)
    return "AND,((" + match.group(1) + ")," + exclusions + ")," + match.group(2) + (match.group(3) or "")


def validate_simple_rule(line):
    parts = line.split(",")
    if len(parts) < 3 or not parts[2].startswith("REJECT"):
        return
    kind, value = parts[0].upper(), parts[1].lower()
    for host in PROTECTED_HOSTS:
        hit = (kind == "DOMAIN" and host == value or
               kind == "DOMAIN-SUFFIX" and (host == value or host.endswith("." + value)) or
               kind == "DOMAIN-KEYWORD" and value in host or
               kind == "DOMAIN-WILDCARD" and fnmatch.fnmatchcase(host, value))
        if hit:
            raise ValueError("Rejected protected host " + host + " by " + line[:150])


def clean_line(section, line, revision):
    normalized = line.replace("\\", "")
    if EXCLUDED.search(normalized):
        return None
    if section == "Rule" and "dig.bdurl.net" in normalized.lower():
        return None
    if section == "Rule" and "RULE-SET," in line:
        line = guard_ruleset(line)
    if section == "Rule":
        validate_simple_rule(line)
    # The upstream Bilibili scripts parse an object, not a positional array.
    if "bilibili.protobuf.request.js" in line and 'argument=[{{{logLevel}}}]' in line:
        line = line.replace('argument=[{{{logLevel}}}]', r'argument="{\"logLevel\":\"error\"}"')
    if "bilibili.protobuf.request.js" in line and "{purifyComment}" in line:
        line = re.sub(r'argument="\[.*\]"', r'argument="{\\"purifyComment\\":true,\\"logLevel\\":\\"error\\"}"', line)
    if "bilibili.protobuf.response.js" in line and "{displayUpList}" in line:
        line = re.sub(r'argument="\[.*\]"', r'argument="{\\"displayUpList\\":\\"show\\",\\"purifyComment\\":true,\\"sponsorBlock\\":false,\\"logLevel\\":\\"error\\"}"', line)
    return line.replace(FENG_PREFIX + "main/", FENG_PREFIX + revision + "/")


def merge(feng, revision, wool_module):
    src, fallback = sections(feng), sections(wool_module)
    unknown = set(src) - set(SECTIONS) - {"MITM"}
    if unknown:
        raise ValueError("Upstream has unsupported sections: " + ", ".join(sorted(unknown)))
    output = ["#!name=截图 App 去广告综合模块", "#!desc=秋风奶思优先，合并截图 App 去广告规则。",
              "#!author=上游：Feng-Feng1、fmz200；合并：mrtanshiyue", "#!system=ios",
              "#!homepage=https://github.com/mrtanshiyue/surge-sgmodule",
              "#!raw-url=" + wool.MODULE_URL, "#!requirement=CORE_VERSION>=6011000"]
    all_scripts, section_lines, seen = set(), {}, set()
    for section in SECTIONS:
        result = []
        for name, blocks in (("Feng-Feng1", src), ("Wool Scripts", fallback)):
            result.append("# Source: " + name)
            for raw in blocks.get(section, []):
                line = raw.strip()
                if not line or line.startswith(("#", ";", "//")):
                    continue
                line = clean_line(section, line, revision)
                if line is None:
                    continue
                identity = (section, script_key(line) if section == "Script" else re.sub(r"\s+", "", line))
                if identity in seen:
                    continue
                seen.add(identity)
                if section == "Script":
                    script_name = line.split("=", 1)[0].strip()
                    if script_name in all_scripts:
                        script_name += "-" + hashlib.sha256(line.encode()).hexdigest()[:8]
                        line = script_name + " = " + line.split("=", 1)[1].strip()
                    all_scripts.add(script_name)
                result.append(line)
        if len(result) > 2:
            section_lines[section] = result
    selected_text = "\n".join(x for v in section_lines.values() for x in v)
    arguments = sorted(set(re.findall(r"\{\{\{([A-Za-z0-9_]+)\}\}\}", selected_text)))
    missing = set(arguments) - ARGUMENTS.keys()
    if missing:
        raise ValueError("Unknown upstream parameters: " + ", ".join(sorted(missing)))
    output.append("#!arguments=" + ",".join(k + ":" + ARGUMENTS[k] for k in arguments))
    for section, lines in section_lines.items():
        output.extend(["", "[" + section + "]"] + lines)
    hosts = []
    for part in (src, fallback):
        for line in part.get("MITM", []):
            match = re.fullmatch(r"\s*hostname\s*=\s*%APPEND%\s*(.*)", line, re.I)
            if match:
                for host in match.group(1).split(","):
                    host = host.strip()
                    if host and not EXCLUDED.search(host) and host != "dig.bdurl.net" and host not in hosts:
                        hosts.append(host)
    if not hosts:
        raise ValueError("No MITM hostnames found")
    output += ["", "[MITM]", "hostname = %APPEND% " + ", ".join(hosts)]
    module = "\n".join(output) + "\n"
    if re.search(r"(?<!\{)\{(?:displayUpList|purifyComment)\}(?!\})", module):
        raise ValueError("Unresolved Bilibili placeholders")
    return module


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--feng-source")
    p.add_argument("--feng-commit")
    p.add_argument("--wool-source")
    p.add_argument("--wool-commit")
    p.add_argument("--output", default="PersonalAds.sgmodule")
    p.add_argument("--manifest", default="sources.json")
    args = p.parse_args()
    feng, revision = feng_source(args.feng_source, args.feng_commit)
    src, wc = wool.read_upstream(args.wool_source)
    if args.wool_source and not args.wool_commit:
        raise ValueError("--wool-commit is required with --wool-source")
    wc = args.wool_commit or wc
    baseline, manifest = wool.build(src, wc)
    module = merge(feng, revision, baseline)
    manifest["feng"] = {"repository": "https://github.com/" + FENG_REPO, "path": FENG_PATH,
                        "commit": revision, "sha256": hashlib.sha256(feng.encode()).hexdigest()}
    names = sorted(set(re.findall(r"\{\{\{([A-Za-z0-9_]+)\}\}\}", module)))
    manifest["module_arguments"] = {name: ARGUMENTS[name].strip('"') for name in names}
    manifest["module_sha256"] = hashlib.sha256(module.encode()).hexdigest()
    manifest["merge_notes"] = {"priority": "Feng before Wool", "protected": list(PROTECTIONS),
                               "excluded": ["小红书专属规则", "小象助力车专属规则", "Spotify.Crack.Dev.js", "wyres.js（包含会员状态改写）"]}
    Path(args.output).write_text(module, encoding="utf-8")
    Path(args.manifest).write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("Built", args.output, "from Feng", revision, "and Wool", wc)


if __name__ == "__main__":
    main()
