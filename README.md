# Uber Eats Deal Finder Web App

A web application that helps you find the best deals on Uber Eats. It scans restaurant pages for promotions and special offers, then presents them in a searchable, sortable table.

## Features

- Input any Uber Eats URL to scan for deals
- Real-time progress tracking during scanning
- Sortable and searchable table of found deals
- Dark mode UI
- Responsive design

## Prerequisites

- Python 3.8+
- Node.js 14+
- Google Chrome (for web scraping)
- OpenAI API key (for deal extraction)

## Installation

1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd uber-cheats
   ```

2. Set up the backend:
   ```bash
   cd backend
   pip install -r requirements.txt
   ```

3. Set up the frontend:
   ```bash
   cd ../frontend
   npm install
   ```

4. Create a `.env` file in the root directory with your OpenAI API key:
   ```
   OPENAI_API_KEY=your_api_key_here
   ```

## Running the Application

You can start both the backend and frontend servers using the provided script:

```bash
./start.sh
```

Or start them separately:

1. Start the backend server:
   ```bash
   cd backend
   python main.py
   ```

2. Start the frontend server (in a new terminal):
   ```bash
   cd frontend
   npm start
   ```

The web app will be available at http://localhost:3000

## Usage

1. Open http://localhost:3000 in your browser
2. Paste an Uber Eats URL into the input field
3. Click "Find Deals" to start scanning
4. Watch the progress bar as deals are found
5. Once complete, you'll be taken to a table showing all found deals
6. Use the search bar to filter deals
7. Click column headers to sort the table

## Notes

- The application uses Chrome in headless mode for web scraping
- Deals are stored in a SQLite database for persistence
- The backend uses FastAPI and WebSocket for real-time progress updates
- The frontend is built with React and Material-UI

## Troubleshooting

If you encounter any issues:

1. Make sure Chrome is installed and up to date
2. Check that all required Python packages are installed
3. Verify your OpenAI API key is valid and properly set in .env
4. Check the console for any error messages
5. Make sure ports 3000 and 8000 are available 