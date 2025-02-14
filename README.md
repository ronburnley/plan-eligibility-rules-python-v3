# Plan Eligibility Rules Evaluator

This Python module evaluates health insurance plan eligibility rules by combining data from the CMS Marketplace API and a local business rules PUF (Public Use File) CSV.

## Features

- Retrieves plan details from CMS Marketplace API
- Evaluates eligibility rules from business rules PUF file
- Generates formatted bullet list of eligibility criteria
- Handles dependent relationships, age limits, and coverage types
- Includes error handling for API calls and data validation

## Requirements

- Python 3.8+
- Dependencies listed in requirements.txt

## Installation

1. Clone this repository
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

## Usage

```python
from plan_eligibility import evaluate_plan

# Initialize with your API key
api_key = "your_cms_api_key"
plan_id = "example_plan_id"
zip_code = "12345"
year = 2025
puf_file = "business-rules-puf 2.csv"

# Get eligibility criteria
criteria = evaluate_plan(api_key, plan_id, zip_code, year, puf_file)

# Print formatted bullet points
for bullet in criteria:
    print(bullet)
```

## Output Format

The evaluator returns a list of bullet points containing:
- Eligible dependents (relationships allowed)
- Maximum dependent age (with note if exceeds standard age 26)
- Plan type (child-only or adult/family)
- Service area
- Tobacco use rules
- Market coverage type
- Dental coverage status

## Error Handling

The module includes error handling for:
- API connection failures
- Missing or invalid plan IDs
- Missing business rules
- Data format issues

## API Key

To use this module, you need a CMS Marketplace API key. Request one at:
https://developer.cms.gov/marketplace-api/key-request.html 