# 截图 App 去广告综合模块（Surge iOS 6）

[安装模块](https://raw.githubusercontent.com/mrtanshiyue/surge-sgmodule/main/PersonalAds.sgmodule) · [来源记录](sources.json) · [合并脚本](scripts/merge_modules.py)

## 来源与更新

模块保留截图中可辨认的 App 及共享广告联盟规则；小红书单独排除。秋风来源中能按奶思上游分组确定属于其他 App 的规则会移除，专用脚本和未分组的重写按截图 App 与共享广告 SDK 筛选，无法明确归属的域名拦截规则保留。截图文件夹未展开，无法据此确认其中全部 App。

模块先采用 [Feng-Feng1/surge](https://github.com/Feng-Feng1/surge) 的秋风奶思综合规则，再补充 [fmz200/wool_scripts](https://github.com/fmz200/wool_scripts) 中截图 App 对应的规则。相同脚本类型及完全相同的 URL 匹配表达式只保留前者；其他规则按来源顺序保留，表达式不同但匹配范围重叠时不保证自动识别。

自动筛选依赖上游分组与已识别的 App 标识，未标注的域名拦截规则和外部广告规则集仍可能包含其他 App 的域名。GitHub Actions 每天检查上游并在保护检查通过后重建模块。构建时将 Feng 的仓库内资源 URL 固定到此次源文件提交；其他上游脚本仍可能使用各自的动态 URL。来源版本和输出 SHA-256 记录于 sources.json。若上游格式或参数发生无法识别的变化，构建会失败并保留上次版本。

## 用户指定的保护范围

- 不纳入小红书专属脚本、重写或 MITM 主机；对 Feng 的外部拒绝规则集增加小红书域名排除。共享广告网络仍可能命中多个 App。
- 不拦截 `dig.bdurl.net`，避免此前抖音精选播放问题；外部拒绝规则集亦包含此例外。
- 外部拒绝规则集排除 `v*-reading-ad.qznovelvod.com`，原来 9 条候选规则不加入。其他已启用模块仍可能拦截这些域名，尤其是独立红果模块。
- 未纳入小象助力车专属模拟响应，以免未经验证地隐藏骑行卡或影响充值。
- 未纳入截图中没有的 Spotify 专属 `Spotify.Crack.Dev.js`。网易云音乐 `wyres.js` 按上游纳入，可能改写会员及页面信息；其上游未解析的首页参数交由脚本默认值处理，导航参数按上游默认值转换。

## 规则整理

- 连续且策略、扩展匹配设置一致的域名规则保留原顺序，拆入仓库 `rules/` 的远程 RULE-SET；文件名含内容摘要，新旧版本可分别缓存。模块更新后 Surge 需能下载这些文件。
- B 站会员状态、账号菜单及首页标签重排等响应改写按上游保留；会员状态改写只影响客户端返回数据，不等于开通服务端权益。其他第三方脚本仍按上游更新，其实际行为可能随上游变化。
- 远程脚本沿用上游地址；响应改写直接保留在模块内。远程规则文件由自动更新工作流一并生成和提交。

## 微信公众号补充

来自 [Walvez/surge-startup-ads](https://github.com/Walvez/surge-startup-ads) 的两条规则针对公众号文章广告接口及商品推广接口；启用需对 `mp.weixin.qq.com` 使用 MITM。它们不等于适用于所有微信小程序，也不能保证清除朋友圈广告。上游改变这两条规则时自动同步会停止，等待人工复核。

## Surge 6 设置

模块要求 Core 6.11.0 或更新版本（`CORE_VERSION>=6011000`），包含 Rule、URL/Header/Body Rewrite、Map Local、Script 和 MITM。部分广告处理需要在 Surge 中开启 Rewrite、MITM、Scripting 并信任 MITM 证书。B 站 protobuf 脚本采用 JSON 对象参数，并默认保留创作者赞助片段。

安装更新后应避免同时启用旧的秋风奶思综合模块，否则同一请求仍可能命中重复脚本。若发现登录、播放、消息、支付或内容加载异常，先停用本模块并重新打开受影响的 App；可从 GitHub 历史提交恢复先前版本。

## 版权与限制

详细来源及第三方说明见 [THIRD_PARTY_NOTICES.txt](THIRD_PARTY_NOTICES.txt)。上游 Feng 仓库未标明整个综合模块的许可证，不能从单个第三方脚本的许可证推定整个模块的授权范围。

合并和规则匹配检查不等于逐个 App 的功能验证；广告能否去除取决于 App 版本、接口和缓存。
