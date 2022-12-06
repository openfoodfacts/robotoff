# Changelog

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
