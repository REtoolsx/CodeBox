# 🔍 CodeBox - Your Project & LLM Friend

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

### Usage

```bash
# Show help
python codebox.py --help

# Index your project (auto-detects languages and project size)
python codebox.py index /path/to/project

# Re-index from scratch (clears all previous data)
python codebox.py reindex

# Search code
python codebox.py search "user authentication" --mode hybrid --limit 10

# Search with different output modes
python codebox.py search "authentication" --output compact    # Default: minimal, 70% token reduction
python codebox.py search "authentication" --output standard   # Balanced: 50% token reduction
python codebox.py search "authentication" --output verbose    # Full metadata

# View statistics
python codebox.py stats
```

## ✨ Features

- **⭐ 2025 SOTA Embedding**: Jina Embeddings v3 with Matryoshka Representation Learning (MRL)
- **Smart Auto-Sync**: Automatic file watching when re-indexing already indexed projects
- **Hybrid Search**: Vector + Keyword search with RRF fusion
- **3 Output Modes**: Compact (70% token reduction), Standard (50% reduction), Verbose (full metadata)
- **Line-Numbered Output**: All code includes line numbers for easy LLM referencing
- **AST Parsing**: Tree-sitter support for 12 core languages (Python, JS/JSX, TS/TSX, Java, C++, C#, Go, Rust, HTML, CSS, JSON, YAML)
  - **Function/Class signatures** with parameters and return types
  - **Decorators & Annotations** (@decorator, @pytest.fixture, etc.)
  - **Import Dependencies** tracking across files
  - **Scope Hierarchy** (parent classes, nested functions)
  - **Call Graph** (same-file function call tracking)
- **Auto Language Detection**: Pygments support for 597+ languages
- **Auto Profile Optimization**: Automatically detects project size and optimizes chunk size (1536/2048)
- **Vector Database**: LanceDB for fast similarity search
- **JSON Output**: Optimized for LLM integration

## 📄 License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.

## 🤝 Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
