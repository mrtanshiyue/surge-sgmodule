#!/usr/bin/env python3
"""Merge the user's filtered Wool module with the Feng upstream module."""

import argparse
import fnmatch
import hashlib
import json
import re
import shlex
import subprocess
import tempfile
import urllib.parse
import urllib.error
import urllib.request
from pathlib import Path

import build_personal_ads as wool

FENG_REPO = "Feng-Feng1/surge"
FENG_PATH = "AdBlock-AllInOne.sgmodule"
STARTUP_REPO = "Walvez/surge-startup-ads"
STARTUP_PATH = "dist/StartUpAds_Selected.sgmodule"
FENG_PREFIX = "https://raw.githubusercontent.com/Feng-Feng1/surge/"
SECTIONS = ("Rule", "Header Rewrite", "URL Rewrite", "Body Rewrite", "Map Local", "Script")
EXCLUDED = re.compile(r"xiaohongshu|xhscdn|(?<![a-z])xhs|rednote\.com|小红书|xiaoantech|spotify\.crack", re.I)
PROTECTIONS = ("DOMAIN,dig.bdurl.net", "DOMAIN-SUFFIX,xiaohongshu.com",
               "DOMAIN-SUFFIX,xhscdn.com", "DOMAIN-SUFFIX,xhslink.com",
               "DOMAIN-SUFFIX,rednote.com", "DOMAIN-WILDCARD,v*-reading-ad.qznovelvod.com")
PROTECTED_HOSTS = ("dig.bdurl.net", "edith.xiaohongshu.com", "ads-video-al.xhscdn.com",
                   "xhslink.com", "rednote.com") + tuple(
                       rule.split(",")[1] for rule in wool.DEFERRED_CANDIDATES["rules"]
                   )
# App-specific hosts not visible in the supplied screenshots.
ABSENT_APPS = re.compile(r"weibo|weibocdn|weibomingzi|viber|zhihu|smzdm|coolapk|csdn|chelaile|gotokeep|xueqiu|douban|cainiao|goofish|taobao\.idle|pupuapi|iqiyi|kugou|dftoutiao|weilitoutiao|jiemian|ixiaochuan|瓜子漫画|微博|知乎|闲鱼|菜鸟|什么值得买|酷安|哔哩哔哩漫画", re.I)
# Unlabelled upstream rewrites are kept only for visible apps and shared ad SDKs.
FENG_APP_PATTERNS = re.compile(r"(?:bilibili|biliapi|pinduoduo|yangkeduo|pddpic|taobao|alimama|alibaba|jdcloud|\.jd\.|meituan|amap|10jqka|walmartmobile|film\.mtop|ys7|lechange|music\.163|ximalaya|mina\.mi\.|xiaoaisound|mitvos|home\.mi\.|youku|wps|kingsoft-office|googlevideo|googleapis|youtube|byteurl|bytescm|bytedance|pangolin|toutiao|snssdk|amemv|qq\.com|gtimg|122\.gov|cloud\.189|api\.cloud\.189|mcd\.cn|96225\.com|neteasecloud|ad-sdk|adunion)", re.I)
FENG_SCRIPT_APPS = re.compile(r"哔哩哔哩|bilibili|bili|喜马拉雅|京东|美团|小爱音箱|优酷|YouTube|阿里巴巴|淘宝|NetEaseCloudMusic|网易云|微信小程序个人中心|广告联盟|myBlockAds", re.I)
REMOTE_RULES = "https://raw.githubusercontent.com/mrtanshiyue/surge-sgmodule/main/rules/"
ARGUMENTS = {**wool.ARGUMENT_DEFAULTS, "per_filter_video_thread": '"0"'}


def fetch(url):
    req = urllib.request.Request(url, headers={"User-Agent": "surge-sgmodule-sync"})
    for attempt in range(3):
        try:
            with urllib.request.urlopen(req, timeout=45) as response:
                return response.read().decode("utf-8")
        except (TimeoutError, urllib.error.URLError):
            if attempt == 2:
                raise


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


def startup_source(path, revision):
    if path:
        if not revision:
            raise ValueError("--startup-commit is required with --startup-source")
        return Path(path).read_text(encoding="utf-8"), revision
    url = "https://api.github.com/repos/" + STARTUP_REPO + "/commits?path=" + STARTUP_PATH + "&per_page=1"
    commits = json.loads(fetch(url))
    if not commits:
        raise RuntimeError("No startup source commit found")
    revision = commits[0]["sha"]
    return fetch("https://raw.githubusercontent.com/" + STARTUP_REPO + "/" + revision + "/" + STARTUP_PATH), revision


def add_wechat(module, source):
    source_sections = sections(source)
    selected = {}
    for section, group, expected in (
        ("URL Rewrite", "weixindaihuo", r"^https?:\/\/mp\.weixin\.qq\.com\/mp\/cps_product_info - reject-200"),
        ("Body Rewrite", "WeChat", r"http-response ^https?:\/\/mp\.weixin\.qq\.com\/mp\/getappmsgad advertisement ddgksf2013"),
    ):
        lines, active = [], False
        for line in source_sections.get(section, []):
            if line.startswith("# ===== "):
                active = line.strip() == "# ===== " + group + " ====="
            elif active and line.strip() and not line.lstrip().startswith("#"):
                lines.append(line.strip())
        if lines != [expected]:
            raise ValueError("WeChat upstream rule changed; review " + group)
        if section == "URL Rewrite":
            pattern = lines[0].removesuffix(" - reject-200")
            selected["Map Local"] = pattern + ' data-type=text data="" status-code=200'
        else:
            selected[section] = lines[0]
    parts = module.splitlines()
    for section, line in selected.items():
        header = "[" + section + "]"
        if header not in parts:
            raise ValueError("Missing output section " + section)
        if line not in parts:
            i = parts.index(header) + 1
            parts[i:i] = ["# 微信公众号：Walvez / 墨鱼", line]
    for i, line in enumerate(parts):
        if line.startswith("hostname = %APPEND% "):
            hosts = [x.strip() for x in line.split("%APPEND% ", 1)[1].split(",")]
            if "mp.weixin.qq.com" not in hosts:
                parts[i] += ", mp.weixin.qq.com"
            break
    else:
        raise ValueError("MITM hostname list missing")
    return "\n".join(parts) + "\n"


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
    exclusions = ",".join("(NOT,((" + rule + ",extended-matching)))" for rule in PROTECTIONS)
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
    # Names in a ruleset's exceptions describe what it allows, not the set's scope.
    if section == "Rule" and "RULE-SET," in line:
        return guard_ruleset(line).replace(FENG_PREFIX + "main/", FENG_PREFIX + revision + "/")
    normalized = line.replace("\\", "")
    if EXCLUDED.search(normalized):
        return None
    if section == "Rule" and "dig.bdurl.net" in normalized.lower():
        return None
    if section == "Rule":
        validate_simple_rule(line)
    if section == "Script" and "DmSegMobile" in normalized:
        return None  # This upstream request handler injects skip actions even with sponsorBlock=false.
    if section == "Map Local":
        data = re.search(r'\bdata="(\{.*\})"(?=\s+[\w-]+=|$)', line)
        if data and data.group(1).startswith(('{"', '{}')):
            json.loads(data.group(1))
            line = line[:data.start(1) - 1] + json.dumps(data.group(1), ensure_ascii=False) + line[data.end(1) + 1:]
    # wyres.js expects named options; its upstream home placeholders are unset.
    if "wyres.js" in line and "link\\/home\\/framework\\/tab" in line:
        line = line.replace('argument="[{{{MY}}},{{{DT}}},{{{FX}}}]"', r'argument="{\"MY\":true,\"DT\":false,\"FX\":true}"')
    if "wyres.js" in line and "{PRGG}" in line:
        line = re.sub(r',\s*argument="\[\{PRGG\}[^"\n]*\]"', '', line)
    # The upstream Bilibili scripts parse an object, not a positional array.
    if "bilibili.protobuf.request.js" in line and 'argument=[{{{logLevel}}}]' in line:
        line = line.replace('argument=[{{{logLevel}}}]', r'argument="{\"sponsorBlock\":false,\"logLevel\":\"error\"}"')
    if "bilibili.protobuf.request.js" in line and "{purifyComment}" in line:
        line = re.sub(r'argument="\[.*\]"', r'argument="{\\"purifyComment\\":true,\\"sponsorBlock\\":false,\\"logLevel\\":\\"error\\"}"', line)
    if "bilibili.protobuf.response.js" in line and "{displayUpList}" in line:
        line = re.sub(r'argument="\[.*\]"', r'argument="{\\"displayUpList\\":\\"show\\",\\"purifyComment\\":true,\\"sponsorBlock\\":false,\\"logLevel\\":\\"error\\"}"', line)
    return line.replace(FENG_PREFIX + "main/", FENG_PREFIX + revision + "/")


def http_host_patterns(content):
    patterns = []
    for section in ("URL Rewrite", "Header Rewrite", "Body Rewrite", "Map Local", "Script"):
        for line in content.get(section, []):
            if not line.strip() or line.startswith("#"):
                continue
            if section == "Script":
                pattern = script_key(line)[1]
            else:
                index = 1 if section in ("Header Rewrite", "Body Rewrite") else 0
                pattern = line.split()[index]
            pattern = pattern.strip('"').replace(r"\/", "/")
            host = re.match(r'^\^?https\??://((?:\[[^]]+\]|[^/])+)', pattern)
            if host:
                try:
                    re.compile(host.group(1))
                    patterns.append(host.group(1))
                except re.error:
                    # Some SDK rules put complete host/path pairs inside one alternation.
                    authority = pattern.split('://', 1)[1].removesuffix('$')
                    if not authority.startswith('(') or not authority.endswith(')'):
                        raise ValueError('Review unsupported HTTP host pattern: ' + pattern)
                    for branch in authority[1:-1].removeprefix('?:').split('|'):
                        branch_host = re.match(r'((?:\[[^]]+\]|[^/])+)/', branch)
                        if not branch_host:
                            raise ValueError('Review unsupported HTTP host branch: ' + branch)
                        re.compile(branch_host.group(1))
                        patterns.append(branch_host.group(1))
    return patterns


def required_hosts(content, candidates):
    required = set()
    for pattern in http_host_patterns(content):
        literal = pattern.replace(r"\.", ".")
        if re.fullmatch(r"[\w.-]+", literal):
            required.add(literal)
        # An any-host path rule must not make every upstream hostname a MITM target.
        if not re.search(r'[A-Za-z0-9][A-Za-z0-9-]*\.[A-Za-z0-9][A-Za-z0-9-]*', literal):
            continue
        regex = re.compile("^(?:" + pattern + ")$", re.I)
        required.update(h for h in candidates if "*" not in h and not h.startswith("-") and regex.fullmatch(h))
    return required


def deduplicate_scripts(lines):
    output, seen = [], {}
    for line in lines:
        if line.startswith("#"):
            output.append(line)
            continue
        pattern = script_key(line)[1]
        canonical = pattern.replace("^https:", "^https?:", 1)
        key = re.sub(r'\bpattern\s*=\s*.*?(?=,\s*[\w-]+\s*=|$)', lambda _: "pattern=" + canonical, line.split("=", 1)[1].strip())
        if key in seen:
            if pattern == canonical:
                output[seen[key]] = line
        else:
            seen[key] = len(output)
            output.append(line)
    return output


def merge(feng, revision, wool_module, wool_source=None):
    src, fallback = sections(feng), sections(wool_module)
    groups = wool.parse_module(wool_source)[1] if wool_source else {}
    attribution = {}
    selected_hosts, other_hosts = set(), set()
    for section, blocks in groups.items():
        for name, lines in blocks:
            for line in lines:
                host_comment = re.match(r"\s*#\s*hostname\s*=\s*(.*)", line, re.I)
                if host_comment:
                    hosts = selected_hosts if name in wool.ALLOWED_GROUPS else other_hosts
                    hosts.update(host.strip().lower() for host in host_comment.group(1).split(","))
                line = line.strip()
                if line and not line.startswith(("#", ";", "//")):
                    attribution.setdefault((section, line), set()).add(name)
    unknown = set(src) - set(SECTIONS) - {"MITM"}
    if unknown:
        raise ValueError("Upstream has unsupported sections: " + ", ".join(sorted(unknown)))
    output = ["#!name=才才的去广告集合", "#!desc=秋风奶思优先，合并截图 App 去广告规则。",
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
                if name == "Feng-Feng1":
                    known_groups = attribution.get((section, line), set())
                    if known_groups and not known_groups.intersection(wool.ALLOWED_GROUPS):
                        continue
                    normalized = line.replace("\\", "")
                    if "RULE-SET," not in line and ABSENT_APPS.search(normalized):
                        continue
                    if section in ("URL Rewrite", "Header Rewrite", "Body Rewrite", "Map Local") and not known_groups and not FENG_APP_PATTERNS.search(normalized):
                        continue
                    if section == "Script" and not FENG_SCRIPT_APPS.search(line.split("=", 1)[0]):
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
        if section == "Script":
            result = deduplicate_scripts(result)
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
    candidates = [h.strip() for part in (src, fallback) for line in part.get("MITM", [])
                  if "%APPEND%" in line for h in line.split("%APPEND%", 1)[1].split(",")]
    dependencies = required_hosts(section_lines, candidates)
    other_hosts.difference_update(selected_hosts)
    for part in (src, fallback):
        for line in part.get("MITM", []):
            match = re.fullmatch(r"\s*hostname\s*=\s*%APPEND%\s*(.*)", line, re.I)
            if match:
                for host in match.group(1).split(","):
                    host = host.strip()
                    selected = host.lower() not in other_hosts and (part is fallback or host.lower() in selected_hosts or FENG_APP_PATTERNS.search(host))
                    if host and (host in dependencies or selected) and not EXCLUDED.search(host) and not ABSENT_APPS.search(host) and host != "dig.bdurl.net" and host not in hosts:
                        hosts.append(host)
    hosts.extend(sorted(h for h in dependencies if h not in hosts and not EXCLUDED.search(h) and not ABSENT_APPS.search(h) and h != "dig.bdurl.net"))
    if not hosts:
        raise ValueError("No MITM hostnames found")
    output += ["", "[MITM]", "hostname = %APPEND% " + ", ".join(hosts)]
    module = "\n".join(output) + "\n"
    if re.search(r"(?<!\{)\{(?:displayUpList|purifyComment)\}(?!\})", module):
        raise ValueError("Unresolved Bilibili placeholders")
    return module


def externalize_rules(module):
    """Move contiguous identical-action domain rules to immutable, content-addressed lists."""
    out, assets, pending, current = [], {}, [], None
    in_rules = False

    def flush():
        nonlocal pending, current
        if len(pending) < 8:
            out.extend(pending)
        else:
            body = "\n".join(",".join((p := line.split(","))[:2] + p[3:]) for line in pending) + "\n"
            digest = hashlib.sha256(body.encode()).hexdigest()[:20]
            filename = f"personal-{digest}.list"
            assets[filename] = body
            out.append("RULE-SET," + REMOTE_RULES + filename + "," + current[0])
        pending, current = [], None

    for line in module.splitlines():
        if line.startswith("[") and line.endswith("]"):
            flush()
            in_rules = line == "[Rule]"
        parts = line.split(",")
        eligible = (in_rules and len(parts) in (3, 4) and
                    parts[0] in ("DOMAIN", "DOMAIN-SUFFIX", "DOMAIN-KEYWORD") and
                    parts[2] in ("REJECT", "DIRECT") and
                    (len(parts) == 3 or parts[3] == "extended-matching"))
        key = (parts[2], len(parts) == 4) if eligible else None
        if key is None:
            flush()
            out.append(line)
        else:
            if current is not None and current != key:
                flush()
            current = key
            pending.append(line)
    flush()
    return "\n".join(out) + "\n", assets


def pin_scripts(module, lock, fetcher=None):
    fetcher = fetcher or fetch
    approved = {(entry["repository"], entry["path"]): entry for entry in lock}
    records = []
    with tempfile.TemporaryDirectory() as temporary:
        for url in sorted(set(re.findall(r'script-path=([^,\s]+)', module))):
            match = re.fullmatch(r'https://raw\.githubusercontent\.com/([^/]+/[^/]+)/[^/]+/(.+)', url)
            if not match or match.groups() not in approved:
                raise ValueError("Unreviewed script dependency: " + url)
            entry = approved[match.groups()]
            if not re.fullmatch(r'[0-9a-f]{40}', entry['commit']):
                raise ValueError("Script dependency needs an immutable commit: " + url)
            prefix = 'https://raw.githubusercontent.com/' + entry['repository'] + '/'
            pinned = prefix + entry['commit'] + '/' + entry['path']
            code = fetcher(pinned)
            if hashlib.sha256(code.encode()).hexdigest() != entry['sha256']:
                raise ValueError("Approved script checksum mismatch: " + pinned)
            commits = json.loads(fetcher('https://api.github.com/repos/' + entry['repository'] + '/commits?path=' + urllib.parse.quote(entry['path'], safe='') + '&per_page=1'))
            if not commits:
                raise ValueError("Script upstream has no commits: " + url)
            latest = prefix + commits[0]['sha'] + '/' + entry['path']
            current = code if latest == pinned else fetcher(latest)
            if hashlib.sha256(current.encode()).hexdigest() != entry['sha256']:
                raise ValueError("Script upstream changed; review script-lock.json: " + latest)
            local = Path(temporary) / ('script-' + str(len(records)) + '.js')
            local.write_text(code, encoding='utf-8')
            subprocess.run(['node', '--check', str(local)], check=True, capture_output=True, text=True)
            module = module.replace(url, pinned)
            records.append(entry)
    return module, records


def validate_module(module, assets):
    content = sections(module)
    hosts = wool.source_mitm_hosts(content)
    missing = required_hosts(content, hosts) - set(hosts)
    if missing:
        raise ValueError('Missing MITM dependency: ' + ', '.join(sorted(missing)))
    for line in content['Map Local']:
        if not line.strip() or line.startswith('#'):
            continue
        params = dict(item.split('=', 1) for item in shlex.split(line)[1:])
        if set(params) - {'data-type', 'data', 'header', 'status-code'}:
            raise ValueError('Invalid Map Local parameters: ' + line)
        body = params.get('data', '').strip()
        if params.get('data-type') == 'text' and body.startswith(('{', '[')):
            json.loads(body)
    for line in content.get('Body Rewrite', []):
        if line.startswith(('http-request-jq ', 'http-response-jq ')):
            expression = shlex.split(line)[2]
            subprocess.run(['jq', '-n', 'if false then (' + expression + ') else null end'], check=True, capture_output=True, text=True)
    airborne = 'https://grpc.biliapi.net/bilibili.community.service.dm.v1.DM/DmSegMobile'
    for line in content.get('Script', []):
        if not line.strip() or line.startswith('#'):
            continue
        kind, pattern = script_key(line)
        if kind == 'http-request' and re.search(pattern, airborne):
            raise ValueError('Sponsor skip request handler must not be enabled')
        if re.search(r'bilibili\.protobuf\.(request|response)\.js', line):
            arg = re.search(r'argument=("(?:\\.|[^"\\])*")', line)
            if not arg or json.loads(json.loads(arg.group(1))).get('sponsorBlock') is not False:
                raise ValueError('Bilibili sponsorBlock must be false')
    for line in content['Rule']:
        if not line.strip() or line.startswith('#'):
            continue
        if 'RULE-SET,' in line and REMOTE_RULES not in line:
            for guard in PROTECTIONS:
                if '(NOT,((' + guard + ',extended-matching)))' not in line:
                    raise ValueError('External ruleset is missing protection: ' + guard)
        else:
            validate_simple_rule(line)
    for name, body in assets.items():
        if name != 'personal-' + hashlib.sha256(body.encode()).hexdigest()[:20] + '.list':
            raise ValueError('Rule file checksum mismatch: ' + name)
        for line in body.splitlines():
            parts = line.split(',')
            validate_simple_rule(','.join(parts[:2] + ['REJECT'] + parts[2:]))


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--feng-source")
    p.add_argument("--feng-commit")
    p.add_argument("--startup-source")
    p.add_argument("--startup-commit")
    p.add_argument("--wool-source")
    p.add_argument("--wool-commit")
    p.add_argument("--output", default="PersonalAds.sgmodule")
    p.add_argument("--manifest", default="sources.json")
    args = p.parse_args()
    feng, revision = feng_source(args.feng_source, args.feng_commit)
    startup, startup_revision = startup_source(args.startup_source, args.startup_commit)
    src, wc = wool.read_upstream(args.wool_source)
    if args.wool_source and not args.wool_commit:
        raise ValueError("--wool-commit is required with --wool-source")
    wc = args.wool_commit or wc
    baseline, manifest = wool.build(src, wc)
    module = merge(feng, revision, baseline, src)
    module = add_wechat(module, startup)
    lock = json.loads((Path(__file__).resolve().parent.parent / 'script-lock.json').read_text(encoding='utf-8'))
    module, dependencies = pin_scripts(module, lock)
    module, assets = externalize_rules(module)
    validate_module(module, assets)
    expected = sum('RULE-SET,' in line for line in sections(feng).get('Rule', []))
    if module.count('AND,((AND,((RULE-SET,') != expected:
        raise ValueError('An upstream external ruleset was lost during merging')
    asset_dir = Path(args.output).resolve().parent / "rules"
    asset_dir.mkdir(exist_ok=True)
    for name, content in assets.items():
        (asset_dir / name).write_text(content, encoding="utf-8")
    manifest["feng"] = {"repository": "https://github.com/" + FENG_REPO, "path": FENG_PATH,
                        "commit": revision, "sha256": hashlib.sha256(feng.encode()).hexdigest()}
    names = sorted(set(re.findall(r"\{\{\{([A-Za-z0-9_]+)\}\}\}", module)))
    manifest["module_arguments"] = {name: ARGUMENTS[name].strip('"') for name in names}
    manifest["wechat_source"] = {"repository": "https://github.com/" + STARTUP_REPO, "path": STARTUP_PATH, "commit": startup_revision, "sha256": hashlib.sha256(startup.encode()).hexdigest(), "scope": "微信公众号广告接口和商品推广"}
    manifest["remote_rules"] = sorted(assets)
    manifest['script_dependencies'] = dependencies
    manifest["module_sha256"] = hashlib.sha256(module.encode()).hexdigest()
    manifest["merge_notes"] = {"priority": "Feng before Wool", "scope": "截图可识别 App；保留共享及无法确定归属的规则", "protected": list(PROTECTIONS),
                               "excluded": ["小红书专属规则", "小象助力车专属规则", "Spotify.Crack.Dev.js", "Bilibili DmSegMobile 赞助空降"]}
    Path(args.output).write_text(module, encoding="utf-8")
    Path(args.manifest).write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
    print("Built", args.output, "from Feng", revision, "and Wool", wc)


if __name__ == "__main__":
    main()
