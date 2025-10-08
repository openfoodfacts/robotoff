# SDK Notification Workflow

This document describes the GitHub Action workflow that automatically notifies OpenFoodFacts SDK repositories when Robotoff releases contain API changes.

## Overview

The `notify-sdk-api-changes.yml` workflow:

1. **Triggers** on every published release
2. **Detects** API changes by scanning release notes for keywords
3. **Creates issues** in relevant SDK repositories to notify maintainers

## How it works

### 1. API Change Detection

The workflow analyzes release notes for these keywords (case-insensitive):
- `api`
- `endpoint` 
- `route`
- `path`
- `openapi`
- `swagger`
- `breaking change`
- `public api`
- `api request`

### 2. Target SDK Repositories

When API changes are detected, issues are created in these repositories:
- `openfoodfacts/openfoodfacts-php`
- `openfoodfacts/openfoodfacts-js`
- `openfoodfacts/openfoodfacts-laravel`
- `openfoodfacts/openfoodfacts-python`
- `openfoodfacts/openfoodfacts-ruby`
- `openfoodfacts/openfoodfacts-java`
- `openfoodfacts/openfoodfacts-elixir`
- `openfoodfacts/openfoodfacts-dart`
- `openfoodfacts/openfoodfacts-go`

### 3. Issue Content

Each created issue includes:
- Release version and link
- Full release notes
- Checklist of actions for SDK maintainers
- Links to relevant documentation

## Configuration

### Required Secret

The workflow requires a `SDK_NOTIFY_TOKEN` secret to create issues in external repositories:

1. Create a Personal Access Token (PAT) with `public_repo` scope
2. Add it as a repository secret named `SDK_NOTIFY_TOKEN`

The token needs these permissions:
- `issues:write` for creating issues in public repositories

### Testing the Detection Logic

You can test the API change detection using the test script:

```bash
/tmp/test_api_detection.sh
```

## Examples

### Release with API changes (triggers notifications)
```
## Features
* integrate nutriSight to public API
* improve /image_predictions route
```

### Release without API changes (no notifications)
```
## Bug Fixes
* fix issue in _is_equal_nutrient_value
* handle missing ingredient fields
```

## Troubleshooting

### No issues created despite API changes
- Check that `SDK_NOTIFY_TOKEN` secret is configured
- Verify the token has sufficient permissions
- Check workflow logs for specific error messages

### Issues created for non-API changes
- Review the keyword detection logic in the workflow
- Consider refining the regular expression pattern

### Repository access errors
- Ensure the PAT has access to the target repositories
- Verify repository names are correct and repositories exist

## Manual Testing

To test the workflow manually:

1. Create a test release with API-related content in the description
2. Check the Actions tab for workflow execution
3. Verify issues are created in target repositories (if you have the proper token configured)

## Maintenance

The workflow should be updated when:
- New SDK repositories are added to the OpenFoodFacts ecosystem
- The API change detection criteria need refinement
- The issue template needs modifications