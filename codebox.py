import sys
import argparse
from app.utils.config import AppConfig
from app.utils.logger import get_logger

logger = get_logger(__name__)


def run_cli(args):
    from app.cli.handler import CLIHandler

    handler = CLIHandler()

    if args.command == "search":
        handler.search(
            query=args.query,
            mode=args.mode,
            limit=args.limit,
            language=args.language,
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

    elif args.command == "auto-sync":
        handler.auto_sync()


def main():
    try:
        AppConfig.init_directories()

        parser = argparse.ArgumentParser(
            description="CodeBox - CLI Code Indexer & Search Tool",
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog="""
Examples:
  # Index current directory
  cd /path/to/your/project
  python codebox.py index

  # Index specific path
  python codebox.py index /path/to/project
  python codebox.py index ./my-project --languages python,javascript

  # Search current directory
  cd /path/to/your/project
  python codebox.py search "user authentication"
  python codebox.py search "login function" --mode vector --limit 5

  # LLM-optimized search (with full content & context)
  python codebox.py search "error handling" --full-content --context 5
  python codebox.py search "database" --preview-length 300 --limit 15

  # Stats for current directory
  cd /path/to/your/project
  python codebox.py stats

  # Auto-sync (watch for changes)
  cd /path/to/your/project
  python codebox.py auto-sync
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

        subparsers.add_parser('auto-sync', help='Watch for file changes and auto-sync')

        args = parser.parse_args()

        if not args.command:
            parser.print_help()
            sys.exit(1)

        run_cli(args)

    except Exception as e:
        logger.error(f"Application failed: {e}")
        raise


if __name__ == "__main__":
    main()
