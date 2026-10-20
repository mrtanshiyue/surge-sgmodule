# 截图 App 去广告聚合

这是给 Surge iOS 5.102.0 使用的上游聚合模块。上一版未覆盖开屏响应等规则；本版直接展开 `[Rule]`，并同步截图中找到的上游 Surge 模块。

[下载完整模块](https://raw.githubusercontent.com/mrtanshiyue/surge-sgmodule/main/PersonalAds.sgmodule) · [逐个 App 核对](截图App逐项核对.md) · [来源与验证](来源与验证.md) · [上游清单与 SHA-256](sources.json)

请只安装上方的 PersonalAds.sgmodule。仓库中的 PersonalAds-Native.sgmodule 和 PersonalAds-DomainOnly.sgmodule 是历史版本，没有同步本轮上游处理器。

目前合入 55 个截图 App 对应的上游模块，以及广告平台、YouTube、B 站和开屏补充来源。模块包含 873 行规则、112 条 URL Rewrite、82 条 Body Rewrite、310 条 Map Local、102 个有效脚本挂钩、208 个 MITM 主机名和 35 个不同的远程脚本地址。脚本挂钩按 Surge 的单响应单脚本行为核对：共享接口只保留一条覆盖处理器，独有接口和版本路径继续保留。京东与淘宝主开屏接口保留真实响应，由 R-Store 上游脚本清理，避免空的 Map Local 响应挡住清理；高德旧版失效脚本已由 R-Store 脚本和 Surge JQ 规则覆盖；B 站旧版失效脚本已换成 Kokoryh/Sparkle 的固定版本脚本，并仅接管 R-Store 未覆盖的 Protobuf 接口，同时保留评论与投稿赞助过滤及 gRPC 搜索默认词接口。抖音 HTTPDNS 主机 `dig.bdurl.net` 已从拒绝规则中排除，避免影响视频域名解析。具体裁决见[来源与验证](来源与验证.md)。

这次全面复核还修复了会让规则“存在但走不到”的冲突：把 58 个仍在用、但原来标成 `max-size=0` 的响应钩子改为 Surge 的无限制值 `-1`；放通网易云 `ipv4` 响应处理；清除拼多多、猫眼和同花顺的相互遮蔽规则。`-1` 会完整缓冲匹配的响应体，iOS 上可能增加内存使用，特别是 Protobuf/信息流响应；设备测试需留意 Surge 进程稳定性。

导入后需要启用 Rewrite、MITM 和 Scripting，并安装、信任 Surge MITM 证书。到 Surge 的外部资源列表更新脚本并确认没有下载失败。22 个 GitHub 脚本已按固定提交读取并做 JavaScript 语法检查；13 个 Kelee CDN 脚本只对公开镜像副本做了语法检查，无法证明与 `kelee.one` 当前实际返回内容一致。详细步骤见[使用说明](使用说明.md)。

上游模块还会执行原作者提供的其他处理，包括界面元素、信息流、启动页、图片水印、微信小程序和遥测端点；通用广告 SDK 规则也可能影响部分应用连接。截图中的每个 App 是否在当前版本实际消除广告，仍要用 iPhone 请求日志和界面逐项验证；本次通过了本机 Surge CLI 语法检查，没有做 iPhone 实机流量测试。

主要模块来源和快照见 `sources.json`。原作者许可和归属见 [第三方声明](THIRD_PARTY_NOTICES.txt) 与 `licenses/`。代码审查还发现个别上游脚本会改写会员状态或解除微信外链限制，这些行为不属于广告过滤，但依照此前“保留完整上游功能”的要求仍包含在上游脚本内；请把登录、付费内容和播放流程列入设备回归测试。Kelee 与 Walvez 上游没有找到仓库级许可文件，Kelee 仓库要求遵循各模块原作者的分发要求；公开再分发时仍需确认相应作者许可。
