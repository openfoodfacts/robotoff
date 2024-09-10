# Ingredients Spellcheck

A key element of Open Food Facts database is the parsing of the product ingredients. These lists of ingredients either come from contributors' annotation or OCR-extracted text from packaging pictures.

However, text typos or wrong OCR-extraction lead to ingredients not recognized by the Product Opener service. (Check more about this process in the [wiki](https://wiki.openfoodfacts.org/Ingredients_Extraction_and_Analysis)).

For this reason, an Ingredients Spellcheck based on Machine Learning has been developed to solve this issue.

## TL;DR

Mistral-7B-Base was fine-tuned on a synthetically generated [dataset](https://huggingface.co/datasets/openfoodfacts/spellcheck-dataset) using proprietary LLMs and manually reviewed.

The current model (v1) performs better than all other proprietary LLMs in term of Precison and Recall on our [benchmark](https://huggingface.co/datasets/openfoodfacts/spellcheck-benchmark) using our custom [evaluation algorithm](#evaluation-algorithm).

The model is integrated into Robotoff in [Batch Inference](batch-job) using Google Batch Job.

## Evaluation algorithm

The solution we want to implement is very specific: the model should correct typos and errors in list of ingredients to enable the parser to correctly detect what the product is composed of. However, since the corrections are later added to the database, we need to ensure the model didn't correct an ingredient, or any other character, by mistake. In other words, we need to reduce the number of False Positives while increasing the Recall.

Existing metrics, such as [ROUGE](https://en.wikipedia.org/wiki/ROUGE_(metric)), [BLEU](https://en.wikipedia.org/wiki/BLEU), or [METEOR](https://en.wikipedia.org/wiki/METEOR) are not appropriate to evaluate the quality of the spellcheck since doesn't allow to look in details how many words were rightly corrected and those that were not based on the reference.

Therefore, we developed an algorithm that takes 3 inputs: the original, the reference, and the prediction of a  list of ingredients.

Example:
``` 
Original:       "Th cat si on the fride,"
Reference:      "The cat is on the fridge."
Prediction:     "Th big cat is in the fridge."
```

Visually, we can already say which words were supposed to be corrected, and those where the prediction wrongly added a modification to the original text!

Algorithmicaly, we transform each text into a sequence of tokens and perform a [sequence alignement method](https://en.wikipedia.org/wiki/Needleman%E2%80%93Wunsch_algorithm) to align identical tokens between respectufully the original and the reference; and the prediction and reference. We assign 1 or 0 if the tokens is modified or not.

By comparing these 2 pairs of sequences, we are able to calculate the number of True Positives (TP), False Positives (FP), and True Negatives (TN). Therefore, the overall Precision and Recall can be calculated.

```
Orig-Ref:          1    0    0    1    0    1    1    1    1
Orig-Pred:         0    1    0    1    1    1    1    1    1
Signification:     FN   FP   TN   TP   FP   TP   TP   TP   TP
```

Coupled with a benchmark carefully prepared using a spellcheck guidelines, the algorithm is capable of evaluating any solution, from Regex techniques to LLMs.

More details about the evaluation algorithm[^evaluation-algo] in the [README](https://github.com/openfoodfacts/openfoodfacts-ai/tree/develop/spellcheck) of the Spellcheck project.


## Guidelines

## Model

## Performance

## Training pipeline with Metaflow & Sagemaker & CometML & Argilla

* Instruction
* Hyperparameters
* Dataset versions

## Synthetic data generation

## Integration with Batch Job

* Dockerfile

## RAF


[^evaluation-algo]: see `src/spellcheck/evaluation/evaluator`