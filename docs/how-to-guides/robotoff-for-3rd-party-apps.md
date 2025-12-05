# Implementing Robotoff Questions in 3rd Party Apps

This tutorial explains how to implement Robotoff questions in your 3rd party application, allowing users to contribute to food transparency and data accuracy on Open Food Facts.

## Rationale

Robotoff questions help increase food transparency and simplify obtaining the Nutri-Score by enabling categorization of products (and more).

## How to Implement

### API Reference

For detailed API endpoints and their specifications, refer to the official Robotoff API documentation:

<https://openfoodfacts.github.io/robotoff/references/api/#tag/Question-Management>

### Displaying Questions

  * **Visibility for Non-Logged Users:** Questions should be visible to users even if they are not logged in.
  * **Prompt for Non-Logged Users:** If a non-logged user attempts to answer a question, display a prompt to log in or create an account (or let them use our anonymous statistical voting system). Provide a setting to hide these prompts if they annoy the user.
  * **Fetching Questions:** When a product is opened in your application, fetch the relevant Robotoff questions.
      * **Example API Call:**
        ``` 
        https://robotoff.openfoodfacts.org/api/v1/questions/3274570800026?lang=en&count=3
        
        ```
        This example fetches 3 questions for the barcode `3274570800026` in English.
      * **Response Structure Example:**
        ``` json
        {
          "questions": [
            {
              "barcode": "3274570800026",
              "type": "add-binary",
              "value": "Scallop",
              "question": "Does the product belong to this category?",
              "insight_id": "5cac03bc-a5a7-4ec2-a548-17fd9319fee7",
              "insight_type": "category",
              "source_image_url": "https://static.openfoodfacts.org/images/products/327/457/080/0026/front_en.4.400.jpg"
            }
          ],
          "status": "found"
        }
        
        ```
      * The `lang` field in the request specifies the language of the returned `question` and `value`.
  * **UI Display:** Display the `question` and possible answers in your application's user interface.

### Sending Answers

If a user answers a question, send the appropriate ping back to the Open Food Facts server.

  * **API for Annotating Insights:**
    ``` 
    https://robotoff.openfoodfacts.org/api/v1/insights/annotate?insight_id=(insight_id)&annotation=(1,0,-1)&update=1
    
    ```
      * Replace `(insight_id)` with the `insight_id` received from the question payload.
      * Replace `(1,0,-1)` with the user's annotation:
          * `1`: Yes
          * `0`: No
          * `-1`: Skip/Don't know

## Authentication

To give credit to contributors for their answers, you need to authenticate your requests to Robotoff.

### Header-based Authentication

Send the following header with your requests:

``` 
Authorization: Basic (base64Credentials)

```

Where `base64Credentials` is the Base64 encoding of your `username:password`.

### Cookie-based Authentication
Note: we have a cookie auth for tools hosted on *.openfoodfacts.org. Please reachout to the Robotoff team if needed.

## Platform-Specific Implementations
* Web component available at https://github.com/openfoodfacts/openfoodfacts-webcomponents
* Flutter/Dart (available in our Dart package, and UI code is available in the official smooth-app repository
* Android (old official app, Kotlin, some code might be usable)
      * <https://github.com/openfoodfacts/openfoodfacts-androidapp/issues/3024>
      * <https://github.com/openfoodfacts/openfoodfacts-androidapp/issues/2931>
* iOS (old official app, Swift, some code might be usable)
      * https://github.com/openfoodfacts/openfoodfacts-ios
