#!/usr/bin/env python3
"""
Startup script for the Veterinary Bloodwork Analyzer.

This script provides a simple way to start the application with proper
configuration checks and helpful messages for developers.

Usage:
    python run_server.py [--dev] [--port PORT]
"""

import argparse
import os
import sys
from pathlib import Path


def check_environment() -> bool:
    """
    Check if the environment is properly configured.

    Returns:
        bool: True if environment is ready, False otherwise
    """
    issues = []

    # Check for required directories
    data_dir = Path("data/blood_work_pdfs")
    if not data_dir.exists():
        data_dir.mkdir(parents=True, exist_ok=True)
        print(f"✅ Created data directory: {data_dir}")

    # Check for OpenAI API key
    if not os.getenv("OPENAI_API_KEY"):
        issues.append(
            "⚠️  OPENAI_API_KEY not set - AI analysis will not work"
        )

    # Check for prompt files
    prompt_file = Path("app/prompts/diagnostic_prompt.txt")
    if not prompt_file.exists():
        issues.append(f"❌ Missing prompt file: {prompt_file}")

    if issues:
        print("\n🔧 Environment Issues Found:")
        for issue in issues:
            print(f"   {issue}")
        print("\n💡 Add your API key to a .env file or environment variables")
        return False

    print("✅ Environment check passed!")
    return True


def main():
    """Main entry point for the startup script."""
    parser = argparse.ArgumentParser(
        description="Start the Veterinary Bloodwork Analyzer")
    parser.add_argument("--dev", action="store_true",
                        help="Run in development mode")
    parser.add_argument("--port", type=int, default=8000,
                        help="Port to run on")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind to")

    args = parser.parse_args()

    print("🐾 Veterinary Bloodwork Analyzer - Starting Up...")
    print("=" * 50)

    # Check environment
    env_ok = check_environment()

    # Import check
    try:
        from app.main import app  # noqa: F401
        print("✅ Application modules loaded successfully")
    except ImportError as e:
        print(f"❌ Failed to import application: {e}")
        sys.exit(1)

    # Build uvicorn command
    uvicorn_args = [
        "uvicorn",
        "app.main:app",
        f"--host={args.host}",
        f"--port={args.port}",
    ]

    if args.dev:
        uvicorn_args.extend(["--reload", "--log-level=debug"])
        print("🔧 Development mode enabled")

    print(f"🚀 Starting server on http://{args.host}:{args.port}")
    print("📖 API Documentation available at:")
    print(f"   • Swagger UI: http://{args.host}:{args.port}/docs")
    print(f"   • ReDoc: http://{args.host}:{args.port}/redoc")

    if not env_ok:
        print("\n⚠️  Starting with configuration issues - some features may not work")

    print("\n" + "=" * 50)

    # Start the server
    import subprocess
    try:
        subprocess.run(uvicorn_args, check=True)
    except KeyboardInterrupt:
        print("\n👋 Server stopped by user")
    except subprocess.CalledProcessError as e:
        print(f"❌ Server failed to start: {e}")
        sys.exit(1)


if __name__ == "__main__":
    main()
