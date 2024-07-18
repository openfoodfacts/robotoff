"""
This file has been copied and adapted from
https://github.com/huggingface/transformers/blob/v4.25.1/src/transformers/pipelines/token_classification.py

The code is under Apache-2.0 license:
https://github.com/huggingface/transformers/blob/main/LICENSE

We use Triton to serve the request, but still need NER prediction
post-processing, and HuggingFace transformers library provide this feature
nicely using `TokenClassificationPipeline`.

Most of the code was kept unchanged, the only modifications that were made
were the following:

- accept numpy array as input instead of Tensorflow/Pytorch tensors
- remove unnecessary code (everything that is not related to post-processing)
- `postprocess` now accepts a single sample (instead of a batched sample of
    size 1)
"""

import enum
import warnings
from typing import List, Optional, Tuple

import numpy as np


class AggregationStrategy(enum.Enum):
    """All the valid aggregation strategies for TokenClassificationPipeline"""

    NONE = "none"
    SIMPLE = "simple"
    FIRST = "first"
    AVERAGE = "average"
    MAX = "max"


class TokenClassificationPipeline:
    default_input_names = "sequences"

    def __init__(self, tokenizer, id2label):
        self.tokenizer = tokenizer
        self.id2label = id2label

    def _sanitize_parameters(
        self,
        ignore_labels=None,
        grouped_entities: Optional[bool] = None,
        ignore_subwords: Optional[bool] = None,
        aggregation_strategy: Optional[AggregationStrategy] = None,
        offset_mapping: Optional[List[Tuple[int, int]]] = None,
    ):

        preprocess_params = {}
        if offset_mapping is not None:
            preprocess_params["offset_mapping"] = offset_mapping

        postprocess_params = {}
        if grouped_entities is not None or ignore_subwords is not None:
            if grouped_entities and ignore_subwords:
                aggregation_strategy = AggregationStrategy.FIRST
            elif grouped_entities and not ignore_subwords:
                aggregation_strategy = AggregationStrategy.SIMPLE
            else:
                aggregation_strategy = AggregationStrategy.NONE

            if grouped_entities is not None:
                warnings.warn(
                    "`grouped_entities` is deprecated and will be removed in version v5.0.0, defaulted to"
                    f' `aggregation_strategy="{aggregation_strategy}"` instead.'
                )
            if ignore_subwords is not None:
                warnings.warn(
                    "`ignore_subwords` is deprecated and will be removed in version v5.0.0, defaulted to"
                    f' `aggregation_strategy="{aggregation_strategy}"` instead.'
                )

        if aggregation_strategy is not None:
            if isinstance(aggregation_strategy, str):
                aggregation_strategy = AggregationStrategy[aggregation_strategy.upper()]
            if (
                aggregation_strategy
                in {
                    AggregationStrategy.FIRST,
                    AggregationStrategy.MAX,
                    AggregationStrategy.AVERAGE,
                }
                and not self.tokenizer.is_fast
            ):
                raise ValueError(
                    "Slow tokenizers cannot handle subwords. Please set the `aggregation_strategy` option"
                    'to `"simple"` or use a fast tokenizer.'
                )
            postprocess_params["aggregation_strategy"] = aggregation_strategy
        if ignore_labels is not None:
            postprocess_params["ignore_labels"] = ignore_labels
        return preprocess_params, {}, postprocess_params

    def postprocess(
        self,
        model_outputs,
        aggregation_strategy=AggregationStrategy.NONE,
        ignore_labels=None,
    ):
        if ignore_labels is None:
            ignore_labels = ["O"]
        logits = model_outputs["logits"]
        sentence = model_outputs["sentence"]
        input_ids = model_outputs["input_ids"]
        offset_mapping = (
            model_outputs["offset_mapping"]
            if model_outputs["offset_mapping"] is not None
            else None
        )
        special_tokens_mask = model_outputs["special_tokens_mask"]

        maxes = np.max(logits, axis=-1, keepdims=True)
        shifted_exp = np.exp(logits - maxes)
        scores = shifted_exp / shifted_exp.sum(axis=-1, keepdims=True)

        pre_entities = self.gather_pre_entities(
            sentence,
            input_ids,
            scores,
            offset_mapping,
            special_tokens_mask,
            aggregation_strategy,
        )
        grouped_entities = self.aggregate(pre_entities, aggregation_strategy)
        # Filter anything that is in self.ignore_labels
        entities = [
            entity
            for entity in grouped_entities
            if entity.get("entity", None) not in ignore_labels
            and entity.get("entity_group", None) not in ignore_labels
        ]
        return entities

    def gather_pre_entities(
        self,
        sentence: str,
        input_ids: np.ndarray,
        scores: np.ndarray,
        offset_mapping: Optional[List[Tuple[int, int]]],
        special_tokens_mask: np.ndarray,
        aggregation_strategy: AggregationStrategy,
    ) -> List[dict]:
        """Fuse various numpy arrays into dicts with all the information
        needed for aggregation"""
        pre_entities = []
        for idx, token_scores in enumerate(scores):
            # Filter special_tokens, they should only occur
            # at the sentence boundaries since we're not encoding pairs of
            # sentences so we don't have to keep track of those.
            if special_tokens_mask[idx]:
                continue

            word = self.tokenizer.convert_ids_to_tokens(int(input_ids[idx]))
            if offset_mapping is not None:
                start_ind, end_ind = offset_mapping[idx]
                word_ref = sentence[start_ind:end_ind]
                if getattr(
                    self.tokenizer._tokenizer.model, "continuing_subword_prefix", None
                ):
                    # This is a BPE, word aware tokenizer, there is a correct
                    # way to fuse tokens
                    is_subword = len(word) != len(word_ref)
                else:
                    # This is a fallback heuristic. This will fail most likely
                    # on any kind of text + punctuation mixtures that will be
                    # considered "words". Non word aware models cannot do
                    # better than this unfortunately.
                    if aggregation_strategy in {
                        AggregationStrategy.FIRST,
                        AggregationStrategy.AVERAGE,
                        AggregationStrategy.MAX,
                    }:
                        warnings.warn(
                            "Tokenizer does not support real words, using fallback heuristic",
                            UserWarning,
                        )
                    is_subword = (
                        start_ind > 0
                        and " " not in sentence[start_ind - 1 : start_ind + 1]
                    )

                if int(input_ids[idx]) == self.tokenizer.unk_token_id:
                    word = word_ref
                    is_subword = False
            else:
                start_ind = None
                end_ind = None
                is_subword = False

            pre_entity = {
                "word": word,
                "scores": token_scores,
                "start": start_ind,
                "end": end_ind,
                "index": idx,
                "is_subword": is_subword,
            }
            pre_entities.append(pre_entity)
        return pre_entities

    def aggregate(
        self, pre_entities: List[dict], aggregation_strategy: AggregationStrategy
    ) -> List[dict]:
        if aggregation_strategy in {
            AggregationStrategy.NONE,
            AggregationStrategy.SIMPLE,
        }:
            entities = []
            for pre_entity in pre_entities:
                entity_idx = pre_entity["scores"].argmax()
                score = pre_entity["scores"][entity_idx]
                entity = {
                    "entity": self.id2label[entity_idx],
                    "score": score,
                    "index": pre_entity["index"],
                    "word": pre_entity["word"],
                    "start": pre_entity["start"],
                    "end": pre_entity["end"],
                }
                entities.append(entity)
        else:
            entities = self.aggregate_words(pre_entities, aggregation_strategy)

        if aggregation_strategy == AggregationStrategy.NONE:
            return entities
        return self.group_entities(entities)

    def aggregate_word(
        self, entities: List[dict], aggregation_strategy: AggregationStrategy
    ) -> dict:
        word = self.tokenizer.convert_tokens_to_string(
            [entity["word"] for entity in entities]
        )
        if aggregation_strategy == AggregationStrategy.FIRST:
            scores = entities[0]["scores"]
            idx = scores.argmax()
            score = scores[idx]
            entity = self.id2label[idx]
        elif aggregation_strategy == AggregationStrategy.MAX:
            max_entity = max(entities, key=lambda entity: entity["scores"].max())
            scores = max_entity["scores"]
            idx = scores.argmax()
            score = scores[idx]
            entity = self.id2label[idx]
        elif aggregation_strategy == AggregationStrategy.AVERAGE:
            scores = np.stack([entity["scores"] for entity in entities])
            average_scores = np.nanmean(scores, axis=0)
            entity_idx = average_scores.argmax()
            entity = self.id2label[entity_idx]
            score = average_scores[entity_idx]
        else:
            raise ValueError("Invalid aggregation_strategy")
        new_entity = {
            "entity": entity,
            "score": score,
            "word": word,
            "start": entities[0]["start"],
            "end": entities[-1]["end"],
        }
        return new_entity

    def aggregate_words(
        self, entities: List[dict], aggregation_strategy: AggregationStrategy
    ) -> List[dict]:
        """
        Override tokens from a given word that disagree to force agreement on
        word boundaries.

        Example: micro|soft| com|pany| B-ENT I-NAME I-ENT I-ENT will be
        rewritten with first strategy as microsoft|
        company| B-ENT I-ENT
        """
        if aggregation_strategy in {
            AggregationStrategy.NONE,
            AggregationStrategy.SIMPLE,
        }:
            raise ValueError(
                "NONE and SIMPLE strategies are invalid for word aggregation"
            )

        word_entities = []
        word_group = None
        for entity in entities:
            if word_group is None:
                word_group = [entity]
            elif entity["is_subword"]:
                word_group.append(entity)
            else:
                word_entities.append(
                    self.aggregate_word(word_group, aggregation_strategy)
                )
                word_group = [entity]
        # Last item
        word_entities.append(self.aggregate_word(word_group, aggregation_strategy))  # type: ignore
        return word_entities

    def group_sub_entities(self, entities: List[dict]) -> dict:
        """
        Group together the adjacent tokens with the same entity predicted.

        Args:
            entities (`dict`): The entities predicted by the pipeline.
        """
        # Get the first entity in the entity group
        entity = entities[0]["entity"].split("-")[-1]
        scores = np.nanmean([entity["score"] for entity in entities])
        tokens = [entity["word"] for entity in entities]

        entity_group = {
            "entity_group": entity,
            "score": np.mean(scores),
            "word": self.tokenizer.convert_tokens_to_string(tokens),
            "start": entities[0]["start"],
            "end": entities[-1]["end"],
        }
        return entity_group

    def get_tag(self, entity_name: str) -> Tuple[str, str]:
        if entity_name.startswith("B-"):
            bi = "B"
            tag = entity_name[2:]
        elif entity_name.startswith("I-"):
            bi = "I"
            tag = entity_name[2:]
        else:
            # It's not in B-, I- format
            # Default to I- for continuation.
            bi = "I"
            tag = entity_name
        return bi, tag

    def group_entities(self, entities: List[dict]) -> List[dict]:
        """
        Find and group together the adjacent tokens with the same entity
        predicted.

        Args:
            entities (`dict`): The entities predicted by the pipeline.
        """

        entity_groups = []
        entity_group_disagg: list[dict] = []

        for entity in entities:
            if not entity_group_disagg:
                entity_group_disagg.append(entity)
                continue

            # If the current entity is similar and adjacent to the previous
            # entity, append it to the disaggregated entity group
            # The split is meant to account for the "B" and "I" prefixes
            # Shouldn't merge if both entities are B-type
            bi, tag = self.get_tag(entity["entity"])
            last_bi, last_tag = self.get_tag(entity_group_disagg[-1]["entity"])

            if tag == last_tag and bi != "B":
                # Modify subword type to be previous_type
                entity_group_disagg.append(entity)
            else:
                # If the current entity is different from the previous entity
                # aggregate the disaggregated entity group
                entity_groups.append(self.group_sub_entities(entity_group_disagg))
                entity_group_disagg = [entity]
        if entity_group_disagg:
            # it's the last entity, add it to the entity groups
            entity_groups.append(self.group_sub_entities(entity_group_disagg))

        return entity_groups
