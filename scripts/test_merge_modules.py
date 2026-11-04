import json
import re
import unittest

from merge_modules import add_wechat, externalize_rules, merge, script_key


class MergeTests(unittest.TestCase):
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
        self.assertEqual(json.loads(json.loads(argument)), {"logLevel": "error"})


if __name__ == "__main__":
    unittest.main()
