# Question format proposal

After loading a product, the client (web, iOS, Android) will request the Robotoff server a _question_ (on 
`/api/v1/questions/{barcode}`).
A question includes an insight and metadata such that the client knows how to display the question and what kind of 
input is expected from the user. All data returned by Robotoff is localized with respect to the `lang` parameter 
provided by the client.

## Question formats

For all formats, a _I don't know_ button will offer the user the possibility to leave without answering the question.

### Addition: Binary choice (`add-binary`)

Add a fact about a product, by accepting (1) or rejecting (0) the insight.

For instance:

- add a new label (`en:organic`)
- add a new packager code (`EMB 52052B`)
- Add a new category (`en:pastas`)

#### Format

+ type (str, required) - The question type (`add-binary`)
+ question (str, required) - The question, in the user locale
+ value (str, optional) - The suggested value for the field
+ image_url (str, optional) - An image to display
+ insight_id (str, required) - ID of the insight

`value` or `image_url` cannot be both missing.

#### Examples

```json
{
  "type": "add-binary",
  "question": "Does this product belong to this category ?",
  "value": "Pastas",
  "insight_id": "{INSIGHT_ID}",
  "insight_type": "category"
}
```

```json
{
  "type": "add-binary",
  "question": "Does this product have this label?",
  "value": "EU Organic",
  "image_url": "https://static.openfoodfacts.org/images/lang/fr/labels/bio-europeen.135x90.png",
  "insight_id": "{INSIGHT_ID}",
  "insight_type": "label"
}
```

The `image_url` can be used to display an image in the `question` interface, such as labels (IGP, organic,...).

The client returns the insight ID and the annotation (0, -1 or 1).


### Spellcheck (`spellcheck`)

Spellchecking on text fields, including the ingredient list. A specific interface is used to show the correction.

#### Format

+ type (str, required) - The question type (`spellcheck`)
+ original_snippet (str, required) - a snippet of the text field
+ value (str, optional) - The suggested value for the field
+ image_url (str, optional) - An image to display
+ insight_id (str, required) - ID of the insight

`value` or `image_url` cannot be both missing.

#### Examples

```json
{
  "type": "add-binary",
  "question": "Does this product belong to this category ?",
  "value": "Pastas",
  "insight_id": "{INSIGHT_ID}"
}
```

```json
{
  "type": "add-binary",
  "question": "Does this product have this label?",
  "value": "EU Organic",
  "image_url": "https://static.openfoodfacts.org/images/lang/fr/labels/bio-europeen.135x90.png",
  "insight_id": "{INSIGHT_ID}"
}
```