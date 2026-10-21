# 截图 App 去广告模块

[安装 Surge 模块](https://raw.githubusercontent.com/mrtanshiyue/surge-sgmodule/main/PersonalAds.sgmodule) · [查看上游](https://github.com/fmz200/wool_scripts/blob/main/Surge/module/blockAds.module)

模块直接筛选 Wool Scripts 的 `blockAds.module`，只保留与截图中 App 对应的上游分组：Amazon、Apple、Facebook/Instagram、Google、YouTube、WPS、哔哩哔哩、抖音、番茄小说/红果短剧、阿里巴巴、淘宝、京东、拼多多、美团、米家/小爱音箱、小米、萤石、网易云音乐、QQ 音乐、喜马拉雅、优酷、淘票票、同花顺、杭州市民、山姆会员商店、中国电信、钉钉、腾讯系和腾讯游戏。

截图里没有对应上游分组的 App 不会自创规则。通用“广告联盟”及其他 App 的分组已剔除。`dig.bdurl.net` 按设备实测反馈单独排除，避免抖音精选视频无法播放。

Surge 的域名规则按网络请求匹配，不能仅靠模块标题限制到某个 App；如果截图外的 App 共用这些域名，仍可能受到影响。已筛选的应用规则和 MITM 主机均来自上游分组，不代表每个广告都能被网络规则移除。

仓库每周检查上游 `blockAds.module`，有变化时自动更新模块和 `sources.json`；也可在 GitHub Actions 手动运行。若上游删除或重命名白名单分组，构建会失败而保留当前模块，避免静默漏规则。

Surge 中安装模块后，按规则启用 Rewrite、MITM 和 Scripting，并信任 MITM 证书。上游远程脚本仍通过其原始 URL 加载。

本模块及生成脚本依 GPL-3.0 发行；上游归属和改动记录见 [THIRD_PARTY_NOTICES.txt](THIRD_PARTY_NOTICES.txt)。
