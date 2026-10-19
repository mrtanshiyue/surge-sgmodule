# Personal App Ad Filter for Surge

A Surge iOS ad-filtering module set assembled for the apps visible in the provided home-screen screenshots. Choose one module only; the enhanced version has the widest coverage, while the native version avoids remote scripts.

## Install one module

- [Enhanced — native rules plus YouTube and Bilibili scripts](https://raw.githubusercontent.com/mrtanshiyue/surge-sgmodule/main/PersonalAds.sgmodule)
- [Native — no remote executable scripts](https://raw.githubusercontent.com/mrtanshiyue/surge-sgmodule/main/PersonalAds-Native.sgmodule)
- [Domain only — does not require MITM, with limited coverage](https://raw.githubusercontent.com/mrtanshiyue/surge-sgmodule/main/PersonalAds-DomainOnly.sgmodule)

In Surge, add the chosen module from its URL. The enhanced and native variants require Surge iOS 5.23.0 or later, Rewrite, and MITM; the enhanced variant also requires Scripting. Read [使用说明.md](使用说明.md) before enabling it, especially the per-app coverage and known limitations. Source attribution and validation details are in [来源与验证.md](来源与验证.md) and [THIRD_PARTY_NOTICES.txt](THIRD_PARTY_NOTICES.txt).

Red Fruit Short Drama has a limited addition: exact blocking for three ByteDance ad-sign image hosts. This is a global host rule, not an app-process rule; it may block those ad assets in other apps too. It cannot swipe past full-screen/video ads or remove ads embedded in content, and Red Fruit iOS traffic has not been tested.

This is a statically checked update, not a guarantee that every ad is removed. Surge's own parser and the target apps on an iPhone were not available for testing. The enhanced YouTube initialization hook may send some playback-init requests to Maasea's third-party Worker; use the native variant if that is not acceptable.
