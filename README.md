# Uber Eats Deal Finder

This utility helps you find the best deals available on Uber Eats by scraping offer pages and collecting information about current promotions.

## Requirements

- Python 3.8+
- Chrome browser installed

## Installation

1. Clone this repository
2. Install the required dependencies:
```bash
pip install -r requirements.txt
```

## Usage

Run the script with a URL from Uber Eats offers page:

```bash
python uber_deals.py --offer_url "YOUR_UBER_EATS_OFFER_URL"
```

The script will:
1. Open the provided Uber Eats offer page
2. Scan through all restaurants
3. Extract deal information
4. Display results in a table format

## Note

This tool is for educational purposes only. Please respect Uber Eats' terms of service and rate limiting when using this tool. 