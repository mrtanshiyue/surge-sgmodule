# 截图 App 去广告综合模块（Surge iOS 6）

[安装 Surge 模块](https://raw.githubusercontent.com/mrtanshiyue/surge-sgmodule/main/PersonalAds.sgmodule) · [查看生成器](scripts/build_personal_ads.py) · [规则来源记录](sources.json)

## 收录范围

模块按截图中可识别且有可用 Surge 规则的 App 选取上游分组，包含：

- Amazon、Apple、Google、YouTube、Instagram/Facebook；
- 京东、淘宝、拼多多、阿里巴巴/1688、美团、山姆、淘票票；
- 哔哩哔哩、抖音/抖音精选相关字节规则、番茄小说、优酷；
- 网易云音乐、QQ 音乐、喜马拉雅；
- 高德地图、同花顺、杭州市民卡；
- WPS、钉钉、腾讯系/腾讯游戏、中国电信；
- 米家、小米、小爱音箱、萤石。

模块保留 Wool Scripts 的通用广告联盟规则。Surge 按域名和 URL 匹配，通用广告域可能被多个 App 共用，因此规则也可能影响截图外的 App。规则是否能去掉某个广告，仍取决于 App 当前接口和缓存。

**小红书不在本模块中**：没有小红书专属域名、MITM 主机或重写规则；你可继续使用独立模块。通用广告联盟规则仍可能命中共享的广告域名。

## 未加入的截图 App 规则

在本轮检索的维护中来源里，没有找到适合直接加入且范围明确的 Starbucks、Shopify、安居客、Tesla、蔚来、开心消消乐、豆包等 Surge 专属广告规则。银行、证券、支付及系统工具也没有凭域名猜测添加拦截项。

红果短剧与番茄小说不能视为同一个专属规则组。已找到一组精确的红果/番茄章节广告视频主机，但它们用于“看广告解锁章节”；拦截会使这类解锁不可用，因此暂未加入主模块。候选来源和 9 条候选规则记在 sources.json，确认后再纳入。

## Surge 6 写法与参数

本模块使用 Surge 原生 .sgmodule 配置语法、#!requirement=CORE_VERSION>=20、模块参数表和 [MITM] 的 %APPEND% 写法。Core 20 对应 Body Rewrite 支持；参数为选中上游脚本提供有效默认值，避免遗留未绑定占位符。

- sponsorBlock=false：保留 B 站视频内创作者赞助片段；
- logLevel=error：减少脚本日志；
- 网易云音乐参数采用上游默认值。

详见 [Surge Modules 文档](https://manual.nssurge.com/profile/module.html)、[Requirement 文档](https://manual.nssurge.com/profile/requirement.html)、[MITM 文档](https://manual.nssurge.com/http/mitm.html) 和 [Scripting 文档](https://manual.nssurge.com/scripting/overview.html)。

## 使用与回退

需要在 Surge 中启用模块使用到的 Rewrite、MITM 和 Scripting，并安装、信任 MITM 证书。模块只把所选上游分组标记的主机追加到 MITM；仍可能与证书锁定的 App 或接口版本不兼容。

如登录、播放、评论、支付或内容加载异常，先停用本模块并重开 App。已知 dig.bdurl.net 会影响抖音精选视频播放，因此未收录。

## 更新与来源

仓库按周检查并从 [fmz200/wool_scripts](https://github.com/fmz200/wool_scripts) 的 Surge blockAds.module 生成规则；当前规则快照为 [2026-10-30 上游提交](https://github.com/fmz200/wool_scripts/commit/4b7830670baf235ed945085cb926dc499cf619e0)。脚本、参数源、选中分组及 SHA-256 记录在 sources.json。

上游归属、改动和许可证见 [THIRD_PARTY_NOTICES.txt](THIRD_PARTY_NOTICES.txt)。仓库没有把模块自动安装到 iPhone。
