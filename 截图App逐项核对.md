# 截图 App 上游覆盖核对

核对范围是截图中能辨认的 App 图标。文件夹图标里的小图标无法可靠辨认，所以没有按猜测补规则。表中“已合入”表示上游模块本身已完整纳入聚合，不代表已在这台 iPhone 上验证所有广告均消失。

## 已合入完整上游模块

| 截图 App | 已合入上游 | 模块覆盖范围 |
|---|---|---|
| 京东 | Kelee、Wool、R-Store、Walvez | 启动/首页/弹窗/推荐等接口、域名规则、脚本和 Map Local；`start` 开屏由 R-Store 清理真实响应，不用 Walvez 空响应覆盖 |
| 淘宝 | Kelee、Wool、R-Store、Walvez | 开屏、弹窗、首页和推广接口，以及域名、Map Local、脚本；主开屏由 R-Store 清理真实响应 |
| 阿里巴巴 1688 | Wool、Walvez | 启动与广告接口规则 |
| 拼多多、拼多多商家版 | Kelee、Wool、R-Store、Walvez | 开屏、营销、首页/推荐响应、域名规则与本地响应 |
| 美团 | Wool、R-Store、Kelee 广告平台、Walvez | 推广图片/接口、首页和启动接口处理 |
| 美团外卖 | Wool、R-Store、Walvez、Blackmatrix7 | 开屏、图片素材和启动响应脚本 |
| 亚马逊购物 | Wool、R-Store | 弹窗/推荐配置与广告域名处理 |
| 支付宝 | R-Store | 上游广告域名规则 |
| 山姆会员商店 | Wool、R-Store | 开屏、广告分组和本地响应 |
| 哔哩哔哩 | Kelee、R-Store、Kokoryh/Sparkle、app2smile、Blackmatrix7 | 开屏、信息流、搜索、详情等响应脚本及规则；共享 Protobuf 响应由 R-Store 处理，Sparkle 补足独有播放、评论和投稿赞助过滤接口 |
| YouTube | Maasea、app2smile | Maasea 完整规则及 3 个请求/响应脚本；它的响应脚本覆盖 app2smile 的 browse/next 共享路径 |
| 优酷 | Kelee、Wool、R-Store | 广告域名、播放/首页响应和脚本 |
| 网易云音乐 | Kelee、Wool、R-Store | 开屏、首页、发现、评论、推荐和广告接口 |
| QQ 音乐 | Kelee、Wool、R-Store | 广告域名、接口与上游重写 |
| 喜马拉雅 | Kelee、R-Store | 广告、开屏、推荐/内容响应 |
| 红果短剧 | Kelee 番茄小说、Wool FanQieNovel、R-Store Fanqie，加既有精确主机规则 | 按你给出的“番茄小说模块”线索覆盖；没有把 `zijieapi.com`、`snssdk.com` 或 `qznovelvod.com` 整个主域加入拦截 |
| 高德地图 | R-Store、Surge JQ | 开屏、首页、搜索、路线与附近页推广字段；截图中失效的 Kelee 脚本已移除 |
| 米家 | Wool、R-Store | 开屏、首页横幅与推广接口 |
| 小米音箱 | Kelee | 广告接口本地响应 |
| 萤石云视频 | Kelee | 开屏与广告接口处理 |
| 小红书 | Kelee、Wool、R-Store | 开屏、信息流、搜索、弹窗、详情响应、图片/视频功能和上游脚本 |
| 微信 | Kelee 公众号、小程序模块；R-Store 微信模块；Walvez 相关组 | 公众号广告、小程序配置及相关接口 |
| 钉钉 | Wool | 完整上游模块 |
| 中国电信 | Wool、R-Store | 开屏、推广接口与域名规则 |
| WPS Office | Wool、R-Store | 启动/活动/商店窗口接口 |
| 淘票票 | Kelee | 完整上游模块 |
| 同花顺 | R-Store、Walvez | 广告/推荐接口 |
| 杭州市民卡 | Wool | 完整上游模块和响应映射 |
| 小翼管家 | Walvez | 上游开屏/配置接口规则 |

此外，纳入 Kelee 广告平台拦截器和 app2smile 广告联盟规则，覆盖穿山甲、腾讯优量汇、快手等通用广告 SDK。该组会影响所有经过这些 SDK 的 App，并非单一图标专用规则。重复的响应脚本按 Surge 每个响应只运行一个 http-response 脚本的行为裁决；各自独有路径及非脚本规则保留，详细分流见来源与验证。

## 截图中未找到专属完整去广告上游模块

天气、查找、文件、无边记、健身、Watch、Gmail、ChatGPT、Surge、Authenticator、密码、Secure SignIn、星巴克、Shopify、Tesla、蔚来、Apple Store、开心消消乐、安居客、Gemini、Linx Camera、Leica LUX、GitHub、抖音、抖音精选、QMT、领星 ERP、灯塔专业版、Panasonic Smart China、Voice、Quantumult X、小门童、手记、AutoSleep、Apple 支持、Loon、Folo、Reko、黑鲨装备箱、HeartWatch、Me、TP-LINK、条码扫描宝、Google Maps、Speedtest、预览、Epson SmartPanel、瞬感宝、游戏、豆包、速度表、像素蛋糕、中信证券、Chrome、熊掌记、Relay、一点万象、王者荣耀、国家网络身份认证、企业手机银行、Manus、Claude、Photos Mobile、Telegram、Instagram。

这些 App 仍会经过通用广告 SDK 规则；本包没有为它们自创未经上游验证的专属域名或响应修改。截图里的“旅行”“财务”“实用工具”等文件夹内容不可辨认，也未逐项推断。

## 红果短剧说明

番茄小说模块是有依据的起点，但红果短剧与番茄小说接口并不保证完全相同。已同步三套当前可用的番茄/FanQie Surge 上游模块，并保留精确广告主机。奖励视频广告、服务端内容插入和广告素材复用业务域名时，网络模块无法承诺全部消除。

## 需要用户设备日志才能继续核对的内容

本地 CLI 只能确认 Surge 能解析配置，不能证明每个 App 当前版本实际请求了这些接口。要逐个确认剩余广告，需要相应 App 版本、广告出现步骤和 Surge 请求日志；这次没有在 iPhone 上抓取这些请求。
