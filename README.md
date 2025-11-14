# 🔍 CodeBox - Code Indexer & Search Tool

![Python Version](https://img.shields.io/badge/python-3.10+-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)
![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20Linux%20%7C%20Mac-lightgrey.svg)
![PyQt6](https://img.shields.io/badge/GUI-PyQt6-41cd52.svg)
![LanceDB](https://img.shields.io/badge/Vector_DB-LanceDB-orange.svg)
![Tree-sitter](https://img.shields.io/badge/Parser-Tree--sitter-yellowgreen.svg)

Powerful code indexing and search tool developed with **Python PyQt6**.

**Hybrid Mode:** Both visual interface and terminal usage with GUI + CLI support.

## 🚀 Quick Start

### Installation

```bash
# Install dependencies
pip install -r requirements.txt
```

### GUI Mode (Default)

```bash
# Open GUI application
python codebox.py
```

1. Go to the **Indexer** tab
2. **Browse** to select your code project
3. Select the languages you want to index (checkboxes)
4. Click the **Start Indexing** button
5. Switch to the **Search** tab and perform searches

### CLI Mode (For Claude Code)

**Basic Commands:**
```bash
# Help
python codebox.py --help

# Index project
python codebox.py index /path/to/project
python codebox.py index ./my-code --languages python,javascript

# Search code (JSON output)
python codebox.py search "user authentication"
python codebox.py search "login function" --mode hybrid --limit 10

# Database stats
python codebox.py stats
```

**Optimized Usage for Claude Code:**
```bash
# For detailed code analysis (recommended)
python codebox.py search "authentication" --full-content --context 5 --limit 10

# For refactoring analysis
python codebox.py search "database connection" --full-content --context 10 --mode hybrid

# For quick scanning
python codebox.py search "API endpoints" --mode vector --preview-length 150 --limit 20

# Error handling analysis with full code content
python codebox.py search "error handling" --full-content --context 5

# Search with custom preview length
python codebox.py search "database" --preview-length 300
```

## ✨ Features

- 🔍 **Hybrid Search**: Vector + Keyword search (RRF fusion)
- 🌳 **AST-based Parsing**: Semantic code analysis with Tree-sitter
- 🎨 **Syntax Highlighting**: Professional code viewing with QScintilla
- 🗂️ **Multi-language**: Python, JS, TS, Java, C++, C#, Go, Rust, HTML, CSS, JSON, YAML
- ⚡ **Fast**: Optimized vector search with LanceDB
- 🖥️ **Dual Mode**: GUI + CLI (Hybrid Mode)
- 🤖 **Claude Code Ready**: LLM integration with JSON output
- 📄 **Full Content Support**: Truncation control and full code viewing
- 🔗 **Context Lines**: Display lines before/after code chunks
- ⚙️ **Flexible Output**: Configurable preview length and content limits

## 📋 CLI Commands

### Search
```bash
python codebox.py search <query> [options]

Options:
  --mode {vector,keyword,hybrid}  Search mode (default: hybrid)
  --limit N                       Max results (default: 10)
  --language LANG                 Filter by language
  --format {json,text}            Output format (default: json)

  # LLM Enhancement Options (Phase 1 & 2)
  --full-content                  Return full code content, not truncated (max 5000 chars)
  --preview-length N              Preview length in characters (default: 200)
  --context N                     Number of context lines before/after chunk (default: 0)

Examples:
  # Basic search
  python codebox.py search "authentication"

  # Full content + context
  python codebox.py search "error handling" --full-content --context 5

  # Custom preview length
  python codebox.py search "database" --preview-length 300 --limit 15
```

### Index
```bash
python codebox.py index <path> [options]

Options:
  --languages LANGS    Comma-separated languages (e.g., python,javascript)

Note: Each indexing automatically clears and recreates the project directory for a clean start.
```

### Stats
```bash
python codebox.py stats
```

## 📁 Project Structure

```
CodeBox/
├── app/
│   ├── gui/              # PyQt6 widgets
│   ├── indexer/          # Parser, embeddings, chunker
│   ├── search/           # Vector DB, hybrid search
│   └── utils/            # Config, logger
├── codebox.py            # Entry point
├── requirements.txt
└── .lancedb/             # Database (auto-created)
```

## 🛠️ Technology Stack

- **GUI**: PyQt6 + QScintilla
- **CLI**: argparse + JSON output
- **Vector DB**: LanceDB
- **Parser**: tree-sitter (multi-language)
- **Embeddings**: sentence-transformers (model TBD)
- **Search**: Hybrid (Vector + Keyword + RRF)

## 📝 Requirements

- Python 3.10+
- Windows 10/11 (Linux/Mac supported)

---

## 🚧 Roadmap / TODO

### Phase 3.1: Basic Metadata ✅ (v2.0 - Completed)

**Breaking Change:** All projects need to be reindexed.

#### Completed Features:

1. **node_name Field** ✅
   - Added `node_name` field to database schema
   - Function/class names stored as metadata
   - Provides filtering and query convenience

2. **File Metadata** ✅
   - Added file size (size_bytes)
   - Added last modified date (modified_at)
   - Relative path information available

3. **Schema Version Control** ✅
   - Added schema versioning system
   - Version information stored in metadata
   - Version display available in stats command

#### Note:
Due to schema changes, all projects need to be reindexed:
```bash
# Reindex your project
python codebox.py index /path/to/project
```

---

### Phase 3.2: Semantic Enrichment (Planned - v2.1)

**Supported Languages:** Python, JavaScript, TypeScript

#### Planned Features:

1. **Function Signatures**
   - Parameters and return type information
   - Native type hint support for each language
   - Overload detection

2. **Docstrings**
   - Python: Triple-quote docstrings
   - JavaScript/TypeScript: JSDoc comments
   - Markdown formatting preservation

3. **Decorator & Imports**
   - Decorator information (@decorator)
   - Import dependencies tracking
   - Module relationship mapping

**Estimated Time:** 2-3 weeks

---

### Phase 3.3: Relationship Tracking (Planned - v2.2)

**Note:** Requires complex static analysis, will be evaluated based on needs.

#### Planned Features:

1. **Call Graph**
   - Function call relationships
   - Caller-callee mapping
   - Same-file call tracking (priority)

2. **Parent/Module Info**
   - Class inheritance hierarchy
   - Nested scope information
   - Module parent tracking

3. **Cross-Reference**
   - Symbol usage tracking
   - Definition-reference links
   - Multi-file symbol resolution (optional)

**Estimated Time:** 1-2 months

#### Decision Criteria:
- Gather feedback from Phase 3.1 and 3.2
- Identify real needs in LLM usage scenarios
- Evaluate symbol resolution complexity vs value

---

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
