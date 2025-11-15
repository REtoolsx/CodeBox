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
            preview_length=args.preview_length,
            context=args.context,
            profile=getattr(args, 'profile', None)
        )

    elif args.command == "index":
        cli_overrides = {}
        if hasattr(args, 'chunk_size') and args.chunk_size:
            cli_overrides['chunk_size'] = args.chunk_size
        if hasattr(args, 'chunk_overlap') and args.chunk_overlap:
            cli_overrides['chunk_overlap'] = args.chunk_overlap
        if hasattr(args, 'max_file_size') and args.max_file_size:
            cli_overrides['max_file_size'] = args.max_file_size

        handler.index(
            project_path=args.path,
            profile=getattr(args, 'profile', None),
            cli_overrides=cli_overrides if cli_overrides else None
        )

    elif args.command == "stats":
        handler.stats()

    elif args.command == "auto-sync":
        handler.auto_sync()


def main():
    try:
        # Fix Windows console encoding for Unicode support
        import sys
        if hasattr(sys.stdout, 'reconfigure'):
            sys.stdout.reconfigure(encoding='utf-8')
            sys.stderr.reconfigure(encoding='utf-8')
    except Exception:
        pass

    try:
        AppConfig.init_directories()

        parser = argparse.ArgumentParser(
            description="CodeBox - Your Project & LLM Friend (Auto Language Detection)",
            formatter_class=argparse.RawDescriptionHelpFormatter,
            epilog="""
Examples:
  # Index current directory (auto-detects all supported languages)
  cd /path/to/your/project
  python codebox.py index

  # Index specific path (auto-detects all supported languages)
  python codebox.py index /path/to/project
  python codebox.py index ./my-project

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
        search_parser.add_argument('--full-content', action='store_true',
                                    help='Return full code content (not truncated)')
        search_parser.add_argument('--preview-length', type=int, default=200,
                                    help='Preview length in characters (default: 200)')
        search_parser.add_argument('--context', type=int, default=0,
                                    help='Number of context lines before/after (default: 0)')

        index_parser = subparsers.add_parser('index', help='Index a codebase (auto-detects languages)')
        index_parser.add_argument('path', nargs='?', default=None,
                                   help='Project directory path (default: current directory)')
        index_parser.add_argument('--profile', choices=['auto', 'medium', 'large'],
                                   help='Profile to use (auto, medium, large)')
        index_parser.add_argument('--chunk-size', type=int,
                                   help='Override chunk size')
        index_parser.add_argument('--chunk-overlap', type=int,
                                   help='Override chunk overlap')
        index_parser.add_argument('--max-file-size', type=int,
                                   help='Override max file size in bytes')

        search_parser.add_argument('--profile', choices=['auto', 'medium', 'large'],
                                   help='Profile to use (auto, medium, large)')

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
