# ANN Benchmark

All logos are embedded through a computer vision model.
In order to help logos annotation, the nearest neighbors of each logo must be easily accesible.
A benchmark has been performed to determine the best way to perform a nearest neighbors search among the following HNSW indexes:

- (faiss)[https://github.com/facebookresearch/faiss]
- (redis)[https://redis.io/docs/stack/search/reference/vectors/]
- (elasticsearch)[https://www.elastic.co/fr/blog/introducing-approximate-nearest-neighbor-search-in-elasticsearch-8-0]

For each framework, multiple parameters were used to find the best index in our use case.

## Our Use Case

The data used to test the performance of the indexes was made of 4.371.343 vectors (each one issued from the CLIP vision model with a logo as input) of dimension 768 and type float32.

The dimension of each vector used in the benchmark is 768, the size of embeddings CLIP outputs before processing through the projection layer. However, in production, as this last layer of the CLIP model is used, the dimension of the embeddings that are indexed is actually 512. The process to go from 768 to 512 being only a projection, the change of dimensionality should not impact the results. A test of elasticsearch with 512 dimension vectors did indeed lead to very similar results as the ones computed with 768 dimension vectors.  

The goal is to search for nearest neighbors in real time.
The search time must be short.
The precision of the search matters as it is important to get logos as close as possible from the query logo for the annotators to be efficient.

The feature is expected to work in production on machines that run other tasks in parallel.
The memory used by the index and search must thus be as small as possible.

## Conditions of the tests

All HNSW results were compared to FLAT faiss index search (an exact search) results to compute the precision of the index.
Only cosine similarity was usedin this benchmark.

HNSW indexes are adjustable trhough three parameters:

- m: the number of connections that each node in the index has to its neighbors
- efConstruction:  the size of the priority queue used during the construction of the index
- efSearch/efRuntime/num_candidates: the size of the priority queue used during search operations

## Benchmark

You can find the code of the various benchmarks [here](https://github.com/openfoodfacts/openfoodfacts-ai/tree/d74dba0/logo-ann/benchmarks/ANN_benchmark).

Here are the results obtained with **Faiss** :

| m  | efConstruction | efSearch | micro-recall@1 | micro-recall@4 | micro-recall@10 | micro-recall@50 | micro-recall@100 |
|----|----------------|----------|----------------|----------------|-----------------|-----------------|------------------|
| -  | -              | -        | -              | -              | -               | -               | -                |
| 8  | 128            | 64       | 0.582          | 0.69475        | 0.706           | 0.70754         | 0.6829           |
| 8  | 128            | 128      | 0.591          | 0.70925        | 0.7238          | 0.72874         | 0.72166          |
| 8  | 256            | 64       | 0.598          | 0.714          | 0.7265          | 0.72542         | 0.70022          |
| 8  | 256            | 128      | 0.603          | 0.72225        | 0.7356          | 0.74082         | 0.7346           |
| 16 | 128            | 64       | 0.605          | 0.72875        | 0.7393          | 0.74212         | 0.72658          |
| 16 | 128            | 128      | 0.615          | 0.737          | 0.7476          | 0.75206         | 0.74833          |
| 16 | 256            | 64       | 0.623          | 0.74175        | 0.7501          | 0.75244         | 0.73805          |
| 16 | 256            | 128      | 0.624          | 0.745          | 0.7546          | 0.7581          | 0.75509          |

The recall never outreaches 0.76. 
A better recall is wanted.
The Redis HNSW indexes were thus explored.

Here are the results obtained with **Redis** :

| m | efConstruction | efRuntime | micro-recall@1 | micro-recall@4 | micro-recall@10 | micro-recall@50 | micro-recall@100 |
|---|----------------|-----------|----------------|----------------|-----------------|-----------------|------------------|
| - | -              | -         | -              | -              | -               | -               | -                |
| 4 | 128            | 64        | 0.799          | 0.795          | 0.7968          | 0.76916         | 0.72839          |
| 4 | 128            | 128       | 0.822          | 0.81875        | 0.8215          | 0.79918         | 0.76812          |
| 4 | 256            | 64        | 0.83           | 0.8305         | 0.8254          | 0.79126         | 0.74795          |
| 4 | 256            | 128       | 0.855          | 0.8565         | 0.8511          | 0.82204         | 0.78854          |
| 8 | 128            | 64        | 0.955          | 0.94075        | 0.9318          | 0.90614         | 0.88248          |
| 8 | 128            | 128       | 0.964          | 0.95           | 0.9403          | 0.91784         | 0.90007          |
| 8 | 256            | 64        | 0.964          | 0.9515         | 0.9424          | 0.91672         | 0.89339          |
| 8 | 256            | 128       | 0.969          | 0.95725        | 0.9477          | 0.92514         | 0.90855          |

The efficiency of these indexes, with the right parameters are better.

However, Redis loads all the embeddings in RAM when loading the index, which accounts for more than 20 GB of RAM used by it.
This is too much for our use case.

The last tool explored is **ElasticSearch**.
With the default parameters, here is what was obtained:

| m  | efConstruction | num_candidates | micro-recall@1 | micro-recall@4 | micro-recall@10 | micro-recall@50 | micro-recall@100 |
|----|----------------|----------------|----------------|----------------|-----------------|-----------------|------------------|
| -  | -              | -              | -              | -              | -               | -               | -                |
| 16 | 200            | 50             | 0.977          | 0.9635         | 0.9533          | 0.93832         | 0.93512          |

The results are excellent. 
The RAM used is bellow 5 GB.
And the time search is around 80 ms, which is acceptable for our use case and way bellow the 3 seconds for exact search with a FLAT faiss index.

ElasticSearch was thus chosen for computing the ANN search.