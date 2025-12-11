#!/usr/bin/env python3
"""
AnkiConnect sync script for Japanese verb pairs.
Syncs scraped verb pair data to Anki via AnkiConnect API.
"""

import base64
import json
import urllib.request
from pathlib import Path

# Configuration
ANKI_CONNECT_URL = "http://localhost:8765"
DECK_NAME = "Japanese::Verb Pairs"
MODEL_NAME = "Japanese Verb Pair"

DATA_DIR = Path(__file__).parent / "data"
IMAGES_DIR = Path(__file__).parent / "images"


def anki_request(action: str, **params) -> dict:
    """Send a request to AnkiConnect."""
    request_data = json.dumps({
        "action": action,
        "version": 6,
        "params": params
    }).encode("utf-8")

    try:
        response = urllib.request.urlopen(
            urllib.request.Request(ANKI_CONNECT_URL, request_data),
            timeout=10
        )
        result = json.loads(response.read().decode("utf-8"))

        if result.get("error"):
            raise Exception(f"AnkiConnect error: {result['error']}")

        return result.get("result")
    except urllib.error.URLError as e:
        raise Exception(f"Cannot connect to Anki. Is Anki running with AnkiConnect? ({e})")


def check_anki_connection():
    """Check if Anki is running and AnkiConnect is available."""
    try:
        version = anki_request("version")
        print(f"Connected to AnkiConnect version {version}")
        return True
    except Exception as e:
        print(f"Error: {e}")
        print("\nMake sure:")
        print("1. Anki is running")
        print("2. AnkiConnect add-on is installed (Code: 2055492159)")
        return False


def ensure_deck_exists():
    """Create the deck if it doesn't exist."""
    decks = anki_request("deckNames")
    if DECK_NAME not in decks:
        anki_request("createDeck", deck=DECK_NAME)
        print(f"Created deck: {DECK_NAME}")
    else:
        print(f"Deck exists: {DECK_NAME}")


def ensure_model_exists():
    """Create the note type (model) if it doesn't exist."""
    models = anki_request("modelNames")

    if MODEL_NAME not in models:
        # Create model with fields for verb pairs
        anki_request("createModel",
            modelName=MODEL_NAME,
            inOrderFields=[
                "VerbPairID",
                "IntransitiveKanji",
                "IntransitiveReading",
                "TransitiveKanji",
                "TransitiveReading",
                "Level",
                "Image",
                "PracticeQuestions",
                "Answers",
                "SourceURL",
                "Attribution"
            ],
            css="""
.card {
    font-family: "Hiragino Kaku Gothic Pro", "Yu Gothic", "Meiryo", sans-serif;
    font-size: 24px;
    text-align: center;
    color: #333;
    background-color: #fafafa;
    padding: 20px;
}

.verb-pair {
    font-size: 36px;
    font-weight: bold;
    margin: 20px 0;
}

.intransitive {
    color: #2196F3;
}

.transitive {
    color: #4CAF50;
}

.particle {
    font-size: 18px;
    color: #666;
    margin: 10px 0;
}

.image-container {
    margin: 20px 0;
}

.image-container img {
    max-width: 100%;
    max-height: 400px;
    border-radius: 8px;
    box-shadow: 0 2px 8px rgba(0,0,0,0.1);
}

.examples {
    text-align: left;
    font-size: 18px;
    line-height: 1.8;
    margin: 20px auto;
    max-width: 500px;
}

.practice {
    text-align: left;
    font-size: 16px;
    line-height: 2;
    margin: 20px auto;
    max-width: 500px;
    background: #f5f5f5;
    padding: 15px;
    border-radius: 8px;
}

.level-tag {
    display: inline-block;
    padding: 4px 12px;
    border-radius: 12px;
    font-size: 12px;
    margin-bottom: 10px;
}

.level-beginner { background: #E8F5E9; color: #2E7D32; }
.level-intermediate { background: #FFF3E0; color: #E65100; }
.level-advanced { background: #FCE4EC; color: #C2185B; }

.attribution {
    font-size: 10px;
    color: #999;
    margin-top: 20px;
}
            """,
            cardTemplates=[
                {
                    "Name": "Verb Pair Recognition",
                    "Front": """
<div class="level-tag level-{{Level}}">{{Level}}</div>

<div class="image-container">
{{Image}}
</div>

<div class="verb-pair">
    <span class="intransitive">{{IntransitiveKanji}}</span>
    ・
    <span class="transitive">{{TransitiveKanji}}</span>
</div>

<div class="particle">
    が (intransitive) vs を (transitive)
</div>
                    """,
                    "Back": """
{{FrontSide}}

<hr>

<div class="verb-pair">
    <span class="intransitive">{{IntransitiveKanji}}{{#IntransitiveReading}}（{{IntransitiveReading}}）{{/IntransitiveReading}}</span>
    ・
    <span class="transitive">{{TransitiveKanji}}{{#TransitiveReading}}（{{TransitiveReading}}）{{/TransitiveReading}}</span>
</div>

<div class="particle">
    <strong>自動詞</strong>: 〜が {{IntransitiveKanji}}<br>
    <strong>他動詞</strong>: 〜を {{TransitiveKanji}}
</div>

<div class="practice">
<strong>Practice:</strong><br>
{{PracticeQuestions}}
</div>

<div class="examples">
<strong>Answers:</strong><br>
{{Answers}}
</div>

<div class="attribution">
{{Attribution}} | <a href="{{SourceURL}}">Source</a>
</div>
                    """
                },
                {
                    "Name": "Intransitive → Transitive",
                    "Front": """
<div class="level-tag level-{{Level}}">{{Level}}</div>

<p>What is the <strong>transitive</strong> (他動詞) pair of:</p>

<div class="verb-pair">
    <span class="intransitive">{{IntransitiveKanji}}</span>
</div>

<div class="particle">
    (〜が {{IntransitiveKanji}})
</div>
                    """,
                    "Back": """
{{FrontSide}}

<hr>

<div class="verb-pair">
    <span class="transitive">{{TransitiveKanji}}{{#TransitiveReading}}（{{TransitiveReading}}）{{/TransitiveReading}}</span>
</div>

<div class="particle">
    〜を {{TransitiveKanji}}
</div>

<div class="image-container">
{{Image}}
</div>
                    """
                },
                {
                    "Name": "Transitive → Intransitive",
                    "Front": """
<div class="level-tag level-{{Level}}">{{Level}}</div>

<p>What is the <strong>intransitive</strong> (自動詞) pair of:</p>

<div class="verb-pair">
    <span class="transitive">{{TransitiveKanji}}</span>
</div>

<div class="particle">
    (〜を {{TransitiveKanji}})
</div>
                    """,
                    "Back": """
{{FrontSide}}

<hr>

<div class="verb-pair">
    <span class="intransitive">{{IntransitiveKanji}}{{#IntransitiveReading}}（{{IntransitiveReading}}）{{/IntransitiveReading}}</span>
</div>

<div class="particle">
    〜が {{IntransitiveKanji}}
</div>

<div class="image-container">
{{Image}}
</div>
                    """
                }
            ]
        )
        print(f"Created model: {MODEL_NAME}")
    else:
        print(f"Model exists: {MODEL_NAME}")


def store_image(filename: str) -> str | None:
    """Store an image in Anki's media folder and return the filename."""
    filepath = IMAGES_DIR / filename
    if not filepath.exists():
        return None

    # Read and base64 encode the image
    with open(filepath, "rb") as f:
        data = base64.b64encode(f.read()).decode("utf-8")

    # Store in Anki
    stored_name = anki_request("storeMediaFile",
        filename=filename,
        data=data
    )

    return stored_name or filename


def format_practice_questions(questions: list[str]) -> str:
    """Format practice questions for display."""
    # Filter to just the questions with choices, not answers
    filtered = [q for q in questions if "［" in q or "【" in q]
    if not filtered:
        filtered = questions[:5]  # Fallback to first 5

    return "<br>".join(filtered[:5])


def format_answers(answers: list[str]) -> str:
    """Format answers for display."""
    return "<br>".join(answers[:5])


def add_or_update_note(verb_data: dict) -> bool:
    """Add a new note or update existing one."""
    verb_id = verb_data["id"]

    # Check if note already exists
    existing = anki_request("findNotes",
        query=f'"deck:{DECK_NAME}" "VerbPairID:{verb_id}"'
    )

    # Store image if available
    image_field = ""
    if verb_data.get("images"):
        first_image = verb_data["images"][0]
        stored_name = store_image(first_image["filename"])
        if stored_name:
            image_field = f'<img src="{stored_name}">'

    # Prepare fields
    fields = {
        "VerbPairID": verb_id,
        "IntransitiveKanji": verb_data["intransitive"]["kanji"],
        "IntransitiveReading": verb_data["intransitive"]["reading"] or "",
        "TransitiveKanji": verb_data["transitive"]["kanji"],
        "TransitiveReading": verb_data["transitive"]["reading"] or "",
        "Level": verb_data["level"],
        "Image": image_field,
        "PracticeQuestions": format_practice_questions(verb_data.get("practice_questions", [])),
        "Answers": format_answers(verb_data.get("answers", [])),
        "SourceURL": verb_data["source_url"],
        "Attribution": verb_data["attribution"]
    }

    if existing:
        # Update existing note
        note_id = existing[0]
        anki_request("updateNoteFields",
            note={
                "id": note_id,
                "fields": fields
            }
        )
        print(f"  Updated: {verb_id}")
        return False  # Not new
    else:
        # Add new note
        anki_request("addNote",
            note={
                "deckName": DECK_NAME,
                "modelName": MODEL_NAME,
                "fields": fields,
                "options": {
                    "allowDuplicate": False
                },
                "tags": [f"level:{verb_data['level']}", "verb-pair", "edewakaru"]
            }
        )
        print(f"  Added: {verb_id}")
        return True  # New


def sync_all_verb_pairs():
    """Sync all verb pairs from JSON files to Anki."""
    if not check_anki_connection():
        return

    ensure_deck_exists()
    ensure_model_exists()

    # Find all JSON files (excluding combined files)
    json_files = [f for f in DATA_DIR.glob("*.json")
                  if not f.name.endswith("_verb_pairs.json")]

    print(f"\nSyncing {len(json_files)} verb pairs to Anki...")

    added = 0
    updated = 0

    for json_file in sorted(json_files):
        with open(json_file, encoding="utf-8") as f:
            data = json.load(f)

        is_new = add_or_update_note(data)
        if is_new:
            added += 1
        else:
            updated += 1

    print(f"\nSync complete!")
    print(f"  Added: {added}")
    print(f"  Updated: {updated}")
    print(f"  Total: {added + updated}")


def sync_level(level: str):
    """Sync verb pairs from a specific level."""
    if not check_anki_connection():
        return

    ensure_deck_exists()
    ensure_model_exists()

    level_file = DATA_DIR / f"{level}_verb_pairs.json"
    if not level_file.exists():
        print(f"Level file not found: {level_file}")
        return

    with open(level_file, encoding="utf-8") as f:
        data = json.load(f)

    print(f"\nSyncing {len(data)} {level} verb pairs to Anki...")

    added = 0
    updated = 0

    for verb_data in data:
        is_new = add_or_update_note(verb_data)
        if is_new:
            added += 1
        else:
            updated += 1

    print(f"\nSync complete!")
    print(f"  Added: {added}")
    print(f"  Updated: {updated}")


if __name__ == "__main__":
    import sys

    if len(sys.argv) > 1:
        level = sys.argv[1]
        if level in ["beginner", "intermediate", "advanced"]:
            sync_level(level)
        else:
            print(f"Unknown level: {level}")
            print("Usage: python anki_sync.py [beginner|intermediate|advanced]")
    else:
        sync_all_verb_pairs()
