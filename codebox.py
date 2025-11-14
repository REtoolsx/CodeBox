import sys
import argparse
from app.utils.config import AppConfig
from app.utils.logger import get_logger

logger = get_logger(__name__)


def run_gui():
    from PyQt6.QtWidgets import QApplication
    from app.gui.main_window import MainWindow

    app = QApplication(sys.argv)
    app.setApplicationName(AppConfig.APP_NAME)
    app.setApplicationVersion(AppConfig.APP_VERSION)
    app.setStyle("Fusion")

    window = MainWindow()
    window.show()

    sys.exit(app.exec())


def run_cli(args):
    from app.cli.handler import CLIHandler

    handler = CLIHandler()

    if args.command == "search":
        handler.search(
            query=args.query,
            mode=args.mode,
            limit=args.limit,
            language=args.language,
            output_format=args.format,
            full_content=args.full_content,
            preview_length=args.preview_length,
            context=args.context
        )

    elif args.command == "index":
        languages = args.languages.split(',') if args.languages else None
        handler.index(
            project_path=args.path,
            languages=languages
        )

    elif args.command == "stats":
        handler.stats()


def main():
    try:
        AppConfig.init_directories()

        parser = argparse.ArgumentParser(
            description="CodeBox - Python Code Indexer & Search Tool",
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog="""
Examples:
  # GUI mode (default)
  python codebox.py

  # CLI mode - Index current directory
  cd /path/to/your/project
  python codebox.py index

  # CLI mode - Index specific path
  python codebox.py index /path/to/project
  python codebox.py index ./my-project --languages python,javascript

  # CLI mode - Search current directory
  cd /path/to/your/project
  python codebox.py search "user authentication"
  python codebox.py search "login function" --mode vector --limit 5

  # CLI mode - LLM-optimized search (with full content & context)
  python codebox.py search "error handling" --full-content --context 5
  python codebox.py search "database" --preview-length 300 --limit 15

  # CLI mode - Stats for current directory
  cd /path/to/your/project
  python codebox.py stats
            """
        )

        subparsers = parser.add_subparsers(dest='command', help='Command to execute')

        search_parser = subparsers.add_parser('search', help='Search code')
        search_parser.add_argument('query', help='Search query')
        search_parser.add_argument('--mode', choices=['vector', 'keyword', 'hybrid'],
                                    default='hybrid', help='Search mode (default: hybrid)')
        search_parser.add_argument('--limit', type=int, default=10,
                                    help='Max results (default: 10)')
        search_parser.add_argument('--language', help='Filter by language')
        search_parser.add_argument('--format', choices=['json', 'text'],
                                    default='json', help='Output format (default: json)')
        search_parser.add_argument('--full-content', action='store_true',
                                    help='Return full code content (not truncated)')
        search_parser.add_argument('--preview-length', type=int, default=200,
                                    help='Preview length in characters (default: 200)')
        search_parser.add_argument('--context', type=int, default=0,
                                    help='Number of context lines before/after (default: 0)')

        index_parser = subparsers.add_parser('index', help='Index a codebase')
        index_parser.add_argument('path', nargs='?', default=None,
                                   help='Project directory path (default: current directory)')
        index_parser.add_argument('--languages',
                                   help='Comma-separated languages (e.g., python,javascript)')

        subparsers.add_parser('stats', help='Show database statistics')

        args = parser.parse_args()

        if args.command:
            run_cli(args)
        else:
            run_gui()

    except Exception as e:
        logger.error(f"Application failed: {e}")
        raise


if __name__ == "__main__":
    main()
