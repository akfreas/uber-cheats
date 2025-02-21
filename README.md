# Uber Eats Deal Finder

A Python application that helps you find and track the best deals on Uber Eats. The application scrapes Uber Eats pages for promotions, stores them in a local database, and provides an interactive chat interface to query deals.

## Features

- Scrapes Uber Eats pages for restaurant deals and promotions
- Stores deal information in a SQLite database
- Interactive chat interface powered by GPT-4 to query deals
- Deal analysis tools to view statistics and trends
- Support for various promotion types (Buy 1 Get 1, Top Offers, etc.)

## Requirements

- Python 3.8+
- Google Chrome browser
- Operating System: macOS (currently optimized for macOS)

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/uber-cheats.git
cd uber-cheats
```

2. Install required packages:
```bash
pip install -r requirements.txt
```

3. Set up environment variables:
Create a `.env` file in the project root and add your OpenAI API key:
```
OPENAI_API_KEY=your_api_key_here
```

## Usage

### Scraping Deals

To scrape deals from an Uber Eats offer page:
```bash
python uber_deals.py --offer_url "https://www.ubereats.com/de/category/berlin-be/deal"
```

### Viewing Stored Deals

To view all stored deals in the database:
```bash
python uber_deals.py --view
```

### Analyzing Deals

To see statistics and analysis of stored deals:
```bash
python uber_deals.py --analyze
```

### Chat Interface

To interact with the deals database using natural language:
```bash
python chat_deals.py
```

Example questions you can ask:
- What are the best pizza deals?
- Show me deals with free delivery
- What are the buy one get one free offers?
- Which restaurants have the most deals?

## Data Storage

The application uses SQLite to store deal information in `uber_deals.db`. The database includes:
- Restaurant details
- Item names and prices
- Promotion types
- Delivery fees
- Ratings and reviews
- URLs for direct access
- Timestamps for deal tracking

## Debug Information

Debug information is stored in the `debug_output` directory, including:
- HTML content of scraped pages
- Extracted menu items
- LLM processing results
- Deal extraction logs

## Security Notes

- API keys are stored in environment variables
- The `.env` file should never be committed to version control
- Debug output is cleared before each new scraping session

## Troubleshooting

If you encounter issues with Chrome/ChromeDriver:
1. Make sure Google Chrome is installed and up to date
2. Try upgrading the webdriver-manager: `pip install --upgrade webdriver-manager selenium`
3. Clear the webdriver cache by removing the `~/.wdm/` directory

## Limitations

- Currently optimized for macOS
- Requires a valid OpenAI API key
- Some deals may require manual verification
- Scraping speed is intentionally throttled to respect website limits

## Contributing

Feel free to submit issues, fork the repository, and create pull requests for any improvements.

## License

[Your chosen license here] 