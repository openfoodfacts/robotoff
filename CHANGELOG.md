# Changelog

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
