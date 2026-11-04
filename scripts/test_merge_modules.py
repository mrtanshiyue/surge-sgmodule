import json
import re
import unittest

from merge_modules import merge, script_key


class MergeTests(unittest.TestCase):
    def test_priority_and_protection(self):
        feng = r'''[Rule]
AND,((RULE-SET,https://example.com/list),(NOT,((DOMAIN,example.com)))),REJECT
DOMAIN,t-ads.xiaohongshu.com,REJECT
DOMAIN,ok.example,REJECT
[Map Local]
^https://ebike-client\.xiaoantech\.com/client/ad/ data-type=text data="{}"
[Script]
upstream = type=http-response, pattern=^https://api\.example/test, script-path=https://example.com/a.js
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
        self.assertIn("upstream = type=http-response", result)
        self.assertNotIn("old = type=http-response", result)
        self.assertNotIn("xiaoantech", result)
        self.assertNotIn("edith.xiaohongshu.com", result)
        rule = next(line for line in result.splitlines() if "RULE-SET,https://example.com/list" in line)
        self.assertEqual(rule.count("("), rule.count(")"))
        for guard in ("DOMAIN,dig.bdurl.net", "DOMAIN-SUFFIX,xiaohongshu.com",
                      "DOMAIN-SUFFIX,xhscdn.com", "DOMAIN-SUFFIX,xhslink.com",
                      "DOMAIN-SUFFIX,rednote.com", "DOMAIN-WILDCARD,v*-reading-ad.qznovelvod.com"):
            self.assertIn(guard, rule)

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
netease=type=http-response,pattern=^https://music.example/,script-path=https://example.com/wyres.js
spotify=type=http-response,pattern=^https://spotify.example/,script-path=https://example.com/Spotify.Crack.Dev.js
bili=type=http-request,pattern=^https://bili.example/,script-path=https://example.com/bilibili.protobuf.request.js,argument=[{{{logLevel}}}]
[MITM]
hostname = %APPEND% bili.example
'''
        output = merge(source, "abc123", "")
        self.assertNotIn("wyres.js", output)
        self.assertNotIn("Spotify.Crack", output)
        line = next(line for line in output.splitlines() if line.startswith("bili="))
        argument = line.split("argument=", 1)[1]
        self.assertEqual(json.loads(json.loads(argument)), {"logLevel": "error"})


if __name__ == "__main__":
    unittest.main()
