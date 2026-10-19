# 截图 App 去广告聚合

这是给 Surge iOS 5.102.0 使用的上游聚合模块。上一版未覆盖开屏响应等规则；本版直接展开 `[Rule]`，并同步截图中找到的上游 Surge 模块。

[下载完整模块](https://raw.githubusercontent.com/mrtanshiyue/surge-sgmodule/main/PersonalAds.sgmodule) · [逐个 App 核对](截图App逐项核对.md) · [来源与验证](来源与验证.md) · [上游清单与 SHA-256](sources.json)

请只安装上方的 PersonalAds.sgmodule。仓库中的 PersonalAds-Native.sgmodule 和 PersonalAds-DomainOnly.sgmodule 是历史版本，没有同步本轮上游处理器。

目前合入 55 个截图 App 对应的上游模块，以及广告平台、YouTube、B 站和开屏补充来源。模块包含 881 行规则、112 条 URL Rewrite、81 条 Body Rewrite、310 条 Map Local、102 个有效脚本挂钩、208 个 MITM 主机名和 35 个不同的远程脚本地址。脚本挂钩按 Surge 的单响应单脚本行为核对：对同一响应重复匹配的处理器不能叠加执行，因此保留一个覆盖共享接口的处理器，同时保留不同接口、版本路径和其他独有规则；小红书按 API 版本拆分，以保留 Wool 的下载增强和 R-Store 的新增接口覆盖。高德另保留只匹配 `info.amap.com` 的 Kelee 路由，避免被仅匹配 `m数字.amap.com` 的 R-Store 路由漏掉。具体裁决见[来源与验证](来源与验证.md)。

导入后需要启用 Rewrite、MITM 和 Scripting，并安装、信任 Surge MITM 证书。到 Surge 的外部资源列表更新脚本并确认没有下载失败。20 个 GitHub 脚本已按固定提交读取并做 JavaScript 语法检查；15 个 Kelee CDN 脚本只对公开镜像副本做了语法检查，无法证明与 `kelee.one` 当前实际返回内容一致，且无法从这里验证 CDN 可达性。详细步骤见[使用说明](使用说明.md)。

上游模块还会执行原作者提供的其他处理，包括界面元素、信息流、启动页、图片水印、微信小程序和遥测端点；通用广告 SDK 规则也可能影响部分应用连接。截图中的每个 App 是否在当前版本实际消除广告，仍要用 iPhone 请求日志和界面逐项验证；本次通过了本机 Surge CLI 语法检查，没有做 iPhone 实机流量测试。

主要模块来源和快照见 `sources.json`。原作者许可和归属见 [第三方声明](THIRD_PARTY_NOTICES.txt) 与 `licenses/`。代码审查还发现个别上游脚本会改写会员状态或解除微信外链限制，这些行为不属于广告过滤，但依照此前“保留完整上游功能”的要求仍包含在上游脚本内；请把登录、付费内容和播放流程列入设备回归测试。Kelee 与 Walvez 上游没有找到仓库级许可文件，Kelee 仓库要求遵循各模块原作者的分发要求；公开再分发时仍需确认相应作者许可。
