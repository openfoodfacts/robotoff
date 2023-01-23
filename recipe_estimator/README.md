In order to install ORTools had to update tritonclient as that depended on an older version of protobuf:

poetry add tritonclient@latest

then

poetry add ortools


Get nutrient types:

```js
db.products.aggregate([
  {
    $project: {
      keys: {
        $map: {
          input: {
            "$objectToArray": "$nutriments"
          },
          in: "$$this.k"
        }
      }
    }
  },
  {
    $unwind: "$keys"
  },
  {
    $group: {
      _id: "$keys",
      count: {
        "$sum": 1
      }
    }
  }
])
```

Need to skip any nutrients where Ciqual value is '-' as this means not known, not zero