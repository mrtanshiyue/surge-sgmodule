# Personal App Ad Filter for Surge

A Surge iOS ad-filtering module set assembled for the apps visible in the provided home-screen screenshots. Choose one module only; the enhanced version has the widest coverage, while the native version avoids remote scripts.

## Install one module

- [Enhanced — native rules plus YouTube and Bilibili scripts](https://raw.githubusercontent.com/mrtanshiyue/surge-sgmodule/main/PersonalAds.sgmodule)
- [Native — no remote executable scripts](https://raw.githubusercontent.com/mrtanshiyue/surge-sgmodule/main/PersonalAds-Native.sgmodule)
- [Domain only — does not require MITM, with limited coverage](https://raw.githubusercontent.com/mrtanshiyue/surge-sgmodule/main/PersonalAds-DomainOnly.sgmodule)

In Surge, add the chosen module from its URL. The enhanced and native variants require Surge iOS 5.23.0 or later, Rewrite, and MITM; the enhanced variant also requires Scripting. Read [使用说明.md](使用说明.md) before enabling it, especially the per-app coverage and known limitations. Source attribution and validation details are in [来源与验证.md](来源与验证.md) and [THIRD_PARTY_NOTICES.txt](THIRD_PARTY_NOTICES.txt).

Red Fruit Short Drama has 18 exact host rules: six ad-service hosts, nine `reading-ad` video hosts, and three ad-sign image hosts. The source project reports a real-device Android capture; these rules have not been verified against Red Fruit on iOS. They are global host rules, so other apps using the same hosts are affected too. The rules leave the main `qznovelvod.com` video CDN and broad ByteDance domains unblocked; they cannot swipe past locally rendered full-screen ads or remove ads embedded in content.

This is a statically checked update, not a guarantee that every ad is removed. Surge's own parser and the target apps on an iPhone were not available for testing. The enhanced YouTube initialization hook may send some playback-init requests to Maasea's third-party Worker; use the native variant if that is not acceptable.
