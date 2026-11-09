"""Regression checks against the module produced from real upstream sources."""
import hashlib
import json
import re
import shlex
import subprocess
import unittest
from pathlib import Path

from merge_modules import REMOTE_RULES, script_key, script_path_field, sections, validate_module

ROOT = Path(__file__).resolve().parent.parent


class BuiltModuleTests(unittest.TestCase):
    def test_generated_artifacts_keep_real_world_protections(self):
        module = (ROOT / 'PersonalAds.sgmodule').read_text(encoding='utf-8')
        manifest = json.loads((ROOT / 'sources.json').read_text(encoding='utf-8'))
        assets = {name: (ROOT / 'rules' / name).read_text(encoding='utf-8') for name in manifest['remote_rules']}
        validate_module(module, assets)
        self.assertEqual(hashlib.sha256(module.encode()).hexdigest(), manifest['module_sha256'])
        content = sections(module)
        external = [line for line in content['Rule'] if 'RULE-SET,' in line and REMOTE_RULES not in line]
        self.assertEqual(len(external), 3)
        mitm = content['MITM'][0].split('%APPEND%', 1)[1].split(', ')
        for host in ('api-access.pangolin-sdk-toutiao.com', 'api-access.pangolin-sdk-toutiao-b.com',
                     'api-access.pangolin-sdk-toutiao1.com', 'mi.gdt.qq.com', 'router-app-api.jdcloud.com'):
            self.assertIn(host, [h.strip() for h in mitm])
        self.assertNotIn('DmSegMobile', module)
        self.assertIn('.vip_type = 2', module)
        dependencies = manifest['script_dependencies']
        lock = json.loads((ROOT / 'script-lock.json').read_text())
        self.assertCountEqual(dependencies, lock)
        locked_urls = {f"https://raw.githubusercontent.com/{e['repository']}/{e['commit']}/{e['path']}" for e in lock}
        script_urls = {script_path_field(l)[0] for l in content['Script'] if l.strip() and not l.startswith('#')}
        self.assertEqual(script_urls, locked_urls)
        for url in ('https://guide-acs.m.taobao.com/gw/mtop.taobao.cloudvideo.video.query',
                    'https://poplayer.template.alibaba.com/test.json'):
            matches = [line for line in content['Script'] if not line.startswith('#') and line.strip()
                       and script_key(line)[0] == 'http-response' and re.search(script_key(line)[1], url)]
            self.assertEqual(len(matches), 1)

    def test_responses_preserve_normal_cards_and_tracking_fields(self):
        lines = sections((ROOT / 'PersonalAds.sgmodule').read_text())['Body Rewrite']
        def apply_jq(url, obj):
            hits = [shlex.split(l) for l in lines if l.startswith('http-response-jq ') and re.search(l.split()[1], url)]
            self.assertEqual(len(hits), 1, url)
            return json.loads(subprocess.check_output(['jq', '-c', hits[0][2]], input=json.dumps(obj).encode()))
        url = 'https://mobile.yangkeduo.com/proxy/api/api/express/post/waybill/red_packet/goods_list'
        for key in (None, 'data', 'result'):
            fields = {'list': [{'ad': 1}], 'order': 'ok', 'tracking': [1, 2], 'other': {'list': [3]}}
            expected = dict(fields, list=[])
            self.assertEqual(apply_jq(url, {key: fields} if key else fields), {key: expected} if key else expected)
        url = 'https://mobile.ximalaya.com/discovery-feed/v1/mix/'
        normal = {'item': {'list': [{'bizType': 'A'}, {'bizType': 'B'}]}}
        ad = {'bizType': 'SceneListenCard'}
        mixed = {'id': 1, 'item': {'list': [ad, {'bizType': 'A'}]}}
        unknown = {'item': {'list': 'unknown'}}
        obj = {'heData': [normal, mixed, unknown, {'item': {'list': [ad]}}], 'more': True}
        expected = {'heData': [normal, {'id': 1, 'item': {'list': [{'bizType': 'A'}]}}, unknown], 'more': True}
        self.assertEqual(apply_jq(url, obj), expected)
        self.assertEqual(apply_jq(url, {'error': 1}), {'error': 1})

    def test_shared_api_routes_do_not_override_other_operations(self):
        content = sections((ROOT / 'PersonalAds.sgmodule').read_text())
        maps = [l.split()[0] for l in content['Map Local'] if l.strip() and not l.startswith('#')]
        scripts = [script_key(l)[1] for l in content['Script'] if l.strip() and not l.startswith('#')]
        def matches(patterns, url):
            return [p for p in patterns if re.search(p, url)]
        meituan = 'https://wmapi.meituan.com/api/v7/'
        self.assertFalse(matches(maps, meituan + 'loadInfo?city=1'))
        self.assertTrue(matches(scripts, meituan + 'loadInfo?city=1'))
        self.assertTrue(matches(maps, meituan + 'openscreen?city=1'))
        jd = 'https://api.m.jd.com/client.action?functionId='
        self.assertFalse(matches(scripts, jd + 'startOther'))
        self.assertTrue(matches(scripts, jd + 'myOrderInfo&v=1'))
        rail_url = 'https://ad.12306.cn/ad/ser/getAdList'
        rail = [l for l in content['Script'] if l.startswith('V5-12306无广告响应')]
        self.assertEqual(len(rail), 1)
        self.assertEqual(script_key(rail[0])[0], 'http-request')
        self.assertTrue(re.search(script_key(rail[0])[1], rail_url))
        self.assertFalse(re.search(script_key(rail[0])[1], rail_url + 'Extra'))
        self.assertIn('argument=rail12306', rail[0])
        self.assertIn('ad.12306.cn', content['MITM'][0].split('%APPEND%', 1)[1].split(', '))
        self.assertTrue(matches(maps, 'https://foo.googleapis.com/player/ad_break'))
        self.assertFalse(matches(maps, 'https://example.org/path/foo.googleapis.com/player/ad_break'))
        self.assertFalse(matches(maps, 'https://example.org/?u=https://interface.music.163.com/eapi/ad'))
        self.assertFalse(matches(maps, 'https://interface.music.163Xcom/eapi/ad'))
        self.assertFalse(any(l.startswith('AND,') and 'RULE-SET,' not in l and 'DOMAIN-KEYWORD,volc)' in l
                             for l in content['Rule']))


if __name__ == '__main__':
    unittest.main()
