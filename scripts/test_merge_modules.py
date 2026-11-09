import json
import hashlib
import io
import re
import shlex
import unittest
import urllib.error
from unittest.mock import patch

import build_personal_ads as wool

from merge_modules import (FENG_PREFIX, REMOTE_RULES, add_wechat, deduplicate_scripts, externalize_rules,
                           guard_ruleset, merge, pin_scripts, required_hosts, script_key, validate_module, verify_external_lists)


class MergeTests(unittest.TestCase):
    def test_upstream_retries_transient_errors_for_both_downloads(self):
        failure = lambda: urllib.error.HTTPError('https://example.com', 500, 'server error', {}, None)
        commit = 'a' * 40
        responses = [failure(), io.BytesIO(json.dumps([{'sha': commit}]).encode()),
                     failure(), io.BytesIO(b'module content')]
        with patch('build_personal_ads.urllib.request.urlopen', side_effect=responses) as get, \
             patch('build_personal_ads.time.sleep') as sleep:
            self.assertEqual(wool.read_upstream(None), ('module content', commit))
        self.assertEqual(get.call_count, 4)
        self.assertEqual(sleep.call_count, 2)
        self.assertIn(commit, get.call_args_list[-1].args[0].full_url)

    def test_upstream_retries_are_bounded_and_do_not_retry_404(self):
        for code, attempts in ((500, 3), (404, 1)):
            error = urllib.error.HTTPError('https://example.com', code, 'failure', {}, None)
            with patch('build_personal_ads.urllib.request.urlopen', side_effect=error) as get, \
                 patch('build_personal_ads.time.sleep'):
                with self.assertRaises(urllib.error.HTTPError):
                    wool.read_upstream(None)
                self.assertEqual(get.call_count, attempts)

    def test_12306_splash_handler_and_mitm_are_kept(self):
        source = r'''[Script]
V5-12306无广告响应 = type=http-request,pattern=^https?:\/\/ad\.12306\.cn\/ad\/ser\/getAdList(?:\?|$),requires-body=true,script-path=https://example.com/ads.js,argument=rail12306
[MITM]
hostname = %APPEND% ad.12306.cn
'''
        output = merge(source, 'abc', '')
        self.assertIn('V5-12306无广告响应', output)
        self.assertIn('argument=rail12306', output)
        self.assertIn('ad.12306.cn', output.split('[MITM]', 1)[1])

    def test_formatted_script_paths_cannot_bypass_review(self):
        pre = '[Rule]\n# script-path=https://example.org/unrelated\n[Script]\n'
        line = 'a= type=http-response, pattern=^https://a.test/, argument="other, script-path=decoy", SCRIPT-PATH = "https://raw.githubusercontent.com/org/repo/main/a.js"'
        with self.assertRaisesRegex(ValueError, 'Unreviewed'):
            pin_scripts(pre + line, [], lambda _: '')
        entry = {'repository': 'org/repo', 'path': 'a.js', 'commit': 'a'*40, 'sha256': hashlib.sha256(b'').hexdigest()}
        output, records = pin_scripts(pre + line, [entry], lambda _: '', check_latest=False)
        self.assertTrue(output.startswith(pre))
        self.assertIn('argument="other, script-path=decoy"', output)
        self.assertIn('/' + 'a'*40 + '/a.js', output)
        self.assertEqual(records, [entry])
        for invalid in (line + ',script-path=local.js', line.split(', SCRIPT-PATH')[0]):
            with self.assertRaises(ValueError):
                pin_scripts(pre + invalid, [entry], lambda _: '')

    def test_dedup_preserves_intervening_http_handler(self):
        def script(name, scheme, path, action):
            return f'{name}=type=http-response,pattern=^{scheme}://api\\.example/{path},script-path={action}'
        a = script('first', 'https', 'feed', 'a')
        b = script('special', 'http', 'feed/story', 'b')
        c = script('fallback', 'https?', 'feed', 'a')
        self.assertEqual(deduplicate_scripts([a, b, c]), [a, b, c])

    def test_unavailable_or_substituted_external_list_fails(self):
        body = 'DOMAIN,ads.example\n'
        sha = hashlib.sha256(body.encode()).hexdigest()
        line = f'AND,((RULE-SET,{FENG_PREFIX}main/Resources/AdBlock/{sha}.list),(DOMAIN,ads.example)),REJECT'
        src, output = '[Rule]\n' + line, '[Rule]\n' + guard_ruleset(line).replace('/main/', '/abc/')
        self.assertEqual(verify_external_lists(src, 'abc', output, lambda _: body)[0]['sha256'], sha)
        with self.assertRaisesRegex(ValueError, 'checksum'):
            verify_external_lists(src, 'abc', output, lambda _: '<html>error</html>')
        with self.assertRaisesRegex(ValueError, 'differs'):
            verify_external_lists(src, 'abc', output.replace(',REJECT', ',DIRECT'), lambda _: body)

    def test_generated_direct_list_may_allow_a_protected_host(self):
        body = 'DOMAIN,dig.bdurl.net\n'
        name = 'personal-' + hashlib.sha256(body.encode()).hexdigest()[:20] + '.list'
        module = '[Map Local]\n[MITM]\nhostname = %APPEND% api.example\n[Rule]\nRULE-SET,' + REMOTE_RULES + name + ',DIRECT\n'
        validate_module(module, {name: body})
        with self.assertRaisesRegex(ValueError, 'protected host'):
            validate_module(module.replace(',DIRECT', ',REJECT'), {name: body})
        with self.assertRaisesRegex(ValueError, 'Missing generated'):
            validate_module(module, {})

    def test_host_patterns_keep_slashes_inside_character_classes(self):
        content = {'Map Local': [r'^https?:\/\/[^\/]+\.amemv\.com\/api\/ad data-type=text data=" "']}
        self.assertEqual(required_hosts(content, ['api.amemv.com']), {'api.amemv.com'})

    def test_host_path_alternatives_each_keep_their_mitm_dependency(self):
        content = {'Script': [r'联盟=type=http-response, pattern=^https:\/\/(api\.example\.com\/api\/ad|other\.example\.com\/rest\/ads$|mi\.gdt\.qq\.com\/gdt_mview\.fcg\?), script-path=https://example.com/a.js']}
        self.assertEqual(required_hosts(content, []), {'api.example.com', 'other.example.com', 'mi.gdt.qq.com'})

    def test_any_host_url_rule_does_not_expand_mitm_to_unrelated_hosts(self):
        content = {'URL Rewrite': [r'^https?:\/\/.+?\/music\/common\/upload\/t_splash_info - reject']}
        self.assertEqual(required_hosts(content, ['bank.example.com', 'api.m.jd.com']), set())

    def test_script_lock_pins_sources_and_stops_independent_upstream_changes(self):
        code = 'const ok = true;\n'
        entry = {'repository': 'owner/repo', 'path': 'test.js', 'commit': 'a' * 40,
                 'sha256': hashlib.sha256(code.encode()).hexdigest()}
        line = '[Script]\n京东=type=http-response,pattern=^https://jd.com/,script-path=https://raw.githubusercontent.com/owner/repo/main/test.js'
        def fetch(url):
            return code
        output, records = pin_scripts(line, [entry], fetch)
        self.assertIn('/' + 'a' * 40 + '/test.js', output)
        self.assertEqual(records, [entry])
        def changed(url):
            return 'const changed = true;' if '/HEAD/' in url else fetch(url)
        with self.assertRaisesRegex(ValueError, 'upstream changed'):
            pin_scripts(line, [entry], changed)
        with self.assertRaisesRegex(ValueError, 'Unreviewed'):
            pin_scripts(line, [], fetch)

    def test_validation_rejects_broken_mock_json_and_sponsor_request_handlers(self):
        base = '[Rule]\n[Map Local]\n[MITM]\nhostname = %APPEND% api.bilibili.com\n'
        broken = base.replace('[Map Local]\n', '[Map Local]\n^https://api.bilibili.com/ data-type=text data="{oops}"\n')
        with self.assertRaises(ValueError):
            validate_module(broken, {})
        airborne = base.replace('[MITM]', '[Script]\nbili=type=http-request,pattern=^https://grpc.biliapi.net/.*/DmSegMobile$,script-path=https://example.com/a.js\n[MITM]').replace('%APPEND% api.bilibili.com', '%APPEND% api.bilibili.com, grpc.biliapi.net')
        with self.assertRaisesRegex(ValueError, 'Sponsor skip'):
            validate_module(airborne, {})

    def test_external_ruleset_exceptions_do_not_remove_the_whole_set(self):
        source = '[Rule]\nAND,((RULE-SET,https://example.com/ads.list),(NOT,((DOMAIN,api.iqiyi.com)))),REJECT,pre-matching\n[MITM]\nhostname = %APPEND% api.bilibili.com\n'
        output = merge(source, 'abc', '')
        self.assertIn('RULE-SET,https://example.com/ads.list', output)
        self.assertIn('DOMAIN,dig.bdurl.net,extended-matching', output)
        self.assertIn('REJECT,pre-matching', output)

    def test_shared_mitm_dependency_survives_absent_app_attribution(self):
        source = r'''[Map Local]
^https?:\/\/api-access\.pangolin-sdk-toutiao\.com\/api\/ad\/union\/sdk\/get_ads data-type=text data="{}"
[MITM]
hostname = %APPEND% api-access.pangolin-sdk-toutiao.com
'''
        wool = '# > 七猫小说\n[URL Rewrite]\n# > 七猫小说\n# hostname = api-access.pangolin-sdk-toutiao.com\n'
        output = merge(source, 'abc', '', wool)
        self.assertIn('hostname = %APPEND% api-access.pangolin-sdk-toutiao.com', output)

    def test_literal_https_dependency_is_added_without_decrypting_all_hosts(self):
        output = merge('[URL Rewrite]\n^https://api\\.mcd\\.cn/bff/splash - reject\n[MITM]\nhostname = %APPEND% api.example\n', 'abc', '')
        self.assertIn('api.mcd.cn', output.split('[MITM]', 1)[1])
        self.assertNotIn(', *', output.split('[MITM]', 1)[1])

    def test_map_local_json_quotes_do_not_consume_following_parameters(self):
        from merge_modules import clean_line
        line = r'^https://api\.bilibili\.com/test data-type=text data="{"code":0,"data":{"showTime":""},"message":"success"}" status-code=200 header="Content-Type:text/plain"'
        result = clean_line('Map Local', line, 'abc')
        params = dict(p.split('=', 1) for p in shlex.split(result)[1:])
        self.assertEqual(json.loads(params['data'])['code'], 0)
        self.assertEqual(params['status-code'], '200')
        self.assertEqual(params['header'], 'Content-Type:text/plain')

    def test_no_airborne_request_and_no_duplicate_http_variants(self):
        source = r'''[Script]
bilibili.airborne=type=http-request, pattern=^https://grpc\.biliapi\.net/bilibili.community.service.dm.v1.DM/DmSegMobile$, script-path=https://example.com/bilibili.protobuf.request.js
淘宝1=type=http-response, pattern=^https:\/\/guide-acs\.m\.taobao\.com\/test, script-path=https://example.com/a.js, requires-body=true
淘宝2=type=http-response, pattern=^https?:\/\/guide-acs\.m\.taobao\.com\/test, script-path=https://example.com/a.js, requires-body=true
[MITM]
hostname = %APPEND% grpc.biliapi.net, guide-acs.m.taobao.com
'''
        output = merge(source, 'abc', '')
        self.assertNotIn('DmSegMobile', output)
        self.assertEqual(output.count('script-path=https://example.com/a.js'), 1)
        self.assertIn('^https?:', output)

    def test_priority_and_protection(self):
        feng = r'''[Rule]
AND,((RULE-SET,https://example.com/list),(NOT,((DOMAIN,example.com)))),REJECT
DOMAIN,t-ads.xiaohongshu.com,REJECT
DOMAIN,ok.example,REJECT
[Map Local]
^https://ebike-client\.xiaoantech\.com/client/ad/ data-type=text data="{}"
[Script]
京东-upstream = type=http-response, pattern=^https://api\.example/test, script-path=https://example.com/a.js
[MITM]
hostname = %APPEND% api.example, edith.xiaohongshu.com
'''
        fallback = r'''[Rule]
DOMAIN,ok.example,REJECT
[Script]
old = type=http-response, pattern=^https://api\.example/test, script-path=https://example.com/b.js
[MITM]
hostname = %APPEND% api.example
'''
        result = merge(feng, "abcdef", fallback)
        self.assertTrue(result.startswith("#!name=才才的去广告集合\n"))
        self.assertEqual(result.count("DOMAIN,ok.example,REJECT"), 1)
        self.assertIn("京东-upstream = type=http-response", result)
        self.assertNotIn("old = type=http-response", result)
        self.assertNotIn("xiaoantech", result)
        self.assertNotIn("edith.xiaohongshu.com", result)
        rule = next(line for line in result.splitlines() if "RULE-SET,https://example.com/list" in line)
        self.assertEqual(rule.count("("), rule.count(")"))
        for guard in ("DOMAIN,dig.bdurl.net", "DOMAIN-SUFFIX,xiaohongshu.com",
                      "DOMAIN-SUFFIX,xhscdn.com", "DOMAIN-SUFFIX,xhslink.com",
                      "DOMAIN-SUFFIX,rednote.com", "DOMAIN-WILDCARD,v*-reading-ad.qznovelvod.com"):
            self.assertIn(guard, rule)

    def test_excludes_absent_apps_and_preserves_shared_rules(self):
        feng = r"""[URL Rewrite]
^https://absent.example/ad _ reject
^https://shared.example/ad _ reject
[Script]
V5-知乎 = type=http-response, pattern=^https://zhihu.com/, script-path=https://example.com/a.js
V5-京东 = type=http-response, pattern=^https://jd.com/, script-path=https://example.com/a.js
[MITM]
hostname = %APPEND% absent.example, shared.example, api.zhihu.com
"""
        source = """[URL Rewrite]
# > 知乎
# hostname = absent.example
^https://absent.example/ad _ reject
# > 淘宝
# hostname = shared.example
^https://shared.example/ad _ reject
"""
        result = merge(feng, "abc", "", source)
        self.assertNotIn("absent.example", result)
        self.assertNotIn("zhihu", result)
        self.assertIn("shared.example", result)
        self.assertIn("V5-京东", result)

    def test_wechat_is_narrow_and_fails_if_upstream_changes(self):
        module = "[URL Rewrite]\n[Body Rewrite]\n[Map Local]\n[MITM]\nhostname = %APPEND% existing.example\n"
        source = r"""[URL Rewrite]
# ===== weixindaihuo =====
^https?:\/\/mp\.weixin\.qq\.com\/mp\/cps_product_info - reject-200
# ===== other =====
^https://other.example/ - reject
[Body Rewrite]
# ===== WeChat =====
http-response ^https?:\/\/mp\.weixin\.qq\.com\/mp\/getappmsgad advertisement ddgksf2013
"""
        result = add_wechat(module, source)
        self.assertIn("mp.weixin.qq.com", result)
        self.assertIn("getappmsgad", result)
        self.assertIn('cps_product_info data-type=text data="" status-code=200', result)
        self.assertNotIn("other.example", result)
        self.assertEqual(add_wechat(result, source), result)
        with self.assertRaises(ValueError):
            add_wechat(module, source.replace("advertisement ddgksf2013", "anything else"))

    def test_remote_rule_lists_preserve_order_and_options(self):
        rules = [f"DOMAIN,ad{i}.example,REJECT" for i in range(8)]
        extended = [f"DOMAIN,ext{i}.example,REJECT,extended-matching" for i in range(8)]
        source = "[Rule]\n" + "\n".join(rules + extended) + "\nDOMAIN,after.example,DIRECT\n"
        module, assets = externalize_rules(source)
        refs = [line for line in module.splitlines() if line.startswith("RULE-SET,")]
        self.assertEqual(len(refs), 2)
        self.assertEqual(assets[refs[0].split(",")[1].rsplit("/", 1)[1]].splitlines(), [f"DOMAIN,ad{i}.example" for i in range(8)])
        self.assertEqual(assets[refs[1].split(",")[1].rsplit("/", 1)[1]].splitlines(), [f"DOMAIN,ext{i}.example,extended-matching" for i in range(8)])
        self.assertTrue(module.rstrip().endswith("DOMAIN,after.example,DIRECT"))

    def test_keeps_membership_and_interface_body_rewrites(self):
        source = r"""[Body Rewrite]
http-response-jq ^https://app.bilibili.com/x/v2/account/mine '.data.vip_type = 2'
http-response-jq ^https://app.bilibili.com/x/v2/splash/list '.data.show = []'
[MITM]
hostname = %APPEND% app.bilibili.com
"""
        output = merge(source, "abc", "")
        self.assertIn("vip_type", output)
        self.assertIn("/x/v2/splash/list", output)

    def test_netease_upstream_arguments(self):
        from merge_modules import clean_line
        tab = r'NetEaseCloudMusic_tab=type=http-response,pattern=link\/home\/framework\/tab,script-path=https://example.com/wyres.js,argument="[{{{MY}}},{{{DT}}},{{{FX}}}]"'
        result = clean_line("Script", tab, "abc")
        self.assertEqual(json.loads(json.loads(result.split("argument=", 1)[1])), {"MY": True, "DT": False, "FX": True})
        home = 'x=type=http-response,script-path=https://example.com/wyres.js,argument="[{PRGG},{PRRK}]"'
        self.assertNotIn("argument=", clean_line("Script", home, "abc"))

    def test_script_identity_includes_type(self):
        self.assertNotEqual(script_key("a=type=http-response, pattern=^https://example.com"),
                            script_key("b=type=http-request, pattern=^https://example.com"))

    def test_reject_unknown_section(self):
        with self.assertRaises(ValueError):
            merge("[Unrecognised]\nx=1\n[MITM]\nhostname = %APPEND% test.example\n", "a", "")

    def test_reject_broad_keyword_covering_protected_host(self):
        with self.assertRaises(ValueError):
            merge("[Rule]\nDOMAIN-KEYWORD,reading-ad,REJECT\n[MITM]\nhostname = %APPEND% test.example\n", "a", "")

    def test_membership_scripts_and_bilibili_arguments(self):
        source = r'''[Script]
NetEaseCloudMusic=type=http-response,pattern=^https://music.example/,script-path=https://example.com/wyres.js
spotify=type=http-response,pattern=^https://spotify.example/,script-path=https://example.com/Spotify.Crack.Dev.js
bili=type=http-request,pattern=^https://app.bilibili.com/,script-path=https://example.com/bilibili.protobuf.request.js,argument=[{{{logLevel}}}]
[MITM]
hostname = %APPEND% app.bilibili.com
'''
        output = merge(source, "abc123", "")
        self.assertIn("wyres.js", output)
        self.assertNotIn("Spotify.Crack", output)
        line = next(line for line in output.splitlines() if line.startswith("bili="))
        argument = line.split("argument=", 1)[1]
        self.assertEqual(json.loads(json.loads(argument)), {"sponsorBlock": False, "logLevel": "error"})


if __name__ == "__main__":
    unittest.main()
