# Changelog

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
