# Changelog

## [1.85.6](https://github.com/openfoodfacts/robotoff/compare/v1.85.5...v1.85.6) (2026-02-23)


### Bug Fixes

* centralize taxonomy download ([#1857](https://github.com/openfoodfacts/robotoff/issues/1857)) ([768848d](https://github.com/openfoodfacts/robotoff/commit/768848d56be9f9ad352af1df0d6bf4f540ec7275))

## [1.85.5](https://github.com/openfoodfacts/robotoff/compare/v1.85.4...v1.85.5) (2026-02-23)


### Bug Fixes

* don't crash in fail_taxonomy if PO server is not responding ([#1856](https://github.com/openfoodfacts/robotoff/issues/1856)) ([3dab674](https://github.com/openfoodfacts/robotoff/commit/3dab674315d58e8a29c9cc8f2f01d192a34fefd8))
* fix bug in taxonomy.py ([c257711](https://github.com/openfoodfacts/robotoff/commit/c25771181b9697aabba56f69d875edc6e870e81b))


### Technical

* fix container name in docker-compose.yml ([f27c139](https://github.com/openfoodfacts/robotoff/commit/f27c139968d9f91de37f220418fce475c8d3b384))
* increase number of product workers to 6 ([#1854](https://github.com/openfoodfacts/robotoff/issues/1854)) ([fe82e52](https://github.com/openfoodfacts/robotoff/commit/fe82e52958d991a4d9856536db708f5b6f68a925))

## [1.85.4](https://github.com/openfoodfacts/robotoff/compare/v1.85.3...v1.85.4) (2026-02-19)


### Technical

* **deps:** upgrade openfoodfacts lib ([#1852](https://github.com/openfoodfacts/robotoff/issues/1852)) ([d17909d](https://github.com/openfoodfacts/robotoff/commit/d17909dc76a8bbe94702be0cc5b2c64de9d3d0af))

## [1.85.3](https://github.com/openfoodfacts/robotoff/compare/v1.85.2...v1.85.3) (2026-02-17)


### Bug Fixes

* upgrade buildx ([bb77914](https://github.com/openfoodfacts/robotoff/commit/bb77914a2df33d16462c00fe79517a266a449141))


### Technical

* **deps-dev:** bump cryptography from 45.0.3 to 46.0.5 ([#1846](https://github.com/openfoodfacts/robotoff/issues/1846)) ([55ffec1](https://github.com/openfoodfacts/robotoff/commit/55ffec1a3eddc9d885959e6104927221c31cfbaf))
* **deps:** ugprade triton-client and protobuf ([#1850](https://github.com/openfoodfacts/robotoff/issues/1850)) ([265b409](https://github.com/openfoodfacts/robotoff/commit/265b409a0b8f46f6aa55a341525e06bba140dfa0))
* **nutrition:** support new nutrition schema ([#1838](https://github.com/openfoodfacts/robotoff/issues/1838)) ([6119b8c](https://github.com/openfoodfacts/robotoff/commit/6119b8c1d94d9bfcddd12c3393128b4ac7d07156))
* switch from poetry to uv ([#1849](https://github.com/openfoodfacts/robotoff/issues/1849)) ([e9e56e9](https://github.com/openfoodfacts/robotoff/commit/e9e56e99e5762bdb31ae799c6dba22570f439ea9))

## [1.85.2](https://github.com/openfoodfacts/robotoff/compare/v1.85.1...v1.85.2) (2026-02-05)


### Bug Fixes

* don't run category prediction with new nutrition schema ([#1844](https://github.com/openfoodfacts/robotoff/issues/1844)) ([7d7c868](https://github.com/openfoodfacts/robotoff/commit/7d7c868db91de0f53718021408bce80d3a514fa7))
* fix issue with NMS ([#1841](https://github.com/openfoodfacts/robotoff/issues/1841)) ([af6116d](https://github.com/openfoodfacts/robotoff/commit/af6116d90e624602a8dd7cca177cdcc5cc986dda))
* Greek translations in robotoff.po ([897774d](https://github.com/openfoodfacts/robotoff/commit/897774d01d176214945aa316dbf98b9996c84b80))
* **openapi:** Fix logo_id path param in /ann/search/{logo_id} ([#1840](https://github.com/openfoodfacts/robotoff/issues/1840)) ([2a1a191](https://github.com/openfoodfacts/robotoff/commit/2a1a191be6c2d5abb0bb7a7e91cdbe3cf2aa33ab))


### Technical

* add documentation on llm-image-extraction dataset type ([#1835](https://github.com/openfoodfacts/robotoff/issues/1835)) ([f68cfd8](https://github.com/openfoodfacts/robotoff/commit/f68cfd8f00a957314aa5f4b0075467c61b3c317c))
* add reference on object detection datasets stored on HF ([#1822](https://github.com/openfoodfacts/robotoff/issues/1822)) ([720606c](https://github.com/openfoodfacts/robotoff/commit/720606c63a88e56f187f3a67bec0275b7b2dbf30))
* avoid crashes when the new nutrition schema is deployed ([#1837](https://github.com/openfoodfacts/robotoff/issues/1837)) ([5af00f1](https://github.com/openfoodfacts/robotoff/commit/5af00f1491879db27c6b6597dc589b47df9788c8))
* **deps-dev:** bump virtualenv from 20.31.2 to 20.36.1 ([#1829](https://github.com/openfoodfacts/robotoff/issues/1829)) ([171c5e5](https://github.com/openfoodfacts/robotoff/commit/171c5e57f4e035a96158ef1370f780a14667a29b))
* **deps-dev:** bump werkzeug from 3.1.3 to 3.1.4 ([#1815](https://github.com/openfoodfacts/robotoff/issues/1815)) ([edbca02](https://github.com/openfoodfacts/robotoff/commit/edbca02ceb83aa453a2f879309ddb877b54190be))
* **deps-dev:** bump werkzeug from 3.1.4 to 3.1.5 ([#1828](https://github.com/openfoodfacts/robotoff/issues/1828)) ([8916437](https://github.com/openfoodfacts/robotoff/commit/8916437ca596aff73189ece760592d5868ad4049))
* **deps:** bump filelock from 3.18.0 to 3.20.1 ([#1824](https://github.com/openfoodfacts/robotoff/issues/1824)) ([92c685b](https://github.com/openfoodfacts/robotoff/commit/92c685b9a4f460aa7a278fb615a1ac856305f2ce))
* **deps:** bump filelock from 3.20.1 to 3.20.3 ([#1830](https://github.com/openfoodfacts/robotoff/issues/1830)) ([32b3a22](https://github.com/openfoodfacts/robotoff/commit/32b3a229d952501d1e57472cc332163b37b5d75b))
* **deps:** bump fonttools from 4.58.1 to 4.61.0 ([#1814](https://github.com/openfoodfacts/robotoff/issues/1814)) ([a2d9f9e](https://github.com/openfoodfacts/robotoff/commit/a2d9f9e4b4aa4eb2931d673c0cfb4cb197b80d58))
* **deps:** bump pyasn1 from 0.6.1 to 0.6.2 ([#1831](https://github.com/openfoodfacts/robotoff/issues/1831)) ([6491348](https://github.com/openfoodfacts/robotoff/commit/64913489117fa6863206bfe6b76102a62a93ec10))
* **deps:** bump the all-actions group with 4 updates ([#1825](https://github.com/openfoodfacts/robotoff/issues/1825)) ([a08c5ec](https://github.com/openfoodfacts/robotoff/commit/a08c5ec406a10bbf3826bb149ca49d09a1fe089e))
* **deps:** bump transformers from 4.50.3 to 4.53.0 ([#1768](https://github.com/openfoodfacts/robotoff/issues/1768)) ([9cb7d26](https://github.com/openfoodfacts/robotoff/commit/9cb7d26782c8695474c965c44a222793a675119e))
* **deps:** bump urllib3 from 2.5.0 to 2.6.0 ([#1821](https://github.com/openfoodfacts/robotoff/issues/1821)) ([08fa1e2](https://github.com/openfoodfacts/robotoff/commit/08fa1e2331e145383408874833fe86d575fa17c8))
* **deps:** bump urllib3 from 2.6.0 to 2.6.3 ([#1827](https://github.com/openfoodfacts/robotoff/issues/1827)) ([55344dc](https://github.com/openfoodfacts/robotoff/commit/55344dc24fb36ce1cf9ce265066fe225e3a09ac5))
* fix formatting ([6d50d4e](https://github.com/openfoodfacts/robotoff/commit/6d50d4e336227a1fb6a7fb3a735b221cc4327d1e))
* update meeting frequency to first Tuesday of each month ([b2fb3eb](https://github.com/openfoodfacts/robotoff/commit/b2fb3eb10746efbb0409fa209f776b7dd88f8cc5))

## [1.85.1](https://github.com/openfoodfacts/robotoff/compare/v1.85.0...v1.85.1) (2025-12-08)


### Bug Fixes

* add field `with_image` to ProductInsight table ([#1820](https://github.com/openfoodfacts/robotoff/issues/1820)) ([f219afb](https://github.com/openfoodfacts/robotoff/commit/f219afbb31ba16cd58a45e02eac2e6e1af2f0724))
* Typo in the markdown installation ([#1817](https://github.com/openfoodfacts/robotoff/issues/1817)) ([d8b4886](https://github.com/openfoodfacts/robotoff/commit/d8b48863cda75a0258c963bd92947ca7123348df))
* validate bounding box before cv2.resize in save_logo_embeddings ([#1812](https://github.com/openfoodfacts/robotoff/issues/1812)) ([5f0930e](https://github.com/openfoodfacts/robotoff/commit/5f0930e01e21638b1f160884f510da7ca3e75586)), closes [#1810](https://github.com/openfoodfacts/robotoff/issues/1810)
* validate energy units only used for energy entities in nutrient extraction ([#1813](https://github.com/openfoodfacts/robotoff/issues/1813)) ([4a4d8c9](https://github.com/openfoodfacts/robotoff/commit/4a4d8c91fc36acf7a219b12596d172a73acd6d9d)), closes [#1764](https://github.com/openfoodfacts/robotoff/issues/1764)


### Technical

* move category prediction to right folder ([63647ef](https://github.com/openfoodfacts/robotoff/commit/63647ef4f85c855dac495b1bf0f0d1d32cd10010))
* rename doc into docs ([#1819](https://github.com/openfoodfacts/robotoff/issues/1819)) ([b155bb3](https://github.com/openfoodfacts/robotoff/commit/b155bb39e78d81b1e369fda312a773399f2e30b9))

## [1.85.0](https://github.com/openfoodfacts/robotoff/compare/v1.84.1...v1.85.0) (2025-11-27)


### Features

* Add parameter with_image to the API route questions ([#1804](https://github.com/openfoodfacts/robotoff/issues/1804)) ([c197349](https://github.com/openfoodfacts/robotoff/commit/c197349a5a34dea4bfe81f7814edf39b431bad7b))

## [1.84.1](https://github.com/openfoodfacts/robotoff/compare/v1.84.0...v1.84.1) (2025-11-20)


### Bug Fixes

* fix db.atomic() wrapper ([#1802](https://github.com/openfoodfacts/robotoff/issues/1802)) ([9b83025](https://github.com/openfoodfacts/robotoff/commit/9b830256e18603efb62818b2ae6929d79461fcb6))

## [1.84.0](https://github.com/openfoodfacts/robotoff/compare/v1.83.2...v1.84.0) (2025-11-20)


### Features

* **object-detection:** log inference metrics in Sentry ([#1807](https://github.com/openfoodfacts/robotoff/issues/1807)) ([b11afcc](https://github.com/openfoodfacts/robotoff/commit/b11afcc155967bbf201d77156261781cf4b40c55))


### Technical

* **object-detection:** remove PIL-based preprocessing ([#1805](https://github.com/openfoodfacts/robotoff/issues/1805)) ([a7bdead](https://github.com/openfoodfacts/robotoff/commit/a7bdead02dd92190e0c05652ad2e6f85e676041c))
* **object-detection:** use ObjectDetector class from SDK ([#1806](https://github.com/openfoodfacts/robotoff/issues/1806)) ([78a90db](https://github.com/openfoodfacts/robotoff/commit/78a90db705d33266c65899fd5fa234588c7de449))
* **triton:** update model configs ([#1800](https://github.com/openfoodfacts/robotoff/issues/1800)) ([eaa8a23](https://github.com/openfoodfacts/robotoff/commit/eaa8a2338cd0b42d9fae2eacd47c6e555bb5a6aa))

## [1.83.2](https://github.com/openfoodfacts/robotoff/compare/v1.83.1...v1.83.2) (2025-11-19)


### Bug Fixes

* use transaction in save_image_embeddings ([#1798](https://github.com/openfoodfacts/robotoff/issues/1798)) ([cebd5a0](https://github.com/openfoodfacts/robotoff/commit/cebd5a0d4cb7245bde4a72006564122b65879c48))

## [1.83.1](https://github.com/openfoodfacts/robotoff/compare/v1.83.0...v1.83.1) (2025-11-18)


### Bug Fixes

* don't load all logo annotation in memory ([#1794](https://github.com/openfoodfacts/robotoff/issues/1794)) ([04e055c](https://github.com/openfoodfacts/robotoff/commit/04e055cbdb4b59f6b254e9fc2bec44d7db86184b))
* don't log a warning when downloading OCRs for category detection ([#1797](https://github.com/openfoodfacts/robotoff/issues/1797)) ([22c12e1](https://github.com/openfoodfacts/robotoff/commit/22c12e1da106cc36a98e52290244e171a2e8abc2))
* prevent concurrent insert for image embeddings ([#1796](https://github.com/openfoodfacts/robotoff/issues/1796)) ([ca02ef0](https://github.com/openfoodfacts/robotoff/commit/ca02ef077bc2d954902b1cf2777c711af5806ddb))

## [1.83.0](https://github.com/openfoodfacts/robotoff/compare/v1.82.0...v1.83.0) (2025-11-18)


### Features

* improve worker and queue management ([#1789](https://github.com/openfoodfacts/robotoff/issues/1789)) ([b8cd7f3](https://github.com/openfoodfacts/robotoff/commit/b8cd7f3558acefb2eb49e9aee972532b785f826d))


### Bug Fixes

* accept all logos detected by the object detector model ([#1790](https://github.com/openfoodfacts/robotoff/issues/1790)) ([28af858](https://github.com/openfoodfacts/robotoff/commit/28af85870dc737107d234b3ba9f81a5b802f559e))
* add missing `with_db` decorator ([510095f](https://github.com/openfoodfacts/robotoff/commit/510095ff70082f3895a2da21bcdb199dea13d862))
* increase profile rate for Sentry to 100% ([#1787](https://github.com/openfoodfacts/robotoff/issues/1787)) ([ecee824](https://github.com/openfoodfacts/robotoff/commit/ecee82450f83cd940838665824e3d2003c6553b6))


### Technical

* add extra log during OFF error ([#1791](https://github.com/openfoodfacts/robotoff/issues/1791)) ([3392b07](https://github.com/openfoodfacts/robotoff/commit/3392b07630db4ad473d995c480cc49bc7e4ae5bd))

## [1.82.0](https://github.com/openfoodfacts/robotoff/compare/v1.81.0...v1.82.0) (2025-11-18)


### Features

* enable sentry logging ([#1786](https://github.com/openfoodfacts/robotoff/issues/1786)) ([f7cdcb3](https://github.com/openfoodfacts/robotoff/commit/f7cdcb3861d5c7c9551ee22461622b1c629dac1f))
* use Peewee DB connection pool ([#1785](https://github.com/openfoodfacts/robotoff/issues/1785)) ([0f859b5](https://github.com/openfoodfacts/robotoff/commit/0f859b5859b12b75aed14171550e1be755e3c676))


### Technical

* improve sentry monitoring ([#1783](https://github.com/openfoodfacts/robotoff/issues/1783)) ([eb538e9](https://github.com/openfoodfacts/robotoff/commit/eb538e9ce9f4dd3cb71c489decc67f3c22331243))

## [1.81.0](https://github.com/openfoodfacts/robotoff/compare/v1.80.0...v1.81.0) (2025-11-17)


### Features

* upgrade logo detector model ([#1781](https://github.com/openfoodfacts/robotoff/issues/1781)) ([6c11615](https://github.com/openfoodfacts/robotoff/commit/6c1161589d3e00f7049dba17041c226e342530d3))


### Bug Fixes

* **object-detection:** fix bug after switch from PIL -&gt; np array ([#1782](https://github.com/openfoodfacts/robotoff/issues/1782)) ([d4073d2](https://github.com/openfoodfacts/robotoff/commit/d4073d233364bf210a331d8ff42dc14a6b4befc2))


### Technical

* **deps:** bump googleapis/release-please-action from 4.3 to 4.4 in the all-actions group ([#1779](https://github.com/openfoodfacts/robotoff/issues/1779)) ([e751ffa](https://github.com/openfoodfacts/robotoff/commit/e751ffa9da01f03c2e6608244a2a7b58a076c701))
* **deps:** bump the all-actions group with 4 updates ([#1771](https://github.com/openfoodfacts/robotoff/issues/1771)) ([e4843fe](https://github.com/openfoodfacts/robotoff/commit/e4843fe0d661908d639b17f829699e6298d318ee))
* update documentation after moving all models to HF ([#1780](https://github.com/openfoodfacts/robotoff/issues/1780)) ([73483a2](https://github.com/openfoodfacts/robotoff/commit/73483a2e85fca904f110e50810fc3697a840d806))

## [1.80.0](https://github.com/openfoodfacts/robotoff/compare/v1.79.2...v1.80.0) (2025-10-20)


### Features

* add standalone CLI to manage triton models ([#1774](https://github.com/openfoodfacts/robotoff/issues/1774)) ([d54edf6](https://github.com/openfoodfacts/robotoff/commit/d54edf6f9f3afbbd9c924a1e3ed887df3a68e77a))
* improve model management ([#1776](https://github.com/openfoodfacts/robotoff/issues/1776)) ([8280952](https://github.com/openfoodfacts/robotoff/commit/828095233157e3968c89b7a98a17e31b55e99484))


### Technical

* add documentation about Triton install & management ([#1777](https://github.com/openfoodfacts/robotoff/issues/1777)) ([5b2d696](https://github.com/openfoodfacts/robotoff/commit/5b2d6961dd44044ec5178f130e0b314cee2206b8))
* **deps:** bump vllm from 0.10.1.1 to 0.11.0 in /batch/spellcheck ([#1772](https://github.com/openfoodfacts/robotoff/issues/1772)) ([37dd68d](https://github.com/openfoodfacts/robotoff/commit/37dd68dfaa3c3d4658fcc89a4205e36d0eb97d19))
* switch Triton to GPU instance for all models ([74edcb3](https://github.com/openfoodfacts/robotoff/commit/74edcb3b7099f890ce234e7d1469c7ac88c2ee1e))

## [1.79.2](https://github.com/openfoodfacts/robotoff/compare/v1.79.1...v1.79.2) (2025-09-12)


### Bug Fixes

* only run logo object detection job when OCR is ready ([#1766](https://github.com/openfoodfacts/robotoff/issues/1766)) ([de75631](https://github.com/openfoodfacts/robotoff/commit/de756312ea0572c9d4709e8e0a6da4f963378279))

## [1.79.1](https://github.com/openfoodfacts/robotoff/compare/v1.79.0...v1.79.1) (2025-09-12)


### Bug Fixes

* fix OPF base domain ([#1763](https://github.com/openfoodfacts/robotoff/issues/1763)) ([abc3ec1](https://github.com/openfoodfacts/robotoff/commit/abc3ec1ee0485990084857936426f43172a06a98))

## [1.79.0](https://github.com/openfoodfacts/robotoff/compare/v1.78.3...v1.79.0) (2025-09-12)


### Features

* support OCR-ready event from Redis ([#1760](https://github.com/openfoodfacts/robotoff/issues/1760)) ([da9db9a](https://github.com/openfoodfacts/robotoff/commit/da9db9ad317055a2a7563355cc395ef0701687f2))

## [1.78.3](https://github.com/openfoodfacts/robotoff/compare/v1.78.2...v1.78.3) (2025-09-08)


### Bug Fixes

* fix issue in _is_equal_nutrient_value ([#1758](https://github.com/openfoodfacts/robotoff/issues/1758)) ([9f94a76](https://github.com/openfoodfacts/robotoff/commit/9f94a76d5129cb997b55f73b2c6509ee7700051f))
* mark invalid nutrient entity (energy_*) as such ([#1755](https://github.com/openfoodfacts/robotoff/issues/1755)) ([acb9ada](https://github.com/openfoodfacts/robotoff/commit/acb9adad05d6bf35a174c13eb8884ac0f9e5832e))

## [1.78.2](https://github.com/openfoodfacts/robotoff/compare/v1.78.1...v1.78.2) (2025-09-01)


### Bug Fixes

* catch exceptions during healthcheck to return it in the response ([#1750](https://github.com/openfoodfacts/robotoff/issues/1750)) ([a8ea109](https://github.com/openfoodfacts/robotoff/commit/a8ea109b4e5ef610eb0b9fdb1fc2b0641cf32935))
* catch Redis events with empty codes ([#1745](https://github.com/openfoodfacts/robotoff/issues/1745)) ([653040e](https://github.com/openfoodfacts/robotoff/commit/653040e464090940d541cf58006d3113d85f0305))
* handle more edge cases when comparing nutrient values ([#1751](https://github.com/openfoodfacts/robotoff/issues/1751)) ([9c34049](https://github.com/openfoodfacts/robotoff/commit/9c340491dac3c4b48697fdaf57ed1a9ebf5fc93e))
* **nutrition:** handle the case where predicted unit is null ([#1747](https://github.com/openfoodfacts/robotoff/issues/1747)) ([b2f03e2](https://github.com/openfoodfacts/robotoff/commit/b2f03e2da0bd0821939621ee5d65937f595b7563))

## [1.78.1](https://github.com/openfoodfacts/robotoff/compare/v1.78.0...v1.78.1) (2025-09-01)


### Bug Fixes

* don't send auth cookies twice ([#1741](https://github.com/openfoodfacts/robotoff/issues/1741)) ([97c12eb](https://github.com/openfoodfacts/robotoff/commit/97c12ebeaa8222a698cc7695171f9944fd12cb00))

## [1.78.0](https://github.com/openfoodfacts/robotoff/compare/robotoff-v1.77.2...robotoff-v1.78.0) (2025-08-29)


### Features

* improve nutrition insight generation ([#1735](https://github.com/openfoodfacts/robotoff/issues/1735)) ([b82a1bb](https://github.com/openfoodfacts/robotoff/commit/b82a1bbb036769f9fc0ec58f6b2f3aa949723fe6))


### Bug Fixes

* allow creating new nutrition insight after an insight was validated ([#1737](https://github.com/openfoodfacts/robotoff/issues/1737)) ([e110009](https://github.com/openfoodfacts/robotoff/commit/e110009964be1f00b11a38a998f5df0d414ad99d))


### Technical

* allow to return np array or bytes in download_image func ([#1727](https://github.com/openfoodfacts/robotoff/issues/1727)) ([02054cc](https://github.com/openfoodfacts/robotoff/commit/02054cc8bc94647a64d327e612e47cfc8e36bae6))
* **deps:** bump the all-actions group with 4 updates ([#1731](https://github.com/openfoodfacts/robotoff/issues/1731)) ([2eccf75](https://github.com/openfoodfacts/robotoff/commit/2eccf75499c724cfe784ebe89f6a098a60c38479))
* **deps:** bump vllm from 0.9.0 to 0.10.1.1 in /batch/spellcheck ([#1714](https://github.com/openfoodfacts/robotoff/issues/1714)) ([2f8f6b7](https://github.com/openfoodfacts/robotoff/commit/2f8f6b74752df76798c6f42f19e22172173dde8c))
* move clip config to triton-config folder ([#1738](https://github.com/openfoodfacts/robotoff/issues/1738)) ([2c88eaf](https://github.com/openfoodfacts/robotoff/commit/2c88eaf67d72e439bf4792c54cd287dbf5be7175))
* remove legacy module ([#1732](https://github.com/openfoodfacts/robotoff/issues/1732)) ([3464875](https://github.com/openfoodfacts/robotoff/commit/346487545a681f4b4354856eb7d6ba80247ff72f))
* remove reference to latest release ([#1724](https://github.com/openfoodfacts/robotoff/issues/1724)) ([ab2935b](https://github.com/openfoodfacts/robotoff/commit/ab2935bb33ba8f2143801e3b259f1747abc16dd8))

## [1.77.2](https://github.com/openfoodfacts/robotoff/compare/robotoff-v1.77.1...robotoff-v1.77.2) (2025-08-22)


### Bug Fixes

* fix issue with subquery used in product_type_switched_job ([#1722](https://github.com/openfoodfacts/robotoff/issues/1722)) ([267ad66](https://github.com/openfoodfacts/robotoff/commit/267ad66e031b14fe6510d378b60a8387931da178))


### Technical

* add current version of Robotoff ([d9d372c](https://github.com/openfoodfacts/robotoff/commit/d9d372cfd273ba296db86c228bdc3f7d27550a4c))
* add release please manifest file ([#1719](https://github.com/openfoodfacts/robotoff/issues/1719)) ([ce8cadd](https://github.com/openfoodfacts/robotoff/commit/ce8cadd7201a312fbcd987825df9ad51e137e527))
* fix release please configuration ([#1718](https://github.com/openfoodfacts/robotoff/issues/1718)) ([32e32f1](https://github.com/openfoodfacts/robotoff/commit/32e32f10c588241ef0b4a6e67f418177743740c5))
* set last release sha ([67e8ae1](https://github.com/openfoodfacts/robotoff/commit/67e8ae13ea8a3c1686f83b3bcc6fba694bb5a01f))

## [1.77.1](https://github.com/openfoodfacts/robotoff/compare/v1.77.0...v1.77.1) (2025-08-21)


### Bug Fixes

* remove local test data stored using git LFS ([#1716](https://github.com/openfoodfacts/robotoff/issues/1716)) ([6021158](https://github.com/openfoodfacts/robotoff/commit/60211583451ed3ede92df7c642f963f3e1842bfb))

## [1.77.0](https://github.com/openfoodfacts/robotoff/compare/v1.76.1...v1.77.0) (2025-08-21)


### Features

* add `delete_image_job` ([#1709](https://github.com/openfoodfacts/robotoff/issues/1709)) ([f93daae](https://github.com/openfoodfacts/robotoff/commit/f93daae668f46b66ca8f93916f0fcd05cf660741))


### Bug Fixes

* add missing `[@with](https://github.com/with)_db` decorator ([b10e9da](https://github.com/openfoodfacts/robotoff/commit/b10e9da5452fbb4d0dd90f74b032ce12688cf155))
* fix issue in get_tag function ([#1713](https://github.com/openfoodfacts/robotoff/issues/1713)) ([d94527a](https://github.com/openfoodfacts/robotoff/commit/d94527a03f46a49e5585ed7e98dfb14bbd881611))

## [1.76.1](https://github.com/openfoodfacts/robotoff/compare/v1.76.0...v1.76.1) (2025-08-14)


### Bug Fixes

* add more perf logs for object detection models ([#1704](https://github.com/openfoodfacts/robotoff/issues/1704)) ([0130724](https://github.com/openfoodfacts/robotoff/commit/01307245558c93dc02b775f18b22f4ef6b948077))

## [1.76.0](https://github.com/openfoodfacts/robotoff/compare/v1.75.1...v1.76.0) (2025-08-14)


### Features

* integrate front-classification image model ([#1702](https://github.com/openfoodfacts/robotoff/issues/1702)) ([7ed0e49](https://github.com/openfoodfacts/robotoff/commit/7ed0e496c887485d1d95ed6626282bb3ddc9babe))


### Bug Fixes

* clean old tmp directory in /tmp ([#1699](https://github.com/openfoodfacts/robotoff/issues/1699)) ([2cc5d9e](https://github.com/openfoodfacts/robotoff/commit/2cc5d9e570b6fcb6433d26e1c0da33c7685a3fef))
* Update labeler.yml with fix for md files ([5fa8d43](https://github.com/openfoodfacts/robotoff/commit/5fa8d433af88680766fa7854009f438ef5bbc1f0))


### Documentation

* Create robotoff-for-3rd-party-apps.md ([#1688](https://github.com/openfoodfacts/robotoff/issues/1688)) ([15b8667](https://github.com/openfoodfacts/robotoff/commit/15b866772a10723a5ae485d01fd0cfbaf20709f8))

## [1.75.1](https://github.com/openfoodfacts/robotoff/compare/v1.75.0...v1.75.1) (2025-07-24)


### Bug Fixes

* remove store Alteza ([#1686](https://github.com/openfoodfacts/robotoff/issues/1686)) ([a115e56](https://github.com/openfoodfacts/robotoff/commit/a115e56b4f01ce5d1815cb37047d979b18a3110b))

## [1.75.0](https://github.com/openfoodfacts/robotoff/compare/v1.74.1...v1.75.0) (2025-07-21)


### Features

* add bearer token to nutripatrol auth ([#1676](https://github.com/openfoodfacts/robotoff/issues/1676)) ([c4be13d](https://github.com/openfoodfacts/robotoff/commit/c4be13d54409c9b11ce272620db0838836aebc35))
* allow to specify Triton backend at the model level ([#1682](https://github.com/openfoodfacts/robotoff/issues/1682)) ([e6fd7f8](https://github.com/openfoodfacts/robotoff/commit/e6fd7f8634041e47acd2594136bb82b4a8bb37ae))


### Documentation

* fix issues in OpenAPI file (api.yml) ([#1681](https://github.com/openfoodfacts/robotoff/issues/1681)) ([8f664c6](https://github.com/openfoodfacts/robotoff/commit/8f664c6fb619114eb3a9acdd5b8fec0498937fba)), closes [#1680](https://github.com/openfoodfacts/robotoff/issues/1680)

## [1.74.1](https://github.com/openfoodfacts/robotoff/compare/v1.74.0...v1.74.1) (2025-07-07)


### Bug Fixes

* pass empty dict instead of None as `diffs` ([#1673](https://github.com/openfoodfacts/robotoff/issues/1673)) ([ad504cc](https://github.com/openfoodfacts/robotoff/commit/ad504cc61eca01072be2b941bf61fe7290542aa9))
* take into account product type changes ([#1671](https://github.com/openfoodfacts/robotoff/issues/1671)) ([6478326](https://github.com/openfoodfacts/robotoff/commit/6478326fa7b7aa2adbae639c2d8e9a7fa4c16ede))

## [1.74.0](https://github.com/openfoodfacts/robotoff/compare/v1.73.1...v1.74.0) (2025-07-04)


### Features

* added spectral linting tool for OpenSpec Api file ([#1663](https://github.com/openfoodfacts/robotoff/issues/1663)) ([7d50f89](https://github.com/openfoodfacts/robotoff/commit/7d50f897caee2419e4397f5eaafd0d788a00f3fd))
* only run category prediction model when model input changes ([#1666](https://github.com/openfoodfacts/robotoff/issues/1666)) ([a2cbddf](https://github.com/openfoodfacts/robotoff/commit/a2cbddfebe14ca4105153bcb2ef5685b8df02cfe))


### Bug Fixes

* delete all previous category predictions during import ([#1251](https://github.com/openfoodfacts/robotoff/issues/1251)) ([#1660](https://github.com/openfoodfacts/robotoff/issues/1660)) ([44c61fc](https://github.com/openfoodfacts/robotoff/commit/44c61fc35f01e9830b83b390a390f31d87b95bdf))
* track errors during OFF updates on Sentry ([#1664](https://github.com/openfoodfacts/robotoff/issues/1664)) ([1b67ced](https://github.com/openfoodfacts/robotoff/commit/1b67cedcf2dfdd72ee4ba87774dcbd858c2a83fd))

## [1.73.1](https://github.com/openfoodfacts/robotoff/compare/v1.73.0...v1.73.1) (2025-06-27)


### Bug Fixes

* handle missing ingredient fields in legacy prediction data conversion ([#1656](https://github.com/openfoodfacts/robotoff/issues/1656)) ([8ebd924](https://github.com/openfoodfacts/robotoff/commit/8ebd924df17d458652d273ecfc00ec258a4c21c6)), closes [#1655](https://github.com/openfoodfacts/robotoff/issues/1655)
* launch refresh insight at 7PM instead of 4PM ([#1659](https://github.com/openfoodfacts/robotoff/issues/1659)) ([d86ffdb](https://github.com/openfoodfacts/robotoff/commit/d86ffdb0ccfc2dbc75470a4d894c6a254d4d3c9f))

## [1.73.0](https://github.com/openfoodfacts/robotoff/compare/v1.72.0...v1.73.0) (2025-06-19)


### Features

* add language code validation for ingredient parsing ([#1640](https://github.com/openfoodfacts/robotoff/issues/1640)) ([917f264](https://github.com/openfoodfacts/robotoff/commit/917f264ad8e820051080f151cd159b394c9b5dc8))


### Bug Fixes

* fix bug in extract_ingredients_job ([#1650](https://github.com/openfoodfacts/robotoff/issues/1650)) ([4290191](https://github.com/openfoodfacts/robotoff/commit/4290191c154ca1d437e9bcf5f9c54fc57f3a47b7)), closes [#1648](https://github.com/openfoodfacts/robotoff/issues/1648)
* handle the case where 'rotation' field is missing ([#1653](https://github.com/openfoodfacts/robotoff/issues/1653)) ([6782bed](https://github.com/openfoodfacts/robotoff/commit/6782bed668ecd84b33063726e9770996cd6994d1))
* use `data['rotation']` when annotating ingredient detection insight ([#1651](https://github.com/openfoodfacts/robotoff/issues/1651)) ([c12b9b7](https://github.com/openfoodfacts/robotoff/commit/c12b9b78bf2fded5279953ddf8c53affebaa3f57))

## [1.72.0](https://github.com/openfoodfacts/robotoff/compare/v1.71.6...v1.72.0) (2025-06-12)


### Features

* remove Slack notifications ([#1646](https://github.com/openfoodfacts/robotoff/issues/1646)) ([0b762ef](https://github.com/openfoodfacts/robotoff/commit/0b762eff6d448c84b52f02da9ab1547c48c5401e))

## [1.71.6](https://github.com/openfoodfacts/robotoff/compare/v1.71.5...v1.71.6) (2025-06-12)


### Bug Fixes

* refresh insights after annotation ([#1642](https://github.com/openfoodfacts/robotoff/issues/1642)) ([d98c9c9](https://github.com/openfoodfacts/robotoff/commit/d98c9c9e90dd328f8c5130129c2c8c0961fc80d8))

## [1.71.5](https://github.com/openfoodfacts/robotoff/compare/v1.71.4...v1.71.5) (2025-06-12)


### Bug Fixes

* discard redis events triggered by Robotoff actions ([#1641](https://github.com/openfoodfacts/robotoff/issues/1641)) ([68daf42](https://github.com/openfoodfacts/robotoff/commit/68daf42606181353880dea3ed879f7a379fb04c9))

## [1.71.4](https://github.com/openfoodfacts/robotoff/compare/v1.71.3...v1.71.4) (2025-06-11)


### Bug Fixes

* add more info in logging message when PO update failed ([#1636](https://github.com/openfoodfacts/robotoff/issues/1636)) ([a6c320a](https://github.com/openfoodfacts/robotoff/commit/a6c320a1bdab891a3f620db9a94136078ae8388e))
* replace processName by pid in log messages ([#1638](https://github.com/openfoodfacts/robotoff/issues/1638)) ([a27804d](https://github.com/openfoodfacts/robotoff/commit/a27804d30dabdf4b2cdfc327aa0a9a9327f1a0e6))

## [1.71.3](https://github.com/openfoodfacts/robotoff/compare/v1.71.2...v1.71.3) (2025-06-10)


### Bug Fixes

* bump version of typer to 0.16.0 ([#1634](https://github.com/openfoodfacts/robotoff/issues/1634)) ([fb05a81](https://github.com/openfoodfacts/robotoff/commit/fb05a8174f7b1df85e38473958d6fba2d4c786a4))
* fix bug during spellcheck insight import ([#1632](https://github.com/openfoodfacts/robotoff/issues/1632)) ([81cf10c](https://github.com/openfoodfacts/robotoff/commit/81cf10c9dc173c4fda8d592d7ecb7c07e4472698))

## [1.71.2](https://github.com/openfoodfacts/robotoff/compare/v1.71.1...v1.71.2) (2025-06-10)


### Bug Fixes

* increase timeouts for spellcheck jobs ([#1628](https://github.com/openfoodfacts/robotoff/issues/1628)) ([69d3dc1](https://github.com/openfoodfacts/robotoff/commit/69d3dc101293a219a0c4c66b4cdbf75cd43b559f))

## [1.71.1](https://github.com/openfoodfacts/robotoff/compare/v1.71.0...v1.71.1) (2025-06-09)


### Bug Fixes

* use Optional syntax for typer commands ([59f0ac1](https://github.com/openfoodfacts/robotoff/commit/59f0ac14e20b3d2af372d917ec2d9acc15794aed))

## [1.71.0](https://github.com/openfoodfacts/robotoff/compare/v1.70.0...v1.71.0) (2025-06-06)


### Features

* integrate nutriSight to public API ([#1619](https://github.com/openfoodfacts/robotoff/issues/1619)) ([78b513e](https://github.com/openfoodfacts/robotoff/commit/78b513eabf62217a639979a92ba28e46d55bb9c4))


### Bug Fixes

* Add retry logic for redis ([#1615](https://github.com/openfoodfacts/robotoff/issues/1615)) ([61798aa](https://github.com/openfoodfacts/robotoff/commit/61798aaf2a82bbda7eee2088ea6c0630b7371639))
* fix bug in NutrientExtractionImporter.keep_prediction ([#1621](https://github.com/openfoodfacts/robotoff/issues/1621)) ([033105a](https://github.com/openfoodfacts/robotoff/commit/033105ab14f62962e048801b2e8cc04ff87e9f50)), closes [#1620](https://github.com/openfoodfacts/robotoff/issues/1620)


### Documentation

* add image flagging prediction documentation ([#1622](https://github.com/openfoodfacts/robotoff/issues/1622)) ([5024943](https://github.com/openfoodfacts/robotoff/commit/502494373ad05cad9ada819b4e545dacf6709d96))

## [1.70.0](https://github.com/openfoodfacts/robotoff/compare/v1.69.0...v1.70.0) (2025-06-04)


### Features

* add product_insights.lc field ([#1607](https://github.com/openfoodfacts/robotoff/issues/1607)) ([a28f8c7](https://github.com/openfoodfacts/robotoff/commit/a28f8c7f2a0a94e6ee3a19103655386bb53f99c2))
* add subfields to `ingredient_detection` and `nutrient_extraction` insights ([#1609](https://github.com/openfoodfacts/robotoff/issues/1609)) ([09a1b99](https://github.com/openfoodfacts/robotoff/commit/09a1b999491e54cb7a995e3683fd71fbde81e4d5))
* improve extra data processing in Annotator ([#1613](https://github.com/openfoodfacts/robotoff/issues/1613)) ([fdc7f74](https://github.com/openfoodfacts/robotoff/commit/fdc7f742b86c83b8d9f931b639dfde39a310e6dc))


### Bug Fixes

* allow user to submit rotation and bounding box when annotating `ingredient_detection` insights ([#1610](https://github.com/openfoodfacts/robotoff/issues/1610)) ([4f15e6a](https://github.com/openfoodfacts/robotoff/commit/4f15e6ab47a5f3fe7604c251e291415d9ec759db))
* fix issue when computing lc from nutrient mention ([f81eeb9](https://github.com/openfoodfacts/robotoff/commit/f81eeb95b9c22e3df606e925394ac7761e4a23c3))


### Documentation

* road to api for nutrient extraction ([#1531](https://github.com/openfoodfacts/robotoff/issues/1531)) ([08e7a00](https://github.com/openfoodfacts/robotoff/commit/08e7a0099fe89a155a62aad3f22d66c2fd6b95d4))

## [1.69.0](https://github.com/openfoodfacts/robotoff/compare/v1.68.1...v1.69.0) (2025-06-02)


### Features

* Implement FaceAnnotation support for image flagging ([#1585](https://github.com/openfoodfacts/robotoff/issues/1585)) ([fe6500a](https://github.com/openfoodfacts/robotoff/commit/fe6500a9e6d5ca70aea0247eafef149dc7c7bfd1)), closes [#1581](https://github.com/openfoodfacts/robotoff/issues/1581)


### Bug Fixes

* Fix warning message for non-matching category in taxonomy ([#1604](https://github.com/openfoodfacts/robotoff/issues/1604)) ([1b647aa](https://github.com/openfoodfacts/robotoff/commit/1b647aac409bff10190d773a27d57995495b7744))

## [1.68.1](https://github.com/openfoodfacts/robotoff/compare/v1.68.0...v1.68.1) (2025-05-28)


### Bug Fixes

* fix bug in `extract_ingredients_job` function ([#1601](https://github.com/openfoodfacts/robotoff/issues/1601)) ([0a029eb](https://github.com/openfoodfacts/robotoff/commit/0a029eb7eb4bac49fff8c80d9b307f4ef799ca14)), closes [#1600](https://github.com/openfoodfacts/robotoff/issues/1600)

## [1.68.0](https://github.com/openfoodfacts/robotoff/compare/v1.67.1...v1.68.0) (2025-05-27)


### Features

* add first implementation of ingredient_detection insights ([#1595](https://github.com/openfoodfacts/robotoff/issues/1595)) ([4602077](https://github.com/openfoodfacts/robotoff/commit/4602077b75d862f5fd522fc069f5762e64097552))
* add ingredient detection annotator ([#1598](https://github.com/openfoodfacts/robotoff/issues/1598)) ([31a418c](https://github.com/openfoodfacts/robotoff/commit/31a418c0d88f8c1065d67a66d1e69b2016d0a435))


### Bug Fixes

* CI clean-up and changes according to suggestion on Slack ([#1592](https://github.com/openfoodfacts/robotoff/issues/1592)) ([3d73704](https://github.com/openfoodfacts/robotoff/commit/3d737046afe7313f2b0712b857fdc9f67e3e3c1f)), closes [#1580](https://github.com/openfoodfacts/robotoff/issues/1580)
* fix bug in convert_bounding_box_absolute_to_relative_from_images ([#1597](https://github.com/openfoodfacts/robotoff/issues/1597)) ([fa2931c](https://github.com/openfoodfacts/robotoff/commit/fa2931caf930e0f95390443758e5fe68fb9aa0cf))

## [1.67.1](https://github.com/openfoodfacts/robotoff/compare/v1.67.0...v1.67.1) (2025-05-23)


### Bug Fixes

* rename ingredient detection model name ([#1589](https://github.com/openfoodfacts/robotoff/issues/1589)) ([7baffc6](https://github.com/openfoodfacts/robotoff/commit/7baffc6c5dcde135c9443ed9ffa7c842d14a65b4))


### Documentation

* add for image orientation ([#1584](https://github.com/openfoodfacts/robotoff/issues/1584)) ([051031a](https://github.com/openfoodfacts/robotoff/commit/051031a0ac88228a6b8d71b5ebcaa3a17b2e038a))
* add more information on image orientation insights ([#1587](https://github.com/openfoodfacts/robotoff/issues/1587)) ([5db66ae](https://github.com/openfoodfacts/robotoff/commit/5db66aedc312a94151d4a3325b258f343b2c831b))

## [1.67.0](https://github.com/openfoodfacts/robotoff/compare/v1.66.4...v1.67.0) (2025-05-22)


### Features

* apply image rotation insights automatically ([#1582](https://github.com/openfoodfacts/robotoff/issues/1582)) ([c6254c5](https://github.com/openfoodfacts/robotoff/commit/c6254c5c3e50dc30fa23a9794c16ee6fc5bed04e))

## [1.66.4](https://github.com/openfoodfacts/robotoff/compare/v1.66.3...v1.66.4) (2025-05-21)


### Bug Fixes

* support new `images` schema by converting to legacy schema ([#1578](https://github.com/openfoodfacts/robotoff/issues/1578)) ([4d71b3e](https://github.com/openfoodfacts/robotoff/commit/4d71b3e208a57772cb83f0b649008e59c739e930))

## [1.66.3](https://github.com/openfoodfacts/robotoff/compare/v1.66.2...v1.66.3) (2025-05-19)


### Bug Fixes

* fix bug in annotation of image orientation ([#1574](https://github.com/openfoodfacts/robotoff/issues/1574)) ([a1db080](https://github.com/openfoodfacts/robotoff/commit/a1db080c5a5bb67c91e730502ffb8a71af645981))

## [1.66.2](https://github.com/openfoodfacts/robotoff/compare/v1.66.1...v1.66.2) (2025-05-19)


### Bug Fixes

* **image-rotation:** convert OFF rotation angle to positive value ([#1572](https://github.com/openfoodfacts/robotoff/issues/1572)) ([c3a375e](https://github.com/openfoodfacts/robotoff/commit/c3a375e72439306345803ac825a1e023ecc32f09))

## [1.66.1](https://github.com/openfoodfacts/robotoff/compare/v1.66.0...v1.66.1) (2025-05-16)


### Bug Fixes

* don't generate image orientation insights if the image is already ([4f44a39](https://github.com/openfoodfacts/robotoff/commit/4f44a391ab41c7c4f48a0d16fed1f24ee2a6b8be))
* fix bug in image orientation angle parsing ([56ee8f0](https://github.com/openfoodfacts/robotoff/commit/56ee8f09b4314c4536743d327fa1e150065c5059))

## [1.66.0](https://github.com/openfoodfacts/robotoff/compare/v1.65.0...v1.66.0) (2025-05-16)


### Features

* Implement auto-rotation for selected images using Google Cloud Vision predictions ([#1562](https://github.com/openfoodfacts/robotoff/issues/1562)) ([564d7a4](https://github.com/openfoodfacts/robotoff/commit/564d7a40cf99ac0cc4a1dd73058a3f618c8a1dea))
* improve image orientation insights ([#1567](https://github.com/openfoodfacts/robotoff/issues/1567)) ([5c581b3](https://github.com/openfoodfacts/robotoff/commit/5c581b3bb72447b472455a4ec98ab499a7e94ab2))


### Bug Fixes

* add missing question formatter ([5ec6db1](https://github.com/openfoodfacts/robotoff/commit/5ec6db134e0707e53be2a60b4a52aa553bfa2ebc))
* bump pre-commit hook version ([#1564](https://github.com/openfoodfacts/robotoff/issues/1564)) ([065977a](https://github.com/openfoodfacts/robotoff/commit/065977a85ddf2d5c80664e93416e39df4e574fd6))
* failing code quality tests ([#1556](https://github.com/openfoodfacts/robotoff/issues/1556)) ([2ccdd77](https://github.com/openfoodfacts/robotoff/commit/2ccdd77cf728eeadb9ee0f5272e284694363740f))
* improve ImageOrientation importers and annotator ([#1566](https://github.com/openfoodfacts/robotoff/issues/1566)) ([3d160c8](https://github.com/openfoodfacts/robotoff/commit/3d160c8f57ce57f79d2a7f5317ee038818a0e10f))


### Technical

* clarify Robotoff intro paragraph in README ([#1538](https://github.com/openfoodfacts/robotoff/issues/1538)) ([c6b3fd9](https://github.com/openfoodfacts/robotoff/commit/c6b3fd99554ea162903377272fc6d9da6e1be596))
* fix test annotate + test nutrients JSON ([#1561](https://github.com/openfoodfacts/robotoff/issues/1561)) ([1678921](https://github.com/openfoodfacts/robotoff/commit/16789218a5293db675e1f68f07ca1b5a461b9af4))
* Regenerate poetry.lock after pyproject.toml changes ([#1555](https://github.com/openfoodfacts/robotoff/issues/1555)) ([4472af1](https://github.com/openfoodfacts/robotoff/commit/4472af1e33b49c876978fba26871773c8fd10d10))
* updated ubuntu version pinning and some minor errors related to deployment ([#1558](https://github.com/openfoodfacts/robotoff/issues/1558)) ([fcd09a0](https://github.com/openfoodfacts/robotoff/commit/fcd09a0e16b694b05bfc00125277c90f8c8a8593))

## [1.65.0](https://github.com/openfoodfacts/robotoff/compare/v1.64.2...v1.65.0) (2025-04-15)


### Features

* add `language_codes` filter in insights ([#1547](https://github.com/openfoodfacts/robotoff/issues/1547)) ([9f4507d](https://github.com/openfoodfacts/robotoff/commit/9f4507dce9c496d2502089f8d467dba3620f0bab))


### Bug Fixes

* add barcode validation to image deletion and product update processes ([#1541](https://github.com/openfoodfacts/robotoff/issues/1541)) ([bd8c081](https://github.com/openfoodfacts/robotoff/commit/bd8c0819ecef99fe66b8c6ddd5edcc6171d9c8e1)), closes [#1445](https://github.com/openfoodfacts/robotoff/issues/1445)


### Technical

* add dependabot configuration ([#1540](https://github.com/openfoodfacts/robotoff/issues/1540)) ([e7cde2b](https://github.com/openfoodfacts/robotoff/commit/e7cde2b4e0de762c9521ec5fa09d040011c573cc))

## [1.64.2](https://github.com/openfoodfacts/robotoff/compare/v1.64.1...v1.64.2) (2025-04-03)


### Bug Fixes

* upgrade openfoodfacts sdk to fix bug with brands taxonomies ([#1536](https://github.com/openfoodfacts/robotoff/issues/1536)) ([8efa90a](https://github.com/openfoodfacts/robotoff/commit/8efa90a3bbf3e3e184916e83cc9684602aea687e))

## [1.64.1](https://github.com/openfoodfacts/robotoff/compare/v1.64.0...v1.64.1) (2025-03-06)


### Bug Fixes

* larger timeout for ES request ([#1529](https://github.com/openfoodfacts/robotoff/issues/1529)) ([205c1fa](https://github.com/openfoodfacts/robotoff/commit/205c1fae2c5a21922eb5f003f5d590046300b1f4))
* larger timeout on logo search ([c456807](https://github.com/openfoodfacts/robotoff/commit/c456807446e542bf597ac56cf28fe2a03e44d2bf))


### Technical

* Revert larger timeout on logo search ([a51fc4b](https://github.com/openfoodfacts/robotoff/commit/a51fc4b791768ee3c8431b32c70c938a16b34e38))

## [1.64.0](https://github.com/openfoodfacts/robotoff/compare/v1.63.2...v1.64.0) (2025-02-12)


### Features

* low queue for mass updates ([#1526](https://github.com/openfoodfacts/robotoff/issues/1526)) ([41fe437](https://github.com/openfoodfacts/robotoff/commit/41fe43739edc5eaa4a204a5d4a66aad4e6abda2f))
* Update maintenance how to ([9249361](https://github.com/openfoodfacts/robotoff/commit/9249361be7306bc3f9275a6f4854a9d6c6f1bcb6))

## [1.63.2](https://github.com/openfoodfacts/robotoff/compare/v1.63.1...v1.63.2) (2024-12-27)


### Bug Fixes

* improve batch import ([906c8b9](https://github.com/openfoodfacts/robotoff/commit/906c8b9913721b8ad38c0d367325fcbe4b029e2d))

## [1.63.1](https://github.com/openfoodfacts/robotoff/compare/v1.63.0...v1.63.1) (2024-12-27)


### Bug Fixes

* add CLI command to import batch job predictions ([16c3239](https://github.com/openfoodfacts/robotoff/commit/16c3239abb74be59e7d91f71df6256c054d5d807))

## [1.63.0](https://github.com/openfoodfacts/robotoff/compare/v1.62.0...v1.63.0) (2024-12-26)


### Features

* Upgrade nutrition extractor model ([#1511](https://github.com/openfoodfacts/robotoff/issues/1511)) ([4f13fbb](https://github.com/openfoodfacts/robotoff/commit/4f13fbb56e86670f1ad4a1fbf3db2397273c54dc))


### Bug Fixes

* **nutrisight:** fix model dir ([125250d](https://github.com/openfoodfacts/robotoff/commit/125250d41b6b2bd67bac51c1b15157f990db8696))

## [1.62.0](https://github.com/openfoodfacts/robotoff/compare/v1.61.0...v1.62.0) (2024-12-26)


### Features

* Add triton CLI commands ([#1510](https://github.com/openfoodfacts/robotoff/issues/1510)) ([bc7a506](https://github.com/openfoodfacts/robotoff/commit/bc7a506eef4c595e26fa045509401c9d0f6ec63d))


### Bug Fixes

* use low-priority queue for image import rerun ([#1508](https://github.com/openfoodfacts/robotoff/issues/1508)) ([585df70](https://github.com/openfoodfacts/robotoff/commit/585df7030482a55db242d947e3a45fba18f650be))


### Technical

* **deps-dev:** bump jinja2 from 3.1.4 to 3.1.5 ([#1507](https://github.com/openfoodfacts/robotoff/issues/1507)) ([aa5f296](https://github.com/openfoodfacts/robotoff/commit/aa5f296f8be27ac141f95442d4dbe2dd799f0659))

## [1.61.0](https://github.com/openfoodfacts/robotoff/compare/v1.60.1...v1.61.0) (2024-12-25)


### Features

* add lang pred in spellcheck insights ([#1504](https://github.com/openfoodfacts/robotoff/issues/1504)) ([c921e8a](https://github.com/openfoodfacts/robotoff/commit/c921e8a2d9439543e0523554fa9f6a5d61ad5658))


### Bug Fixes

* allow prices.openfoodfacts.org/net for image cropping ([da3fbc5](https://github.com/openfoodfacts/robotoff/commit/da3fbc55bfcf6de73683839f47816776889cd462))
* convert image to RGB after cropping if needed ([77ce5a4](https://github.com/openfoodfacts/robotoff/commit/77ce5a49e48a07b06e8200ab9bcc4bda9f463b34))

## [1.60.1](https://github.com/openfoodfacts/robotoff/compare/v1.60.0...v1.60.1) (2024-12-20)


### Bug Fixes

* **nutrisight:** allow to override nutrition image ([#1502](https://github.com/openfoodfacts/robotoff/issues/1502)) ([a53485c](https://github.com/openfoodfacts/robotoff/commit/a53485cae4a49e707a015d4e7d038bf4eea907e8))

## [1.60.0](https://github.com/openfoodfacts/robotoff/compare/v1.59.2...v1.60.0) (2024-12-20)


### Features

* Improve annotation process for `nutrition_extraction` insight ([#1501](https://github.com/openfoodfacts/robotoff/issues/1501)) ([6030833](https://github.com/openfoodfacts/robotoff/commit/60308337201cfe485e7fb5e642662ccb8adf0fd8))


### Technical

* change default name for redis stream ([cc23950](https://github.com/openfoodfacts/robotoff/commit/cc239501c2af96f5869596018561329d3d27f3bd))
* create temp volume for es logs ([5268911](https://github.com/openfoodfacts/robotoff/commit/5268911a117859505eec128a6b739b81867d788d))
* increase allowed memory for Triton ([#1498](https://github.com/openfoodfacts/robotoff/issues/1498)) ([0c52a59](https://github.com/openfoodfacts/robotoff/commit/0c52a59d96effa5a2fb918cfeb67e801edbb0a63))

## [1.59.2](https://github.com/openfoodfacts/robotoff/compare/v1.59.1...v1.59.2) (2024-12-12)


### Bug Fixes

* fix the absence of matching synonyms during category insight import ([#1497](https://github.com/openfoodfacts/robotoff/issues/1497)) ([66c5322](https://github.com/openfoodfacts/robotoff/commit/66c532215ae9a0f689631b3e5431b248b2da23c3))
* remove output_image parameter in detect_from_image_tf ([#1494](https://github.com/openfoodfacts/robotoff/issues/1494)) ([5e43dab](https://github.com/openfoodfacts/robotoff/commit/5e43dabe68391c34bd15343790fca9a2568e26b9))
* use Python SDK update listener ([#1496](https://github.com/openfoodfacts/robotoff/issues/1496)) ([fb60549](https://github.com/openfoodfacts/robotoff/commit/fb60549e1243351bae08b92d526168b0613459e9))


### Technical

* add comments ([fb6c5dc](https://github.com/openfoodfacts/robotoff/commit/fb6c5dc36bf58d0eb99cdbdb266b7e624318368e))
* allow to specify triton URI as one envvar ([abcc2e5](https://github.com/openfoodfacts/robotoff/commit/abcc2e5a83aa40d1d422c99e846727a9cd0ed75b))

## [1.59.1](https://github.com/openfoodfacts/robotoff/compare/v1.59.0...v1.59.1) (2024-12-10)


### Bug Fixes

* improve nutrition post-processing ([#1490](https://github.com/openfoodfacts/robotoff/issues/1490)) ([946c73b](https://github.com/openfoodfacts/robotoff/commit/946c73bcca63af0ace67779e817aca0504030f29))
* improve resources caching ([#1492](https://github.com/openfoodfacts/robotoff/issues/1492)) ([bb72dce](https://github.com/openfoodfacts/robotoff/commit/bb72dcedb196fb1040da3aa6fda5138c0f9e99d0))


### Technical

* use openfoodfacts.ml for object detection ([#1493](https://github.com/openfoodfacts/robotoff/issues/1493)) ([54843be](https://github.com/openfoodfacts/robotoff/commit/54843bec061113a3aeec675a72cc6e4873baa989))

## [1.59.0](https://github.com/openfoodfacts/robotoff/compare/v1.58.0...v1.59.0) (2024-12-06)


### Features

* improve /image_predictions route ([#1489](https://github.com/openfoodfacts/robotoff/issues/1489)) ([63add1f](https://github.com/openfoodfacts/robotoff/commit/63add1f300623d3c9a55a8a2e4b68796add3ba7a))


### Bug Fixes

* **nutrisight:** improve extraction postprocessing ([#1486](https://github.com/openfoodfacts/robotoff/issues/1486)) ([4137468](https://github.com/openfoodfacts/robotoff/commit/41374686ec409788787009e1e40acd22ba27306f))
* support votes on GET /api/v1/insights route ([#1488](https://github.com/openfoodfacts/robotoff/issues/1488)) ([33645a6](https://github.com/openfoodfacts/robotoff/commit/33645a63ab7c01275df45695cd44f59db137b3e6))

## [1.58.0](https://github.com/openfoodfacts/robotoff/compare/v1.57.5...v1.58.0) (2024-12-05)


### Features

* Improve nutrition extraction ([#1484](https://github.com/openfoodfacts/robotoff/issues/1484)) ([2430741](https://github.com/openfoodfacts/robotoff/commit/2430741adad4f3d552d247d1a98afb9c4522b021))


### Technical

* New Crowdin translations to review and merge ([#1338](https://github.com/openfoodfacts/robotoff/issues/1338)) ([e310700](https://github.com/openfoodfacts/robotoff/commit/e3107009c098bf1327a31de130a32d09c9e9682f))

## [1.57.5](https://github.com/openfoodfacts/robotoff/compare/v1.57.4...v1.57.5) (2024-12-04)


### Bug Fixes

* add new CLI command to rerun image import for all images ([#1482](https://github.com/openfoodfacts/robotoff/issues/1482)) ([98a1374](https://github.com/openfoodfacts/robotoff/commit/98a13742e62b0b4653559e3c02fadbbb6a39e335))

## [1.57.4](https://github.com/openfoodfacts/robotoff/compare/v1.57.3...v1.57.4) (2024-12-04)


### Bug Fixes

* improve nutrition extraction ([#1479](https://github.com/openfoodfacts/robotoff/issues/1479)) ([730c132](https://github.com/openfoodfacts/robotoff/commit/730c13272d8c9412afd5905f6b790a3b3e01b457))

## [1.57.3](https://github.com/openfoodfacts/robotoff/compare/v1.57.2...v1.57.3) (2024-12-04)


### Bug Fixes

* allow to filter insights by campaign ([#1477](https://github.com/openfoodfacts/robotoff/issues/1477)) ([8079258](https://github.com/openfoodfacts/robotoff/commit/807925874d0869748f268f3f155e72d995c7cee8))

## [1.57.2](https://github.com/openfoodfacts/robotoff/compare/v1.57.1...v1.57.2) (2024-12-03)


### Bug Fixes

* fix refresh-insights command ([0752727](https://github.com/openfoodfacts/robotoff/commit/07527275baf2f81e6d04e28c931ff2938a957bc7))

## [1.57.1](https://github.com/openfoodfacts/robotoff/compare/v1.57.0...v1.57.1) (2024-12-03)


### Bug Fixes

* add campaign for NutrientExtraction insights ([4d8d752](https://github.com/openfoodfacts/robotoff/commit/4d8d752329ffaa6b254e7fe26c00648184dd6f16))
* improve refresh-insights command ([262479a](https://github.com/openfoodfacts/robotoff/commit/262479a9ed7baa4df3767a1d27add4c3ccf99fd2))

## [1.57.0](https://github.com/openfoodfacts/robotoff/compare/v1.56.6...v1.57.0) (2024-12-03)


### Features

* add nutrition annotation ([#1473](https://github.com/openfoodfacts/robotoff/issues/1473)) ([cbe570e](https://github.com/openfoodfacts/robotoff/commit/cbe570ea893cfd4acd67443a326eb2e05cc6981a))

## [1.56.6](https://github.com/openfoodfacts/robotoff/compare/v1.56.5...v1.56.6) (2024-12-01)


### Bug Fixes

* fix Robotoff port numbers ([b7d95c3](https://github.com/openfoodfacts/robotoff/commit/b7d95c3551e6c5c9435ce0bea43ce52d83b8b29a))

## [1.56.5](https://github.com/openfoodfacts/robotoff/compare/v1.56.4...v1.56.5) (2024-11-27)


### Bug Fixes

* revert max_requests limit on gunicorn ([fbd9554](https://github.com/openfoodfacts/robotoff/commit/fbd9554257f56ca6a09cb840e0c1a176e00097dd))

## [1.56.4](https://github.com/openfoodfacts/robotoff/compare/v1.56.3...v1.56.4) (2024-11-26)


### Bug Fixes

* increase max_requests to 500 ([b942c16](https://github.com/openfoodfacts/robotoff/commit/b942c16f4916f0a0d65b3e20f8ad7bbf24a10d72))

## [1.56.3](https://github.com/openfoodfacts/robotoff/compare/v1.56.2...v1.56.3) (2024-11-23)


### Bug Fixes

* remove dataset push to HF ([#1465](https://github.com/openfoodfacts/robotoff/issues/1465)) ([40ecbb2](https://github.com/openfoodfacts/robotoff/commit/40ecbb28a39257c857fbb363d4bb577b8e329c6f))
* restart gunicorn workers every 50 requests ([#1469](https://github.com/openfoodfacts/robotoff/issues/1469)) ([642583c](https://github.com/openfoodfacts/robotoff/commit/642583c9d76df8a8f4e7caf5db782901901db0e8))
* use Robotoff attributed ports for ML services ([#1464](https://github.com/openfoodfacts/robotoff/issues/1464)) ([dd016d9](https://github.com/openfoodfacts/robotoff/commit/dd016d9d8ce8ed98854acfafb865b64bbe913717))


### Technical

* add documentation about the nutrition extraction model ([#1468](https://github.com/openfoodfacts/robotoff/issues/1468)) ([26bc881](https://github.com/openfoodfacts/robotoff/commit/26bc881c72df9e8b243d3c4d4a7fa8b1480c0eb5))
* fix markdown syntax ([1d68bc9](https://github.com/openfoodfacts/robotoff/commit/1d68bc9f36e079eaac71580eef82fb6c32554e57))
* fix syntax error ([d46052f](https://github.com/openfoodfacts/robotoff/commit/d46052fbbf4f716774d8d02ff9aedf508178b4bb))
* remove legacy settings for container deploy ([9117d68](https://github.com/openfoodfacts/robotoff/commit/9117d6820d41e752c50c47a35a86aeb7b36f6eb9))
* use port numbers in Robotoff attributed range ([#1463](https://github.com/openfoodfacts/robotoff/issues/1463)) ([6a99eba](https://github.com/openfoodfacts/robotoff/commit/6a99ebadb0bac4767164a68c51cedc54fba132eb))

## [1.56.2](https://github.com/openfoodfacts/robotoff/compare/v1.56.1...v1.56.2) (2024-11-07)


### Technical

* increase memory limit for scheduler ([#1461](https://github.com/openfoodfacts/robotoff/issues/1461)) ([e698510](https://github.com/openfoodfacts/robotoff/commit/e698510c3af64e288d9cd2f2d913e68b25a4393a))
* remove useless file ([192f3e6](https://github.com/openfoodfacts/robotoff/commit/192f3e6c70c6bef8bdc939e61fee5f390b81d87f))

## [1.56.1](https://github.com/openfoodfacts/robotoff/compare/v1.56.0...v1.56.1) (2024-11-05)


### Bug Fixes

* fix barcode filtering ([9d081a5](https://github.com/openfoodfacts/robotoff/commit/9d081a5c1fbc84250814d13b02ff49e4b2b5f43f))
* fix Parquet dataset push to Hub ([#1458](https://github.com/openfoodfacts/robotoff/issues/1458)) ([87e0fce](https://github.com/openfoodfacts/robotoff/commit/87e0fce87f1740eabe978c1d46950aeb9dc81866))

## [1.56.0](https://github.com/openfoodfacts/robotoff/compare/v1.55.0...v1.56.0) (2024-10-29)


### Features

* schedule Hugging Face Parquet dataset push every day ([7e525c1](https://github.com/openfoodfacts/robotoff/commit/7e525c194187f5ee0f5a3d5f9d23021ec5322e1b))


### Technical

* **deps-dev:** bump werkzeug from 3.0.4 to 3.0.6 ([64f5dbc](https://github.com/openfoodfacts/robotoff/commit/64f5dbca0df31be599994e3f8d67f78fa83fc693))

## [1.55.0](https://github.com/openfoodfacts/robotoff/compare/v1.54.1...v1.55.0) (2024-10-29)


### Features

* :zap: Add CLI command to convert and push JSONL to Huggingface ([#1436](https://github.com/openfoodfacts/robotoff/issues/1436)) ([d68a231](https://github.com/openfoodfacts/robotoff/commit/d68a2319e73d6cb2463869de25984d7025b359bc))
* improve Slack & nutripatrol notifiers ([ef0f861](https://github.com/openfoodfacts/robotoff/commit/ef0f861fb0d7d17c1b05960586226c2bf391fba1))


### Bug Fixes

* add order_by parameter to /api/v1/insights route ([2dcf4a7](https://github.com/openfoodfacts/robotoff/commit/2dcf4a77503412f77492cb664d7f227421538a7c))
* convert image to RGB before nutrition extraction ([#1448](https://github.com/openfoodfacts/robotoff/issues/1448)) ([96401ef](https://github.com/openfoodfacts/robotoff/commit/96401ef94dced4242956f7269ddf3c7b8a5a851f))
* fix KeyError exception in UPCImageImporter ([#1443](https://github.com/openfoodfacts/robotoff/issues/1443)) ([022a788](https://github.com/openfoodfacts/robotoff/commit/022a7882432da2a15bd56411a7635a1732e8955b)), closes [#1442](https://github.com/openfoodfacts/robotoff/issues/1442)
* fix wrong call to logger.exception ([#1441](https://github.com/openfoodfacts/robotoff/issues/1441)) ([750eea9](https://github.com/openfoodfacts/robotoff/commit/750eea99ee60562d9d6ac21705b1d7d5306e6e68)), closes [#1440](https://github.com/openfoodfacts/robotoff/issues/1440)
* remove columns in output parquet files ([d8534fe](https://github.com/openfoodfacts/robotoff/commit/d8534fe13534e776c09421bf097797d944fc0a06))
* update fields fetched to generate parquet file ([4f57419](https://github.com/openfoodfacts/robotoff/commit/4f57419e0b460aee73ed96d1b3d436ed01d1fa4b))


### Technical

* add /api/v1/insights endpoint to documentation ([f5b1de4](https://github.com/openfoodfacts/robotoff/commit/f5b1de43a77b27ccc99ab19836cab53647073b71))
* add HF_TOKEN to .env ([73019bb](https://github.com/openfoodfacts/robotoff/commit/73019bbb5b9caf76ba931080636ee0e63ae6be28))
* reformat test_products.py ([11e0199](https://github.com/openfoodfacts/robotoff/commit/11e0199c35ce71a728cab0f847dca5f62812c327))

## [1.54.1](https://github.com/openfoodfacts/robotoff/compare/v1.54.0...v1.54.1) (2024-10-25)


### Bug Fixes

* fix issue with max() call on empty sequence ([5410b30](https://github.com/openfoodfacts/robotoff/commit/5410b30ba8cf26f98ea6cd53e9522659c5cc5bf8))

## [1.54.0](https://github.com/openfoodfacts/robotoff/compare/v1.53.3...v1.54.0) (2024-10-25)


### Features

* add nutrient extractor ([#1437](https://github.com/openfoodfacts/robotoff/issues/1437)) ([9ae5ff7](https://github.com/openfoodfacts/robotoff/commit/9ae5ff722103602889318257a16909e2478de101))
* Add spellcheck annotate ([#1434](https://github.com/openfoodfacts/robotoff/issues/1434)) ([f9a60dc](https://github.com/openfoodfacts/robotoff/commit/f9a60dc0a0c96da93fef17b470440af7f6798951))


### Bug Fixes

* fix nutrient insight importer ([0e4aff3](https://github.com/openfoodfacts/robotoff/commit/0e4aff3bb83807194ab163334ced75d4d72fe5dd))
* fix NutrientExtractionImporter ([b533199](https://github.com/openfoodfacts/robotoff/commit/b533199ea248c824110182cbe5f536c8d5f86dfb))
* fix nutrition extraction insight generation ([#1438](https://github.com/openfoodfacts/robotoff/issues/1438)) ([cfdfb07](https://github.com/openfoodfacts/robotoff/commit/cfdfb0763b49be7a2d45bccf54173fec1029c0ba))

## [1.53.3](https://github.com/openfoodfacts/robotoff/compare/v1.53.2...v1.53.3) (2024-10-16)


### Bug Fixes

* add mg as possible unit for salt ([463a1f1](https://github.com/openfoodfacts/robotoff/commit/463a1f153a75aff401dfcc4f03bbd1a57937f3ab))
* bump openfoodfacts python dependency ([560c596](https://github.com/openfoodfacts/robotoff/commit/560c59670eb02d33fc6416c646bfe763595273e0))
* fix launch normalize barcode job ([65bdacb](https://github.com/openfoodfacts/robotoff/commit/65bdacbda9158fc6f80e1c5d946a6501e4746bb2))
* remove incorrect parameter when calling CLIPImageProcessor ([340a8e0](https://github.com/openfoodfacts/robotoff/commit/340a8e0d4bc1898aae8eb95db9a1fcdee2e6d22f))

## [1.53.2](https://github.com/openfoodfacts/robotoff/compare/v1.53.1...v1.53.2) (2024-10-08)


### Bug Fixes

* add script to normalize barcodes in DB ([4adeb6b](https://github.com/openfoodfacts/robotoff/commit/4adeb6b7e03daa29f5e611c3ae8704d8e11f9320))
* fix normalize script ([24db8fb](https://github.com/openfoodfacts/robotoff/commit/24db8fbb32ce2d390d704d4299a9f3768a0badcf))
* normalize barcode in all API routes ([7ca87de](https://github.com/openfoodfacts/robotoff/commit/7ca87ded248c4847a79e35fe6c4d18067cf25718))
* use ReditUpdate.product_type ([963eabb](https://github.com/openfoodfacts/robotoff/commit/963eabb14479278d90a21c7bc34cca23ef187604))

## [1.53.1](https://github.com/openfoodfacts/robotoff/compare/v1.53.0...v1.53.1) (2024-10-07)


### Bug Fixes

* add new nutrient mention for portuguese ([#1425](https://github.com/openfoodfacts/robotoff/issues/1425)) ([49df155](https://github.com/openfoodfacts/robotoff/commit/49df1555df905906be9ce6c1648efcf94b9c7659))
* remove legacy routes ([#1424](https://github.com/openfoodfacts/robotoff/issues/1424)) ([c53617d](https://github.com/openfoodfacts/robotoff/commit/c53617d4f85ac62e622b15ecc259b08e4593e132))
* use images.openfoodfacts.org to fetch OCR files ([59fa01f](https://github.com/openfoodfacts/robotoff/commit/59fa01f2751343c0c5c84071dc3cfb33d6561991))
* use new barcode normalization ([65e16dd](https://github.com/openfoodfacts/robotoff/commit/65e16dd4497e97799d689d3e64c08d206cea4a90))

## [1.53.0](https://github.com/openfoodfacts/robotoff/compare/v1.52.1...v1.53.0) (2024-10-01)


### Features

* Add image classifier models ([#1421](https://github.com/openfoodfacts/robotoff/issues/1421)) ([bd369da](https://github.com/openfoodfacts/robotoff/commit/bd369dac2f1e80229965ec95ae7f54a19ddb7e91))


### Bug Fixes

* don't create index concurrently in migration ([96d3374](https://github.com/openfoodfacts/robotoff/commit/96d33744074c149aeb169d60d7e58e6dcb8ecc87))
* remove old object detection models ([#1423](https://github.com/openfoodfacts/robotoff/issues/1423)) ([4d22142](https://github.com/openfoodfacts/robotoff/commit/4d221427490859c8f8fc8995ff00f0d9dd9b0035))
* remove scripts/ocr/run_ocr.py ([2d8fbaf](https://github.com/openfoodfacts/robotoff/commit/2d8fbaffa1f86792e25d58e3b4ef95dd1d71ef1d))

## [1.52.1](https://github.com/openfoodfacts/robotoff/compare/v1.52.0...v1.52.1) (2024-09-18)


### Technical

* :memo: Batch Job - Spellcheck documentation ([#1408](https://github.com/openfoodfacts/robotoff/issues/1408)) ([2748324](https://github.com/openfoodfacts/robotoff/commit/2748324b40aab6f5c11d31e03d24ac31de93e1af))
* **deps:** bump vllm from 0.5.4 to 0.5.5 in /batch/spellcheck ([9a09729](https://github.com/openfoodfacts/robotoff/commit/9a09729406c92947633cf3d0157904839533dc46))

## [1.52.0](https://github.com/openfoodfacts/robotoff/compare/v1.51.0...v1.52.0) (2024-09-17)


### Features

* update ingredient detection model ([459f6f4](https://github.com/openfoodfacts/robotoff/commit/459f6f4689b5e0d5aa0d29a191d8b3fc92af013d))


### Bug Fixes

* bump ingredient detection model version ([dfa2614](https://github.com/openfoodfacts/robotoff/commit/dfa2614f8a81cd2326c83dc332054453a4417e4e))
* fix entity aggregation bug for NER detection ([5f2b94c](https://github.com/openfoodfacts/robotoff/commit/5f2b94ce67ecc4f697cb194ff2bad702980b9102))
* use datetime.now(timezone.utc) instead of utcnow() ([2203ecf](https://github.com/openfoodfacts/robotoff/commit/2203ecfaa4d8803f7a07709ca1203b805e8d12d5))
* use the same predictor_version for all spellcheck predictions ([857fea1](https://github.com/openfoodfacts/robotoff/commit/857fea1e891b238b7e04b605338090eae1755f43))
* wait for Product Opener to generate the dump before downloading it ([6eae9d5](https://github.com/openfoodfacts/robotoff/commit/6eae9d591f06eacaa9ea9ca11ceaf6fdc20bc665))

## [1.51.0](https://github.com/openfoodfacts/robotoff/compare/v1.50.5...v1.51.0) (2024-09-11)


### Features

* :ambulance: Changes ([b8dcd5a](https://github.com/openfoodfacts/robotoff/commit/b8dcd5a9ac781ab33d9743b4cdbe439ca3500e77))
* :ambulance: Credential + Importer ([53752d5](https://github.com/openfoodfacts/robotoff/commit/53752d5c63cdd13276d4f9235dbf6553b81bfcd3))
* :ambulance: Credentials + Importer + Test ([3e2f5e3](https://github.com/openfoodfacts/robotoff/commit/3e2f5e38117eeb759cfab1c1e814435532d78a2b))
* :art: Add key during request by the batch job ([fd7c587](https://github.com/openfoodfacts/robotoff/commit/fd7c5879699568d26f35124dcab8677a82862a60))
* :bug: Forgot a return ([a1de5d9](https://github.com/openfoodfacts/robotoff/commit/a1de5d9b24ac6f847d677241d916217c55a65b31))
* :lock: Secure Batch Data Import endpoint with a token key ([360f2e4](https://github.com/openfoodfacts/robotoff/commit/360f2e4dc69bc7bfdb3adfab6c8b7c8a5f479be3))
* :sparkles: Change batch job launch from api endpoint to CLI ([93c1232](https://github.com/openfoodfacts/robotoff/commit/93c12320a21f2a199af34c79fabb01e4123481a9))
* :sparkles: Implemenation reviews ([c76df4d](https://github.com/openfoodfacts/robotoff/commit/c76df4dd8d39cdf3bb807257a84c61b2728090c7))
* :sparkles: Restructure code ([b7a44c4](https://github.com/openfoodfacts/robotoff/commit/b7a44c46b76b2c17cae741d430c97b453b351123))
* allow to specify parameters when launching spellcheck job ([de050fc](https://github.com/openfoodfacts/robotoff/commit/de050fc61c2091572cd4929fcfd204a416ec44d3))
* **batch - spellcheck:** :zap: API endpoint batch/launch ok: Batch extraction with DuckDB and launch on GCP ([a417fdf](https://github.com/openfoodfacts/robotoff/commit/a417fdf9e6996da34f7827d3b07a49edc9cfa146))
* **batch - spellcheck:** :zap: From predictions to insights ([74c3828](https://github.com/openfoodfacts/robotoff/commit/74c382871c2f6ba12171d5f5a001e5d94df5b22d))
* **batch - spellcheck:** :zap: Integrate batch data from job into Robotoff sql tables ([bdb8733](https://github.com/openfoodfacts/robotoff/commit/bdb8733522937b115e548064da362c5138cfe5e6))
* **Batch job - Spellcheck:** :zap: ([531f3b5](https://github.com/openfoodfacts/robotoff/commit/531f3b521c554616e17d3ae555f8a49a0d2b4e19))
* **batch-spellcheck:** :zap: Batch extraction from database before Batch processing operational ([baf1f1d](https://github.com/openfoodfacts/robotoff/commit/baf1f1d10a4176baea4e8d24071825b34f0e613a))


### Bug Fixes

* :art: Change predictor version to also track... the predictor version ([9800591](https://github.com/openfoodfacts/robotoff/commit/98005911499cc0e0ebc87751d2f91e7bfa80fb30))
* :bug: Fixed bug & Better error handling with Falcon ([e87857c](https://github.com/openfoodfacts/robotoff/commit/e87857c8c842e371fcd7d43638653d48352aaafa))
* add batch_dir as param in /batch/import route ([36f02fb](https://github.com/openfoodfacts/robotoff/commit/36f02fb03ec01c3cb26cec6e64a5ae7df4ef1976))
* add log message in import_spellcheck_batch_predictions ([2329201](https://github.com/openfoodfacts/robotoff/commit/23292014ca6d4cd45d42f1f458ac635ccccf07be))
* **batch-spellcheck:** :lipstick: Fix Spellcheck Batch job file name for Dockerfile ENTRYPOINT ([7a17edc](https://github.com/openfoodfacts/robotoff/commit/7a17edc99fdcff0ac2084b832e3cab665914dbc0))
* fix bug in spellcheck insights import ([db73aea](https://github.com/openfoodfacts/robotoff/commit/db73aea8a6c1a5943dd8e6f2bd6156ae564c78d6))
* fix issues with duckdb command + unit test ([cbe250f](https://github.com/openfoodfacts/robotoff/commit/cbe250fb60ea38e361ba563050f59fc5ab1cb6e1))
* fix mypy and flake8 issues ([ac7907d](https://github.com/openfoodfacts/robotoff/commit/ac7907d14f63e1b7934e3688c8e4f98f591cda22))
* improve naming of batch jobs bucket files ([242f950](https://github.com/openfoodfacts/robotoff/commit/242f9507380e123dc74e96442e239bf96613cfaa))
* improve spellcheck Dockerfile ([235ed4b](https://github.com/openfoodfacts/robotoff/commit/235ed4b58564959ee8a6cd47387127665eaea5e8))
* pass GOOGLE_CREDENTIALS envvar as base64 encoded string ([6be2367](https://github.com/openfoodfacts/robotoff/commit/6be2367e5f7f7a37b18cfb67c23dfed8152207de))
* provide webhook URL as envvar in spellcheck batch job ([3897d65](https://github.com/openfoodfacts/robotoff/commit/3897d65269bbbd1fd441669e942b0d135e36ccc4))
* update content-type in batch job robotoff webhook call ([368ee12](https://github.com/openfoodfacts/robotoff/commit/368ee122e4d1fbe69470dc9239491631ebcc98e9))
* update spellcheck batch script ([374a829](https://github.com/openfoodfacts/robotoff/commit/374a829043bb1cda16b8497e266a56b828a046bf))


### Technical

* :memo: Add batch/import api endpoint to doc ([be563e3](https://github.com/openfoodfacts/robotoff/commit/be563e3d3af11b319e7113335d6cc3e72aa29581))
* :memo: Because perfection ([3ea91d2](https://github.com/openfoodfacts/robotoff/commit/3ea91d205adbdb8b160420aad00c47314c6427f7))
* :sparkles: Black on spellcheck script ([8f84146](https://github.com/openfoodfacts/robotoff/commit/8f84146f0df1fd3323246ed4092363e2d766a041))
* :sparkles: make lint ([2ff7345](https://github.com/openfoodfacts/robotoff/commit/2ff73453623bac61b91ab9255bd891eba1f2c97d))
* add GOOGLE_APPLICATION_CREDENTIALS envvar ([f93fc9f](https://github.com/openfoodfacts/robotoff/commit/f93fc9fb587e97b29f498b561ac5689190d9b37f))
* add GOOGLE_CREDENTIALS during deployment ([b18e613](https://github.com/openfoodfacts/robotoff/commit/b18e613dd05c703f9bf53d60aff7f125424e4b4b))
* **batch-spellcheck:** :green_heart: Fix some bugs: batch-extraction & batch-launch ([c8758e1](https://github.com/openfoodfacts/robotoff/commit/c8758e1239600ac53ae862d6cca2a9eac60a8288))
* remove CodeQL analysis ([1c0946d](https://github.com/openfoodfacts/robotoff/commit/1c0946dc6031df60c2c54e6ff897198fe9bc7a1c))
* remove Sonar Cloud analysis ([4997a01](https://github.com/openfoodfacts/robotoff/commit/4997a013d66dabc36334312fea2ceb240aefe33c))

## [1.50.5](https://github.com/openfoodfacts/robotoff/compare/v1.50.4...v1.50.5) (2024-09-04)


### Technical

* **deps-dev:** bump cryptography from 43.0.0 to 43.0.1 ([0ad0c56](https://github.com/openfoodfacts/robotoff/commit/0ad0c56fb3044c2847573c7de49de6fea616b48d))
* update SSH_PROXY_USERNAME for prod deployment ([34e6aef](https://github.com/openfoodfacts/robotoff/commit/34e6aef1139d469a9a2ad4af1430198b33f86130))

## [1.50.4](https://github.com/openfoodfacts/robotoff/compare/v1.50.3...v1.50.4) (2024-09-03)


### Bug Fixes

* fix product weight detection bug ([fe7e758](https://github.com/openfoodfacts/robotoff/commit/fe7e75814bbbce42e6d6ee86e73102d58c5eff1b))
* only run nutrition table detection for food type ([c019df9](https://github.com/openfoodfacts/robotoff/commit/c019df94b99c7260308b9aeb54d43b685668a57a))
* remove Hacendado store ([e946444](https://github.com/openfoodfacts/robotoff/commit/e946444ee1dabd67b4269d18fafa7639fbc2bac9))
* remove unused class ([22fae32](https://github.com/openfoodfacts/robotoff/commit/22fae32f798240bdfecaf04f0a7adfd08fa41d23))


### Technical

* add tmp volume for ES ([6225bcb](https://github.com/openfoodfacts/robotoff/commit/6225bcb02273aa72f40caa0d837676cd03ccd31f))
* add volume for /tmp ([15130d2](https://github.com/openfoodfacts/robotoff/commit/15130d21747592f816360928f93f5a5e4db84569))
* **deps:** bump sentry-sdk from 1.14.0 to 2.8.0 ([f991bf5](https://github.com/openfoodfacts/robotoff/commit/f991bf536300660613c97f43b294b50a7740f5f0))
* improve robotoff documentation ([b9365a7](https://github.com/openfoodfacts/robotoff/commit/b9365a7cb9c91e25ca0eb2688c95b15506fac2c4))
* make api depends on elasticsearch in docker-compose.yml ([bf99ca8](https://github.com/openfoodfacts/robotoff/commit/bf99ca8f75b1adc8b0fa2f6032cc1e68992220d9))

## [1.50.3](https://github.com/openfoodfacts/robotoff/compare/v1.50.2...v1.50.3) (2024-08-21)


### Technical

* update proxy_username in container-deploy.yml ([d469798](https://github.com/openfoodfacts/robotoff/commit/d4697987ebdd3e38288b88c565aa325a95e3d6c7))

## [1.50.2](https://github.com/openfoodfacts/robotoff/compare/v1.50.1...v1.50.2) (2024-08-21)


### Bug Fixes

* add logo_annotation.server_type field ([a318737](https://github.com/openfoodfacts/robotoff/commit/a3187375a551bb7757f033a43146d3acd0c4d5bd))
* **dev_build:** :zap: Add network po-default before build in make dev ([c99b2c1](https://github.com/openfoodfacts/robotoff/commit/c99b2c160bd2f34abc0de2351e2dd1e19fa08a36))
* display number of logos in index in add-logo-to-ann command ([8251082](https://github.com/openfoodfacts/robotoff/commit/825108258d2cfb41694b0640f3444f310b00c36f))
* improve performance of random logo search ([dec765f](https://github.com/openfoodfacts/robotoff/commit/dec765f148dc1bdaee1419438ae6bb1b2c963c4e))
* improve question count query performance with vote ([f19d49a](https://github.com/openfoodfacts/robotoff/commit/f19d49a9f832b91c4317c163fb82ec3f78f4edee))
* remove some store regex false positive ([6ba5f7e](https://github.com/openfoodfacts/robotoff/commit/6ba5f7e4dc4fe09221eda3c45a86b70b20cee00d))
* use subquery when fetching questions without user votes ([15e6cfb](https://github.com/openfoodfacts/robotoff/commit/15e6cfb0749bafff9de25b6f3328f61d445f84e5))


### Technical

* add index on logo_annotation.server_type ([0da1006](https://github.com/openfoodfacts/robotoff/commit/0da1006e94008ac454c1c061dfc726c171e9a029))
* bring back robotoff-backups ([0f5b8ca](https://github.com/openfoodfacts/robotoff/commit/0f5b8ca7c0a2762bfba053d84a66b408f1a2be65))
* fix deploy configuration ([e4999ac](https://github.com/openfoodfacts/robotoff/commit/e4999acb519e1e00aa703855764a818274c0296e))
* Update README.md ([fc94d96](https://github.com/openfoodfacts/robotoff/commit/fc94d96f6a4a25fc76f4edd8f5494bf48912ad5f))

## [1.50.1](https://github.com/openfoodfacts/robotoff/compare/v1.50.0...v1.50.1) (2024-08-13)


### Technical

* add envvar during deployment ([57488d0](https://github.com/openfoodfacts/robotoff/commit/57488d087b33d970e3cb3100dc062613137a2b1b))
* update configuration for Robotoff Moji migration ([eaf8699](https://github.com/openfoodfacts/robotoff/commit/eaf8699aa142ba8a39cbd82d726ef4e6430de8f4))

## [1.50.0](https://github.com/openfoodfacts/robotoff/compare/v1.49.0...v1.50.0) (2024-07-30)


### Features

* switch from PostgreSQL 11 to PostgreSQL 16 ([7cdb0d2](https://github.com/openfoodfacts/robotoff/commit/7cdb0d2003a607b80156f675825a14b2229b2883))

## [1.49.0](https://github.com/openfoodfacts/robotoff/compare/v1.48.1...v1.49.0) (2024-07-29)


### Features

* add sentry to update-listener daemon ([65a1a49](https://github.com/openfoodfacts/robotoff/commit/65a1a493f61183f4fb89b856dbaa2d96ccaea628))


### Bug Fixes

* catch all exceptions in run_update_listener ([3a4a8ea](https://github.com/openfoodfacts/robotoff/commit/3a4a8ea1e2c3a9d3b7c7fca9fbf731e6fb280e1b))
* lint Dockerfile ([3477239](https://github.com/openfoodfacts/robotoff/commit/34772397fb12e18fdad0dced363baa61761498bd))


### Technical

* upgrade matplotlib ([e094e60](https://github.com/openfoodfacts/robotoff/commit/e094e60b6f0504720c920783ec93c5979391900d))

## [1.48.1](https://github.com/openfoodfacts/robotoff/compare/v1.48.0...v1.48.1) (2024-07-19)


### Bug Fixes

* apply toml lint on pyproject.toml ([c316e41](https://github.com/openfoodfacts/robotoff/commit/c316e414b94a10d677fbf9fd879a7701357dba9d))
* avoid failing all metrics for a single failure ([86f0cae](https://github.com/openfoodfacts/robotoff/commit/86f0cae6608bc19aa645210247b7a7b0435ebd7d))
* delete more unused DB indices ([4942c44](https://github.com/openfoodfacts/robotoff/commit/4942c440cd9d831c4f0da9133b208b0ca18e3ecc))
* improve scheduler ([88501e3](https://github.com/openfoodfacts/robotoff/commit/88501e3a3a2588f0ea3bceefe49e047c7aff9c86))
* switch some info logs into debug ([03e8213](https://github.com/openfoodfacts/robotoff/commit/03e82133e72d1008097c38f74e4006a45d65efab))
* turn more info message into debug ([3dffceb](https://github.com/openfoodfacts/robotoff/commit/3dffceb2e74a8d09780ac49c83a53030b794b339))


### Technical

* add types-pytz dev dep ([6d29674](https://github.com/openfoodfacts/robotoff/commit/6d296749a0d281d41d43ac1dfdec561fab993b28))
* fix backup script ([1a03dd8](https://github.com/openfoodfacts/robotoff/commit/1a03dd8ed0560889bfff8364e5c1976b124994b9))
* fix errors when building docs ([bf26f57](https://github.com/openfoodfacts/robotoff/commit/bf26f578d8229947e4e3e2949c2654d7b30f154c))
* upgrade poetry ([c742e10](https://github.com/openfoodfacts/robotoff/commit/c742e1014cd51cfc531482cf5bea9378b0160281))

## [1.48.0](https://github.com/openfoodfacts/robotoff/compare/v1.47.0...v1.48.0) (2024-07-18)


### Features

* use Redis Stream to listen to events ([e79e8ec](https://github.com/openfoodfacts/robotoff/commit/e79e8ecc46382a0991881de6e536dada17476e32))


### Bug Fixes

* fix bug when latest ID was not found in Redis ([ca1b37a](https://github.com/openfoodfacts/robotoff/commit/ca1b37a943b38806850654e6439a4ff7de5a73c4))
* fix typing issues ([a56c03b](https://github.com/openfoodfacts/robotoff/commit/a56c03be7691656c3e60f44a1e0dd35328c781e8))


### Technical

* **deps-dev:** bump black from 22.10.0 to 24.3.0 ([#1323](https://github.com/openfoodfacts/robotoff/issues/1323)) ([bc259ec](https://github.com/openfoodfacts/robotoff/commit/bc259ecf87744c2c0aebcb61573a3f2f8529ef06))
* upgrade black ([462483d](https://github.com/openfoodfacts/robotoff/commit/462483d37cdc3b0dab6c6b2dd6c62da489e96dd6))
* use the common network to access update redis & mongodb ([6cf259f](https://github.com/openfoodfacts/robotoff/commit/6cf259f0265e650e93528d8ffc38234c9d69dc7f))

## [1.47.0](https://github.com/openfoodfacts/robotoff/compare/v1.46.0...v1.47.0) (2024-07-12)


### Features

* add Yolov8 model for nutrition table detection ([#1365](https://github.com/openfoodfacts/robotoff/issues/1365)) ([5b069af](https://github.com/openfoodfacts/robotoff/commit/5b069af7e1dc7d1f264b2a05c40a9c1c84cd8620))


### Bug Fixes

* decrease minimum score to leverage nutrition table detections ([4a26918](https://github.com/openfoodfacts/robotoff/commit/4a26918081215e1781a5f4c6ce2b97df807462f4))
* drop unused indices ([#1364](https://github.com/openfoodfacts/robotoff/issues/1364)) ([f0c348f](https://github.com/openfoodfacts/robotoff/commit/f0c348f2d2a6f83f8d2f9e7730d50066a5742e4f))
* fix get_type call ([18181bb](https://github.com/openfoodfacts/robotoff/commit/18181bb5fa96e4ad0dbe39d88f5153c037e8a471))
* fix ImagePrediction.model_name ([4a9e1a6](https://github.com/openfoodfacts/robotoff/commit/4a9e1a659111dcb5557c611b0d1fce9040a3725f))
* fix issue with model loading ([1e15d72](https://github.com/openfoodfacts/robotoff/commit/1e15d7257ff1f34d74d8ac5437040a650b3a1e0f))


### Technical

* add doc about triton ([3a6fcb3](https://github.com/openfoodfacts/robotoff/commit/3a6fcb36732cee54752862f71f2b7d552725e766))
* improve docstring ([e6f8533](https://github.com/openfoodfacts/robotoff/commit/e6f8533e04d053e3682a4214f6f8eb8e1ee77d6c))

## [1.46.0](https://github.com/openfoodfacts/robotoff/compare/v1.45.2...v1.46.0) (2024-07-08)


### Features

* add yolo model for nutriscore object detection ([#1356](https://github.com/openfoodfacts/robotoff/issues/1356)) ([be19217](https://github.com/openfoodfacts/robotoff/commit/be192179c188e17cd6359afd3104bdcdc0e880bc))


### Bug Fixes

* fix incorrect astype call ([#1359](https://github.com/openfoodfacts/robotoff/issues/1359)) ([f3d3ff6](https://github.com/openfoodfacts/robotoff/commit/f3d3ff64d4c77fff37b77c6dc1ab6c51d713ab89))
* make log message less verbose in api.py ([#1361](https://github.com/openfoodfacts/robotoff/issues/1361)) ([83e043b](https://github.com/openfoodfacts/robotoff/commit/83e043bc76584c74a2d0e54f0fb680aef80d9f32))


### Technical

* update some envvar config ([#1360](https://github.com/openfoodfacts/robotoff/issues/1360)) ([923324e](https://github.com/openfoodfacts/robotoff/commit/923324efe5db65b9a76f6b2f06a6d37309e9ae76))
* upgrade dep ([#1358](https://github.com/openfoodfacts/robotoff/issues/1358)) ([a02ec39](https://github.com/openfoodfacts/robotoff/commit/a02ec391b86d0281ac25ff4bb26b210d92a95261))

## [1.45.2](https://github.com/openfoodfacts/robotoff/compare/v1.45.1...v1.45.2) (2024-07-04)


### Bug Fixes

* improve OCR dump script ([#1351](https://github.com/openfoodfacts/robotoff/issues/1351)) ([b49836b](https://github.com/openfoodfacts/robotoff/commit/b49836b45a3046b679a9aed397b0a6c1215517d8))


### Technical

* increase SHARED_BUFFERS and WORK_MEM ([#1354](https://github.com/openfoodfacts/robotoff/issues/1354)) ([f26fdba](https://github.com/openfoodfacts/robotoff/commit/f26fdbac77314ac1d17e62fd6ad348423dbc37f2))

## [1.45.1](https://github.com/openfoodfacts/robotoff/compare/v1.45.0...v1.45.1) (2024-06-24)


### Bug Fixes

* don't select nutrition image if one has already been selected ([#1348](https://github.com/openfoodfacts/robotoff/issues/1348)) ([68cc43d](https://github.com/openfoodfacts/robotoff/commit/68cc43dbc8156892264187e8f6a4f96f5f8f554f))


### Technical

* **deps:** bump urllib3 from 2.1.0 to 2.2.2 ([#1347](https://github.com/openfoodfacts/robotoff/issues/1347)) ([0937f1e](https://github.com/openfoodfacts/robotoff/commit/0937f1eee8f9d2c991d6b5ce3233bdf95bad0741))

## [1.45.0](https://github.com/openfoodfacts/robotoff/compare/v1.44.0...v1.45.0) (2024-05-15)


### Features

* improve Slack & nutripatrol notifier ([#1343](https://github.com/openfoodfacts/robotoff/issues/1343)) ([076fb11](https://github.com/openfoodfacts/robotoff/commit/076fb11e125bfade78ce30c3076463a92fefe434))


### Technical

* **deps-dev:** bump jinja2 from 3.1.3 to 3.1.4 ([#1342](https://github.com/openfoodfacts/robotoff/issues/1342)) ([60e7f13](https://github.com/openfoodfacts/robotoff/commit/60e7f132166fe3d4582485c44aa28f723a48e37f))
* **deps-dev:** bump werkzeug from 3.0.1 to 3.0.3 ([#1341](https://github.com/openfoodfacts/robotoff/issues/1341)) ([a9244f9](https://github.com/openfoodfacts/robotoff/commit/a9244f967b3b44f71be30086b6720b3d3ad14d6e))
* **deps:** bump dnspython from 2.4.2 to 2.6.1 ([#1335](https://github.com/openfoodfacts/robotoff/issues/1335)) ([084b9d9](https://github.com/openfoodfacts/robotoff/commit/084b9d915ede638c9e71307de276f41fa4ab864c))
* **deps:** bump gunicorn from 20.1.0 to 22.0.0 ([#1336](https://github.com/openfoodfacts/robotoff/issues/1336)) ([9ec607a](https://github.com/openfoodfacts/robotoff/commit/9ec607a7377becdd92ed099b3f50f6a64a5a0028))
* **deps:** bump idna from 3.6 to 3.7 ([#1334](https://github.com/openfoodfacts/robotoff/issues/1334)) ([d514f82](https://github.com/openfoodfacts/robotoff/commit/d514f82d4fcc5f9f542d4b978a86a148ff7394e9))
* **deps:** bump tqdm from 4.66.1 to 4.66.3 ([#1340](https://github.com/openfoodfacts/robotoff/issues/1340)) ([beef9a4](https://github.com/openfoodfacts/robotoff/commit/beef9a4066c9a5b7e7015c4c8238e84465a507d9))
* New Crowdin translations to review and merge ([#1324](https://github.com/openfoodfacts/robotoff/issues/1324)) ([5310130](https://github.com/openfoodfacts/robotoff/commit/5310130a9bee99115ed170595bf88cb8cbf5a6aa))

## [1.44.0](https://github.com/openfoodfacts/robotoff/compare/v1.43.0...v1.44.0) (2024-04-11)


### Features

* Add nutripatrol integration ([#1326](https://github.com/openfoodfacts/robotoff/issues/1326)) ([fa3dc0c](https://github.com/openfoodfacts/robotoff/commit/fa3dc0cea60b6c34f95200e2fb983ea8bdd9ec39))


### Bug Fixes

* fix nutripatrol deployment ([#1333](https://github.com/openfoodfacts/robotoff/issues/1333)) ([9e88ac2](https://github.com/openfoodfacts/robotoff/commit/9e88ac28544b54b273c475f0efeb4ad5330135a1))
* fix nutripatrol deployment and API call ([8455a0e](https://github.com/openfoodfacts/robotoff/commit/8455a0e4786edb3be33bc9eb790031f5a65ec8ee))
* fix unit test ([9d339d0](https://github.com/openfoodfacts/robotoff/commit/9d339d0a57681e17fd073bd1a78387a869e66af6))
* **tests:** fix unit test ([0195926](https://github.com/openfoodfacts/robotoff/commit/0195926e09e7a78b3fa7b2099daf8e9c30d5c507))


### Technical

* **deps:** bump pillow from 10.2.0 to 10.3.0 ([#1328](https://github.com/openfoodfacts/robotoff/issues/1328)) ([a3357dc](https://github.com/openfoodfacts/robotoff/commit/a3357dc88543733bf9be24fe7ab913de74a717bc))
* **deps:** bump pymongo from 4.5.0 to 4.6.3 ([#1330](https://github.com/openfoodfacts/robotoff/issues/1330)) ([5f8b75e](https://github.com/openfoodfacts/robotoff/commit/5f8b75e1e40e5196dfd453c9ef49e647a3e92ead))
* **deps:** bump transformers from 4.36.0 to 4.38.0 ([#1331](https://github.com/openfoodfacts/robotoff/issues/1331)) ([4fe0ede](https://github.com/openfoodfacts/robotoff/commit/4fe0ede6e95e88319706e7f5b46bc9ee1e913ab0))
* **docker:** remove legacy "version" field in docker-compose configs ([1e047aa](https://github.com/openfoodfacts/robotoff/commit/1e047aaf6305391097e77299ed4208800335397c))

## [1.43.0](https://github.com/openfoodfacts/robotoff/compare/v1.42.1...v1.43.0) (2024-03-26)


### Features

* **main:** correct and add label logos ([#1322](https://github.com/openfoodfacts/robotoff/issues/1322)) ([1213c7d](https://github.com/openfoodfacts/robotoff/commit/1213c7d8cfb550906489022b64e37238730da21d))


### Technical

* **deps:** bump orjson from 3.8.14 to 3.9.15 ([#1319](https://github.com/openfoodfacts/robotoff/issues/1319)) ([0f2ee58](https://github.com/openfoodfacts/robotoff/commit/0f2ee58702a5050e2b2d88af18e249d07ae847fc))
* New Crowdin translations to review and merge ([#1312](https://github.com/openfoodfacts/robotoff/issues/1312)) ([6f888aa](https://github.com/openfoodfacts/robotoff/commit/6f888aada983f512e7406c4c5f6f3e79a2557b88))
* switch to docker compose v2 ([#1325](https://github.com/openfoodfacts/robotoff/issues/1325)) ([5bde479](https://github.com/openfoodfacts/robotoff/commit/5bde4790fbc7000f8cc225cc24a6737f55a06491))
* Update docker config ([#1321](https://github.com/openfoodfacts/robotoff/issues/1321)) ([09dc8b4](https://github.com/openfoodfacts/robotoff/commit/09dc8b454c621b49e0c994b8517ac937d3f52bcc))

## [1.42.1](https://github.com/openfoodfacts/robotoff/compare/v1.42.0...v1.42.1) (2024-02-22)


### Technical

* **deps-dev:** bump cryptography from 42.0.0 to 42.0.2 ([#1316](https://github.com/openfoodfacts/robotoff/issues/1316)) ([cc3a6bf](https://github.com/openfoodfacts/robotoff/commit/cc3a6bf074bd319b6a614ce78898da05139a184d))
* **deps-dev:** bump cryptography from 42.0.2 to 42.0.4 ([#1318](https://github.com/openfoodfacts/robotoff/issues/1318)) ([b775b8d](https://github.com/openfoodfacts/robotoff/commit/b775b8d06a3b9ae10ceb51f2e8a6fe6cd7c5ca94))

## [1.42.0](https://github.com/openfoodfacts/robotoff/compare/v1.41.2...v1.42.0) (2024-02-13)


### Features

* add multiple triton backend ([#1314](https://github.com/openfoodfacts/robotoff/issues/1314)) ([a7eab33](https://github.com/openfoodfacts/robotoff/commit/a7eab33622f13da3554274f70a2eb5c938cd6578))


### Bug Fixes

* fix extreme weight detection for multi-packaging ([#1298](https://github.com/openfoodfacts/robotoff/issues/1298)) ([d9660c6](https://github.com/openfoodfacts/robotoff/commit/d9660c6e713bd2b578d6d8c6dab232d75add5994))
* fix run_logo_detection function ([4775ccc](https://github.com/openfoodfacts/robotoff/commit/4775ccccf545ef0079e63de35943b5370ee10640))
* fix unit test ([cf12304](https://github.com/openfoodfacts/robotoff/commit/cf12304ed55bee018be98ec97cf6d75233e43a1c))
* improve docstring and add log messages ([#1310](https://github.com/openfoodfacts/robotoff/issues/1310)) ([3e03f83](https://github.com/openfoodfacts/robotoff/commit/3e03f836ec99ab6c8a33c1253730a4a68af03c44))


### Technical

* change prod mongodb address (again) ([ade67c2](https://github.com/openfoodfacts/robotoff/commit/ade67c21bab152afe64c33b9f540bf91b212efb0))
* Create FEATURES.md to doc features and todos ([#1309](https://github.com/openfoodfacts/robotoff/issues/1309)) ([8c1b404](https://github.com/openfoodfacts/robotoff/commit/8c1b404f0a5c74ccf4af2a0d8d2c7c7cb6cb4668))
* **deps-dev:** bump cryptography from 41.0.7 to 42.0.0 ([#1308](https://github.com/openfoodfacts/robotoff/issues/1308)) ([6585390](https://github.com/openfoodfacts/robotoff/commit/65853904e3ba911867f55dad9d78febf55506afc))
* **deps-dev:** bump jinja2 from 3.1.2 to 3.1.3 ([#1305](https://github.com/openfoodfacts/robotoff/issues/1305)) ([e237b6a](https://github.com/openfoodfacts/robotoff/commit/e237b6ab6350010f5e9a3702a7d35cf6a0b32c1c))
* **deps:** bump pillow from 10.0.1 to 10.2.0 ([#1306](https://github.com/openfoodfacts/robotoff/issues/1306)) ([5ea2ab7](https://github.com/openfoodfacts/robotoff/commit/5ea2ab7e08d34cf4f7ae55f65fd95f6434f721db))
* **deps:** bump transformers from 4.30.2 to 4.36.0 ([#1301](https://github.com/openfoodfacts/robotoff/issues/1301)) ([e36eb3b](https://github.com/openfoodfacts/robotoff/commit/e36eb3b5135aaeb40e0cb14b591f8bbde6f4c66c))
* New Crowdin translations to review and merge ([#1303](https://github.com/openfoodfacts/robotoff/issues/1303)) ([bc00a7c](https://github.com/openfoodfacts/robotoff/commit/bc00a7c77f17105e1ddefbe292c67fd5d5342ee1))

## [1.41.2](https://github.com/openfoodfacts/robotoff/compare/v1.41.1...v1.41.2) (2024-01-08)


### Bug Fixes

* update .gitignore ([7b2b849](https://github.com/openfoodfacts/robotoff/commit/7b2b8494b57c6d969b1127cf4e23b421b70aaf0b))


### Technical

* new mongodb connection through stunnel ([#1302](https://github.com/openfoodfacts/robotoff/issues/1302)) ([bc41164](https://github.com/openfoodfacts/robotoff/commit/bc4116449dd3c00d1db7185dc710165a6d5cf941))

## [1.41.1](https://github.com/openfoodfacts/robotoff/compare/v1.41.0...v1.41.1) (2023-12-18)


### Bug Fixes

* fix image_response function ([82a826d](https://github.com/openfoodfacts/robotoff/commit/82a826d420bb4e2310dd9835741fad3130c4cc7c))

## [1.41.0](https://github.com/openfoodfacts/robotoff/compare/v1.40.0...v1.41.0) (2023-12-18)


### Features

* add endpoint to predict language ([686e180](https://github.com/openfoodfacts/robotoff/commit/686e180cd3d7a1a76460fb71ec3cbfb3f9e88d39))
* add language predictor for product ([c77f049](https://github.com/openfoodfacts/robotoff/commit/c77f049da0a3e28053acab64ee1f077bf9b1e367))


### Bug Fixes

* add a POST version of /predict/lang endpoint ([619c477](https://github.com/openfoodfacts/robotoff/commit/619c47726a2d60f99564ae9eae0cadf97498ee4b))
* allow gunicorn auto-reload locally ([a1ffa44](https://github.com/openfoodfacts/robotoff/commit/a1ffa444c25ca190c322275f8e2379299afeaf9a))
* fix delete_images call ([f0ad1e1](https://github.com/openfoodfacts/robotoff/commit/f0ad1e1d56a0927f9bd0fe6fa3ff85440bff23df))
* fix missing SQL join in ANNResource ([607f743](https://github.com/openfoodfacts/robotoff/commit/607f743a926530c36bf68819e5a778ef4a37ed43))
* fix parse_ingredients function ([189c5cc](https://github.com/openfoodfacts/robotoff/commit/189c5cc98f9c6e45ae25cce82e55c5d5d45e0f1f))


### Technical

* **deps-dev:** bump werkzeug from 3.0.0 to 3.0.1 ([#1276](https://github.com/openfoodfacts/robotoff/issues/1276)) ([da54a80](https://github.com/openfoodfacts/robotoff/commit/da54a803588235b40832d7740b9abbd7585e55a7))
* increase mem limit of API service ([ed32bfb](https://github.com/openfoodfacts/robotoff/commit/ed32bfb4452f740b8ae26282a90cd75123801473))
* New Crowdin translations to review and merge ([#1291](https://github.com/openfoodfacts/robotoff/issues/1291)) ([9b10ae0](https://github.com/openfoodfacts/robotoff/commit/9b10ae006b5b06f3854dbb6196e247dd6782a352))
* switch to Falcon 3.X ([6362185](https://github.com/openfoodfacts/robotoff/commit/6362185b7d6c12dda086d87ef9e0ed8ec38c00c7))

## [1.40.0](https://github.com/openfoodfacts/robotoff/compare/v1.39.0...v1.40.0) (2023-11-13)


### Features

* add basic detection for mention of organic ingredient ([0939075](https://github.com/openfoodfacts/robotoff/commit/0939075e58515bcf3c9792c7fb3fc11ea0060ec9))
* add bounding box info to IngredientPredictionAggregatedEntity ([f45cd39](https://github.com/openfoodfacts/robotoff/commit/f45cd39903a8c0a009a4e7a3eae12ffa80233b24))
* add ingredient parsing information ([e9f2b60](https://github.com/openfoodfacts/robotoff/commit/e9f2b60672a0812d2804b6295d31078f2fe391c6))
* save ingredient list detection in DB ([8f2a4b4](https://github.com/openfoodfacts/robotoff/commit/8f2a4b41fef431857db6057293052709c68ebe33))
* use allergen grammar to postprocess ingredient detections ([36eac56](https://github.com/openfoodfacts/robotoff/commit/36eac566730b660e71374394cb13227626fa9bf0))


### Bug Fixes

* add bounding box information to /predict/ingredient_list route ([af40b55](https://github.com/openfoodfacts/robotoff/commit/af40b558c626b0206e3eed7101c6b2b43a479c56))
* add missing transformer_pipeline.py file ([7543ef0](https://github.com/openfoodfacts/robotoff/commit/7543ef05ea6cb57ef9d34ed1501148e242144e94))
* delete logos in elasticsearch when image is deleted ([b137866](https://github.com/openfoodfacts/robotoff/commit/b1378665bc74ea1cff3905f4cdae64e7e7b42adb))
* don't include deleted images in searched logos ([1fce684](https://github.com/openfoodfacts/robotoff/commit/1fce684a0f1256af364dc2ac8f9f645dce937267))
* don't include logos from deleted images in additional routes ([4b7e130](https://github.com/openfoodfacts/robotoff/commit/4b7e1300853bf14483a9833c9746178596db7ff1))
* improve allergen detection ([2a66666](https://github.com/openfoodfacts/robotoff/commit/2a666665b9f294189ff6a18f6daad53c6db594da))
* improve ingredient detection output saved in DB ([6b62ca2](https://github.com/openfoodfacts/robotoff/commit/6b62ca221db87c2901c300ca7add634b39fa9a31))
* increase default logo threshold to 0.2 (from 0.1) ([74b48f5](https://github.com/openfoodfacts/robotoff/commit/74b48f55ade813aed21633eb38c9245946c86e88))
* remove warning log message ([8ea3476](https://github.com/openfoodfacts/robotoff/commit/8ea3476e558d5da1f10cff27ee03e150caba1c4b))


### Technical

* add allergen taxonomy ([6704189](https://github.com/openfoodfacts/robotoff/commit/67041891d18b1aa6f471fd434c0013a40af32558))
* add clean_tests command ([a6f8f33](https://github.com/openfoodfacts/robotoff/commit/a6f8f333f3074c561432ae0ce5a0c40d21d49152))
* add first version of trace grammar ([6bafa88](https://github.com/openfoodfacts/robotoff/commit/6bafa882baaca4441de0b74665c4d5c69e79f4e8))
* fix docstring in models.py ([d9edc6f](https://github.com/openfoodfacts/robotoff/commit/d9edc6fec0dfe8122fa415453bd431320949970e))
* improve documentation on Dockerfile and docker-compose.yml ([ab4c4ac](https://github.com/openfoodfacts/robotoff/commit/ab4c4acaeeca6dc26efa698d327f70be88f1f0f0))

## [1.39.0](https://github.com/openfoodfacts/robotoff/compare/v1.38.1...v1.39.0) (2023-11-06)


### Features

* save logo text (extracted using OCR in DB) ([bf4632f](https://github.com/openfoodfacts/robotoff/commit/bf4632fbf84727a1b158bf174fb44c6eea631439))


### Bug Fixes

* add cache directory to repo ([2905741](https://github.com/openfoodfacts/robotoff/commit/29057413d14615065b2f81dcecbdb74de63199eb))
* add timeout to robotoff request (healthcheck) ([ab17cee](https://github.com/openfoodfacts/robotoff/commit/ab17cee4bd75b540d943710c49e86b3640a5e819))
* fix bounding box field default value ([5b78f5d](https://github.com/openfoodfacts/robotoff/commit/5b78f5d839e6c320a1e38582fee5cdc959cb4e70))
* fix incorrect call to cache_asset_from_url ([d5562c1](https://github.com/openfoodfacts/robotoff/commit/d5562c17b3f1219ff1ca6894f5d3212d9ec5f3bd))
* use distinct cache for test assets ([c52d3f9](https://github.com/openfoodfacts/robotoff/commit/c52d3f9ec3569eca432ee7df3ec90a2a39a45469))

## [1.38.1](https://github.com/openfoodfacts/robotoff/compare/v1.38.0...v1.38.1) (2023-10-30)


### Bug Fixes

* fix bug in get_image_from_url ([ce0c1b2](https://github.com/openfoodfacts/robotoff/commit/ce0c1b25502d13e87e76ad4bdc6aa68357486d3c))

## [1.38.0](https://github.com/openfoodfacts/robotoff/compare/v1.37.0...v1.38.0) (2023-10-30)


### Features

* add a disk cache mechanism to cache images ([0330216](https://github.com/openfoodfacts/robotoff/commit/0330216b398071691e68eac9f05753521cb93828))
* add migrate_peewee library to handle DB migrations ([8b77195](https://github.com/openfoodfacts/robotoff/commit/8b77195329810b915154fff48ee823206f483e58))
* add product_insight.bounding_box field ([1901b15](https://github.com/openfoodfacts/robotoff/commit/1901b1531435ff5030230a05710143603629080d))


### Bug Fixes

* fix Dockerfile related to migrations folder ([0fc70ef](https://github.com/openfoodfacts/robotoff/commit/0fc70ef3b0ceb30b66f9ab37ec598e3c9c3b38f6))
* fix logging issue ([5e86341](https://github.com/openfoodfacts/robotoff/commit/5e86341ec698257df5db46a380ccf8ce61935046))
* fix migration application during deployment ([27ea630](https://github.com/openfoodfacts/robotoff/commit/27ea6305dc004dbfd65e38d89611fd79d1ceeeaf))
* fix previously introduced issues ([0624efe](https://github.com/openfoodfacts/robotoff/commit/0624efeb666c63a2cd2975bbee536041f6a901d5))
* improve DB migration ([e67d271](https://github.com/openfoodfacts/robotoff/commit/e67d271eff7b68b3ff9783576f37b41eba4bc8a7))
* mark images as deleted in DB when deleted on Product Opener ([997e989](https://github.com/openfoodfacts/robotoff/commit/997e98949c8ae3df9856c1a17c1f295aed73bf1d))
* migrate-db when running make dev ([0a2171d](https://github.com/openfoodfacts/robotoff/commit/0a2171d82efb68e76b06f285607406e2e0b16ac4))
* more stores ([3dea05d](https://github.com/openfoodfacts/robotoff/commit/3dea05d1a2a13f6d9ef1010f536408e390ae3f1e))
* pull image before launching migration ([bd6a15a](https://github.com/openfoodfacts/robotoff/commit/bd6a15a723c1e25ef74678f6558d92a0043fc452))
* upgrade peewee ([264d9bf](https://github.com/openfoodfacts/robotoff/commit/264d9bf27067f86262f74ac6ba0165b8ba802623))


### Technical

* add documentation about DB migration ([16c865f](https://github.com/openfoodfacts/robotoff/commit/16c865f2998f8b98117f5e609df2445bf76d205f))
* **deps:** bump pillow from 9.3.0 to 10.0.1 ([e056268](https://github.com/openfoodfacts/robotoff/commit/e056268d2bef5cebbc5a62909a1baa7051910ca5))
* remove CachedStore class ([5d8c007](https://github.com/openfoodfacts/robotoff/commit/5d8c007dc3a0868d9ce8c80a3aaf3b4a497560f2))

## [1.37.0](https://github.com/openfoodfacts/robotoff/compare/v1.36.0...v1.37.0) (2023-10-25)


### Features

* allow to submit category value_tag in /annotate route ([dd6d81e](https://github.com/openfoodfacts/robotoff/commit/dd6d81e3f62949eb89feaacf4d3d2c508f2ee495))
* store fingerprint of all images ([ed8fd38](https://github.com/openfoodfacts/robotoff/commit/ed8fd388215268a2709ae055cf223e9c65139dd4))


### Bug Fixes

* improve add-logo-to-ann CLI command ([c67b8ff](https://github.com/openfoodfacts/robotoff/commit/c67b8ff03e433da9216357f1078e6aae1480e8d3))
* set K_NEAREST_NEIGHBORS to 10 (instead of 100) ([a177e13](https://github.com/openfoodfacts/robotoff/commit/a177e137bea4b6ed50fe59bc3ba320b4e16218a1))


### Technical

* use json.dump instead of f.write + json.dumps ([60f15e9](https://github.com/openfoodfacts/robotoff/commit/60f15e923de2a04822d1e48ed382f23fe385ca74))

## [1.36.0](https://github.com/openfoodfacts/robotoff/compare/v1.35.0...v1.36.0) (2023-10-16)


### Features

* use openfoodfacts SDK for OCR processing ([6344936](https://github.com/openfoodfacts/robotoff/commit/63449367eea12f46b576fe23a6631563bc0fa2c6))


### Bug Fixes

* update pymongo ([cac6241](https://github.com/openfoodfacts/robotoff/commit/cac624193a50cf7fd9fffa80b03eba66c4f85e8a))
* use new version of openfoodfacts-python ([a7d0b28](https://github.com/openfoodfacts/robotoff/commit/a7d0b28dbd4df5252578acb06f8a3a07430de0c8))


### Technical

* upgrade to Pydantic V2 ([6979cec](https://github.com/openfoodfacts/robotoff/commit/6979cecb62557b4f7c56afcd409db99b8f898a5f))

## [1.35.0](https://github.com/openfoodfacts/robotoff/compare/v1.34.1...v1.35.0) (2023-09-04)


### Features

* remove matcher predictor completely ([d0847c6](https://github.com/openfoodfacts/robotoff/commit/d0847c6036eec65a12f0af3d5f6c7c3f89896f45))
* remove matcher predictor from API ([de97f9f](https://github.com/openfoodfacts/robotoff/commit/de97f9fa43d342a2d64e9611a7d4ff1f07e81dbd))


### Bug Fixes

* Crowdin PR title ([1adfc96](https://github.com/openfoodfacts/robotoff/commit/1adfc9610f96ddabf5c3b7d6efd1dab962470814))
* don't initialize unit registry in product_weight.py ([468c4f6](https://github.com/openfoodfacts/robotoff/commit/468c4f65d2bba33ea13637e3b9556b8bd87e0dc7))
* fix wrong label rouge detection ([492fda4](https://github.com/openfoodfacts/robotoff/commit/492fda49a97e13bdf8f3c5fc7d9d421ea0a0426c)), closes [#1255](https://github.com/openfoodfacts/robotoff/issues/1255)


### Technical

* add docstring ([279ced1](https://github.com/openfoodfacts/robotoff/commit/279ced16115d3da5b6616d4d71ef1723bf2543af))

## [1.34.1](https://github.com/openfoodfacts/robotoff/compare/v1.34.0...v1.34.1) (2023-08-31)


### Bug Fixes

* fix bug in product_weight.py ([2e94d11](https://github.com/openfoodfacts/robotoff/commit/2e94d115732d05b9f9ca6addcdef2cb0b6aac180))
* update normalize_weight function after Pint upgrade ([80d3a09](https://github.com/openfoodfacts/robotoff/commit/80d3a09af24447570a7c09362e6c416194add671))
* update packaging denylist ([23e6e26](https://github.com/openfoodfacts/robotoff/commit/23e6e2641d8881fd5a36d8a1f9611dc6d8a0b060))


### Technical

* update dependencies ([5353f1c](https://github.com/openfoodfacts/robotoff/commit/5353f1caaef7f82be5b199bf864670b150233c72))

## [1.34.0](https://github.com/openfoodfacts/robotoff/compare/v1.33.0...v1.34.0) (2023-08-31)


### Features

* apply automatically nutrition images insights ([6d79855](https://github.com/openfoodfacts/robotoff/commit/6d79855f9f02aa2fc355f17e7cb1112d88997554))


### Bug Fixes

* sort label whitelist ([7b13090](https://github.com/openfoodfacts/robotoff/commit/7b1309063279b769607d13f121aefecab26f4a06))
* Update packaging material shape map for fr ([450409f](https://github.com/openfoodfacts/robotoff/commit/450409fea8bcb2cf783b5286ae04225c52364e59)), closes [#1250](https://github.com/openfoodfacts/robotoff/issues/1250)
* update packaging shape denylist ([84256ba](https://github.com/openfoodfacts/robotoff/commit/84256ba9539095c2e6833037ba9f173a633b66c9))


### Technical

* update brand blacklist ([625111b](https://github.com/openfoodfacts/robotoff/commit/625111b4da013e982b6768098c5befe767220fce))
* update label whitelist ([70bcfaf](https://github.com/openfoodfacts/robotoff/commit/70bcfaf6c742a6617320ca7faafc198e10ef34a3))

## [1.33.0](https://github.com/openfoodfacts/robotoff/compare/v1.32.1...v1.33.0) (2023-08-29)


### Features

* disable matcher predictor for category ([07ada5b](https://github.com/openfoodfacts/robotoff/commit/07ada5bd0bde125f3e3cc3b718c5bcf97b8b05e3))


### Bug Fixes

* add new exception for packaging ([e397e57](https://github.com/openfoodfacts/robotoff/commit/e397e577a1c38a7f0ded9ad45ce8b41010ad5bd8)), closes [#1058](https://github.com/openfoodfacts/robotoff/issues/1058)
* disable temporarily en:eu-non-agriculture and en:eu-agriculture ([043b96c](https://github.com/openfoodfacts/robotoff/commit/043b96c3f64507e860edab04eb4a3eabb692c415))
* don't generate weight insight when value is suspicious ([51a19fa](https://github.com/openfoodfacts/robotoff/commit/51a19fa46efdb238d0eedfa69b7540f0a1333984)), closes [#302](https://github.com/openfoodfacts/robotoff/issues/302)
* fix bug in refresh_insights ([dd19b6e](https://github.com/openfoodfacts/robotoff/commit/dd19b6e5ad778a648ea32b718884abdcd1a94c72))
* fix init-elasticsearch Makefile command ([2d729d4](https://github.com/openfoodfacts/robotoff/commit/2d729d4c2ff67f5db29c802e9bd46c627375b519))
* remove pdo and pgi regex ([008bd9d](https://github.com/openfoodfacts/robotoff/commit/008bd9dd840c5a392dc73da839da7196dc5bb53d))
* update label whitelist ([2497642](https://github.com/openfoodfacts/robotoff/commit/2497642bf81d4ebcc1745d280d606e10e97c1246))


### Technical

* pin openfoodfacts dependency ([1f9ac80](https://github.com/openfoodfacts/robotoff/commit/1f9ac800e8a0545661edb7f9667adbf9609afb2b))
* update branc blacklist and label whitelist ([d7948c5](https://github.com/openfoodfacts/robotoff/commit/d7948c5a60a58b24186af7ad4ab6067e1ac689a9))
* upgrade requests ([f937442](https://github.com/openfoodfacts/robotoff/commit/f937442f36eeb9f451d27ff675364a5c16e044dc))

## [1.32.1](https://github.com/openfoodfacts/robotoff/compare/v1.32.0...v1.32.1) (2023-08-28)


### Bug Fixes

* add some items to brand taxonomy blacklist ([ef0b626](https://github.com/openfoodfacts/robotoff/commit/ef0b626e171514a488a52c45e23f18e61a6bd243))
* auupdate brand_taxonomy_blacklist.txt ([739c748](https://github.com/openfoodfacts/robotoff/commit/739c748428e792191328cfec55fdbe3008c1442d))
* brand blocklist ([3055d13](https://github.com/openfoodfacts/robotoff/commit/3055d135c095d61fbea683502fe40985e4925273))
* fix bug in doctext.py and improve script ([b54ef2b](https://github.com/openfoodfacts/robotoff/commit/b54ef2b227db8f6c58e3ba616277adabe6950d7b))
* fix bug in pprint ([c620d59](https://github.com/openfoodfacts/robotoff/commit/c620d590d0a29b9f2d65fc51601ebdc699aa5f42))
* fix call to get_insights_ ([5d909b9](https://github.com/openfoodfacts/robotoff/commit/5d909b969440d250b22233f00ec4012c6338b2ad))
* fix is_data_required method signature ([6342832](https://github.com/openfoodfacts/robotoff/commit/6342832cabc7f5ffb440748b99b9f7405a0fa6f5))
* fix wrong call to add_category_insight in tests ([69b5f1e](https://github.com/openfoodfacts/robotoff/commit/69b5f1e21373e3cc4f70aa01f44e299f3134f835))
* improve brand exclusion for 'taxonomy' predictor ([7705823](https://github.com/openfoodfacts/robotoff/commit/770582338960610ab7c4ef9d81f17a6c67e1b250))
* improve candidate generation in LabelInsightImporter ([51e046a](https://github.com/openfoodfacts/robotoff/commit/51e046a193591a2ef3294ae7a2cbfe32506a209f))
* mark use of md5 and sha1 hash function as safe ([ca0963f](https://github.com/openfoodfacts/robotoff/commit/ca0963f83f2d43dbd6db3f657d39921dbae76243))
* set automatic_processing=None for flashtext label insight ([ba6ceb7](https://github.com/openfoodfacts/robotoff/commit/ba6ceb72bed3296b16a9b9d9bb309c9910d838d4))


### Technical

* fix deepsource warning ([58ca3e7](https://github.com/openfoodfacts/robotoff/commit/58ca3e7560d27fb9318a819989e82e57ed634aa0))
* remove legacy function mark_insights ([9460393](https://github.com/openfoodfacts/robotoff/commit/9460393475b09c90357a6d406a88b867555a7794))
* remove legacy functions in visualization_utils.py ([b620062](https://github.com/openfoodfacts/robotoff/commit/b620062664af4734693d4a5950c247883a5e80e2))
* remove pypi.yml action ([1773b87](https://github.com/openfoodfacts/robotoff/commit/1773b87f77c82e59ffa6297400a61c9d30e91890))
* switch to f-strings ([fdeba36](https://github.com/openfoodfacts/robotoff/commit/fdeba36e21dbdd5ed4ec71ff2ea7a8d5b4e27035))
* update brand taxonomy blacklist ([df19331](https://github.com/openfoodfacts/robotoff/commit/df1933174d67711c0f3cd80bacfb7705df626565))
* use consistent logging arg passing ([2385889](https://github.com/openfoodfacts/robotoff/commit/238588945c6e10c8b3175496b079974fe76165ac))

## [1.32.0](https://github.com/openfoodfacts/robotoff/compare/v1.31.1...v1.32.0) (2023-08-21)


### Features

* add a few more stores for automatic extraction ([878f7ed](https://github.com/openfoodfacts/robotoff/commit/878f7ed65cf8aaac1ca66e7f7cee6ee28741696c))
* Stores from across Europe ([1274243](https://github.com/openfoodfacts/robotoff/commit/1274243f80a1a7edef18a688f23eeceebfcedea0))


### Bug Fixes

* fix re-imports ([9a6bcbe](https://github.com/openfoodfacts/robotoff/commit/9a6bcbe6a3bbc6337a1ba20651c0d31a23c40ac7))
* fix some deepsource performance warnings ([7424587](https://github.com/openfoodfacts/robotoff/commit/74245872aaa787dc7457b4294351589f8b607d9f))
* remove legacy code ([1aa13ad](https://github.com/openfoodfacts/robotoff/commit/1aa13adf85336c919364e2a9c13f1a95aa74b315))
* use prod JSONL dump in staging ([07ab8fd](https://github.com/openfoodfacts/robotoff/commit/07ab8fdc102f7bc93a00634d263f3a87d8cb7d72))


### Technical

* add make command to download ingredient detection model ([fa305cd](https://github.com/openfoodfacts/robotoff/commit/fa305cd34bdb168bc2e190aa963fdc92f8374008))
* delay scheduled jobs relying on JSONL export ([d4033f5](https://github.com/openfoodfacts/robotoff/commit/d4033f5524cf81362d12589cead667440145d408))
* fix release-please.yml ([07a5ff7](https://github.com/openfoodfacts/robotoff/commit/07a5ff78a4d134c74c492a0983b3d8e55221f235))
* improve release changelog ([57d4bbf](https://github.com/openfoodfacts/robotoff/commit/57d4bbf595f85a7305c47e17659aab2cf07c0c0e))
* rename master to main (update workflows and doc) ([b9e1107](https://github.com/openfoodfacts/robotoff/commit/b9e11071c90947fffbd19b9d2a7737d2d917c718))

## [1.31.1](https://github.com/openfoodfacts/robotoff/compare/v1.31.0...v1.31.1) (2023-08-14)


### Bug Fixes

* add robots.txt ([10387ff](https://github.com/openfoodfacts/robotoff/commit/10387ffe83c91d2e42595873367808e5cc238e91))

## [1.31.0](https://github.com/openfoodfacts/robotoff/compare/v1.30.1...v1.31.0) (2023-08-11)


### Features

* New Crowdin updates ([#1152](https://github.com/openfoodfacts/robotoff/issues/1152)) ([a0eae2d](https://github.com/openfoodfacts/robotoff/commit/a0eae2d39093df7f7bd2ceffc4b96e49549f268f))


### Bug Fixes

* add mdx-truly-sane-list extension back ([460dae6](https://github.com/openfoodfacts/robotoff/commit/460dae688061f0f49adb93e2c300f95201b3d119))
* barcode should not be an empty str in webhook call ([a7b6472](https://github.com/openfoodfacts/robotoff/commit/a7b64727f568c716cbbc9609cfca69b15a23d722))
* fix bug in run_upc_detection ([a62319d](https://github.com/openfoodfacts/robotoff/commit/a62319d69ddf13a50ca663ce6074722705fdce4c))
* remove above-threshold-campaign ([326626a](https://github.com/openfoodfacts/robotoff/commit/326626ae5f44f31d5ca3a727f9119056116d43ab))
* replace parameter `country` by `countries` ([56b0804](https://github.com/openfoodfacts/robotoff/commit/56b0804d53f3ef7aaadffc5f36d8f3e65d11ab7b))
* send release info to Sentry ([58acf39](https://github.com/openfoodfacts/robotoff/commit/58acf397165309fc2eb2282e4c3b36461f3661d8))
* use openfoodfacts-python package for taxonomy processing ([eaaeca3](https://github.com/openfoodfacts/robotoff/commit/eaaeca3e46bc5d6494414964e0390289c63ccafe))


### Documentation

* update OpenAPI documentation ([6da2978](https://github.com/openfoodfacts/robotoff/commit/6da29786991804279c032d336ded9b47ba1ca532))

## [1.30.1](https://github.com/openfoodfacts/robotoff/compare/v1.30.0...v1.30.1) (2023-06-30)


### Bug Fixes

* allow to provide image embedding as input in /predict/category ([655a230](https://github.com/openfoodfacts/robotoff/commit/655a2305e1b6780abb5eea8b19c8352f7d337324))
* make more robust unit tests ([bbebf3f](https://github.com/openfoodfacts/robotoff/commit/bbebf3fc937e51b880d0210529915cd07a8651bb))
* remove false positive label for moderation ([bfd2b58](https://github.com/openfoodfacts/robotoff/commit/bfd2b586c2706624050a93eb9f8e7d8e4c1769e4))
* remove previous categorization model ([058d0cc](https://github.com/openfoodfacts/robotoff/commit/058d0cc6ba66db0308b1abd67bbe2662eeabc647))
* update /predict/category schema to accept images as input ([728246e](https://github.com/openfoodfacts/robotoff/commit/728246ebbba932ed9401f38ff50fcc10ccfd03d5))


### Documentation

* improve OpenAPI documentation ([c4b3843](https://github.com/openfoodfacts/robotoff/commit/c4b38433a0fb6edf38858e9a8728599140c95a56))
* improve OpenAPI documentation (2) ([db5df96](https://github.com/openfoodfacts/robotoff/commit/db5df9614964beb05a100ccd31c9e52a5de8b22d))
* update OpenAPI documentation ([07d1136](https://github.com/openfoodfacts/robotoff/commit/07d113680f19b70dfa1354869b9e0f6b05cefad9))

## [1.30.0](https://github.com/openfoodfacts/robotoff/compare/v1.29.0...v1.30.0) (2023-06-22)


### Features

* add fasttext langid module ([432027b](https://github.com/openfoodfacts/robotoff/commit/432027bf61daf06c71ce9ccc49b307add06aea86)), closes [#1122](https://github.com/openfoodfacts/robotoff/issues/1122)
* add first version of ingredient list NER + API ([9083bdb](https://github.com/openfoodfacts/robotoff/commit/9083bdb8f995b0dead012c3fa34e4ded05659ec2))


### Bug Fixes

* add `insight_types` parameter in /question/{barcode} ([fc7b76a](https://github.com/openfoodfacts/robotoff/commit/fc7b76a753df8d8c951c1965f9a6d730f06cd6dc)), closes [#1139](https://github.com/openfoodfacts/robotoff/issues/1139)
* fix default FASTTEXT_MODEL_DIR value ([e4cc4e7](https://github.com/openfoodfacts/robotoff/commit/e4cc4e701ecb73467d483ede16cef349973b1e22))
* improve error handling in /predict/ingredient_list route ([7a996cc](https://github.com/openfoodfacts/robotoff/commit/7a996cc3a7a4942e088ad7b0cea5d78492071222))
* improve ingredient detection pipeline ([9ff8aec](https://github.com/openfoodfacts/robotoff/commit/9ff8aec390df2a3f2a5bd3ac2d74144442a240c2))
* remove spellcheck module ([916132a](https://github.com/openfoodfacts/robotoff/commit/916132a4df39241515b81a51aab2d1daf45a3674))
* sort product questions by priority ([5ea69e3](https://github.com/openfoodfacts/robotoff/commit/5ea69e39138f1c12d14b4db787cb3769eb262013)), closes [#1138](https://github.com/openfoodfacts/robotoff/issues/1138)
* update apscheduler ([dd4eed8](https://github.com/openfoodfacts/robotoff/commit/dd4eed8967402a02aaadf09a8e92da92a02222c9))
* update poetry install command in Dockerfile ([75f8b34](https://github.com/openfoodfacts/robotoff/commit/75f8b342ebf6348b80cb7c06cf41908a54a768aa))

## [1.29.0](https://github.com/openfoodfacts/robotoff/compare/v1.28.1...v1.29.0) (2023-06-01)


### Features

* Improve /predict/{nutrient|ocr_prediction} routes ([f06a45a](https://github.com/openfoodfacts/robotoff/commit/f06a45a8cc185fc0a19e23c8e12ce38560aa36bf))
* improve nutrition image bounding box detection ([737b630](https://github.com/openfoodfacts/robotoff/commit/737b630bc973e01d14e58cf60cdcf1c2b3526867))


### Bug Fixes

* add CLI command to pretty print OCR result ([26f44a4](https://github.com/openfoodfacts/robotoff/commit/26f44a4d7a8380e88662f9623714694bc7a94438))
* display diffs in /webhook/products route ([07255c6](https://github.com/openfoodfacts/robotoff/commit/07255c60b937766ee9124e714638c2124a1f5045))
* fix ENABLE_PRODUCT_CHECK flag ([dd1d09f](https://github.com/openfoodfacts/robotoff/commit/dd1d09f626f96108681331946ae7f8ae1e8d761c))
* fix NutritionImageImporter.generate_candidate ([74e346c](https://github.com/openfoodfacts/robotoff/commit/74e346cb17d1dc5e024f2370ed638e5566aa5b68))
* fix wrong paragraph offset for OCR ([abb54a6](https://github.com/openfoodfacts/robotoff/commit/abb54a6c05b5e230320f5bac398a87e4ffbe43e3))
* improve /predict/nutrition route ([95d953b](https://github.com/openfoodfacts/robotoff/commit/95d953bc78780101314a21b0a058c72d43148dce))
* only display most important services in make log command ([60b2843](https://github.com/openfoodfacts/robotoff/commit/60b2843042fdf680b1dbf5632f9b2d770b0f0a8d))
* rename compute_intersection_bounding_box function ([d8d732c](https://github.com/openfoodfacts/robotoff/commit/d8d732cd7ad07fd8390ea92c944b4f60864d1789))
* support pro platform for MongoDB queries and image/OCR URLs ([a3ac603](https://github.com/openfoodfacts/robotoff/commit/a3ac60370d9294b8e63d8fcf9011ecb869852037))
* update SSH_PROXY_HOST for deployment ([a8b8292](https://github.com/openfoodfacts/robotoff/commit/a8b82928f7410653d693ba1c6b5a5fb698dc1fea))

## [1.28.1](https://github.com/openfoodfacts/robotoff/compare/v1.28.0...v1.28.1) (2023-05-11)


### Bug Fixes

* add a Make command to init elasticsearch ([68e7edf](https://github.com/openfoodfacts/robotoff/commit/68e7edf0f686ca29fdf430ce12cc585f7dce93df))
* add danish translation for nutrient detection ([ba02a63](https://github.com/openfoodfacts/robotoff/commit/ba02a638087519967687162f7bc57867e79496d5))
* add log messages to init-elasticsearch CLI command ([e950cbd](https://github.com/openfoodfacts/robotoff/commit/e950cbd04e39f4970a850cb9a7c4b4e45b610ef1))
* add ml-gpu.yml docker-compose file ([a005b0f](https://github.com/openfoodfacts/robotoff/commit/a005b0fbfce6c155e68586140c32ae46a88475d3))
* don't update elasticsearch indices in _update_data scheduler job ([c12f803](https://github.com/openfoodfacts/robotoff/commit/c12f80326a289d2b68fe0e90af777736516aeb27))
* don't update product dump at scheduler startup ([4bee57c](https://github.com/openfoodfacts/robotoff/commit/4bee57caf210873eb63cf541707bbb4554402165))
* fix dl-models command ([ef26311](https://github.com/openfoodfacts/robotoff/commit/ef26311748926ef01f2880c52c071e2da50e6f79))
* fix launch-burst-worker command ([4a49ac3](https://github.com/openfoodfacts/robotoff/commit/4a49ac3836b06c51cae37dda2ae1f14488d2a025))
* fix logo elasticsearch index mapping ([8a5a119](https://github.com/openfoodfacts/robotoff/commit/8a5a119b0aec7f2fa9bc00618ebd38b755c67326))
* fix make dl-models command ([d6a3b25](https://github.com/openfoodfacts/robotoff/commit/d6a3b25e4e0fa5fcfc39107c474f3ad4d29ee368))
* fix unit tests ([90cce2a](https://github.com/openfoodfacts/robotoff/commit/90cce2a362e8df0c718ea0332871eb0cc0c10916))
* init elasticsearch during make dev call ([0ac9051](https://github.com/openfoodfacts/robotoff/commit/0ac90510bafb019b38a4d370b17032901e0c7174))
* remove tf_models/models.config file ([eb54e81](https://github.com/openfoodfacts/robotoff/commit/eb54e812f99b75733b0e7ec374d5bb0156126e73))
* use explicit model control model on Triton ([fb46bf8](https://github.com/openfoodfacts/robotoff/commit/fb46bf8f5b311a6cf14504ba5040740d8610cc13))


### Documentation

* fix comment in prediction.ocr.dataclass ([4bdb768](https://github.com/openfoodfacts/robotoff/commit/4bdb768e9f3d5c79b6bc828acf4d2eb0e45bca8d))
* improve documentation about prediction processing ([ab75c09](https://github.com/openfoodfacts/robotoff/commit/ab75c0988e2322d019d198d04b784d54417d467e))

## [1.28.0](https://github.com/openfoodfacts/robotoff/compare/v1.27.2...v1.28.0) (2023-05-02)


### Features

* add UPC Image detector ([f592acd](https://github.com/openfoodfacts/robotoff/commit/f592acd1ce36327bc9b1e05d383d4887847907f8))


### Bug Fixes

* add question formatter for is_upc_image insights ([bb6a6da](https://github.com/openfoodfacts/robotoff/commit/bb6a6da1f2e48bbd77e82c44e4ed246a9b960011))
* enforce max doc length of 79 with flake8 ([d7d58d6](https://github.com/openfoodfacts/robotoff/commit/d7d58d6c985aa60ef13dc76536a2a1bcffdaeb0d))
* improve import-logo-embeddings CLI command ([34139d1](https://github.com/openfoodfacts/robotoff/commit/34139d15a4028cf10bc76b712027b3557be13afe))
* remove keras category classifier 2.0 model ([4038a6e](https://github.com/openfoodfacts/robotoff/commit/4038a6e9f1dd9eb25c172d10a2476446fc1cbbd7))
* remove legacy model download commands ([4a5ef8f](https://github.com/openfoodfacts/robotoff/commit/4a5ef8f7f40e4c19ca59669c5cb948c1c795e975))
* remove Tensorflow Serving entirely ([f260887](https://github.com/openfoodfacts/robotoff/commit/f26088738e1f6dd0b4b06ca9328754c595f8800b))
* set predictor_version and predictor for is_upc_image preds/insights ([a9eefc5](https://github.com/openfoodfacts/robotoff/commit/a9eefc532e2aa3814a92b975ca987463dffc5a16))

## [1.27.2](https://github.com/openfoodfacts/robotoff/compare/v1.27.1...v1.27.2) (2023-04-28)


### Bug Fixes

* fix import_insights CLI command ([d151b3d](https://github.com/openfoodfacts/robotoff/commit/d151b3d2bd723c8a19a4edf4d84995c566598d9c))

## [1.27.1](https://github.com/openfoodfacts/robotoff/compare/v1.27.0...v1.27.1) (2023-04-28)


### Bug Fixes

* make ServerType inherit from str ([4f4244c](https://github.com/openfoodfacts/robotoff/commit/4f4244c290122f7ada9f5f0f10371a26a82c6f16))

## [1.27.0](https://github.com/openfoodfacts/robotoff/compare/v1.26.1...v1.27.0) (2023-04-27)


### Features

* introduce prediction deletion ([3dc0a44](https://github.com/openfoodfacts/robotoff/commit/3dc0a448d76005bdc4fe797f7a6b395501a45604))


### Bug Fixes

* add missing test JSON data ([d885729](https://github.com/openfoodfacts/robotoff/commit/d88572938a00760bfb4352ab1f9d42c772e2a150))
* create robotoff.utils.text module ([5d2bc86](https://github.com/openfoodfacts/robotoff/commit/5d2bc865904f18662ab4d2352fb8a46a91689950))
* don't raise error when getting bounding box by default ([9208b42](https://github.com/openfoodfacts/robotoff/commit/9208b42518b61fa4637ff2024ae956042329a232))
* fix mypy typing issues ([107cc23](https://github.com/openfoodfacts/robotoff/commit/107cc23d9c6da57827dbf46777151b3798e0db8c))
* fix span offset issue when case_sensitive=False ([15eb2f8](https://github.com/openfoodfacts/robotoff/commit/15eb2f8d0225ca5b64c11070f9a35ab5ee06a0ee))
* integrate flashtext into robotoff codebase ([3ec9979](https://github.com/openfoodfacts/robotoff/commit/3ec99793a5b358da2415bdc2df7e2ba6920b3494))
* remove debug log message ([bc80eee](https://github.com/openfoodfacts/robotoff/commit/bc80eeed0a86d3f67fd4f580f32dee89ab6739ec))

## [1.26.1](https://github.com/openfoodfacts/robotoff/compare/v1.26.0...v1.26.1) (2023-04-26)


### Bug Fixes

* fix NutritionImageImporter.is_conflicting_insight ([581376e](https://github.com/openfoodfacts/robotoff/commit/581376efae28deb1150321d0c57365766c0a5272))


### Documentation

* fix typo in nutrition-table.md ([3357adc](https://github.com/openfoodfacts/robotoff/commit/3357adc8cb0a6f80aa5377464a54f9f871a094dc))

## [1.26.0](https://github.com/openfoodfacts/robotoff/compare/v1.25.4...v1.26.0) (2023-04-24)


### Features

* add nutrition_image insight type ([27fd62c](https://github.com/openfoodfacts/robotoff/commit/27fd62c55712902c014f3f6ea8a640cd52798e6d))


### Bug Fixes

* add debug log message in importer.py ([6c5febc](https://github.com/openfoodfacts/robotoff/commit/6c5febc81f62ab816bda6cbcfe2251795f3734d2))
* enable again nutrition table object detection ([b529769](https://github.com/openfoodfacts/robotoff/commit/b5297693feb37aae29045fa29741b73855e3d943))
* fix error raised when releasing expired lock ([0859eef](https://github.com/openfoodfacts/robotoff/commit/0859eef7fffdb96d0356276d712e8fdea7b820b5))
* fix Github action ([3847226](https://github.com/openfoodfacts/robotoff/commit/38472267510cff721a715281cfbe4429270b59cf))
* fix issue in unit tests ([271b2bb](https://github.com/openfoodfacts/robotoff/commit/271b2bb2ea07d3627009b5cdf2513cc614a38736))
* fix issue with crop in `select_rotate_image` ([b40984d](https://github.com/openfoodfacts/robotoff/commit/b40984dab3fef6f2d4f314542b22c44090dd589b))
* fix livecheck script ([#1103](https://github.com/openfoodfacts/robotoff/issues/1103)) ([aa1ab8a](https://github.com/openfoodfacts/robotoff/commit/aa1ab8a09acb00c317012c10538570b24a4b3f38))
* fix type error in slack.py ([d076be7](https://github.com/openfoodfacts/robotoff/commit/d076be71020b0f43980b73877dd4e8429fd9c9d3))
* increase lock expire duration during insight import (to 5 min) ([fb8b787](https://github.com/openfoodfacts/robotoff/commit/fb8b787d4316995e6c73b527b66c8ba0b33261a6))
* increase min score for nutrition image detector model ([fd29693](https://github.com/openfoodfacts/robotoff/commit/fd29693f326651f6ffd7ef015f8a55b8b1154d6e))
* try to trigger Github actions on push on master ([08902b6](https://github.com/openfoodfacts/robotoff/commit/08902b695621b0a012eed8eb4e352822b1ce345f))
* try to trigger Github actions on push on master (2) ([bda2abf](https://github.com/openfoodfacts/robotoff/commit/bda2abf861c75ab559a1272ad58b6253c6ca4638))

## [1.25.4](https://github.com/openfoodfacts/robotoff/compare/v1.25.3...v1.25.4) (2023-04-21)


### Bug Fixes

* always use the same queue for jobs of the same product ([e9f066c](https://github.com/openfoodfacts/robotoff/commit/e9f066c6a0f154d076f8d4029855407f7d59c13c))
* fix typo in Makefile ([6594035](https://github.com/openfoodfacts/robotoff/commit/6594035e663b445d51042e8e24e9e7d41ce85549))
* improve Robotoff edit message ([4b5f230](https://github.com/openfoodfacts/robotoff/commit/4b5f2305803f8bd5a0bba86e9684526ee956d2de))
* send webhook update jobs for all projects ([7949dec](https://github.com/openfoodfacts/robotoff/commit/7949dec1716ecf74101a27c2bc88cee6ea7a1bc5))
* update DATASET_CHECK_MIN_PRODUCT_COUNT ([e5555cc](https://github.com/openfoodfacts/robotoff/commit/e5555cc26b17a3fdd5b6fed5b4fe7cd3dbd217a4))
* use md5 hash function in `get_high_queue` ([29befd6](https://github.com/openfoodfacts/robotoff/commit/29befd6a3b05877e318e6cce4fe47ba1842f66b6))


### Documentation

* incorrect link in README.md predictions section ([bb63afc](https://github.com/openfoodfacts/robotoff/commit/bb63afcf6cdfd4e05dae60a2b466251620392859))
* move a comment in docker-compose.yml ([b687265](https://github.com/openfoodfacts/robotoff/commit/b687265ad7bd26ba8ec2eeb25f26935c860af364))
* update maintenance.md ([842eaf3](https://github.com/openfoodfacts/robotoff/commit/842eaf3492128eff8419ab41b0569ade931f966a))

## [1.25.3](https://github.com/openfoodfacts/robotoff/compare/v1.25.2...v1.25.3) (2023-04-16)


### Bug Fixes

* improve scheduled job refresh_insight ([79f68a9](https://github.com/openfoodfacts/robotoff/commit/79f68a9144e865ce881301df4c82479a09e219e1))
* remove unused server_domain method ([2b43ff6](https://github.com/openfoodfacts/robotoff/commit/2b43ff657d1dbadf56c0d2b4b27487ea740fab10))
* use world subdomain instead of api everywhere ([09cb67e](https://github.com/openfoodfacts/robotoff/commit/09cb67e121fbd193e479201baad2a2e4fefb6649))

## [1.25.2](https://github.com/openfoodfacts/robotoff/compare/v1.25.1...v1.25.2) (2023-04-16)


### Bug Fixes

* fix call to `update_product` ([16c6453](https://github.com/openfoodfacts/robotoff/commit/16c645329ee3343b1ecb96fa2721ebb086f807eb))

## [1.25.1](https://github.com/openfoodfacts/robotoff/compare/v1.25.0...v1.25.1) (2023-04-16)


### Bug Fixes

* display Product Opener response during OFF product update if an ([91d05d4](https://github.com/openfoodfacts/robotoff/commit/91d05d4a83075741d8b580c1c18a00817b9143c5))

## [1.25.0](https://github.com/openfoodfacts/robotoff/compare/v1.24.2...v1.25.0) (2023-04-16)


### Features

* add a function to send image to OFF ([f6ac894](https://github.com/openfoodfacts/robotoff/commit/f6ac89414024c1f7a66801cf045aef29f3ee54a9))
* implement real multi-platform support (OFF, OBF,...) ([9464f46](https://github.com/openfoodfacts/robotoff/commit/9464f46df11542d42a0987666506a90fc9f367d3))
* support multiple MongoDB DB (multi-project) ([2c36b6f](https://github.com/openfoodfacts/robotoff/commit/2c36b6f7c815fd3d1ef4fc46c7862954f7c34e1b))


### Bug Fixes

* add `server_type` field to logo indexed in ES ([506ab02](https://github.com/openfoodfacts/robotoff/commit/506ab0294852ca3ca9e036001c0a1759d9081d4a))
* add DISABLE_PRODUCT_CHECK settings ([a201fae](https://github.com/openfoodfacts/robotoff/commit/a201faeaaa03ca5abb90b6ec357c9bba8edc0568))
* fix in insert_images.py script ([8dd914f](https://github.com/openfoodfacts/robotoff/commit/8dd914f49288bc5a79e7578f3b97726676f4f45a))
* fix issue in settings (DISABLE_PRODUCT_CHECK value) ([232e5c6](https://github.com/openfoodfacts/robotoff/commit/232e5c6e91a3b130336980afb2651faa586e8c62))
* fix refresh-insight scheduled job ([d363cf8](https://github.com/openfoodfacts/robotoff/commit/d363cf861bfce7e96de0fd72678c571c97603800))
* fix value for ENABLE_PRODUCT_CHECK in local env ([20a58d5](https://github.com/openfoodfacts/robotoff/commit/20a58d5768e9873f62e9eec38d113c61844ce141))
* fix wrong call to run_nutriscore_object_detection ([a211249](https://github.com/openfoodfacts/robotoff/commit/a2112495e7c695b23a2e59cc74d1df8337761381))
* fix wrongly formatted logging message ([3ef4a0d](https://github.com/openfoodfacts/robotoff/commit/3ef4a0ddce197cc8b7bba5a1d47ea7a015c4b531))
* rename DISABLE_PRODUCT_CHECK into ENABLE_PRODUCT_CHECK ([8c07478](https://github.com/openfoodfacts/robotoff/commit/8c0747845cc79669aa7b9e99d1128a31c4c33c79))
* rename en:gluten-free into en:no-gluten ([e1f6417](https://github.com/openfoodfacts/robotoff/commit/e1f6417c216fb76b15c7a1b6a0566d4214920e9c))
* replace call to lru_cache() by call to cache() ([191faab](https://github.com/openfoodfacts/robotoff/commit/191faab0c2d538f1d7f2e9243e9e2d7c842b8c34))
* suppress mypy warnings ([49a29b9](https://github.com/openfoodfacts/robotoff/commit/49a29b9ad80384a398fd39b97510086d25285260))
* switch log level to DEBUG ([d3ebd85](https://github.com/openfoodfacts/robotoff/commit/d3ebd85607fc9ec9db11a52189f8410acfa09b6a))


### Documentation

* add missing docstring parameter descriptions ([32cc8f8](https://github.com/openfoodfacts/robotoff/commit/32cc8f8546bc63d0633eeed2bbdb90ab1d2c4361))
* improve docstrings ([d4bb80b](https://github.com/openfoodfacts/robotoff/commit/d4bb80ba2a2d0d55ea6f91254bf3e77baa7d1d1c))
* improve documentation in add-predictor.md ([195f1fd](https://github.com/openfoodfacts/robotoff/commit/195f1fdd02ef38743f413f85879a5b2125b75445))
* improve documentation in add-predictor.md ([90bfda2](https://github.com/openfoodfacts/robotoff/commit/90bfda2382b0fe70f820e7adc4d7bf20dbe67933))
* improve Robotoff API documentation ([d930592](https://github.com/openfoodfacts/robotoff/commit/d9305928b118a0463d053c2472697e1c8b2aef7f))

## [1.24.2](https://github.com/openfoodfacts/robotoff/compare/v1.24.1...v1.24.2) (2023-04-06)


### Bug Fixes

* fix error in product weight insight ([6866739](https://github.com/openfoodfacts/robotoff/commit/6866739989b28d5c3f459f4f07a833aae26a8718))
* load lazily all resources in Robotoff ([4dfa93f](https://github.com/openfoodfacts/robotoff/commit/4dfa93f9822ae1246e0192fd00f32f7b548c1f84))
* move LogoLabelType to robotoff.types ([0cc7efe](https://github.com/openfoodfacts/robotoff/commit/0cc7efe512a3a5f1ae439b1dcc436d45b66a69d1))


### Documentation

* add documentation about how to add a predictor ([d467a4c](https://github.com/openfoodfacts/robotoff/commit/d467a4c982cb33ac83bf38676d3aa31d9c285e45))
* add documentation about interaction with Product Opener ([05c0781](https://github.com/openfoodfacts/robotoff/commit/05c078169fa4ee746552312e732d07d23ba4659c))
* add references to codebase in category-prediction.md ([56ccfba](https://github.com/openfoodfacts/robotoff/commit/56ccfba254e6b48af5310e007788f964b30f0e95))

## [1.24.1](https://github.com/openfoodfacts/robotoff/compare/v1.24.0...v1.24.1) (2023-04-05)


### Bug Fixes

* fix incorrect offset in get_words_from_indices ([547a867](https://github.com/openfoodfacts/robotoff/commit/547a867c530d811ecb22d5fb99183f32f158a2fe))

## [1.24.0](https://github.com/openfoodfacts/robotoff/compare/v1.23.1...v1.24.0) (2023-04-05)


### Features

* add function to get match bounding box ([5d7eafa](https://github.com/openfoodfacts/robotoff/commit/5d7eafa5b4c21efb9d5ca35bc53d63f3305c7c98))
* allow to match text on OCRResult ([73ae0e6](https://github.com/openfoodfacts/robotoff/commit/73ae0e6639649d248c4055a8867367633cb017e5))
* save bounding box information in OCR/flashtext predictions ([9d4d432](https://github.com/openfoodfacts/robotoff/commit/9d4d432025bd28a6ed863c8e44b2f0b18c1a4916))


### Bug Fixes

* add functions to delete/unselect an image ([ade0294](https://github.com/openfoodfacts/robotoff/commit/ade02946a8874a455a018d73e12139c5b63a9603))
* allow partial match in get_words_from_indices ([34cbd24](https://github.com/openfoodfacts/robotoff/commit/34cbd2434a4f872092fe7694828fb3206cc18bc0))
* allow to match across blocks ([c073129](https://github.com/openfoodfacts/robotoff/commit/c073129d375ffe6f684a0e4c14c1ce4c12ccd242))
* bug fix in product weight insight generation ([031e117](https://github.com/openfoodfacts/robotoff/commit/031e117c65e14b209556630d32ee2926b97c6f27))
* cache result word string in Word ([30bc347](https://github.com/openfoodfacts/robotoff/commit/30bc347e6e6863c60a974b2f967cb69add41e5da))
* convert absolute coordinates to relative ones ([e86e671](https://github.com/openfoodfacts/robotoff/commit/e86e67102b907d3c2eec64ba3a4cf0c38450a1a3))
* fix offset bug ([a6e1e51](https://github.com/openfoodfacts/robotoff/commit/a6e1e51d6aac060d8d36388d7cfaf4a419c5306f))
* make error message easier to understand during HTTP 404 during OCR fetch ([b352387](https://github.com/openfoodfacts/robotoff/commit/b3523876e81fb0cbf33639294a0d0ea077b54cda))
* remove text_annotations OCRField and use new text field ([f0637a4](https://github.com/openfoodfacts/robotoff/commit/f0637a4bdc1862e1ff12e8a860b7ec73fe614322))
* save mapping between position of words and full annotation text ([674ad77](https://github.com/openfoodfacts/robotoff/commit/674ad77edf895c79c8f65d952de66a4d5f311a39))
* use new computed text field in regex matching ([b29e1db](https://github.com/openfoodfacts/robotoff/commit/b29e1db0eb87a7cd243b9e0a4b122ff176bbc7ec))
* use re.I flag instead of lowercasing string ([0ecef5e](https://github.com/openfoodfacts/robotoff/commit/0ecef5e98a0d0e39b100671083548c674f53807b))
* use strip_accents_v1 when necessary ([f2ee677](https://github.com/openfoodfacts/robotoff/commit/f2ee677a6df3dfdce439a3c44b2790fb9cb8d95e))


### Documentation

* improve OCR class documentation ([b461669](https://github.com/openfoodfacts/robotoff/commit/b461669b83e9c32032c8e3a62f30ddb4a34654c5))
* improve OCR documentation ([0a76f83](https://github.com/openfoodfacts/robotoff/commit/0a76f83680c9009a75f8ce4fe8ae52c6e4f74b14))

## [1.23.1](https://github.com/openfoodfacts/robotoff/compare/v1.23.0...v1.23.1) (2023-03-16)


### Bug Fixes

* always select deepest categorized nodes in category importer ([aba33f8](https://github.com/openfoodfacts/robotoff/commit/aba33f8b591fe8d7224f3b5af835755f793a3135))
* improve healthcheck status check messages ([e24e136](https://github.com/openfoodfacts/robotoff/commit/e24e1361bf79ee2b424a844cc6d4a8c857c01efa))

## [1.23.0](https://github.com/openfoodfacts/robotoff/compare/v1.22.1...v1.23.0) (2023-03-15)


### Features

* add missing_category campaign to track products without categories ([b103e66](https://github.com/openfoodfacts/robotoff/commit/b103e664bd5ae468d2cdda046bb2f8e0e0d037d9))
* cache image embeddings in DB (ImageEmbedding table) ([ba25c75](https://github.com/openfoodfacts/robotoff/commit/ba25c7568be028140d32bfe8bce0782fa33c0fae))
* store neighbor categories for v3 categorizer models ([8d1d727](https://github.com/openfoodfacts/robotoff/commit/8d1d727bd90030486f8c4f313465716c98b9e56f))
* use keras new v3 model as default to predict categories ([c0f55cf](https://github.com/openfoodfacts/robotoff/commit/c0f55cff47ef204a784d361a0c16184f8d9c9a6e))
* use keras v3 model as default ([a2d23a3](https://github.com/openfoodfacts/robotoff/commit/a2d23a32d549270a1bc01ab39be09d44402438c3))
* use keras_image_embeddings_3_0 by default in categorize CLI ([737716e](https://github.com/openfoodfacts/robotoff/commit/737716ef57e08b13fadc1e539baaf519cb06ba4e))


### Bug Fixes

* allow to specify LOG_LEVEL in .env file ([50a3aa4](https://github.com/openfoodfacts/robotoff/commit/50a3aa4269cc1b027a8b5d65e85e422875b8651c))
* deprecate campaign parameter in /questions* ([82c26fe](https://github.com/openfoodfacts/robotoff/commit/82c26fe834960f2c21448b501166f35bf5263cde))
* exclude some categories from predictions ([503fa8d](https://github.com/openfoodfacts/robotoff/commit/503fa8d13a0961fad8d5baca5b58b5171c8994b9))
* fix bug in save_image_embeddings ([a600502](https://github.com/openfoodfacts/robotoff/commit/a60050279088e00f3e628a0306672d63f157d684))
* fix bug that occurs when image are missing in images table ([1968f56](https://github.com/openfoodfacts/robotoff/commit/1968f561b22c5d97367c67d318f4cd839430481f))
* fix edge-case bug when no image is available ([fac1ab1](https://github.com/openfoodfacts/robotoff/commit/fac1ab1c7a51c4fc0d18a1d9a719c61dcfd74cf5))
* fix newly introduced bug in category importer ([a1bb507](https://github.com/openfoodfacts/robotoff/commit/a1bb50731a08e6e7f709689d7660e73dcd4b4904))
* fix serialization bug in predict ([1a69ab2](https://github.com/openfoodfacts/robotoff/commit/1a69ab2ef3e7ad15e78f7c0dee10ef62631b12e5))
* fix SonarCloud-detected bug in BaseURLProvider ([290a3fb](https://github.com/openfoodfacts/robotoff/commit/290a3fbc06a0ffc612a1c782c154282036e4b68f))
* fix unit tests ([61c6177](https://github.com/openfoodfacts/robotoff/commit/61c6177f1650b48dcf304a4377cb608c4f677b77))
* fix unit tests ([0a3702f](https://github.com/openfoodfacts/robotoff/commit/0a3702f57ef7dfc4e0e406dd5e4376956445bc72))
* ignore predicted category if it no longer exist in taxonomy ([c3c4fbe](https://github.com/openfoodfacts/robotoff/commit/c3c4fbe09c1311cd977d2b5b160eaf292a5fda20))
* move save_image function to new robotoff.images module ([6efdaf2](https://github.com/openfoodfacts/robotoff/commit/6efdaf24104a881f9369ed1b7f0c8bec045c6f83))
* pass stub as argument in predict for easier testing ([807c157](https://github.com/openfoodfacts/robotoff/commit/807c157bce8d9769f3f210e2ec5a811db6b53338))
* relax checks in save_images function ([bcf998f](https://github.com/openfoodfacts/robotoff/commit/bcf998f8fd7b7c8a0533527a4c2b4f3eb7ed53d4))
* remove legacy unit tests ([6f3e5e2](https://github.com/openfoodfacts/robotoff/commit/6f3e5e22af8a8cbed8098fb9c13e97042a00a9d0))


### Documentation

* add comment in build_triton_request function ([cf1e8db](https://github.com/openfoodfacts/robotoff/commit/cf1e8db1bf73af8c9e71d6b5d306387ca26fa569))
* add documentation about category prediction ([0a21476](https://github.com/openfoodfacts/robotoff/commit/0a2147679390207fdb85084f1aa3872c4284f54e))

## [1.22.1](https://github.com/openfoodfacts/robotoff/compare/v1.22.0...v1.22.1) (2023-03-13)


### Bug Fixes

* don't generate image embedding/fetch OCR texts if not required ([93fc96d](https://github.com/openfoodfacts/robotoff/commit/93fc96d235aaee4ad94f05737022809f94b96456))

## [1.22.0](https://github.com/openfoodfacts/robotoff/compare/v1.21.0...v1.22.0) (2023-03-12)


### Features

* add model with image embeddings as input ([d79bbc2](https://github.com/openfoodfacts/robotoff/commit/d79bbc22bb9b41952b6994256334ee6e15ef68f5))


### Bug Fixes

* add authentication for .net Product Opener when fetching products ([18cbb20](https://github.com/openfoodfacts/robotoff/commit/18cbb20c8778c46e38e7a78ac4ffa2392ac44baf))
* add object detection label assets to repository ([c925558](https://github.com/openfoodfacts/robotoff/commit/c925558f2607c769dab848ca425db11e30fb0bd0))
* add support for git LFS ([d6db888](https://github.com/openfoodfacts/robotoff/commit/d6db888100f1ade06572fe679b545741296a445e))
* disable cat matcher (en) for partial matches ([649c016](https://github.com/openfoodfacts/robotoff/commit/649c01690b8ba52d6ff7d741b39700edff251687))
* don't keep numpy ndarray in debug.inputs dict ([64e7124](https://github.com/openfoodfacts/robotoff/commit/64e71244931f750980686b2af973cb954496b08a))
* fix integration test ([b2b4f5a](https://github.com/openfoodfacts/robotoff/commit/b2b4f5ace82c1097081e630effae1d0acbe8987b))
* increase CLIP max_batch_size to 32 ([a39d61a](https://github.com/openfoodfacts/robotoff/commit/a39d61a77f2e751b2933cf9a84917dc0c3ae24ca))
* refactor category predictor data structure ([812a406](https://github.com/openfoodfacts/robotoff/commit/812a4061a00dfbd302d998ae7ac2eea346783bac))
* update code after code review [#1061](https://github.com/openfoodfacts/robotoff/issues/1061) ([deb20d8](https://github.com/openfoodfacts/robotoff/commit/deb20d863cf5fbf063f365123273bb96ba9b0024))
* update PUT /images/logos/LOGO_ID route to accept null value field ([2e488ab](https://github.com/openfoodfacts/robotoff/commit/2e488ab81636258b5a6a5d4b841c2c6ecaffe9be))


### Documentation

* add docstring ([b4ace04](https://github.com/openfoodfacts/robotoff/commit/b4ace04f86c886e867be5d21ab2f89f15d53677d))
* add documentation about install of git lfs ([1cd9866](https://github.com/openfoodfacts/robotoff/commit/1cd98662d6a5641b10af87b93b135fa190c1da1d))
* add documentation in metrics.py ([0ce2b0e](https://github.com/openfoodfacts/robotoff/commit/0ce2b0ece71cd7ca89b0105f3be25abf501cb611))

## [1.21.0](https://github.com/openfoodfacts/robotoff/compare/v1.20.2...v1.21.0) (2023-02-28)


### Features

* add new category classification models ([60d167d](https://github.com/openfoodfacts/robotoff/commit/60d167d5e0226a519d164ff3fab07114cee159be))
* return debug information in /predict/category route ([5b2b392](https://github.com/openfoodfacts/robotoff/commit/5b2b39220cc2776677d34f78d9b62696d0770f30))


### Bug Fixes

* fix category predictions ([347c72c](https://github.com/openfoodfacts/robotoff/commit/347c72c024d50722b3e30963ae5707968b71246e))
* remove unused functions ([5b0f1ae](https://github.com/openfoodfacts/robotoff/commit/5b0f1aecb6c72e599258a80e5dc46f6d4958197e))
* silence false-positive mypy error ([337777d](https://github.com/openfoodfacts/robotoff/commit/337777dccce4441fca253e46fd29affadfe1e54c))
* update /predict/category schema ([f86c098](https://github.com/openfoodfacts/robotoff/commit/f86c098e1e2c4508d9059b54c0f792562d681235))
* update poetry lock file ([48d921c](https://github.com/openfoodfacts/robotoff/commit/48d921ce9fc1d3575a77c6b991e9d4365ff774de))


### Documentation

* improve documentation in v3 category predictor code ([675e056](https://github.com/openfoodfacts/robotoff/commit/675e0564c98c9b229b29872e2fae01fd6654a2c8))

## [1.20.2](https://github.com/openfoodfacts/robotoff/compare/v1.20.1...v1.20.2) (2023-02-06)


### Bug Fixes

* adapt for autoblack ([93e75ca](https://github.com/openfoodfacts/robotoff/commit/93e75ca8081ef8164d36172d2aed8b104653f690))
* add new question to robotoff.pot ([b13d505](https://github.com/openfoodfacts/robotoff/commit/b13d5059b945e407e58c4168a6f91bb23bf4583c))
* manually cropping and resizing of logos before CLIP processor ([2a660e0](https://github.com/openfoodfacts/robotoff/commit/2a660e09f98764ec925c4474c8388ba04b5846a9))

## [1.20.1](https://github.com/openfoodfacts/robotoff/compare/v1.20.0...v1.20.1) (2023-01-30)


### Bug Fixes

* add packaging to default types for questions ([8c2988f](https://github.com/openfoodfacts/robotoff/commit/8c2988f1db75e1ecab6ddd64ecf7d97ab8eea75e))

## [1.20.0](https://github.com/openfoodfacts/robotoff/compare/v1.19.1...v1.20.0) (2023-01-29)


### Features

* add detailed packaging detection ([4916845](https://github.com/openfoodfacts/robotoff/commit/4916845e563e797e74aaa9900a60bde2861d664f))
* add packaging formatter and annotator ([cd6ec75](https://github.com/openfoodfacts/robotoff/commit/cd6ec75a446c2ebdc152fcf2a742a6d319feca56))
* add PackagingImporter ([ce9af41](https://github.com/openfoodfacts/robotoff/commit/ce9af41d8d9498fe92f57f749f131a6ff9f2ecb4))
* implement new packaging API ([3e292f5](https://github.com/openfoodfacts/robotoff/commit/3e292f576df27c40e2a127782378ccc7f1e540aa))


### Bug Fixes

* add brand to taxonomy exclude list ([fe39f1d](https://github.com/openfoodfacts/robotoff/commit/fe39f1d483b5b4298c0294a11bd4dbe9e3837d88))
* add water brand to taxonomy exclude list ([50cb021](https://github.com/openfoodfacts/robotoff/commit/50cb02104becd44c612a53c2783bd08ff80e5a54))
* increase memory limit of robotoff api service to 4G ([9cb2454](https://github.com/openfoodfacts/robotoff/commit/9cb2454895ed13d2981354e9f7f73685a8555aeb))
* increase MongoDB timeout from 5s to 10s ([6fc1a0d](https://github.com/openfoodfacts/robotoff/commit/6fc1a0d461a5b0c9c28303edf3a5ec0339e1a682))
* remove legacy code ([b209707](https://github.com/openfoodfacts/robotoff/commit/b209707cc062310b51f9886c87ee14be91527644))


### Documentation

* add section about robotoff models ([738cc9a](https://github.com/openfoodfacts/robotoff/commit/738cc9a53dc229ad4fa5325c565248f7d3c7080a))
* adding ann benchmark ([ede4330](https://github.com/openfoodfacts/robotoff/commit/ede4330b542d626b50a9676285ab46dfcc35f93d))
* Adding ann-doc in Robotoff Technical References ([4090568](https://github.com/openfoodfacts/robotoff/commit/4090568c24f0f4e4284a147726aaf54557cece39))
* changing the link of the code ([eb7cd85](https://github.com/openfoodfacts/robotoff/commit/eb7cd8540ef8b79f0fd73acd1a1709beb1729a2c))
* correcting mistakes in the doc ([84a6370](https://github.com/openfoodfacts/robotoff/commit/84a63703fcb3ed20da7c3033c9532e47cd9761ab))
* english trad ([2254126](https://github.com/openfoodfacts/robotoff/commit/22541269973d52ca4e7a8355a1cc9d4673f4f92d))
* fix typo ([5bdcb33](https://github.com/openfoodfacts/robotoff/commit/5bdcb33325b97fc70144b66bbad480a3b3e3e8ad))

## [1.19.1](https://github.com/openfoodfacts/robotoff/compare/v1.19.0...v1.19.1) (2023-01-17)


### Bug Fixes

* disable nutrition table detection ([d9fa78b](https://github.com/openfoodfacts/robotoff/commit/d9fa78b9e7777d632c95a02075f6458dae9cf4d6))
* fix UPDATE_LOGO_SCHEMA JSON schema ([d6a4b22](https://github.com/openfoodfacts/robotoff/commit/d6a4b229d916120b60c0773fdac537fd434036d1))

## [1.19.0](https://github.com/openfoodfacts/robotoff/compare/v1.18.2...v1.19.0) (2023-01-16)


### Features

* allow users to filter by confidence in /questions ([8af5719](https://github.com/openfoodfacts/robotoff/commit/8af57191a5d590569d7b73f7c8eddc833282cda9))


### Bug Fixes

* fix UnboundLocalError exception ([6c3ea9a](https://github.com/openfoodfacts/robotoff/commit/6c3ea9a0935ae82270c968dcba66ff24137d8b7c))

## [1.18.2](https://github.com/openfoodfacts/robotoff/compare/v1.18.1...v1.18.2) (2023-01-10)


### Bug Fixes

* create and annotate logo insights in job ([0e825ed](https://github.com/openfoodfacts/robotoff/commit/0e825edca8a83a5246204b68cd879c1767cd0708))
* display front image as default for regex-based brand insights ([e898b1d](https://github.com/openfoodfacts/robotoff/commit/e898b1da5596dc95659c246721e75d41efe81ecb))
* fix server_domain bug ([80730e4](https://github.com/openfoodfacts/robotoff/commit/80730e4437c210216a7895fd9eb6148d55419115))
* fix unit tests in test_question.py ([a05d4ac](https://github.com/openfoodfacts/robotoff/commit/a05d4ac6f442db83c88f821d3328e3eccccf0e15))
* improve BaseURLProvider class ([5178bac](https://github.com/openfoodfacts/robotoff/commit/5178bac94a6be1ad6a7fb5be0d9faeb641bf3345))
* improve import-logos CLI command ([0e1e92b](https://github.com/openfoodfacts/robotoff/commit/0e1e92bf08c8ac5aeeee682f98a5cb22134e1adf))
* remove CachedStore use in products.py ([57b0970](https://github.com/openfoodfacts/robotoff/commit/57b0970ff8f5620b42179db5562bacb26cd17683))
* use correct image subdomain for slack notifications ([1345e94](https://github.com/openfoodfacts/robotoff/commit/1345e94bbf0a9c7b5afa854db44abbfef394f7fe))
* use image.openfoodfacts.* as default server for serving images ([70aceee](https://github.com/openfoodfacts/robotoff/commit/70aceee8e41c1f6616f170b400794dfeecdcded3))

## [1.18.1](https://github.com/openfoodfacts/robotoff/compare/v1.18.0...v1.18.1) (2022-12-30)


### Bug Fixes

* delete robotoff.utils.types module ([e8949da](https://github.com/openfoodfacts/robotoff/commit/e8949dad05071db5fc4731eea1ac6b1db024b5de))
* fix /dump route ([27dd472](https://github.com/openfoodfacts/robotoff/commit/27dd472b75ccc42b7e7af3134046e87b63293b44))
* fix unit and integration tests ([ab17fd2](https://github.com/openfoodfacts/robotoff/commit/ab17fd217a6a7c9b030df7bf05f05269711b58d0))
* improve /insights/dump route ([bc9029c](https://github.com/openfoodfacts/robotoff/commit/bc9029cd31e09f7882180c79808f48b10e7a6d50))
* improve annotator classes and  logo annotation tests ([3a7fc7a](https://github.com/openfoodfacts/robotoff/commit/3a7fc7a491bb18b79ddcd410b8a2b4aeb2d4ba18))
* improve handling of deleted images in import_image.py ([2d24a99](https://github.com/openfoodfacts/robotoff/commit/2d24a99dde560cfc963131c904619ec5140877ea))
* return xx name if exists in taxonomy.get_localized_name() ([64c9175](https://github.com/openfoodfacts/robotoff/commit/64c91751e9c8d8df401027933b4f0b5660efc30b))
* save confidence score in Prediction.confidence ([1aebdc5](https://github.com/openfoodfacts/robotoff/commit/1aebdc5e71e3cd8e7551485fb55eccf1c360f13a))
* turn a warning log into an info ([f1fa4b9](https://github.com/openfoodfacts/robotoff/commit/f1fa4b9b33cd674193a55f36ea0a8908adee0013))
* use directly LogoAnnotation.{barcode,source_image} ([e31cedb](https://github.com/openfoodfacts/robotoff/commit/e31cedb4cb66c1997780e1a635419910de9d2439))


### Documentation

* improve API documentation ([3b5c607](https://github.com/openfoodfacts/robotoff/commit/3b5c6073e483c16c3fff5fb023f4fbfcf758116b))
* improve documentation on Robotoff maintenance ([75b1459](https://github.com/openfoodfacts/robotoff/commit/75b1459add89935dc9df40d63ba5b3306e0d2b69))

## [1.18.0](https://github.com/openfoodfacts/robotoff/compare/v1.17.0...v1.18.0) (2022-12-29)


### Features

* add DB columns ([ffc0de8](https://github.com/openfoodfacts/robotoff/commit/ffc0de839a2a8c6a69fccec7832b4aeb32518e7c))


### Bug Fixes

* fix condition check for logo processing ([ba72538](https://github.com/openfoodfacts/robotoff/commit/ba725383e0e52923c7096ba01f440a572382b6a8))

## [1.17.0](https://github.com/openfoodfacts/robotoff/compare/v1.16.7...v1.17.0) (2022-12-28)


### Features

* add new endpoint to reset logo annotation ([089d289](https://github.com/openfoodfacts/robotoff/commit/089d2890a93c1f3806a3966681fbe9c6c6ff4a06))


### Bug Fixes

* create annotate function to centralize annotation ([b55d72c](https://github.com/openfoodfacts/robotoff/commit/b55d72cade14cae62c752dc4f4ac6282ebaf0450))
* give credit to annotator when annotating logos ([02f7e2e](https://github.com/openfoodfacts/robotoff/commit/02f7e2ed661dcced1fecf92a428f05c05d4f13d7))
* honor limit parameter in all cases in run-object-detection CLI ([4268939](https://github.com/openfoodfacts/robotoff/commit/42689394da734a060578d08b0a775273213c76bd))
* move InsightType to robotoff.types ([a5420c8](https://github.com/openfoodfacts/robotoff/commit/a5420c813dd8f2e2332ba5bf2e45f7e000183cc0))
* never delete annotated insights ([8c67dbe](https://github.com/openfoodfacts/robotoff/commit/8c67dbe984e39bd0afb7de5553ecc422a309891a))
* remove legacy log message ([20aab5a](https://github.com/openfoodfacts/robotoff/commit/20aab5a583c7452022c057da59aaf2848cce15ff))
* require auth for logo annotation ([4420346](https://github.com/openfoodfacts/robotoff/commit/44203462e537245d29b8693521f4d18aaee865c3))

## [1.16.7](https://github.com/openfoodfacts/robotoff/compare/v1.16.6...v1.16.7) (2022-12-27)


### Bug Fixes

* add missing field in SQL query ([e49af95](https://github.com/openfoodfacts/robotoff/commit/e49af95a64c31c4cfad36fbf14a24a1c847642aa))

## [1.16.6](https://github.com/openfoodfacts/robotoff/compare/v1.16.5...v1.16.6) (2022-12-27)


### Bug Fixes

* add CLI to refresh all nearest neighbors ([80fa554](https://github.com/openfoodfacts/robotoff/commit/80fa554b09efef54b8c5a04d75a0147aaf5bec5c))
* allow to run object detection models on URL list file ([6b04692](https://github.com/openfoodfacts/robotoff/commit/6b046920758d1ace4f3b4361917040da0110cc79))
* don't perform full update during insight update ([671af07](https://github.com/openfoodfacts/robotoff/commit/671af07f8cb4f2b91e34bc3621fdf660984f1fba))
* don't refresh nearest neighbors of annotated logos ([27fa3de](https://github.com/openfoodfacts/robotoff/commit/27fa3dea8bdcf20aae10522be6597f4c27d88fb0))
* open DB connection when refreshing product insight ([f8c9a36](https://github.com/openfoodfacts/robotoff/commit/f8c9a36697a39da6263cf170eef8d359c0edf47d))
* use better default for MONGO_URI ([5a392db](https://github.com/openfoodfacts/robotoff/commit/5a392dbb3494c1aad07645a35cd817f1593e16e8))

## [1.16.5](https://github.com/openfoodfacts/robotoff/compare/v1.16.4...v1.16.5) (2022-12-27)


### Bug Fixes

* fix /ann/search route ([9016968](https://github.com/openfoodfacts/robotoff/commit/90169682e4c60872d04eb36f35bf6aa5ccf879c6))

## [1.16.4](https://github.com/openfoodfacts/robotoff/compare/v1.16.3...v1.16.4) (2022-12-26)


### Bug Fixes

* don't open DB connection twice ([3319c0b](https://github.com/openfoodfacts/robotoff/commit/3319c0bfbb00179802d65602c7f594c5d8c5ff41))
* generate insights from annotated logos after PUT logo/{logo_id} ([e45bd3a](https://github.com/openfoodfacts/robotoff/commit/e45bd3a61abb49e6517b272effa44bdeb13abdd4))
* simplify call to /ann/search ([1164f65](https://github.com/openfoodfacts/robotoff/commit/1164f65a5f4ce3cae433e930ed51d1fc40a62228))

## [1.16.3](https://github.com/openfoodfacts/robotoff/compare/v1.16.2...v1.16.3) (2022-12-26)


### Bug Fixes

* bulk-index logo embeddings (instead of indexing one by one) ([4768cfb](https://github.com/openfoodfacts/robotoff/commit/4768cfb75f656892721621f6dce174eb26b01378))
* fix ES product export ([ea9cd21](https://github.com/openfoodfacts/robotoff/commit/ea9cd21944f9b575876ed01b4cea988b8be546e4))
* fix test_import_image integration test ([2031fa4](https://github.com/openfoodfacts/robotoff/commit/2031fa48d39760f9491588b0a6e4404952e9bc3b))
* remove automatic processing disabling ([081f4a9](https://github.com/openfoodfacts/robotoff/commit/081f4a95a2b5aa41afa2ea60fec4681eec3ab3f1))

## [1.16.2](https://github.com/openfoodfacts/robotoff/compare/v1.16.1...v1.16.2) (2022-12-26)


### Bug Fixes

* add result_ttl=0 for upate_insight job ([09862f1](https://github.com/openfoodfacts/robotoff/commit/09862f1f836e6e5bbeafabcf40271d40d281e2e9))
* don't perform image extraction jobs on invalid images ([02458c4](https://github.com/openfoodfacts/robotoff/commit/02458c484978759c54ad21100334569b27dad70b))
* fix add-logo-to-ann CLI command ([8385689](https://github.com/openfoodfacts/robotoff/commit/8385689951ffe2cf9915443e8d56a8a2906d87b5))
* remove useless log message ([7ded92d](https://github.com/openfoodfacts/robotoff/commit/7ded92d63565dadc3ee164a99f56b87ebba96924))

## [1.16.1](https://github.com/openfoodfacts/robotoff/compare/v1.16.0...v1.16.1) (2022-12-26)


### Bug Fixes

* check that brand prediction is not in blacklist during import ([45bc014](https://github.com/openfoodfacts/robotoff/commit/45bc0147c16417ba4a9611b3247b15e096e54409))
* improve logging messages for cached resources ([844bfd3](https://github.com/openfoodfacts/robotoff/commit/844bfd3dbe67bc71fcbdc9779f21ffc10d256142))
* limit CLIP batch size to 4 ([ab0cc99](https://github.com/openfoodfacts/robotoff/commit/ab0cc992c42e6f35dfda862d803550d74ca9299e))
* set TTL of 1h for get_logo_annotations function ([28e2505](https://github.com/openfoodfacts/robotoff/commit/28e25059d96b94cd2de7a8fab2e86af84a284074))

## [1.16.0](https://github.com/openfoodfacts/robotoff/compare/v1.15.2...v1.16.0) (2022-12-23)


### Features

* Adding ES ANN for logos in robotoff ([e4beaad](https://github.com/openfoodfacts/robotoff/commit/e4beaad7343ece5a757efb76908e9a31f62ae4f0))
* create elasticsearch indices at startup ([17c0f17](https://github.com/openfoodfacts/robotoff/commit/17c0f172c643da4913d5e10c2854f8330743672c))
* disable temporarily logo processing ([10bc089](https://github.com/openfoodfacts/robotoff/commit/10bc08911b6451a637dba7d5e1f7e7336bb67d33))
* save CLIP embeddings in DB ([dbc4d34](https://github.com/openfoodfacts/robotoff/commit/dbc4d34b631779d5272459e7dd1bdcd21fad7993))


### Bug Fixes

* add `query_logo_id` field in /ann/search response ([698025c](https://github.com/openfoodfacts/robotoff/commit/698025cdf4bb9ef79f66fd55f31054b86dd203d3))
* add integration tests to process_created_logos ([0e02f7b](https://github.com/openfoodfacts/robotoff/commit/0e02f7b125f93fb6ed72c850d4127f4c05e5c3dd))
* add robotoff-ann API to robotoff ([895264a](https://github.com/openfoodfacts/robotoff/commit/895264a9a99023fb996a819c628e6c2c1931df28))
* add robotoff.triton module ([5fe1332](https://github.com/openfoodfacts/robotoff/commit/5fe13324d2102bc49644df1826c2f882a2d942ea))
* add updated_at field to logo.nearest_neighbors JSON ([db0c44d](https://github.com/openfoodfacts/robotoff/commit/db0c44d2f054450834329f51c8c2fb0d2c54fe75))
* cast logo_id to int in ES ANN response ([abeec15](https://github.com/openfoodfacts/robotoff/commit/abeec15e80638bf1e0e1417cf41907b599422149))
* fix add-logo-to-ann CLI command ([52ae430](https://github.com/openfoodfacts/robotoff/commit/52ae4304cd11b71e41959a8048eaa59564d4011d))
* fix ES healthcheck ([1b54761](https://github.com/openfoodfacts/robotoff/commit/1b54761d2d403f9ffbc60efaf57655b80fcd7a53))
* fix integration tests ([316d330](https://github.com/openfoodfacts/robotoff/commit/316d330bd47c318b627f7c2486dbc4c29d984846))
* fix LogoEmbedding model backref name ([b8f2d04](https://github.com/openfoodfacts/robotoff/commit/b8f2d0425c9d489d1ce14b683a889ed2ad04b21c))
* fix process_created_logos function ([a3aa2c4](https://github.com/openfoodfacts/robotoff/commit/a3aa2c47a68c89005ce63f200eed0580f62165ca))
* fix run_object_detection_model CLI command ([1480350](https://github.com/openfoodfacts/robotoff/commit/1480350c3b3bf822c0108379e6905801c5c92956))
* fix wrong logging level for error messages ([9002356](https://github.com/openfoodfacts/robotoff/commit/90023560449bb4aaea6cbc7cda5c50b7045e5a5a))
* improve add-logo-to-ann CLI command ([a6c6fc7](https://github.com/openfoodfacts/robotoff/commit/a6c6fc76042adaf78677fc53f328a50684659b12))
* Improve export-logos CLI command ([8441163](https://github.com/openfoodfacts/robotoff/commit/84411632ab97a7f10a76056c2ddfd2a45289e0a4))
* improve run_object_detection model function ([a8040c5](https://github.com/openfoodfacts/robotoff/commit/a8040c5a3aa5b8900ecdf617f472a6d36e70aa8e))
* move knn_search to distinct function ([aa7eff6](https://github.com/openfoodfacts/robotoff/commit/aa7eff6a25485ee7bbda715cdbc14d09c1cf5ac1))
* normalize vector before ANN query ([d6f18af](https://github.com/openfoodfacts/robotoff/commit/d6f18afe532c8e01a0fee77561e6481b2422709e))
* pyproject-fix ([daaed91](https://github.com/openfoodfacts/robotoff/commit/daaed91c4291107704872b10c15adfa07dbd680c))
* remove ANN healthcheck and add an healthcheck for ES ([b962659](https://github.com/openfoodfacts/robotoff/commit/b962659ad03abd750829de0db54d6bab737b84c0))
* remove legacy export_logo_annotation CLI command ([0a3ffdc](https://github.com/openfoodfacts/robotoff/commit/0a3ffdcd851f9d7f45c3b27ad6be765fa554574e))
* switch log messages from WARNING to INFO ([89c0933](https://github.com/openfoodfacts/robotoff/commit/89c09339d230ae26e62db80dd40ce66552958393))
* use good defaults for ES config in settings.py ([71320a9](https://github.com/openfoodfacts/robotoff/commit/71320a9524e7a7d617b8672bf860bebabb5d1fe2))

## [1.15.2](https://github.com/openfoodfacts/robotoff/compare/v1.15.1...v1.15.2) (2022-12-21)


### Bug Fixes

* add nutriscore predictor for nutriscore model predictions ([3a61b24](https://github.com/openfoodfacts/robotoff/commit/3a61b2408b5710b4c81edc25326908a5bfde7ea3))
* catch ConnectionError from requests.exceptions and not from stdlib ([2357d3e](https://github.com/openfoodfacts/robotoff/commit/2357d3e9f0249a6ee4ab249ba9b1215c55c5cd51))
* improve request exception handling ([36b675e](https://github.com/openfoodfacts/robotoff/commit/36b675e4c0d3bf6586cb9b990c7db924ef03a7a6))
* improve request exception handling ([b7e3665](https://github.com/openfoodfacts/robotoff/commit/b7e3665b06eb6296185a2017e64a89ed1b472531))
* improve Slack notification request exception handling ([41d37f6](https://github.com/openfoodfacts/robotoff/commit/41d37f6072a8055adbb89ec3025d11c38ce51090))

## [1.15.1](https://github.com/openfoodfacts/robotoff/compare/v1.15.0...v1.15.1) (2022-12-15)


### Bug Fixes

* add better request error handling during annotations ([e60a719](https://github.com/openfoodfacts/robotoff/commit/e60a7197a53abd0dd71f32396bb7f6f4fd2e20ec))
* add better request error handling in process_created_logos ([c9b6d9e](https://github.com/openfoodfacts/robotoff/commit/c9b6d9eafd4fbc4cb92e02015ccd682fc53f5c2c))
* don't notify on Slack when annotating logos ([3503425](https://github.com/openfoodfacts/robotoff/commit/35034259d57628729458a84787cd7431170cd939))
* Don't overwrite annotations in /images/logos/annotate ([9d82321](https://github.com/openfoodfacts/robotoff/commit/9d82321b29f9a09c575fb6b58329578a9d99e617))
* fix auth error on OFF due to Smoothie ([368b07b](https://github.com/openfoodfacts/robotoff/commit/368b07b83510933f29e4cd5611b4431f605f67fa))
* fix IndexError when no nutriscore is detected ([55d4829](https://github.com/openfoodfacts/robotoff/commit/55d4829ae43b639b5b96fa1cd6f14ca7077dc492))
* improve get_image_from_url exception handling ([c5d0b3e](https://github.com/openfoodfacts/robotoff/commit/c5d0b3e404d63124d53526853a8c5b397a55f592))
* improve HTTPError handling during insight annotation ([cb9c47a](https://github.com/openfoodfacts/robotoff/commit/cb9c47a3d49bcc3061a9ecbe4a4562df78376062))
* make logging call uniform ([390e144](https://github.com/openfoodfacts/robotoff/commit/390e1440d23a67fc7bffa61ccdfc6eaef159dd91))
* remove en:nutriscore detection alert ([d201d90](https://github.com/openfoodfacts/robotoff/commit/d201d9044f5236bbb8a7cee5a78ef142d5792f4e))
* remove nutriscore Slack alerts ([160c6ad](https://github.com/openfoodfacts/robotoff/commit/160c6ad932a6c3e319364e47501bf2ee2afbb36d))
* retry 3 times when getting an image/static resource from OFF ([901ed97](https://github.com/openfoodfacts/robotoff/commit/901ed97662c3959e956d151cd1537ce7dc21c1da))
* switch to INFO level for most warning log messages in save_images ([717471d](https://github.com/openfoodfacts/robotoff/commit/717471df4263453a939cd6355181ac66d40f09a9))


### Documentation

* update OpenAPI documentation ([a8594e2](https://github.com/openfoodfacts/robotoff/commit/a8594e27ef11c0cd7e288e9f21944dda35dadbfe))
* update README.md ([952e152](https://github.com/openfoodfacts/robotoff/commit/952e1526232478f217f29f9ee9efa38594e935f3))

## [1.15.0](https://github.com/openfoodfacts/robotoff/compare/v1.14.0...v1.15.0) (2022-12-13)


### Features

* add a lock during product update jobs ([a94632e](https://github.com/openfoodfacts/robotoff/commit/a94632e078ea3feb36211a96c1bf2834bbb31bc5))
* add more logs during resource loading ([7aedd8d](https://github.com/openfoodfacts/robotoff/commit/7aedd8df531bf74e16e655723b677105c2c514bd))
* add new CLI commands to launch background tasks ([6c3184e](https://github.com/openfoodfacts/robotoff/commit/6c3184e9d5951dd3bb4a035addefba6298ecf7d7))
* add redis lock to avoid concurrent insight import for the same product ([f596c97](https://github.com/openfoodfacts/robotoff/commit/f596c973ed5533bc40228bcc1436ac2cce578572))
* add two kind of workers: worker_high and worker_low ([f5eddf0](https://github.com/openfoodfacts/robotoff/commit/f5eddf076129ceabe1f00c1cc9f1a34a51b5bef1))
* create more atomic tasks during image import ([69497f1](https://github.com/openfoodfacts/robotoff/commit/69497f101728183f0ad4d20423384839b8523806))
* don't process logos when running batch logo detector model ([24ed944](https://github.com/openfoodfacts/robotoff/commit/24ed94497f76dcbe619c301e69ef2858c4147f07))
* enable `python -m robotoff` to call CLI ([7286053](https://github.com/openfoodfacts/robotoff/commit/72860536ed2ac95b2ed2c904fccdaec56b973f41))
* improve CLI import commands ([f5491d1](https://github.com/openfoodfacts/robotoff/commit/f5491d18a67bbc30d1e4d55ae39742228bff8634))
* improve generate-ocr-predictions CLI command ([15ef7c3](https://github.com/openfoodfacts/robotoff/commit/15ef7c3d67846c1fae1c048a7bd31c16eec236e1))
* improve import-insights CLI command ([7766feb](https://github.com/openfoodfacts/robotoff/commit/7766feb3b08a7d93dff6f5cbd29a673b990589bb))
* make object detection jobs idempotent ([a8f002e](https://github.com/openfoodfacts/robotoff/commit/a8f002ef72bff6924f0190c51e4ca242327039e7))
* only accept predictions from one product during insight import ([58cf2d4](https://github.com/openfoodfacts/robotoff/commit/58cf2d47e1bb8bd7db1afdc5555f24adec37f90e))
* refresh cache when performing worker maintenance tasks ([240490b](https://github.com/openfoodfacts/robotoff/commit/240490ba6649659b770a688364f5a8c8898525cf))
* remove orphan containers when doing make up ([6452db7](https://github.com/openfoodfacts/robotoff/commit/6452db73066cd677e58d33152ccaad68d0ec527d))
* save brand prefix as gzipped file ([c7c8322](https://github.com/openfoodfacts/robotoff/commit/c7c8322be01747de54eb06437f04a85410b9675f))
* simplify image import process ([ec272a3](https://github.com/openfoodfacts/robotoff/commit/ec272a3356967f6a77fb50d69c365e36a668219d))
* update brand_from_taxonomy.gz ([1f5cee8](https://github.com/openfoodfacts/robotoff/commit/1f5cee8d5c78e03e3a842d11f3d353d7d9281cf9))
* update prediction duplicate detection mecanism ([ef658ca](https://github.com/openfoodfacts/robotoff/commit/ef658ca9b4e48ff6edadd2e4a8a3d57b08e2bb0e))
* use batches in refresh_insights job ([66fea3b](https://github.com/openfoodfacts/robotoff/commit/66fea3b05416cb426971b89d25dc905d39c3eaef))
* use built-in types instead of typing.* ([289dc17](https://github.com/openfoodfacts/robotoff/commit/289dc174e36a0bf6a70e36bd98214f8dd63a6da8))
* use queues for refresh_insight job on all DB ([71e5319](https://github.com/openfoodfacts/robotoff/commit/71e531918ce0ef3161639744405d71c8fd6a4554))
* use robotoff.types.PredictionType enum in Robotoff CLI ([032213f](https://github.com/openfoodfacts/robotoff/commit/032213f2e25d1ce7dae5fd6de471775509086a28))
* use rq to send tasks to workers ([7163610](https://github.com/openfoodfacts/robotoff/commit/71636108c47537490b5cefa11120bad7faf0fa59))


### Bug Fixes

* add default TF_SERVING_HOST in .env file ([21c0760](https://github.com/openfoodfacts/robotoff/commit/21c0760c7cdd52c11a7e04fa89d379ae70f44266))
* add default timeout during TF serving request ([9aaceea](https://github.com/openfoodfacts/robotoff/commit/9aaceeafb784db11c00db89f3156eda2794fa39e))
* add predictor=regex for store predictions ([ecac885](https://github.com/openfoodfacts/robotoff/commit/ecac8851c0be3167bface90652002cfc94a2be7f))
* add with_db decorator to generate_fiber_quality_facet ([c62f14c](https://github.com/openfoodfacts/robotoff/commit/c62f14cdcca56dbd7c98ac26864930f38190e92e))
* disable deepsource autofix ([ace1df3](https://github.com/openfoodfacts/robotoff/commit/ace1df367b8908d7d409ca75dbbe74faac29c406))
* disable INFO log message from selected dependencies ([b5eeeab](https://github.com/openfoodfacts/robotoff/commit/b5eeeab79a3b049cf051740e4222788ca69cb65a))
* don't refresh ES indexes during scheduler startup ([fa72748](https://github.com/openfoodfacts/robotoff/commit/fa7274823cd2d4783bab7264c76b959b3bb2560c))
* fix DB connection in workers ([2333b41](https://github.com/openfoodfacts/robotoff/commit/2333b41092a73487b5e541681cc49ed95cada424))
* fix flake8 and isort errors ([7ed93fc](https://github.com/openfoodfacts/robotoff/commit/7ed93fc6d061e0beb30d5a94ebf451024694be07))
* fix integration tests after adding autoconnect=False ([0382e35](https://github.com/openfoodfacts/robotoff/commit/0382e357784ea5b2de5c942671d14dac42b3585c))
* fix integration tests after switch to manual DB connection management ([2f3e8f4](https://github.com/openfoodfacts/robotoff/commit/2f3e8f4a59fc622d81946a12866e53f39b72525e))
* fix wrong import ([15894e5](https://github.com/openfoodfacts/robotoff/commit/15894e57b253aced5b43087f54ad79e2e74bac22))
* improve DB transaction management during image import ([a2e390a](https://github.com/openfoodfacts/robotoff/commit/a2e390afd3fe61dea21a1d9130240462ae30e485))
* move PredictionType to robotoff/types.py ([7f374e6](https://github.com/openfoodfacts/robotoff/commit/7f374e6875bd20b7de87c387de4c12b20d41167e))
* move types required by CLI in robotoff/types.py ([d66d7e0](https://github.com/openfoodfacts/robotoff/commit/d66d7e0754937f89637766543e5e70a79c1f5b6b))
* no need to use db.atomic() when db context manager is used ([f24a600](https://github.com/openfoodfacts/robotoff/commit/f24a6002c8c1525b611706adc1d4c309b1b832c3))
* open DB connection when needed in scheduler ([3e1ec39](https://github.com/openfoodfacts/robotoff/commit/3e1ec39a03714cdd911015cee9c2ecc79c5d12f3))
* remove CLI documentation generation ([4258748](https://github.com/openfoodfacts/robotoff/commit/42587484f6fd6fc786a77d68560d4891336366af))
* remove legacy script comments ([2d96e7a](https://github.com/openfoodfacts/robotoff/commit/2d96e7a2218c484627b1ed3202002ae06ff2e082))
* remove legacy test file ([21c39c5](https://github.com/openfoodfacts/robotoff/commit/21c39c56b0be9f248b098bdcdc2e909889652e53))
* revert container-deploy-ml.yml update ([667d19d](https://github.com/openfoodfacts/robotoff/commit/667d19dfb91d7ceac1a10799e13fb24943896810))
* switch from redis-stack to classic redis ([123fcbf](https://github.com/openfoodfacts/robotoff/commit/123fcbf4129caf2c765b138f30ebbeb634f773ab))
* Update Makefile ([0c90461](https://github.com/openfoodfacts/robotoff/commit/0c90461e17b92a008161ef9fa574f4b813a41261))
* update poetry lock file ([1cfd0c2](https://github.com/openfoodfacts/robotoff/commit/1cfd0c2c16459b5a123bea2e1a4fcb3364eaf78e))
* updating log level of a log message ([ac2a479](https://github.com/openfoodfacts/robotoff/commit/ac2a4795fd0df4efe59705badedfa65b49163599))
* use autoconnect=False during DB connection ([683ba6a](https://github.com/openfoodfacts/robotoff/commit/683ba6a1b1da258f9707731839ccf8c4437acec3))
* use db.connection_context in with_db decorator ([bac669c](https://github.com/openfoodfacts/robotoff/commit/bac669ccf60b95ff73f8c6b900fdfc2a193cd8ab))
* use enqueue_job function everywhere ([0dc53c7](https://github.com/openfoodfacts/robotoff/commit/0dc53c74d356407d59741ef720580e172a987ad7))
* validate params in GET /images/logos route ([b265686](https://github.com/openfoodfacts/robotoff/commit/b2656867a8ab3796f6cd59f2d1ae6da35371c575))


### Documentation

* add docstrings ([4771657](https://github.com/openfoodfacts/robotoff/commit/47716571fd20233adb93d7021c848afe335d8a10))
* improve documentation ([7e43b4d](https://github.com/openfoodfacts/robotoff/commit/7e43b4d773308849f4717f2cd8a8503bdb6cf01d))
* update documentation in maintenance.md ([64d495d](https://github.com/openfoodfacts/robotoff/commit/64d495d04bad5462524e13562f476973c895c526))

## [1.14.0](https://github.com/openfoodfacts/robotoff/compare/v1.13.0...v1.14.0) (2022-12-06)


### Features

* add insights metric ([9cc8bb6](https://github.com/openfoodfacts/robotoff/commit/9cc8bb64792076416da88d557205d68e75e7af72))
* add misc metrics to InfluxDB ([e8e0633](https://github.com/openfoodfacts/robotoff/commit/e8e0633c76bb4b5d35541db1029a7a5a6b5a1a42))
* add percent field to influx 'insights' measurement ([8308027](https://github.com/openfoodfacts/robotoff/commit/830802768101d3c293290b5419270a712a501f7e))
* remove update_recycle task ([9884ef4](https://github.com/openfoodfacts/robotoff/commit/9884ef4ea0ad04e92bcfbf3dbd9c885653d78189))


### Bug Fixes

* add lower value for MongoDB serverSelectionTimeoutMS ([8d204c1](https://github.com/openfoodfacts/robotoff/commit/8d204c18446ab37b5b399869ceab198bbd3d6df5))
* add mongodb service in webnet network ([7714d1b](https://github.com/openfoodfacts/robotoff/commit/7714d1b85be85e6c87750683743982cbf2afe13a))
* clean obsolete CLI commands ([fba622d](https://github.com/openfoodfacts/robotoff/commit/fba622d143ffa4f0f243e329efde37da3055ea74))
* don't build robotoff image by default ([ca8f486](https://github.com/openfoodfacts/robotoff/commit/ca8f486061642f9f2fbb62fd19478abae34a5387))
* fix default value for MONGO_URI in .env ([4229c94](https://github.com/openfoodfacts/robotoff/commit/4229c94d97bb570e9b0078b29f8f77ad9a914d13))
* fix mongoDB healthcheck ([c91761a](https://github.com/openfoodfacts/robotoff/commit/c91761a297928a3500ec91a4d28fb52143fbb664))
* fix parameter typing in one API route ([ca19c7c](https://github.com/openfoodfacts/robotoff/commit/ca19c7c4c2ae03dc30b07b0ee2c2b019fd4aa828))
* revert deletion of CLI run command ([5d0bbeb](https://github.com/openfoodfacts/robotoff/commit/5d0bbeb8db08ef9120984cc19f1a54a64917b6ca))
* update barcode range check during insight import ([090c746](https://github.com/openfoodfacts/robotoff/commit/090c7468a9b53b07640e4efa21303a4f2f0fad0d))


### Documentation

* add documentation about predictions and insights ([3c43229](https://github.com/openfoodfacts/robotoff/commit/3c432290b525fd975a6c17d4f7f0b6b7190f4507))
* fix error in dev-install.md ([1ef8d33](https://github.com/openfoodfacts/robotoff/commit/1ef8d33eefe87c99ceb080f273fbb4c301766ea4))
* fix typo ([aca7a39](https://github.com/openfoodfacts/robotoff/commit/aca7a397552c3b2e2e67205a447b06773538e286))
* update make dev installation message ([705c580](https://github.com/openfoodfacts/robotoff/commit/705c580e653099efb210a7429531fcbb57a7156c))

## [1.13.0](https://github.com/openfoodfacts/robotoff/compare/v1.12.0...v1.13.0) (2022-11-25)


### Features

* disable extraction of `packaging` predictions ([0b68fd2](https://github.com/openfoodfacts/robotoff/commit/0b68fd231e6f4ce6c92df20a3301cdf4414d7809))


### Bug Fixes

* fix mypy and flake8 issues ([80fef79](https://github.com/openfoodfacts/robotoff/commit/80fef79385c124f38a99222d47072ab020ac314e))

## [1.12.0](https://github.com/openfoodfacts/robotoff/compare/v1.11.0...v1.12.0) (2022-11-24)


### Features

* switch to InfluxDB v2 ([3161015](https://github.com/openfoodfacts/robotoff/commit/31610150c68e141046d50aaedbd9ecccc1e2a921))


### Bug Fixes

* add proper authentication in metrics.py for .net env ([5e1ccb9](https://github.com/openfoodfacts/robotoff/commit/5e1ccb9fd02369332dbbcfda9919eb1487be6962))
* disable grafana annotation until grafana is up and running again ([3415c48](https://github.com/openfoodfacts/robotoff/commit/3415c48bb8936b66e4b08b119a4874991ef35520))
* fix ISO_3166-1 alpha-2 codes used in metrics.py ([2224915](https://github.com/openfoodfacts/robotoff/commit/22249150080587f86aa41d462550f5d7f425d6d5))
* really catch JSONDecodeError exceptions in metrics.py ([5c65ee9](https://github.com/openfoodfacts/robotoff/commit/5c65ee97c83a70a8e1e5bbfb076ef78035b897cd))
* use same version for requests and types-requests ([b13160e](https://github.com/openfoodfacts/robotoff/commit/b13160eec566ba11dda0556573671b576b88ef6a))

## [1.11.0](https://github.com/openfoodfacts/robotoff/compare/v1.10.0...v1.11.0) (2022-11-15)


### Features

* allow to filter insights/question by predictor value ([6f840d6](https://github.com/openfoodfacts/robotoff/commit/6f840d66d04d182171ccc36209219d321a152fff))
* consider annotation=-1 as a vote ([#908](https://github.com/openfoodfacts/robotoff/issues/908)) ([18e9552](https://github.com/openfoodfacts/robotoff/commit/18e9552e5aef5b9a08d449f6ad4cd2898697c966))
* remove dependabot ([b8df1aa](https://github.com/openfoodfacts/robotoff/commit/b8df1aa943fdd487bdaed8d18f5dadf486833774))
* set value_tag to canonical label value during prediction import ([80cf93c](https://github.com/openfoodfacts/robotoff/commit/80cf93cd7c9c8cf85ac9e316d0883bdc0d0ac808))
* switch all object detection models to Triton ([#622](https://github.com/openfoodfacts/robotoff/issues/622)) ([3c786c4](https://github.com/openfoodfacts/robotoff/commit/3c786c488c32ad56a688c1f940d341f181b4b35e))


### Bug Fixes

* add a small fix on dump_ocr.py ([450d53f](https://github.com/openfoodfacts/robotoff/commit/450d53f0c03a90de3ff972d0d8b80c78d52dea4e))
* add triton HTTP port in env file ([11395c6](https://github.com/openfoodfacts/robotoff/commit/11395c6e8f8aba05df39d9853d88b5d257966613))
* always serialize insights the same way ([4a00f48](https://github.com/openfoodfacts/robotoff/commit/4a00f4820ec020a31fc0940187d6f28c7711e3fa))
* fix codecov configuration ([56ee4b0](https://github.com/openfoodfacts/robotoff/commit/56ee4b0835744a32308c4abcd068c6c71c6a8b00))
* fix min_confidence parameter in /logos/search route ([b00ad84](https://github.com/openfoodfacts/robotoff/commit/b00ad8443a81b4bff23962ac9d91e21154c83d8f))
* fix refresh_all_insights function ([43d6078](https://github.com/openfoodfacts/robotoff/commit/43d60786593526e89ef0cc61fb114e75967d2869))
* fix triton model dir volume binding ([d8ccffa](https://github.com/openfoodfacts/robotoff/commit/d8ccffad836bc1b9b3115093260ad4b675ff78db))
* make API parameters uniform ([80ad784](https://github.com/openfoodfacts/robotoff/commit/80ad7841eb02c3deaacb8e7999870ffdc7811cb4))
* make voting mechanism work again ([4f9d499](https://github.com/openfoodfacts/robotoff/commit/4f9d49998da47c21a16f3944c4eaa318e6e975bd))
* remove automatic parameter in InsightImporter ([1c11652](https://github.com/openfoodfacts/robotoff/commit/1c11652df705aa65d84f7faf510a266102f33f6c))
* update brand taxonomy blacklist ([4ea5b0c](https://github.com/openfoodfacts/robotoff/commit/4ea5b0c2ce03271c74e39613fa00b762faf9fcb0))


### Reverts

* revert codecov config change ([850aea1](https://github.com/openfoodfacts/robotoff/commit/850aea1b7dafce6c8501e070cedba5a9b45345dc))

## [1.10.0](https://github.com/openfoodfacts/robotoff/compare/v1.9.0...v1.10.0) (2022-10-25)


### Features

* add `data->bounding_box` field in logo derived insights ([1e18b2e](https://github.com/openfoodfacts/robotoff/commit/1e18b2ed4aa1eb6749ecf85fddb72271c78e385d))
* add build command to Makefile ([5c3961d](https://github.com/openfoodfacts/robotoff/commit/5c3961d5c3b0d3ddaedaebf38c12b8376497bd3f))
* add CLI command export-logos-ann ([add6141](https://github.com/openfoodfacts/robotoff/commit/add6141b857c20af8c7577cff60ed6f122ea424e))
* allow to launch a single service with make ([92b01d9](https://github.com/openfoodfacts/robotoff/commit/92b01d9c6e047c5901e420b63ca10971385cd9af))
* improve `generate_prediction` function ([52247f9](https://github.com/openfoodfacts/robotoff/commit/52247f9ce759fda893adbcf9b0a5b7d742fd8a15))
* improve apply-insight CLI command ([93524c6](https://github.com/openfoodfacts/robotoff/commit/93524c6eba85f5abba3c49aa85d8ad58195e86a6))
* improve JSON OCR generation script ([603e355](https://github.com/openfoodfacts/robotoff/commit/603e355454386eed550e1cb347d9d413965ce10d))
* improve taxonomized value matching ([52c99be](https://github.com/openfoodfacts/robotoff/commit/52c99be07f040434969aa8f24a812e0ae6cc3c0a))
* update category matching algorithm ([#952](https://github.com/openfoodfacts/robotoff/issues/952)) ([d8a04c7](https://github.com/openfoodfacts/robotoff/commit/d8a04c79a6b282c5082e3c35532a21ecd27bb09a))
* update OCR scripts ([111ada9](https://github.com/openfoodfacts/robotoff/commit/111ada94b4bd8a058cc0f4fc2e72ff30bebd60f4))


### Bug Fixes

* add fixes to category matcher ([b8c1912](https://github.com/openfoodfacts/robotoff/commit/b8c1912ce3942f857d7655779845394b860f2646))
* don't return auto processable insights in /questions/{barcode} ([03376b8](https://github.com/openfoodfacts/robotoff/commit/03376b8955a5ea5df4ed4de57be919ff2d80665c))
* filter logos that are almost exactly the same ([33cfc88](https://github.com/openfoodfacts/robotoff/commit/33cfc8839473523e7272b30073c24f99ea3adc66))
* fix /logos/search route ([e932407](https://github.com/openfoodfacts/robotoff/commit/e93240760bc5a047231036d59112d15096d74551))
* fix `get_tag` function ([cca5592](https://github.com/openfoodfacts/robotoff/commit/cca5592bd56124596cf6eeb68b959e4673a51922))
* fix insight import mecanism ([#963](https://github.com/openfoodfacts/robotoff/issues/963)) ([04412df](https://github.com/openfoodfacts/robotoff/commit/04412dfec138cb85818f9b22d744a4114286ad55))
* rename image_url field into ref_image_url ([3539d84](https://github.com/openfoodfacts/robotoff/commit/3539d84907552e8ff366990b5770b9a2f8e8a484))
* rename ocr_dump.py script into dump_ocr.py ([bcce867](https://github.com/openfoodfacts/robotoff/commit/bcce867c4ac3ab0fa97f636fea1e539c3adf6e49))
* require insight_id to be an UUID in /insights/annotate ([abb9574](https://github.com/openfoodfacts/robotoff/commit/abb95744c8b8e6edb7d22cc8b051f7ebe608bc45))
* simplify filter_logo function ([9eb8fdd](https://github.com/openfoodfacts/robotoff/commit/9eb8fddf197d29914bacd9b6c5a69abecfa0f0af))
* update .gitignore and .dockerignore ([2eb985a](https://github.com/openfoodfacts/robotoff/commit/2eb985a228233c220f7411d1e3cdd65c361efb58))
* update tags of some labels detected with flashtext ([f2bd704](https://github.com/openfoodfacts/robotoff/commit/f2bd7040be49f7402f2091ea9424502067f05795))
* use canonical value fr:label-rouge everywhere ([05197cc](https://github.com/openfoodfacts/robotoff/commit/05197cc1d1bc07ab90e8f4b9506777e00ba158ea))
* use f-string everywhere in robotoff/cli/insights.py ([bbd81fa](https://github.com/openfoodfacts/robotoff/commit/bbd81fa043f04e70c4cc03f37824abb4dacf6679))

## [1.9.0](https://github.com/openfoodfacts/robotoff/compare/v1.8.0...v1.9.0) (2022-10-17)


### Features

* improve request validation during logo annotation ([7a1e6d5](https://github.com/openfoodfacts/robotoff/commit/7a1e6d585119dd76429a62732fe8548565f9dd4b))
* Request image directly from MongoDB instead of Product Opener ([#921](https://github.com/openfoodfacts/robotoff/issues/921)) ([83f0f09](https://github.com/openfoodfacts/robotoff/commit/83f0f0981f5b189b3809d26a4fe89e785eacc682))
* support providing taxonomized value as input during logo annotation ([53a9bdf](https://github.com/openfoodfacts/robotoff/commit/53a9bdf1c988e3256732ee92c58cfca37ccfbae1))
* use gzipped version of fallback taxonomy files ([73e23ce](https://github.com/openfoodfacts/robotoff/commit/73e23ceb31ac578c1817c558fc59c9d03edb6558))


### Bug Fixes

* allow to fetch both annotated/not annotated logos in /images/logos/search ([f9e5e96](https://github.com/openfoodfacts/robotoff/commit/f9e5e9646f445cccf6bb1949cb1a0a941356c09f))
* create new /images/logos/search endpoint from /images/logos ([20034d8](https://github.com/openfoodfacts/robotoff/commit/20034d81bbc0bf619407c65dc0d7c3c7bf8a6679))
* ignore protobuf-generated files during mypy analysis ([e3d84ae](https://github.com/openfoodfacts/robotoff/commit/e3d84aed4c3f1c502e08b0f9cd644e9c4495bee3))
* remove .gz files from .gitignore ([0af8a34](https://github.com/openfoodfacts/robotoff/commit/0af8a340e69f402c2aa8c887d17fed4dade1f854))
* set higher expiration interval for taxonomy ([c15e077](https://github.com/openfoodfacts/robotoff/commit/c15e07773bb366bddbc3cd3deb06bf1cf63b3fc2))

## [1.8.0](https://github.com/openfoodfacts/robotoff/compare/v1.7.0...v1.8.0) (2022-10-12)


### Features

* Add `agribalyse-category` campaign to agribalyse category insights ([69d0023](https://github.com/openfoodfacts/robotoff/commit/69d0023c176bfe204d913497c2189b92dd18b3bd))
* add a `threshold` parameter to /predict/category endpoint ([0f68e93](https://github.com/openfoodfacts/robotoff/commit/0f68e932fa2353aa2ca1c320d2e1f3e3407d08d1))
* add campaign filter in question endpoints ([91ed2d2](https://github.com/openfoodfacts/robotoff/commit/91ed2d23bae236420a2aca85879fd3f42b3f62b5))
* add ProductInsight.campaign field ([4a54484](https://github.com/openfoodfacts/robotoff/commit/4a54484b9f8de18f5f9ed7699ebf5ae6af83fadf))
* Improve /predict/category endpoint ([0438f4e](https://github.com/openfoodfacts/robotoff/commit/0438f4e32a8ae369d4d985a4dab4b95972e153ef))


### Bug Fixes

* add fixes to /questions/unanswered endpoint ([6ed2d42](https://github.com/openfoodfacts/robotoff/commit/6ed2d424c08f8984d33a91de79bfcbd7f171acb2))
* adding a benchmark done with cosine-distance to the research doc ([#945](https://github.com/openfoodfacts/robotoff/issues/945)) ([f189031](https://github.com/openfoodfacts/robotoff/commit/f18903136a58de5673918294920a558a440d1555))
* adding documentation about the insights/annotate.py file ([#944](https://github.com/openfoodfacts/robotoff/issues/944)) ([18e5c66](https://github.com/openfoodfacts/robotoff/commit/18e5c667796eaaf67387b7c751a0c13a448b76cf))
* don't display question about insights that are automatically applicable ([5ac392e](https://github.com/openfoodfacts/robotoff/commit/5ac392e1edb4ba8d92c7e1ff4d03f1fab4ef7d75))
* don't return in /questions/unanswered reserved barcode by default ([78af005](https://github.com/openfoodfacts/robotoff/commit/78af005e18ab440a808c0055d5a6750bc3c76947))
* remove some moderation cloud vision labels ([1daa889](https://github.com/openfoodfacts/robotoff/commit/1daa889564ecc443f5571814e10921672efc1ba0))

## [1.7.0](https://github.com/openfoodfacts/robotoff/compare/v1.6.0...v1.7.0) (2022-10-04)


### Features

* add to repository latest versions of OCR scripts ([#920](https://github.com/openfoodfacts/robotoff/issues/920)) ([be44e81](https://github.com/openfoodfacts/robotoff/commit/be44e81643f56edcb7011af5adc11d13780b46d7))
* added country parameter to the API and started with test cases ([12b2359](https://github.com/openfoodfacts/robotoff/commit/12b2359af57f83249cc6a46d600d71460fa9d113))
* added server_domain to the API ([#899](https://github.com/openfoodfacts/robotoff/issues/899)) ([761aa51](https://github.com/openfoodfacts/robotoff/commit/761aa5165d235f4b53dd270c453a8aba0ecfc56d))
* Adding MongoDB container to Robotoff in dev ([#693](https://github.com/openfoodfacts/robotoff/issues/693)) ([946ce1d](https://github.com/openfoodfacts/robotoff/commit/946ce1d0fa8b15347759ff4cfa5f4ce13b411e0b))
* expose postgres DB locally ([2668f2a](https://github.com/openfoodfacts/robotoff/commit/2668f2a3b9272e5ce5e105f2967636b91c7ccc23))
* Extract USDA packager codes with REGEX and flashtext ([aa2b8ec](https://github.com/openfoodfacts/robotoff/commit/aa2b8ec21476c1a4ac80622f3ddc4ca5529570d3))
* Extract USDA packager codes with REGEX and flashtext ([e92163f](https://github.com/openfoodfacts/robotoff/commit/e92163fc020ffb9bfaa50a7e2a7de942cf454ff9))
* Robotoff quality monitoring: Saving AnnotationResult ([#796](https://github.com/openfoodfacts/robotoff/issues/796)) ([755d296](https://github.com/openfoodfacts/robotoff/commit/755d296471cde7d799dafe2d75d906bf1e4d5672))


### Bug Fixes

* adapting REGEX to codes like M123 + V123 ([470b4d2](https://github.com/openfoodfacts/robotoff/commit/470b4d2b777383f63e9afae10e10bfe7cf18b93d))
* Adding documentation and reviewing syntaxes ([e296f17](https://github.com/openfoodfacts/robotoff/commit/e296f1792b94ed66fe42a931b40aaa7ce21a1431))
* changing legacy file not to get an error in the typing check mypy ([6f1f113](https://github.com/openfoodfacts/robotoff/commit/6f1f11398610bd4263ef18e8a3d2e42134823483))
* changing legacy file not to get an error in the typing check mypy ([8b5bcae](https://github.com/openfoodfacts/robotoff/commit/8b5bcaef1ae93acb737d269d9d7031c80ef738b0))
* Changing names from category_from_AOC to category ([c490669](https://github.com/openfoodfacts/robotoff/commit/c49066925eda26d16d7974e150e3fc3644f64cfa))
* docstring and file name ([3114aea](https://github.com/openfoodfacts/robotoff/commit/3114aeac91f33cfaf6c2ca05a265dcffcc5188ab))
* dumping an unused import ([5c92e59](https://github.com/openfoodfacts/robotoff/commit/5c92e597bc6e3583a87b1f536005a55acbf74f77))
* fix flake8 errors on scrits/ocr/extract_ocr_text.py ([aef38df](https://github.com/openfoodfacts/robotoff/commit/aef38df048fd46ebc3d92c93c55a41c3ba342561))
* fixed the test case ([1b6fb0d](https://github.com/openfoodfacts/robotoff/commit/1b6fb0d0b060cba90a9ec73dbd39c41e08291606))
* Incompatible return value ([1b4453b](https://github.com/openfoodfacts/robotoff/commit/1b4453b548c8041f79381d2e3a243abbedb1a59f))
* Incompatible return value type ([2dc7831](https://github.com/openfoodfacts/robotoff/commit/2dc7831726094f920f8ffde8f22c81e8f5cdd50b))
* incorrect brand taxonomy fallback path + fix tests ([13baec4](https://github.com/openfoodfacts/robotoff/commit/13baec4e80e15957497a85df00a95053d7f38e1e))
* move docker mongodb service to a distinct file in dev mode ([#916](https://github.com/openfoodfacts/robotoff/issues/916)) ([c283499](https://github.com/openfoodfacts/robotoff/commit/c28349983b6e415adc022d4106a1a0f6f2cf96e3))
* only save annotation_result in ProductInsight when needed ([#938](https://github.com/openfoodfacts/robotoff/issues/938)) ([c14b07f](https://github.com/openfoodfacts/robotoff/commit/c14b07f27279c10fa6254c08f8561a360a0ff491))
* Outdated commentaries ([2bdc26f](https://github.com/openfoodfacts/robotoff/commit/2bdc26f5c1deea13b3dd644de2054edb17ebcd28))
* remove trailing slash in all URLs ([#915](https://github.com/openfoodfacts/robotoff/issues/915)) ([5e89e95](https://github.com/openfoodfacts/robotoff/commit/5e89e957fe52f7d9292af339dce53b3c19b148af))
* replace with fr prefix references to en:ab-agriculture-biologique ([#919](https://github.com/openfoodfacts/robotoff/issues/919)) ([ec1500c](https://github.com/openfoodfacts/robotoff/commit/ec1500cbbad0c276962d1431673e1919e1b3accb))
* solving mypy check issue ([3a5f9ab](https://github.com/openfoodfacts/robotoff/commit/3a5f9ab2365b3f59a349140835e04d4ee5d4023c))
* store category neural model in ProductInsight.predictor field ([#914](https://github.com/openfoodfacts/robotoff/issues/914)) ([c1c8d8d](https://github.com/openfoodfacts/robotoff/commit/c1c8d8d78edfd25bc6b28264222c374bfceeeef4))
* temporarily disable USDA packager code extraction ([#933](https://github.com/openfoodfacts/robotoff/issues/933)) ([91f65c1](https://github.com/openfoodfacts/robotoff/commit/91f65c1f900376084b1bb84dbb7c3460e832f8f8))
* typing.dict unused ([90112b7](https://github.com/openfoodfacts/robotoff/commit/90112b7cab8aa486e2a264deb706b1485aaeb224))
* unused import ([cdab35f](https://github.com/openfoodfacts/robotoff/commit/cdab35fefe45830d56916aedfda1735de388f6af))
* Unused import ([43930b1](https://github.com/openfoodfacts/robotoff/commit/43930b1bd781af5e08e9708d895a2e352ce17e91))
* Unused variables in a loop ([d4a37f1](https://github.com/openfoodfacts/robotoff/commit/d4a37f141e26acf04270d919a8438895e56df036))
* Unused variables in a loop ([a30b964](https://github.com/openfoodfacts/robotoff/commit/a30b964ae39255f3163ec56bc7ca0c5d522f3374))

## [1.6.0](https://github.com/openfoodfacts/robotoff/compare/v1.5.1...v1.6.0) (2022-09-12)


### Features

* add an edit and remove button when nutriscore prediction is posted on Slack channel ([#783](https://github.com/openfoodfacts/robotoff/issues/783)) ([0055ba7](https://github.com/openfoodfacts/robotoff/commit/0055ba754d87975af151a13d50fb1c35618eaeb2))
* add events API requests ([#677](https://github.com/openfoodfacts/robotoff/issues/677)) ([1f212fd](https://github.com/openfoodfacts/robotoff/commit/1f212fd85f8b6c626c2f7ed56de7c4d6d9ab6303))
* Add image moderation service ([#889](https://github.com/openfoodfacts/robotoff/issues/889)) ([40d4ea4](https://github.com/openfoodfacts/robotoff/commit/40d4ea422bc042b8245b67efd149d8d66bd36e61))
* Adding a regex for gluten packaging code ([#823](https://github.com/openfoodfacts/robotoff/issues/823)) ([d22ee99](https://github.com/openfoodfacts/robotoff/commit/d22ee99d740498455fc40672baffff97904d6452))
* api returning predictions ([#815](https://github.com/openfoodfacts/robotoff/issues/815)) ([a9c9be8](https://github.com/openfoodfacts/robotoff/commit/a9c9be82ef395a3c11cb43e5da2715dcdac32084))
* detect cat images (opff) ([#883](https://github.com/openfoodfacts/robotoff/issues/883)) ([b2b1b00](https://github.com/openfoodfacts/robotoff/commit/b2b1b00ed3630d549ac3632e744f50f3ecf4f762))
* filter images and display in a list ([#832](https://github.com/openfoodfacts/robotoff/issues/832)) ([e9bcb58](https://github.com/openfoodfacts/robotoff/commit/e9bcb5841adf25975163d9662f746e8fecc767d0))
* Filter insights opportunities based on type of tags ([#859](https://github.com/openfoodfacts/robotoff/issues/859)) ([bc5ee1b](https://github.com/openfoodfacts/robotoff/commit/bc5ee1badb9072f60e2f73c819ebeb7d542ae35c))
* Get Logo Annotation list  ([#882](https://github.com/openfoodfacts/robotoff/issues/882)) ([965b409](https://github.com/openfoodfacts/robotoff/commit/965b4096eae072e7dc4edfbe6943fc08cd0b0f71))
* images predictions collection api ([#834](https://github.com/openfoodfacts/robotoff/issues/834)) ([1477943](https://github.com/openfoodfacts/robotoff/commit/147794392a94884146a140b209de85b5f4b46712))
* isolate test network + make single test run ([#806](https://github.com/openfoodfacts/robotoff/issues/806)) ([3618cb1](https://github.com/openfoodfacts/robotoff/commit/3618cb18d76341472f0d3d927491fa63ab7e24f5))
* Sort collection API ([#888](https://github.com/openfoodfacts/robotoff/issues/888)) ([275ef95](https://github.com/openfoodfacts/robotoff/commit/275ef952a2f8f77cdffe7b074586e5a8dff6ca4f))
* test voting first anonymous then authenticated  ([#805](https://github.com/openfoodfacts/robotoff/issues/805)) ([61a24cd](https://github.com/openfoodfacts/robotoff/commit/61a24cd20607d25b215cbbdc9e9492db048ce59f)), closes [#801](https://github.com/openfoodfacts/robotoff/issues/801)


### Bug Fixes

* action name ([4d88ca1](https://github.com/openfoodfacts/robotoff/commit/4d88ca1540cc06fddbb82bc567a0b461999b0143))
* Added server_domain to all "Collection" class ([#887](https://github.com/openfoodfacts/robotoff/issues/887)) ([f3bcd85](https://github.com/openfoodfacts/robotoff/commit/f3bcd85a958963f0d255ed9a08af564e1f79a4fe))
* create docker network in Makefile + docs ([#770](https://github.com/openfoodfacts/robotoff/issues/770)) ([b5ab0e7](https://github.com/openfoodfacts/robotoff/commit/b5ab0e7dcea7e0ee59c2c5af07580c9b3c25d458))
* fix click dependency in autoblack ([151bd25](https://github.com/openfoodfacts/robotoff/commit/151bd252753963653a047375b20b38c16c34f593))
* fix tests + some i18n utils ([#799](https://github.com/openfoodfacts/robotoff/issues/799)) ([17619ec](https://github.com/openfoodfacts/robotoff/commit/17619ec94bcc2e6cef8783f091b227d76077d3b3))
* fix tests date to use utc ([#686](https://github.com/openfoodfacts/robotoff/issues/686)) ([dd76fc0](https://github.com/openfoodfacts/robotoff/commit/dd76fc037a0eb7bfdd54623ff3c730263f5f3758))
* improve the bug report template ([72e2073](https://github.com/openfoodfacts/robotoff/commit/72e2073213f38efa61ce915866987b10a04db4d7))
* improve the Feature Request template ([f7d9a24](https://github.com/openfoodfacts/robotoff/commit/f7d9a240b2595b43f73adc9f4e67ef36e580a09f))


### Documentation

* add doc about image prediction ([#764](https://github.com/openfoodfacts/robotoff/issues/764)) ([0882878](https://github.com/openfoodfacts/robotoff/commit/0882878b6e7b9816d4f68e5a6e2b6e808d358784))

### [1.5.1](https://github.com/openfoodfacts/robotoff/compare/v1.5.0...v1.5.1) (2022-03-28)


### Bug Fixes

* **api:** Question API, fix query randomness, and allow to use pagination ([#666](https://github.com/openfoodfacts/robotoff/issues/666)) ([5a7fd71](https://github.com/openfoodfacts/robotoff/commit/5a7fd71170789f5a6be926e6a005f5fa56a2e2b6))
* fetch_taxonomy should check response status ([26f318e](https://github.com/openfoodfacts/robotoff/commit/26f318e170b1d3e154e395092c9c764acc79bd4e))
* fix log message for sentry grouping ([bbf2749](https://github.com/openfoodfacts/robotoff/commit/bbf27499d89c0616dda19c6c223f458ae9419b02))
* wrong error message on exception in fetch taxonomy ([5b9252d](https://github.com/openfoodfacts/robotoff/commit/5b9252d298bda2b56fdd530aee50e13112f13912))

## [1.5.0](https://github.com/openfoodfacts/robotoff/compare/v1.4.0...v1.5.0) (2022-03-18)


### Features

* sleep now happens in thread ([#653](https://github.com/openfoodfacts/robotoff/issues/653)) ([d4489cd](https://github.com/openfoodfacts/robotoff/commit/d4489cdcb3b14817ea5c3bfe345c0f20bf05f6b5))


### Bug Fixes

* change error messages to enable sentry grouping ([#654](https://github.com/openfoodfacts/robotoff/issues/654)) ([15abbeb](https://github.com/openfoodfacts/robotoff/commit/15abbeb8ca6f0f65645d1c8ebaa411beb8257463))
* fix timeout issue on fetch taxonomy ([#656](https://github.com/openfoodfacts/robotoff/issues/656)) ([a91ba4e](https://github.com/openfoodfacts/robotoff/commit/a91ba4e4e877130ed5e68f8f14e0cbef9024a10f))

## [1.4.0](https://github.com/openfoodfacts/robotoff/compare/v1.3.0...v1.4.0) (2022-03-16)


### Features

* disable auto processing of predicted category ([8455868](https://github.com/openfoodfacts/robotoff/commit/8455868b041cbb0cbe5310c0b2cdf81d857d7969))
* logo annotation propagation to insight ([2a57a7d](https://github.com/openfoodfacts/robotoff/commit/2a57a7de7a1161292dd23d5e8a9dc4412ba02fbb))


### Bug Fixes

* add test on annotation vote cascade ([2641e25](https://github.com/openfoodfacts/robotoff/commit/2641e251e758e0fa78eb6aa90300a10c355b6bcc))
* avoid process_insight failing for all ([69aeb63](https://github.com/openfoodfacts/robotoff/commit/69aeb63ec9d901a20f5c7c42afada5c659af8490)), closes [#605](https://github.com/openfoodfacts/robotoff/issues/605)
* avoid raising in ObjectDetectionRawResult ([c2ab5f6](https://github.com/openfoodfacts/robotoff/commit/c2ab5f64c7aeff1ccba321210d61482e562a3cbe)), closes [#621](https://github.com/openfoodfacts/robotoff/issues/621)
* fix notification message for categories ([cf6a675](https://github.com/openfoodfacts/robotoff/commit/cf6a6758c44cf3535c3fd0223f1c2cd4beeee2f8)), closes [#614](https://github.com/openfoodfacts/robotoff/issues/614)
* test logo annotation ([e265ce6](https://github.com/openfoodfacts/robotoff/commit/e265ce66a07b149fbaec306e374d42dd7d5461b2))


### Documentation

* some typos fixes ([6f8ebe0](https://github.com/openfoodfacts/robotoff/commit/6f8ebe066f4b411c26b327c4b38d97f175c37b21))

## [1.3.0](https://www.github.com/openfoodfacts/robotoff/compare/v1.2.0...v1.3.0) (2022-02-22)

### Features

* continue structural changes to have insights derived from predictions

## [1.2.0](https://www.github.com/openfoodfacts/robotoff/compare/v1.1.0...v1.2.0) (2022-02-07)


### Features

* add value_tag in the question formater ([#579](https://www.github.com/openfoodfacts/robotoff/issues/579)) ([84239f1](https://www.github.com/openfoodfacts/robotoff/commit/84239f1ca686d94ab69cdfe3bd2b02b338363768))
* make neural category apply automatically ([#555](https://www.github.com/openfoodfacts/robotoff/issues/555)) ([2146f78](https://www.github.com/openfoodfacts/robotoff/commit/2146f7805b2be21476f14c0bde5a7fab6bf65ab8)), closes [#552](https://www.github.com/openfoodfacts/robotoff/issues/552)


### Bug Fixes

* ensure influxdb database exists ([#559](https://www.github.com/openfoodfacts/robotoff/issues/559)) ([1f7a9ee](https://www.github.com/openfoodfacts/robotoff/commit/1f7a9eed04dcc254a079c9eef8dc1479563ce6a5))
* scheduler and tasks in isolated transactions - fixes [#608](https://www.github.com/openfoodfacts/robotoff/issues/608) ([#609](https://www.github.com/openfoodfacts/robotoff/issues/609)) ([c5d44a4](https://www.github.com/openfoodfacts/robotoff/commit/c5d44a421a2bd75be8c573c3f4a44dfde7aa5a7f))
* set num workers in gunicorn from env ([#563](https://www.github.com/openfoodfacts/robotoff/issues/563)) ([0290964](https://www.github.com/openfoodfacts/robotoff/commit/0290964babcbc4f5c3a21c53e3dd905dadac405f))
* set num workers in gunicorn from env ([#563](https://www.github.com/openfoodfacts/robotoff/issues/563)) ([#564](https://www.github.com/openfoodfacts/robotoff/issues/564)) ([89c1c13](https://www.github.com/openfoodfacts/robotoff/commit/89c1c13e4e055ce27fa5ab389c57cd982fab3858))
* straight conditions for category insights ([#570](https://www.github.com/openfoodfacts/robotoff/issues/570)) ([1d44643](https://www.github.com/openfoodfacts/robotoff/commit/1d4464326fd1ace01bf625c4e1285e57b8817e91))

## [1.1.0](https://www.github.com/openfoodfacts/robotoff/compare/v1.1.0-rc1...v1.1.0) (2022-01-20)


### Features

* add health tests & improve CI ([#527](https://www.github.com/openfoodfacts/robotoff/issues/527)) ([56dcfdc](https://www.github.com/openfoodfacts/robotoff/commit/56dcfdce8d1352cfbae9b1c1e19234cdaaa8b57a))
* make wait on product update a parameter ([70d54c3](https://www.github.com/openfoodfacts/robotoff/commit/70d54c32afaab009547894e9283a461baec7f9b9))
