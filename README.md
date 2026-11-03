# 截图 App 去广告模块

[安装 Surge 模块](https://raw.githubusercontent.com/mrtanshiyue/surge-sgmodule/main/PersonalAds.sgmodule) · [查看上游模块](https://github.com/fmz200/wool_scripts/blob/main/Surge/module/blockAds.module)

模块从 Wool Scripts 当前的 Surge `blockAds.module` 中筛选与截图 App 对应的分组：Amazon、Apple、Facebook/Instagram、Google、YouTube、WPS、哔哩哔哩、抖音、番茄小说（不含红果短剧专属规则）、阿里巴巴、淘宝、京东、拼多多、美团、米家/小爱音箱、小米、萤石、网易云音乐、QQ 音乐、喜马拉雅、优酷、淘票票、同花顺、高德地图、杭州市民、山姆会员商店、中国电信、钉钉、腾讯系和腾讯游戏。

小红书额外只拦截上游列出的 4 个独立广告素材域名：`ads-img-qc.xhscdn.com`、`ads-video-al.xhscdn.com`、`ads-video-qc.xhscdn.com`、`t-ads.xiaohongshu.com`。没有导入上游小红书组中的全域 QUIC 阻断、MITM 主机或响应脚本，以缩小对登录、信息流和视频的影响。小红书信息流内嵌广告因此可能仍会出现。

模块保留上游“广告联盟”通用规则。Surge 按域名和 URL 匹配，不能仅按 App 隔离；这类通用域名规则可能影响截图外的 App。没有上游专属分组的 App 不会凭猜测添加拦截规则，也不保证这些 App 的广告会被移除。

`dig.bdurl.net` 按设备播放反馈单独排除，避免抖音精选视频无法播放。仓库每周检查上游模块，有变化时自动生成并提交；若上游白名单分组消失或重命名，构建会失败并保留当前版本。

模块使用到的 MITM 主机和远程脚本来自上游分组。安装后需在 Surge 中启用模块所需的 Rewrite、MITM 和 Scripting，并信任 MITM 证书。未将此模块自动安装到手机。

本模块及生成脚本依 GPL-3.0 发行；上游归属和改动记录见 [THIRD_PARTY_NOTICES.txt](THIRD_PARTY_NOTICES.txt)。
