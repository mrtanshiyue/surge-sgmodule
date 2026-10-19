# Personal App Ad Filter for Surge

A Surge iOS ad-filtering module set assembled for the apps visible in the provided home-screen screenshots. Choose one module only; the enhanced version has the widest coverage, while the native version avoids remote scripts.

## Install one module

- [Enhanced — native rules plus YouTube, Bilibili, and Meituan Waimai scripts](https://raw.githubusercontent.com/mrtanshiyue/surge-sgmodule/main/PersonalAds.sgmodule)
- [Native — no remote executable scripts](https://raw.githubusercontent.com/mrtanshiyue/surge-sgmodule/main/PersonalAds-Native.sgmodule)
- [Domain only — does not require MITM, with limited coverage; does not remove the JD splash API response](https://raw.githubusercontent.com/mrtanshiyue/surge-sgmodule/main/PersonalAds-DomainOnly.sgmodule)

In Surge, add the chosen module from its URL. The enhanced and native variants require Surge iOS 5.23.0 or later, Rewrite, and MITM; the enhanced variant also requires Scripting. Read [使用说明.md](使用说明.md) before enabling it, especially the per-app coverage and known limitations. The full screenshot-by-screenshot audit is in [截图App逐项核对.md](截图App逐项核对.md). Source attribution and validation details are in [来源与验证.md](来源与验证.md) and [THIRD_PARTY_NOTICES.txt](THIRD_PARTY_NOTICES.txt).

The enhanced and native variants include JD `start` response editing and a targeted `getSplash` endpoint block. Both require a trusted Surge CA and MITM for `api.m.jd.com`; the domain-only variant cannot remove these API-delivered splash ads.

Red Fruit Short Drama has 18 exact host rules: six ad-service hosts, nine `reading-ad` video hosts, and three ad-sign image hosts. The source project reports a real-device Android capture; these rules have not been verified against Red Fruit on iOS. They are global host rules, so other apps using the same hosts are affected too. The rules leave the main `qznovelvod.com` video CDN and broad ByteDance domains unblocked; they cannot swipe past locally rendered full-screen ads or remove ads embedded in content.

Version 0.3.2 adds narrowly selected upstream rules for Amazon, Alipay, Amap, Meituan, Tonghuashun, Xiaohongshu, JD, and Taobao. The enhanced module has four remote script URLs across five hooks. It adds a reviewed Blackmatrix7 Meituan Waimai startup-response hook; the native variant contains all the same native rules and no executable scripts.

Surge Mac's CLI accepts the module contents when checked inside a complete profile; this does not test iOS behavior or guarantee every ad is removed. The enhanced YouTube initialization hook may send some playback-init requests to Maasea's third-party Worker; use the native variant if that is not acceptable.
