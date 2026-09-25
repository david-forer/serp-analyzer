# SERP Analyzer

A Python tool for analyzing search engine results pages (SERP) using Google Custom Search API and OpenAI GPT for intent detection and result classification.

## Features

- **Google Custom Search Integration**: Fetch real search results using Google's Custom Search API
- **Intent Detection**: Automatically classify search queries into intent categories (Informational, Navigational, Transactional, Commercial Investigation)
- **Result Classification**: Classify each search result by type (informational, commercial, navigational, transactional, local, news)
- **Multiple Output Formats**: Export results as JSON, CSV, or formatted text summary
- **CLI Interface**: Easy-to-use command-line interface

## Prerequisites

- Python 3.8+
- Google Custom Search API Key
- Google Custom Search Engine ID
- OpenAI API Key

## Installation

1. Clone the repository:
```bash
git clone https://github.com/yourusername/serp-analyzer.git
cd serp-analyzer
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Set up environment variables:
```bash
cp .env.example .env
```

Edit `.env` and add your API keys:
```
GOOGLE_API_KEY=your_google_api_key_here
GOOGLE_CSE_ID=your_search_engine_id_here
OPENAI_API_KEY=sk-your_openai_key_here
```

## Usage

### Basic Usage

```bash
python -m src.cli "best smartphones 2024"
```

### Advanced Options

```bash
python -m src.cli "best smartphones 2024" \
  --num-results 20 \
  --output-dir ./my-results \
  --format json \
  --verbose
```

### Command-Line Options

- `query`: Search query to analyze (required)
- `-n, --num-results`: Number of results to fetch (default: 10)
- `-o, --output-dir`: Output directory for results (default: ./outputs)
- `-f, --format`: Output format: json, csv, summary, or all (default: all)
- `--no-intent`: Skip intent detection
- `--no-classify`: Skip result classification
- `-v, --verbose`: Enable verbose logging

## Output

The tool generates the following outputs:

### JSON Format
Complete analysis including intent, classifications, and all metadata.

### CSV Format
Tabular format with columns: position, title, url, snippet, intent_category, classification, etc.

### Summary Format
Human-readable text summary with key insights and top results.

## Project Structure

```
serp-analyzer/
├── src/
│   ├── __init__.py
│   ├── cli.py              # Command-line interface
│   ├── google_search.py    # Google Custom Search client
│   ├── intent_detector.py  # Search intent detection
│   ├── classifier.py       # Result classification
│   └── output_writer.py    # Output formatting and export
├── outputs/                # Generated analysis files
├── requirements.txt        # Python dependencies
├── .env.example           # Environment variables template
└── README.md

```

## API Setup

### Google Custom Search API

1. Go to [Google Cloud Console](https://console.cloud.google.com/)
2. Create a new project or select existing one
3. Enable "Custom Search API"
4. Create credentials (API Key)
5. Create a Custom Search Engine at [Programmable Search Engine](https://programmablesearchengine.google.com/)
6. Note your Search Engine ID

### OpenAI API

1. Sign up at [OpenAI](https://platform.openai.com/)
2. Generate an API key from the API keys section
3. Add billing information if needed

## Examples

### Analyze query with full features:
```bash
python -m src.cli "python tutorials" -n 15 -f all
```

### Quick CSV export only:
```bash
python -m src.cli "buy running shoes" -n 10 -f csv --no-intent
```

### Search without classification:
```bash
python -m src.cli "weather forecast" --no-classify
```

## License

MIT License

## Contributing

Contributions welcome! Please open an issue or submit a pull request.

## Contact

For questions or support, please open an issue on GitHub.