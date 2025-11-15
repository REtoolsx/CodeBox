# 🔍 CodeBox - Code Indexer & Search Tool

![Python Version](https://img.shields.io/badge/python-3.10+-blue.svg)
![License](https://img.shields.io/badge/license-MIT-green.svg)
![Platform](https://img.shields.io/badge/platform-Windows%20%7C%20Linux%20%7C%20Mac-lightgrey.svg)
![LanceDB](https://img.shields.io/badge/Vector_DB-LanceDB-orange.svg)
![Tree-sitter](https://img.shields.io/badge/Parser-Tree--sitter-yellowgreen.svg)
![Pygments](https://img.shields.io/badge/Language_Detection-Pygments-blue.svg)

Powerful code indexing and search tool with CLI interface and automatic language detection.

**CLI-Only Mode:** Terminal-based code indexing and search optimized for LLM integration.

## 🚀 Quick Start

### Installation

```bash
# Install dependencies
pip install -r requirements.txt
```

### CLI Commands

**Basic Usage:**
```bash
# Help
python codebox.py --help

# Index project (auto-detects all supported languages)
python codebox.py index /path/to/project
python codebox.py index ./my-code

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
- 🤖 **Auto Language Detection**: Powered by Pygments (supports 597+ languages, tree-sitter parsers for 12 core languages)
- 🗂️ **Core Languages**: Python, JS/JSX, TS/TSX, Java, C++, C#, Go, Rust, HTML, CSS, JSON, YAML
- ⚡ **Fast**: Optimized vector search with LanceDB
- 🤖 **LLM Ready**: JSON output optimized for Claude Code and other LLMs
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
  --full-content                  Return full code content, not truncated (max 5000 chars)
  --preview-length N              Preview length in characters (default: 200)
  --context N                     Number of context lines before/after chunk (default: 0)

Note: All CLI commands return JSON output for easy LLM integration.

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
python codebox.py index <path>

Note:
- Automatically detects all supported programming languages using Pygments
- Each indexing automatically clears and recreates the project directory for a clean start
- Supports 12 core languages with tree-sitter parsing: Python, JavaScript/JSX, TypeScript/TSX, Java, C++, C#, Go, Rust, HTML, CSS, JSON, YAML
```

### Stats
```bash
python codebox.py stats
```

## 📁 Project Structure

```
CodeBox/
├── app/
│   ├── cli/              # CLI command handlers
│   ├── core/             # Core business logic
│   ├── indexer/          # Parser, embeddings, chunker
│   ├── search/           # Vector DB, hybrid search
│   └── utils/            # Config, logger
├── codebox.py            # Entry point
├── requirements.txt
└── .lancedb/             # Database (auto-created)
```

---

## 🚧 Roadmap / TODO

### Phase 3.2.3: Decorator & Imports (Planned - Future)
- Decorator tracking, import dependencies
- **Estimated:** 1-2 weeks

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
