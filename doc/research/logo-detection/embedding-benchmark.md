# Benchmark

When releasing the first version of the logo detection pipeline, the performance was unknown, as we didn't have any labeled logo dataset to measure it.

This pipeline helped us build the [first annotated logo dataset](https://github.com/openfoodfacts/openfoodfacts-ai/releases/tag/dataset-logo-2022-01-21) so that we can now measure how the original EfficientNet-b0 model (pretrained on ImageNet) performs compared to other pretrained models.

Logo embeddings were computed using each model. For each logo, two different distances were used to find the most similar logos among the rest of the dataset, and results were sorted by ascending distance. The first table shows the results obtained with the L2 distance and the second one shows the results we got with the cosine distance.

To keep the comparison fair and avoid favoring classes with many samples, for each target image, we only considered at most 4 items of each class. These items were sampled at random among the class items. As each class contains at least 5 items, all classes (including the target class, i.e. the class of the target logo) have 4 candidates. With this setting, an oracle model would have a recall@4 of 1.

The *val* split was used to perform this benchmark. The benchmark code can be found [here](https://github.com/openfoodfacts/openfoodfacts-ai/tree/develop/logo-ann/benchmarks/embedding_models_benchmark).

We use the following metrics:

- **micro-recall@4**: skewed by classes with many samples.
- **macro-recall@4**: gives equal weight to all classes.

All compared models were trained on ImageNet, except:

- `beit_large_patch16_224_in22k`, trained on ImageNet 22k
- `clip-vit-*`, trained on the proprietary dataset described in the [CLIP paper](https://arxiv.org/abs/2103.00020).

Note that we use the `timm` library to generate embeddings (except for CLIP models, where the `transformers` library was used). The model weights mostly come from the `timm` author's training and differ from the original weights.

Latency was measured on 50 batches of 8 samples with a Tesla T4 GPU.

With **L2 distance** :

| model                        | micro-recall@4 | macro-recall@4 |
| ---------------------------- | -------------- | -------------- |
| random                       | 0.0083         | 0.0063         |
| efficientnet_b1              | 0.4612         | 0.5070         |
| resnest101e                  | 0.4322         | 0.5124         |
| beit_large_patch16_384       | 0.4162         | 0.5233         |
| efficientnet_b2              | 0.4707         | 0.5323         |
| rexnet_100                   | 0.5158         | 0.5340         |
| efficientnet_b4              | 0.4807         | 0.5450         |
| resnet50                     | 0.4916         | 0.5609         |
| efficientnet_b0              | 0.5420         | 0.5665         |
| beit_base_patch16_384        | 0.4758         | 0.5666         |
| resnet50d                    | 0.5313         | 0.6133         |
| beit_large_patch16_224_in22k | 0.5723         | 0.6660         |
| clip-vit-base-patch32        | 0.7006         | 0.8243         |
| clip-vit-base-patch16        | 0.7295         | 0.8428         |
| clip-vit-large-patch14       | **0.7706**     | **0.8755**     |
| deit_base_patch16_384        | 0.3920         | 0.4375         |

With **cosine distance** :

| model                        | micro-recall@4 | macro-recall@4 |
| ---------------------------- | -------------- | -------------- |
| random                       | 0.0091         | 0.0114         |
| efficientnet_b1              | 0.4941         | 0.5334         |
| resnest101e                  | 0.4777         | 0.5415         |
| efficientnet_b2              | 0.4909         | 0.5466         |
| rexnet_100                   | 0.5461         | 0.5716         |
| efficientnet_b4              | 0.5141         | 0.5861         |
| resnet50                     | 0.5241         | 0.5868         |
| efficientnet_b0              | 0.5489         | 0.5838         |
| resnet50d                    | 0.5791         | 0.6353         |
| clip-vit-base-patch32        | 0.7030         | 0.8244         |
| clip-vit-base-patch16        | 0.7297         | 0.8470         |
| clip-vit-large-patch14       | **0.7753**     | **0.8722**     |
| deit_base_patch16_384        | 0.4403         | 0.5070         |

Embedding size and per-sample latency (independent of the distance used):

| model                        | embedding size | per-sample latency (ms) |
| ---------------------------- | -------------- | ----------------------- |
| random                       | -              | -                       |
| efficientnet_b1              | 1280           | 3.93                    |
| resnest101e                  | 1024           | 142.75                  |
| efficientnet_b2              | 1408           | 4.29                    |
| rexnet_100                   | 1280           | 3.91                    |
| efficientnet_b4              | 1792           | 6.99                    |
| resnet50                     | 2048           | 3.50                    |
| efficientnet_b0              | 1280           | 5.51                    |
| beit_base_patch16_384        | 768            | 41.88                   |
| resnet50d                    | 2048           | 4.01                    |
| beit_large_patch16_224_in22k | 1024           | 43.56                   |
| clip-vit-base-patch32        | 768            | **3.08**                |
| clip-vit-base-patch16        | 768            | 11.69                   |
| clip-vit-large-patch14       | 1024           | 56.68                   |
| deit_base_patch16_384        | 768            | 1.73                    |

N.B: we didn't use the cosine-distance for the beit models as they were not working anymore when doing the benchmark with the cosine distance. Some explanations can be found [there](https://github.com/rwightman/pytorch-image-models/issues/1346).

We note that the cosine distance tends to be slightly better than the L2 distance for each model (except for the `clip-vit-large-patch14`) but the use of one distance or the other does not change the following analysis as the ranking of the models remains the same.

As expected, the current model (`efficientnet-b0`) performs well above the random baseline. Its performances are competitive compared to most other architectures pretrained on ImageNet.

However, CLIP models largely outperform any other tested architecture on this benchmark: with `clip-vit-large-patch14` we gain +22.8 on micro-recall@4 and +30.9 on macro-recall@4 compared to `efficientnet-b0`.

Performances of CLIP models increase as models gets larger or with a smaller image patch size. The prediction latency is however 3.8x and 18,4x higher for `clip-vit-base-patch16` and `clip-vit-large-patch14` respectively compared to `clip-vit-base-patch32`.

In conclusion, CLIP models are very good candidates for an off-the-shelf replacement of the `efficientnet-b0` model currently used to generate logo embeddings. An additional benefit from this model architecture is the smaller embedding size (768 or 1024, depending on the version) compared to the original `efficientnet-b0` model (1280).

To study the behaviour of each model in a case closer to our usecase, we performed another benchmark based this time of the efficiency of each model to predict the right label for each logo of val.txt file. The predicted label is the most represented one among the k closest neighbours.

Here are the results we obtained working with a cosine distance :

| model                        | micro-recall@4 | macro-recall@4 |
| ---------------------------- | -------------- | -------------- |
| random                       | 0.0098         | 0.0098         |
| efficientnet_b1              | 0.7347         | 0.7711         |
| resnest101e                  | 0.7089         | 0.7653         |
| efficientnet_b2              | 0.7379         | 0.7847         |
| rexnet_100                   | 0.7848         | 0.7896         |
| efficientnet_b4              | 0.7590         | 0.8025         |
| resnet50                     | 0.7667         | 0.8050         |
| efficientnet_b0              | 0.7835         | 0.8098         |
| resnet50d                    | 0.8054         | 0.8229         |
| clip-vit-base-patch32        | 0.9139         | 0.9196         |
| clip-vit-base-patch16        | 0.9171         | 0.9219         |
| clip-vit-large-patch14       | **0.9427**     | **0.9417**     |
| deit_base_patch16_384        | 0.7025         | 0.7573         |

The CLIP models remain better than the others.