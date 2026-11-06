"""Regression checks against the module produced from real upstream sources."""
import hashlib
import json
import re
import unittest
from pathlib import Path

from merge_modules import REMOTE_RULES, script_key, sections, validate_module

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
        self.assertEqual(len(dependencies), 14)
        self.assertEqual({(d['repository'], d['path']) for d in dependencies},
                         {(d['repository'], d['path']) for d in json.loads((ROOT / 'script-lock.json').read_text())})
        for url in re.findall(r'script-path=([^,\s]+)', module):
            self.assertRegex(url, r'githubusercontent\.com/[^/]+/[^/]+/[0-9a-f]{40}/')
        for url in ('https://guide-acs.m.taobao.com/gw/mtop.taobao.cloudvideo.video.query',
                    'https://poplayer.template.alibaba.com/test.json'):
            matches = [line for line in content['Script'] if not line.startswith('#') and line.strip()
                       and script_key(line)[0] == 'http-response' and re.search(script_key(line)[1], url)]
            self.assertEqual(len(matches), 1)


if __name__ == '__main__':
    unittest.main()
