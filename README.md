# Japanese Verb Pairs

Scraper and Anki sync tool for Japanese transitive/intransitive verb pairs (自動詞・他動詞) from [edewakaru.com](https://www.edewakaru.com).

## Overview

In Japanese, many verbs come in transitive (他動詞) and intransitive (自動詞) pairs:
- **自動詞** (intransitive): The subject changes state on its own (ドア**が**開く - the door opens)
- **他動詞** (transitive): Someone acts on an object (ドア**を**開ける - [I] open the door)

This tool scrapes 94 verb pairs from edewakaru.com and creates Anki flashcards with:
- Illustrations showing the distinction
- Practice questions with answers
- Three card types for comprehensive learning

## Setup

```bash
# Create virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

## Usage

### Scraping

```bash
# Scrape all levels (94 verb pairs)
python scraper.py

# Scrape only beginner level (15 pairs) for testing
python scraper.py --beginner
```

Data is saved to:
- `data/` - JSON files with verb pair information
- `images/` - Downloaded illustrations

### Syncing to Anki

Requires [AnkiConnect](https://ankiweb.net/shared/info/2055492159) add-on (Code: 2055492159).

```bash
# Make sure Anki is running with AnkiConnect

# Sync all scraped verb pairs
python anki_sync.py

# Sync only beginner level
python anki_sync.py beginner
```

Creates a deck called "Japanese::Verb Pairs" with three card types:
1. **Verb Pair Recognition** - Image + both verbs, practice on back
2. **Intransitive → Transitive** - Given 自動詞, recall 他動詞
3. **Transitive → Intransitive** - Given 他動詞, recall 自動詞

## Content Levels

| Level | Japanese | Count |
|-------|----------|-------|
| Beginner | 初級 | 15 |
| Intermediate | 中級 | 21 |
| Advanced | 上級 | 17 |
| Other categories | - | ~41 |

## Attribution

All content and illustrations are from [edewakaru.com](https://www.edewakaru.com) (絵でわかる日本語). This tool is for personal educational use.

## License

MIT
