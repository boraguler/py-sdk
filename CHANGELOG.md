# Changelog

## [0.1.0-b5](https://github.com/Polymarket/py-sdk/compare/polymarket-client-v0.1.0-b4...polymarket-client-v0.1.0-b5) (2026-06-09)


### Features

* **client:** support combo position lifecycle ([947efd2](https://github.com/Polymarket/py-sdk/commit/947efd2a418bd543c554b160ea25ee99a0774d2d))
* **gamma:** expose market position ids ([cb6a97d](https://github.com/Polymarket/py-sdk/commit/cb6a97d256d6e9b90e0989ef545e54d50b52480c))
* **jupyter:** notebook-friendly models ([8ee5fd3](https://github.com/Polymarket/py-sdk/commit/8ee5fd3cddbe85014c349c6801143260ac3c4141))
* **jupyter:** notebook-friendly models ([02e8574](https://github.com/Polymarket/py-sdk/commit/02e8574d470d4a8ef1fe71e664901aab3601540c))
* **rfq:** add async RFQ session ([7beaafd](https://github.com/Polymarket/py-sdk/commit/7beaafd4e454611dfad613dd9fd29a215202b3a3))
* **rfq:** distinguish combo condition ids ([9ee5b63](https://github.com/Polymarket/py-sdk/commit/9ee5b6305719d9ca5632a5f3eaa947b5c73cd1b0))


### Bug Fixes

* **client:** align market lifecycle context ([d28c211](https://github.com/Polymarket/py-sdk/commit/d28c2117bff70beebccf27582438114fde21d8a9))
* **client:** resolve market ids before redemption ([fa4fe35](https://github.com/Polymarket/py-sdk/commit/fa4fe35741d62583efbabfc422892343c41287c3))
* **clob:** align order book timestamp validation ([4be6456](https://github.com/Polymarket/py-sdk/commit/4be645646fdc41ae8661c00a9a67e0422f708b7d))
* **data:** accept global open interest rows ([1cfda2d](https://github.com/Polymarket/py-sdk/commit/1cfda2ddb0eed8bdcec94eb2023b6514735512b1))
* **data:** accept global open interest rows ([1855b7f](https://github.com/Polymarket/py-sdk/commit/1855b7f2134c4cbb041de4df78d31eb1b9fb0bf4))
* **models:** prefer ctf condition id brand ([59dbe47](https://github.com/Polymarket/py-sdk/commit/59dbe474efbdfd9b1982f7989b24f90cf9bd085d))
* **models:** validate condition ids at runtime ([7a0675d](https://github.com/Polymarket/py-sdk/commit/7a0675dded1a8d1656ee5b5d83f98f9adaf9ea93))
* **rfq:** queue duplicate pending acknowledgements ([c90fdd7](https://github.com/Polymarket/py-sdk/commit/c90fdd7dc156cc9e870f0c68a82a4d0fc477b109))
* **rfq:** use production quoter websocket ([e3f3d27](https://github.com/Polymarket/py-sdk/commit/e3f3d278164869d2916490bf69b4a9718733c40a))
* **rfq:** validate unsupported error codes ([f3a400f](https://github.com/Polymarket/py-sdk/commit/f3a400f2e893eee9b60c6fca785b87ca3004a5b8))


### Documentation

* fix stale items() reference in list_builder_trades docstring ([ad2725c](https://github.com/Polymarket/py-sdk/commit/ad2725c2dbb006efcf360d4dc6f60d5a62b8601f))

## [0.1.0-b4](https://github.com/Polymarket/py-sdk/compare/polymarket-client-v0.1.0-b3...polymarket-client-v0.1.0-b4) (2026-06-08)


### Features

* **client:** default secure clients to deposit wallet ([98ad0e9](https://github.com/Polymarket/py-sdk/commit/98ad0e995ef917d372cd025a66bccd9f59c852f4))
* **client:** default secure clients to deposit wallet ([872c5de](https://github.com/Polymarket/py-sdk/commit/872c5ded24be3cecc344492d8a01063787747d56))
* **frames:** add dataframe conversion foundation ([6d873f9](https://github.com/Polymarket/py-sdk/commit/6d873f95b0846a8694a29450bc9673ba4d70556f))
* **frames:** add dataframe conversion foundation ([e17d5bb](https://github.com/Polymarket/py-sdk/commit/e17d5bbcf08f4f6c8db12f715cefd814d8cf1c5d))


### Bug Fixes

* **frames:** emit identity columns for OrderBook sequences ([a4a9601](https://github.com/Polymarket/py-sdk/commit/a4a9601820810fbbf0f159afdc1ccf9b0c1084b3))
* **gamma:** accept event market URLs ([afcdca5](https://github.com/Polymarket/py-sdk/commit/afcdca59f1b2586c0eb235b96977427eabd203a4))
* **gamma:** accept event market URLs ([c1e9893](https://github.com/Polymarket/py-sdk/commit/c1e9893e8f35a603d2166f9bcdaa19c95bcaae10))
* **gamma:** default list_events to open events ([4f66139](https://github.com/Polymarket/py-sdk/commit/4f66139f289733ef4fdf814aac7635b03d7bbd7e))
* **gamma:** default list_events to open events ([9d92d4f](https://github.com/Polymarket/py-sdk/commit/9d92d4f0d11d8ef6af901bbaea0c145082cc712c))
* **gamma:** drop tag/series request params not honored upstream ([0e6c8f0](https://github.com/Polymarket/py-sdk/commit/0e6c8f0d11c21f93b9355b3f28623591481b37f2))
* **gamma:** drop tag/series response fields not populated upstream ([24ff6f9](https://github.com/Polymarket/py-sdk/commit/24ff6f9ce20f53b46c2e84083739ab9b8ee5bf57))
* **orders:** map unknown builder code to user input error ([67a00fb](https://github.com/Polymarket/py-sdk/commit/67a00fb3cf57b42c94ecd3d638d9104b6405930d))
* **orders:** map unknown builder code to user input error ([6cace4f](https://github.com/Polymarket/py-sdk/commit/6cace4fa7e28853d21b287eea9a2168a862bc02b))
* **pagination:** skip fetch when paginator drain limit is 0 ([8ae911c](https://github.com/Polymarket/py-sdk/commit/8ae911cafe18605b219f835a1367ebf8a42bc97d))


### Performance Improvements

* **pagination:** avoid extra fetch when drain limit hits page boundary ([ff38c8f](https://github.com/Polymarket/py-sdk/commit/ff38c8f3c05177b8a1673fcdf3dc8a81f7638970))


### Documentation

* fix get_market examples ([86c6606](https://github.com/Polymarket/py-sdk/commit/86c660685e9231bfa52d4e089e4d4a743f9f2f0f))
* fix get_market examples ([4c893c9](https://github.com/Polymarket/py-sdk/commit/4c893c9327e2b89a8c3c5e52d30f888c9b80e748))

## [0.1.0-b3](https://github.com/Polymarket/py-sdk/compare/polymarket-client-v0.1.0-b2...polymarket-client-v0.1.0-b3) (2026-05-26)


### Bug Fixes

* accept GTD expiration boundary ([3a5615f](https://github.com/Polymarket/py-sdk/commit/3a5615f279058df1ba98b77948a03ff13f0be4ab))
* accept GTD expiration boundary ([7d24c67](https://github.com/Polymarket/py-sdk/commit/7d24c67db78311d0307a56f82cc3583b5c79e17f))


### Documentation

* clarify market stream and orderbook fields ([ae23142](https://github.com/Polymarket/py-sdk/commit/ae23142e4bda6587a78433d98985a58aaaa6fdec))
* clarify market stream and orderbook fields ([cb5fc33](https://github.com/Polymarket/py-sdk/commit/cb5fc337715840e06bda436c3777b10cad0819c2))
* note GTD expiration buffer ([20c9600](https://github.com/Polymarket/py-sdk/commit/20c9600c40fe7420a2ed20da993c357db28abf56))

## [0.1.0-b2](https://github.com/Polymarket/py-sdk/compare/polymarket-client-v0.1.0-b1...polymarket-client-v0.1.0-b2) (2026-05-25)


### Bug Fixes

* hide credential validation test switch ([87af5eb](https://github.com/Polymarket/py-sdk/commit/87af5eb7dfc11b07b0abbf20d97d81a0e5e8fb2d))
* hide credential validation test switch ([3cd361a](https://github.com/Polymarket/py-sdk/commit/3cd361a47bb36e4c8415cc2552941fc25a155ede))
* update idna lockfile dependency ([60a1139](https://github.com/Polymarket/py-sdk/commit/60a11392da9950c0a6f02dd4dab6b34512c4ccdb))
* update idna lockfile dependency ([24ca1db](https://github.com/Polymarket/py-sdk/commit/24ca1db9d6654bec32ab03266dcf2a430a8221f9))


### Documentation

* add beta status badge ([1b5baf7](https://github.com/Polymarket/py-sdk/commit/1b5baf71484df9325a9184cce4ef6b7114b77908))
* add beta status badge ([8b4f99b](https://github.com/Polymarket/py-sdk/commit/8b4f99bc297b70bcee3196bc9ee860b7a732c3a5))
* complete public client docstrings ([9b1b28c](https://github.com/Polymarket/py-sdk/commit/9b1b28c0da10963cce987711379840189ff2cd47))
* improve Python SDK public docstrings ([70304f5](https://github.com/Polymarket/py-sdk/commit/70304f56aa7c105147bb4606652c1fa238ea2d3d))
* improve Python SDK public docstrings ([d9d51d1](https://github.com/Polymarket/py-sdk/commit/d9d51d1a1dc32cbb6e2eabb78e5d51f99b464413))
* polish public beta guidance ([f5185a9](https://github.com/Polymarket/py-sdk/commit/f5185a9bea7ce9de71b224093329d980d11130f8))
* polish repo for public beta ([c65142e](https://github.com/Polymarket/py-sdk/commit/c65142e9fb36b5d349d39e41890f0554349c6662))
* refresh SDK direction wording ([59c361d](https://github.com/Polymarket/py-sdk/commit/59c361d2fb2d102c87b52633f3ad6c2de013310c))

## Changelog

All notable changes to this project will be documented in this file.

This project uses Conventional Commits and release-please for release automation.
