# Paperstack

```
╔══════════════════════════════════════════════════════════════════╗
║                                                                  ║
║             ██████╗  █████╗ ██████╗ ███████╗██████╗              ║
║             ██╔══██╗██╔══██╗██╔══██╗██╔════╝██╔══██╗             ║
║             ██████╔╝███████║██████╔╝█████╗  ██████╔╝             ║
║             ██╔═══╝ ██╔══██║██╔═══╝ ██╔══╝  ██╔══██╗             ║
║             ██║     ██║  ██║██║     ███████╗██║  ██║             ║
║             ╚═╝     ╚═╝  ╚═╝╚═╝     ╚══════╝╚═╝  ╚═╝             ║
║                                                                  ║
║            ███████╗████████╗ █████╗  ██████╗██╗  ██╗             ║
║            ██╔════╝╚══██╔══╝██╔══██╗██╔════╝██║ ██╔╝             ║
║            ███████╗   ██║   ███████║██║     █████╔╝              ║
║            ╚════██║   ██║   ██╔══██║██║     ██╔═██╗              ║
║            ███████║   ██║   ██║  ██║╚██████╗██║  ██╗             ║
║            ╚══════╝   ╚═╝   ╚═╝  ╚═╝ ╚═════╝╚═╝  ╚═╝             ║
║                                                                  ║
║             ┌─────────────────────┐                              ║
║             │ ▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓▓ │  ◄── Your Papers             ║
║             ├─────────────────────┤                              ║
║             │ ░░░░░░░░░░░░░░░░░░░ │  ◄── Smart Tags              ║
║             ├─────────────────────┤                              ║
║             │ ▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒▒ │  ◄── AI Summaries            ║
║             └─────────────────────┘                              ║
║                                                                  ║
║               [ INSERT COIN TO CONTINUE READING ]                ║
║                                                                  ║
╚══════════════════════════════════════════════════════════════════╝
```

> **Academic paper management CLI** with web-based PDF viewer, semantic search, and AI-powered organization.

> **Disclaimer:** 100% vibe-coded with claude-code.

> **Your Feedback Is Welcomed!** Please leave an issue with your feedback :)

[![Python 3.9+](https://img.shields.io/badge/python-3.9+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

---

## Features

```
┌──────────────────────────────────────────────────────────────────┐
│  FEATURE SELECT                                    [PRESS START] │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  > PDF VIEWER        Web-based reader with annotations           │
│    READING LIST      Track papers you're studying                │
│    DONE LIST         Record what you learned                     │
│    SEMANTIC SEARCH   Find papers using AI embeddings             │
│    AUTO-TAGGING      Claude generates tags & descriptions        │
│    INTERACTIVE UI    Arrow-key navigation in terminal            │
│    MULTI-SELECT      Batch operations on multiple papers         │
│    BIBTEX EXPORT     One-click citations for LaTeX               │
│                                                                  │
│  ┌────────────────────────────────────────────────────────────┐  │
│  │ BONUS FEATURES:  Google Drive sync - Scholar PDF Reader    │  │
│  │                  arXiv/DOI metadata - Annotation search    │  │
│  └────────────────────────────────────────────────────────────┘  │
└──────────────────────────────────────────────────────────────────┘
```

---

## Screenshots

### Main Menu

```
        ╔═══════════════════════════════════════════════════════════╗
        ║   ██████╗  █████╗ ██████╗ ███████╗██████╗                 ║
        ║   ██╔══██╗██╔══██╗██╔══██╗██╔════╝██╔══██╗                ║
        ║   ██████╔╝███████║██████╔╝█████╗  ██████╔╝                ║
        ║   ██╔═══╝ ██╔══██║██╔═══╝ ██╔══╝  ██╔══██╗                ║
        ║   ██║     ██║  ██║██║     ███████╗██║  ██║                ║
        ║   ╚═╝     ╚═╝  ╚═╝╚═╝     ╚══════╝╚═╝  ╚═╝                ║
        ║   ███████╗████████╗ █████╗  ██████╗██╗  ██╗               ║
        ║   ██╔════╝╚══██╔══╝██╔══██╗██╔════╝██║ ██╔╝               ║
        ║   ███████╗   ██║   ███████║██║     █████╔╝                ║
        ║   ╚════██║   ██║   ██╔══██║██║     ██╔═██╗                ║
        ║   ███████║   ██║   ██║  ██║╚██████╗██║  ██╗               ║
        ║   ╚══════╝   ╚═╝   ╚═╝  ╚═╝ ╚═════╝╚═╝  ╚═╝               ║
        ╚═══════════════════════════════════════════════════════════╝

        ▸ Browse Reading List             ·····  3 papers
          Browse Completed Papers         ·····  5 papers
          Add New Paper                   ·····  from URL or search
          Search Papers                   ·····  local or external
          Show Statistics                 ·····  library overview
          Preferences                     ·····  configure settings
          Interactive Shell               ·····  REPL mode
          Quit                            ·····  exit paperstack

                    ↑/↓: Navigate   Enter: Select   q: Quit
```

### Paper Browser (with Multi-Select)

```
  Reading List (2 marked)

   ●   1. Attention Is All You Need [transformers, NLP]
►●   2. BERT: Pre-training of Deep Bidirectional... [NLP, embeddings]
     3. GPT-4 Technical Report [language models]
     4. Constitutional AI: Harmlessness from AI... [alignment, safety]
►    5. Retrieval-Augmented Generation for Know... [RAG, retrieval]

  ↑/↓: Navigate  Space: Mark  Enter: Details  v: View  b: BibTeX  d: Done  x: Delete  q: Quit
```

### BibTeX Export

```
  BibTeX Export (3 papers)
    ✓ Attention Is All You Need... (cached)
    ✓ BERT: Pre-training of Deep Bidirectional... (cached)
    Fetching: GPT-4 Technical Report...
    ✓ GPT-4 Technical Report...

  Found 3 BibTeX entries.
  Save to file (default: citations.bib): ~/thesis/references.bib
  Saved 3 entries to /Users/you/thesis/references.bib

  Press Enter to continue...
```

### Paper Details

```
  #1 Attention Is All You Need

  Authors: Ashish Vaswani, Noam Shazeer, Niki Parmar, Jakob Uszkoreit...
  arXiv: 1706.03762
  Tags: transformers, NLP, attention
  Status: done
  URL: https://arxiv.org/abs/1706.03762
  PDF: ~/.paperstack/papers/1706.03762.pdf

  BibTeX:
  @article{vaswani2017attention,
    title={Attention is all you need},
    author={Vaswani, Ashish and Shazeer, Noam...},
    ...
  }

  Description: Introduces the Transformer architecture using self-attention...

  Abstract:
    The dominant sequence transduction models are based on complex recurrent
    or convolutional neural networks...

  Press Enter to continue...
```

---

## Installation

```bash
# Clone the repository
git clone https://github.com/Or-Tal/Paperstack.git
cd Paperstack

# Install with pip
pip install -e .

# Initialize the database
paperstack init
```

### Optional: Enable AI Features

```bash
# Option 1: Set your Anthropic API key
export ANTHROPIC_API_KEY="your-key-here"

# Option 2: Run from within Claude Code (automatic!)
# Paperstack auto-detects Claude Code and uses its proxy - no API key needed
```

**Claude Code Integration**: When running paperstack from a Claude Code session, AI features work automatically without any API key. Paperstack detects the Claude Code environment and uses its built-in proxy.

---

## Quick Start

```
┌──────────────────────────────────────────────────────────────────┐
│  GAME START                                                      │
└──────────────────────────────────────────────────────────────────┘
```

### 1. Launch Paperstack

```bash
# Interactive main menu
paperstack

# Or jump directly to reading list
paperstack reading
```

### 2. Add a Paper

```bash
# Add from arXiv
paperstack add url "https://arxiv.org/abs/2301.07041"

# Add from DOI
paperstack add url "https://doi.org/10.1234/example"

# Attach a local PDF
paperstack add pdf <paper-id> ~/Downloads/paper.pdf
```

### 3. Browse Your Library

```bash
# Interactive browser (arrow keys to navigate)
paperstack reading

# Non-interactive list
paperstack reading list
```

**Interactive Browser Controls:**
```
┌─────────────────────────────────────────────────────────┐
│  NAVIGATION                                              │
│  ↑/↓ or j/k    Navigate papers                          │
│  PgUp/PgDn     Jump 10 papers                           │
│  Home/End      Jump to start/end                        │
│                                                          │
│  SELECTION                                               │
│  Space or m    Mark/unmark paper for batch operations   │
│  a             Select/deselect all papers               │
│                                                          │
│  ACTIONS (applies to marked papers or current paper)    │
│  Enter         Show paper details                        │
│  v             View PDF in browser                       │
│  b             Get BibTeX citation                       │
│  d             Mark as done                              │
│  r             Move to reading list                      │
│  x             Delete paper(s)                           │
│  q             Quit                                      │
└─────────────────────────────────────────────────────────┘
```

### 4. Export BibTeX

```bash
# From the browser, press 'b' on a paper or select multiple with Space
# For single paper: copies to clipboard
# For multiple papers: saves to citations.bib
```

### 5. Mark Papers as Done

```bash
# Interactive mode - select with arrow keys
paperstack done mark

# Direct mode with concepts
paperstack done mark 1 --concepts "attention mechanisms" --concepts "transformers"

# Browse completed papers
paperstack done
```

### 6. Search Your Knowledge

```bash
# Semantic search over your completed papers
paperstack search local "transformer efficiency"

# External search (Semantic Scholar, arXiv, CrossRef)
paperstack search deep "multimodal learning"
```

### 7. View Papers

```bash
# Open PDF viewer in browser
paperstack view

# Or specify paper directly
paperstack view 1
```

---

## Commands Reference

```
┌──────────────────────────────────────────────────────────────────┐
│  COMMAND LIST                                      [HELP SCREEN] │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│  MAIN COMMANDS                                                   │
│  -------------                                                   │
│  paperstack             Interactive main menu                    │
│  paperstack reading     Browse reading list (interactive)        │
│  paperstack done        Browse completed papers (interactive)    │
│  paperstack view        Open paper in PDF viewer                 │
│  paperstack shell       Start interactive REPL                   │
│  paperstack stats       Show library statistics                  │
│  paperstack init        Initialize database                      │
│                                                                  │
│  ADD PAPERS                                                      │
│  ----------                                                      │
│  paperstack add url <URL>           Add from URL                 │
│  paperstack add pdf <ID> <PATH>     Attach PDF to paper          │
│                                                                  │
│  READING LIST                                                    │
│  ------------                                                    │
│  paperstack reading                 Interactive browser          │
│  paperstack reading list            Show all papers              │
│  paperstack reading show [ID]       Show paper details           │
│  paperstack reading remove [ID]     Remove paper                 │
│  paperstack reading update <ID>     Update metadata              │
│                                                                  │
│  DONE LIST                                                       │
│  ---------                                                       │
│  paperstack done                    Interactive browser          │
│  paperstack done mark [ID]          Mark paper as done           │
│  paperstack done list               List completed papers        │
│  paperstack done show [ID]          Show done entry              │
│  paperstack done unmark [ID]        Move back to reading         │
│                                                                  │
│  SEARCH                                                          │
│  ------                                                          │
│  paperstack search local <QUERY>    Search your papers           │
│  paperstack search deep <QUERY>     Search external sources      │
│                                                                  │
│  PREFERENCES                                                     │
│  -----------                                                     │
│  paperstack prefs show              Show all preferences         │
│  paperstack prefs set <KEY> <VAL>   Set a preference             │
│  paperstack prefs get <KEY>         Get a preference             │
│                                                                  │
│  [ID] = optional, uses interactive browser if omitted            │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

---

## Configuration

Paperstack stores data in `~/.paperstack/`:

```
~/.paperstack/
├── paperstack.db      # SQLite database
├── papers/            # PDF storage
├── annotations/       # JSON annotation files
└── config.json        # User preferences
```

### Environment Variables

| Variable | Description |
|----------|-------------|
| `ANTHROPIC_API_KEY` | Enable AI auto-tagging and summaries |
| `PAPERSTACK_HOME_DIR` | Override default data directory |

### Preferences

```bash
# View all settings
paperstack prefs show

# Change PDF viewer port
paperstack prefs set viewer_port 8080

# Set storage backend (local or gdrive)
paperstack prefs set storage_backend local

# Set viewer mode (builtin or scholar)
paperstack prefs set viewer_mode scholar
```

---

## Workflow Example

```
┌──────────────────────────────────────────────────────────────────┐
│  PLAYER 1 WORKFLOW                                               │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│    [FIND]  -->  [READ]  -->  [ANNOTATE]  -->  [DONE]             │
│     PAPER        PAPER        & NOTE          LIST               │
│                                                                  │
│      |            |             |              |                 │
│      v            v             v              v                 │
│                                                                  │
│   add url     view <id>     PDF viewer     done mark             │
│               reading       annotations    --concepts            │
│                                                                  │
│   ┌────────────────────────────────────────────────────────┐     │
│   │              EXPORT FOR PAPER                          │     │
│   │      Select papers → Press 'b' → citations.bib         │     │
│   └────────────────────────────────────────────────────────┘     │
│                                                                  │
│   ┌────────────────────────────────────────────────────────┐     │
│   │              SEARCH LATER                              │     │
│   │      paperstack search local "your query"              │     │
│   └────────────────────────────────────────────────────────┘     │
│                                                                  │
│                  HIGH SCORE: inf papers read                     │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
```

---

## PDF Viewer

Paperstack supports two PDF viewing modes:

### Option 1: Built-in Viewer (Default)

The web-based PDF viewer runs at `http://localhost:5000` and supports:

- **Highlights** - Select text to highlight
- **Comments** - Add notes to highlights
- **Page Notes** - Add notes to any page
- **Keyboard shortcuts** - Navigate with arrow keys
- **Search annotations** - All annotations are searchable

### Option 2: Google Scholar PDF Reader

Use the Google Scholar PDF Reader Chrome extension for enhanced academic reading:

- **Citation hover** - Click in-text citations to see summaries and find PDFs
- **AI-powered outline** - Quick summaries with section jumping
- **Figure navigation** - Click figure references to see images inline
- **Native annotations** - Highlight, draw, and add text notes

Install from: https://chromewebstore.google.com/detail/dahenjhkoodjbpjheillcadbppiidmhp

```bash
# Set during init
paperstack init

# Or change later
paperstack prefs set viewer_mode scholar

# Override per-view
paperstack view 1 --scholar    # Use Scholar extension
paperstack view 1 --builtin    # Use built-in viewer
```

---

## Development

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest tests/ -v

# Type checking
mypy src/paperstack
```

---

## License

```
╔════════════════════════════════════════════╗
║  MIT License                               ║
║  Copyright (c) 2024                        ║
║  See LICENSE file for details              ║
╚════════════════════════════════════════════╝
```

---

<p align="center">
  <code>GAME OVER - INSERT PAPER TO CONTINUE</code>
</p>
