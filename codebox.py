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
            full_content=args.full_content,
            context=args.context,
            output=getattr(args, 'output', 'compact')
        )

    elif args.command == "index":
        handler.index(project_path=args.path)

    elif args.command == "reindex":
        handler.reindex(project_path=args.path)

    elif args.command == "stats":
        handler.stats()


def main():
    try:
        import sys
        if hasattr(sys.stdout, 'reconfigure'):
            sys.stdout.reconfigure(encoding='utf-8')
            sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

    try:
        AppConfig.init_directories()
        AppConfig.ensure_config_loaded()

        parser = argparse.ArgumentParser(
            description="CodeBox - Your Project & LLM Friend (Auto Language Detection)",
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog="""
Examples:
  # Index current directory (auto-detects all supported languages)
  cd /path/to/your/project
  python codebox.py index

  # Index specific path (auto-detects all supported languages and project size)
  python codebox.py index /path/to/project
  python codebox.py index ./my-project

  # Re-index from scratch (clears all previous data)
  python codebox.py reindex

  # Search current directory
  cd /path/to/your/project
  python codebox.py search "user authentication"
  python codebox.py search "login function" --mode vector --limit 5

  # LLM-optimized search (with different output formats)
  python codebox.py search "error handling" --output standard --context 5
  python codebox.py search "database" --output verbose --limit 15

  # Stats for current directory
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
        search_parser.add_argument('--full-content', action='store_true',
                                    help='Return full code content (not truncated)')
        search_parser.add_argument('--context', type=int, default=0,
                                    help='Number of context lines before/after (default: 0)')
        search_parser.add_argument('--output', choices=['compact', 'standard', 'verbose'],
                                    default='compact',
                                    help='Output format: compact (minimal), standard (balanced), verbose (full metadata)')

        index_parser = subparsers.add_parser('index', help='Index a codebase (auto-detects languages and project size, auto-sync if already indexed)')
        index_parser.add_argument('path', nargs='?', default=None,
                                   help='Project directory path (default: current directory)')

        reindex_parser = subparsers.add_parser('reindex', help='Re-index from scratch (clears all previous data)')
        reindex_parser.add_argument('path', nargs='?', default=None,
                                     help='Project directory path (default: current directory)')

        subparsers.add_parser('stats', help='Show database statistics')

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
