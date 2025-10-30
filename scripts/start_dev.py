#!/usr/bin/env python3
"""
scripts/start_dev.py

Start complete development stack for Archer Voice Agent:
- PostgreSQL database (via docker-compose)
- Redis server (via docker-compose)
- FastAPI backend on port 8000
- Ngrok tunnel for Twilio webhooks
- (Frontend on port 3000 - Phase 3)

Usage:
    python scripts/start_dev.py

    # Or make executable:
    chmod +x scripts/start_dev.py
    ./scripts/start_dev.py
"""

import os
import signal
import subprocess
import sys
import time
from pathlib import Path
from typing import Optional

try:
    from rich.console import Console
    from rich.panel import Panel
    RICH_AVAILABLE = True
    console = Console()
except Exception:
    RICH_AVAILABLE = False
    class _SimpleConsole:
        def print(self, *args, **kwargs):
            print(*args)
    console = _SimpleConsole()

# HTTP client for ngrok API
try:
    import requests
    def http_get_json(url: str, timeout: float = 2.0) -> dict:
        r = requests.get(url, timeout=timeout)
        r.raise_for_status()
        return r.json()
except Exception:
    def http_get_json(url: str, timeout: float = 2.0) -> dict:
        raise RuntimeError("No HTTP client available. Install 'requests'.")

ROOT = Path(__file__).resolve().parents[1]
BACKEND_DIR = ROOT / "archer" / "backend"
NGROK_API = "http://localhost:4040/api/tunnels"

# Global process handles
_docker_services: list[str] = []
_backend_proc: Optional[subprocess.Popen] = None
_ngrok_proc: Optional[subprocess.Popen] = None


def kill_port(port: int) -> None:
    """Force kill any process on the given TCP port."""
    try:
        result = subprocess.run(
            ["lsof", "-ti", f":{port}"],
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            check=False,
        )
        if not result.stdout:
            return
        for pid in {pid.strip() for pid in result.stdout.splitlines() if pid.strip()}:
            subprocess.run(["kill", "-TERM", pid], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
            time.sleep(0.5)
            subprocess.run(["kill", "-KILL", pid], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
    except FileNotFoundError:
        # lsof not available
        if port == 8000:
            subprocess.run(["pkill", "-f", "uvicorn"], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
    except Exception:
        pass


def check_docker() -> bool:
    """Check if Docker is available."""
    try:
        result = subprocess.run(
            ["docker", "--version"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=True
        )
        return True
    except Exception:
        return False


def check_docker_compose() -> bool:
    """Check if docker-compose is available."""
    try:
        result = subprocess.run(
            ["docker-compose", "--version"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=True
        )
        return True
    except Exception:
        # Try docker compose (v2 syntax)
        try:
            result = subprocess.run(
                ["docker", "compose", "version"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                check=True
            )
            return True
        except Exception:
            return False


def get_docker_compose_cmd() -> list[str]:
    """Get the docker-compose command (v1 or v2 syntax)."""
    try:
        subprocess.run(
            ["docker-compose", "--version"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            check=True
        )
        return ["docker-compose"]
    except Exception:
        return ["docker", "compose"]


def check_env_file() -> None:
    """Check for .env file and warn if missing."""
    env_path = ROOT / ".env"
    env_example = ROOT / ".env.example"

    if not env_path.exists():
        msg = (
            "⚠️  WARNING: .env file not found in project root.\n\n"
            "Create one by copying .env.example and filling in your credentials:\n\n"
            "    cp .env.example .env\n\n"
            "Required variables:\n"
            "  - CARTESIA_API_KEY\n"
            "  - TWILIO_ACCOUNT_SID\n"
            "  - TWILIO_AUTH_TOKEN\n"
            "  - DATABASE_URL\n"
        )
        if RICH_AVAILABLE:
            console.print(Panel(msg, title="Missing .env", style="yellow"))
        else:
            print(msg)

        response = input("\nContinue without .env? (y/N): ").strip().lower()
        if response != 'y':
            sys.exit(1)


def start_docker_services() -> bool:
    """Start PostgreSQL and Redis via docker-compose."""
    global _docker_services

    if not check_docker():
        if RICH_AVAILABLE:
            console.print("❌ Docker not found - install Docker Desktop", style="red")
        else:
            print("❌ Docker not found - install Docker Desktop")
        return False

    if not check_docker_compose():
        if RICH_AVAILABLE:
            console.print("❌ docker-compose not found", style="red")
        else:
            print("❌ docker-compose not found")
        return False

    docker_cmd = get_docker_compose_cmd()

    # Check if services are already running
    try:
        result = subprocess.run(
            docker_cmd + ["ps", "-q", "postgres", "redis"],
            cwd=ROOT,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
            check=False
        )
        if result.stdout.strip():
            if RICH_AVAILABLE:
                console.print("✓ Docker services already running", style="green")
            else:
                print("✓ Docker services already running")
            _docker_services = ["postgres", "redis"]
            return True
    except Exception:
        pass

    # Start postgres and redis
    try:
        if RICH_AVAILABLE:
            console.print("🐳 Starting PostgreSQL and Redis...", style="cyan")
        else:
            print("🐳 Starting PostgreSQL and Redis...")

        subprocess.run(
            docker_cmd + ["up", "-d", "postgres", "redis"],
            cwd=ROOT,
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL
        )

        _docker_services = ["postgres", "redis"]

        # Wait for services to be healthy
        if RICH_AVAILABLE:
            console.print("   Waiting for services to be healthy...", style="dim")
        else:
            print("   Waiting for services to be healthy...")

        time.sleep(3)

        if RICH_AVAILABLE:
            console.print("✓ PostgreSQL started on localhost:5432", style="green")
            console.print("✓ Redis started on localhost:6379", style="green")
        else:
            print("✓ PostgreSQL started on localhost:5432")
            print("✓ Redis started on localhost:6379")

        return True

    except subprocess.CalledProcessError as exc:
        if RICH_AVAILABLE:
            console.print(f"❌ Failed to start Docker services: {exc}", style="red")
        else:
            print(f"❌ Failed to start Docker services: {exc}")
        return False


def run_migrations() -> bool:
    """Run database migrations."""
    if not BACKEND_DIR.exists():
        return True  # Skip if backend not set up yet

    try:
        if RICH_AVAILABLE:
            console.print("🔄 Running database migrations...", style="cyan")
        else:
            print("🔄 Running database migrations...")

        result = subprocess.run(
            ["poetry", "run", "alembic", "upgrade", "head"],
            cwd=BACKEND_DIR,
            check=True,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True
        )

        if RICH_AVAILABLE:
            console.print("✓ Database migrations complete", style="green")
        else:
            print("✓ Database migrations complete")

        return True

    except subprocess.CalledProcessError as exc:
        if "already exists" in exc.stderr or "already exists" in exc.stdout:
            # Migration already applied
            if RICH_AVAILABLE:
                console.print("✓ Database already migrated", style="green")
            else:
                print("✓ Database already migrated")
            return True

        if RICH_AVAILABLE:
            console.print(f"⚠️  Migration failed (continuing anyway): {exc.stderr}", style="yellow")
        else:
            print(f"⚠️  Migration failed: {exc.stderr}")
        return False
    except FileNotFoundError:
        if RICH_AVAILABLE:
            console.print("⚠️  Poetry not found - skipping migrations", style="yellow")
        else:
            print("⚠️  Poetry not found - skipping migrations")
        return False


def print_banner() -> None:
    """Print startup banner."""
    banner_text = "Archer Voice Agent - Development Stack"
    if RICH_AVAILABLE:
        console.print(Panel(banner_text, border_style="cyan", style="bold white"))
    else:
        print("=" * 50)
        print(banner_text)
        print("=" * 50)


def start_backend() -> subprocess.Popen:
    """Start FastAPI backend on port 8000."""
    global _backend_proc

    if not BACKEND_DIR.exists():
        raise RuntimeError(f"Backend directory not found: {BACKEND_DIR}")

    # Ensure port 8000 is free
    kill_port(8000)

    log_level = os.getenv("LOG_LEVEL", "info").lower()

    cmd = [
        "poetry", "run",
        "uvicorn",
        "src.main:app",
        "--host", "127.0.0.1",
        "--port", "8000",
        "--reload",
        "--reload-dir", "src",
        "--log-level", log_level,
    ]

    popen_kwargs = {
        "cwd": BACKEND_DIR,
        "env": {**os.environ, "PYTHONDONTWRITEBYTECODE": "1"},
        "stdout": None,
        "stderr": None,
    }
    if os.name != "nt":
        popen_kwargs["preexec_fn"] = os.setsid
    else:
        popen_kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP

    try:
        _backend_proc = subprocess.Popen(cmd, **popen_kwargs)
        if RICH_AVAILABLE:
            console.print("✓ Backend starting on http://localhost:8000", style="green")
        else:
            print("✓ Backend starting on http://localhost:8000")
        return _backend_proc
    except Exception as exc:
        raise RuntimeError(f"Failed to start backend: {exc}")


def start_ngrok() -> Optional[subprocess.Popen]:
    """Start ngrok tunnel."""
    global _ngrok_proc

    cmd = ["ngrok", "http", "8000"]

    popen_kwargs = {
        "stdout": subprocess.DEVNULL,
        "stderr": subprocess.DEVNULL,
    }
    if os.name != "nt":
        popen_kwargs["preexec_fn"] = os.setsid
    else:
        popen_kwargs["creationflags"] = subprocess.CREATE_NEW_PROCESS_GROUP

    try:
        _ngrok_proc = subprocess.Popen(cmd, **popen_kwargs)
        if RICH_AVAILABLE:
            console.print("✓ Ngrok tunnel starting...", style="green")
        else:
            print("✓ Ngrok tunnel starting...")
        return _ngrok_proc
    except FileNotFoundError:
        if RICH_AVAILABLE:
            console.print("⚠️  Ngrok not found - skipping tunnel (install: brew install ngrok)", style="yellow")
        else:
            print("⚠️  Ngrok not found - skipping tunnel")
        return None
    except Exception as exc:
        if RICH_AVAILABLE:
            console.print(f"⚠️  Failed to start ngrok: {exc}", style="yellow")
        else:
            print(f"⚠️  Failed to start ngrok: {exc}")
        return None


def fetch_ngrok_url(retries: int = 10, delay: float = 0.5) -> Optional[str]:
    """Fetch ngrok public URL."""
    for attempt in range(retries):
        try:
            data = http_get_json(NGROK_API, timeout=2.0)
            tunnels = data.get("tunnels", [])
            for t in tunnels:
                public_url = t.get("public_url")
                if public_url and public_url.startswith("https://"):
                    return public_url
        except Exception:
            time.sleep(delay)
    return None


def print_status(ngrok_url: Optional[str]) -> None:
    """Print status panel."""
    lines = [
        "[bold blue]PostgreSQL:[/] localhost:5432 (archer_dev)",
        "[bold red]Redis:[/] localhost:6379",
        "[bold cyan]Backend:[/] http://localhost:8000",
        "[bold yellow]API Docs:[/] http://localhost:8000/docs",
        "[bold green]Health:[/] http://localhost:8000/health",
    ]

    if ngrok_url:
        lines.append("")
        lines.append(f"[bold magenta]Ngrok:[/] {ngrok_url}")
        webhook = f"{ngrok_url.rstrip('/')}/api/v1/webhooks/twilio/voice"
        lines.append(f"[bold orange]Webhook:[/] {webhook}")
        lines.append("")
        lines.append("[dim]Update Twilio webhook to ngrok URL above[/]")

    if RICH_AVAILABLE:
        console.print("\n")
        console.print(Panel("\n".join(lines), title="🚀 Archer Dev Stack Running", border_style="green"))
        console.print("\n[dim]Press Ctrl+C to stop all services[/]\n")
    else:
        print("\n" + "=" * 60)
        print("🚀 Archer Dev Stack Running:")
        print("  PostgreSQL: localhost:5432 (archer_dev)")
        print("  Redis:      localhost:6379")
        print("  Backend:    http://localhost:8000")
        print("  API Docs:   http://localhost:8000/docs")
        print("  Health:     http://localhost:8000/health")
        if ngrok_url:
            print(f"  Ngrok:      {ngrok_url}")
            print(f"  Webhook:    {ngrok_url.rstrip('/')}/api/v1/webhooks/twilio/voice")
        print("=" * 60)
        print("\nPress Ctrl+C to stop all services\n")


def stop_process(proc: Optional[subprocess.Popen], name: str) -> None:
    """Stop a subprocess and all its children."""
    if not proc:
        return

    try:
        if proc.poll() is None:
            # Try process group termination first
            if os.name != "nt":
                try:
                    os.killpg(os.getpgid(proc.pid), signal.SIGTERM)
                    try:
                        proc.wait(timeout=2.0)
                    except subprocess.TimeoutExpired:
                        os.killpg(os.getpgid(proc.pid), signal.SIGKILL)
                except Exception:
                    pass
            else:
                try:
                    proc.send_signal(signal.CTRL_BREAK_EVENT)
                    proc.wait(timeout=2.0)
                except Exception:
                    pass

        if proc.poll() is None:
            try:
                proc.terminate()
                proc.wait(timeout=2.0)
            except Exception:
                try:
                    proc.kill()
                    proc.wait(timeout=1.0)
                except Exception:
                    pass
    except Exception:
        pass

    # Extra cleanup
    if name == "backend":
        try:
            subprocess.run(["pkill", "-f", "uvicorn.*src.main:app"],
                         stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, check=False)
        except Exception:
            pass
        kill_port(8000)


def stop_docker_services() -> None:
    """Stop Docker services."""
    if not _docker_services:
        return

    docker_cmd = get_docker_compose_cmd()

    try:
        if RICH_AVAILABLE:
            console.print("🐳 Stopping Docker services...", style="yellow")
        else:
            print("🐳 Stopping Docker services...")

        subprocess.run(
            docker_cmd + ["stop"] + _docker_services,
            cwd=ROOT,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=10,
            check=False
        )
    except Exception:
        pass


_shutdown_in_progress = False

def handle_shutdown(signum=None, frame=None) -> None:
    """Handle shutdown gracefully."""
    global _shutdown_in_progress

    if _shutdown_in_progress:
        return
    _shutdown_in_progress = True

    if RICH_AVAILABLE:
        console.print("\n[yellow]Stopping all services...[/]")
    else:
        print("\nStopping all services...")

    stop_process(_backend_proc, "backend")
    stop_process(_ngrok_proc, "ngrok")
    stop_docker_services()

    if RICH_AVAILABLE:
        console.print("[green]Shutdown complete![/]")
    else:
        print("Shutdown complete!")

    sys.exit(0)


def main() -> None:
    """Main entry point."""
    print_banner()

    # Check environment
    check_env_file()

    # Install signal handlers
    try:
        signal.signal(signal.SIGINT, handle_shutdown)
        if hasattr(signal, "SIGTERM"):
            signal.signal(signal.SIGTERM, handle_shutdown)
    except Exception:
        pass

    # Start Docker services (PostgreSQL + Redis)
    if not start_docker_services():
        if RICH_AVAILABLE:
            console.print("[red]Failed to start Docker services - exiting[/]")
        else:
            print("Failed to start Docker services - exiting")
        sys.exit(1)

    # Run database migrations
    run_migrations()

    # Start backend
    try:
        start_backend()
        time.sleep(2)
    except Exception as exc:
        if RICH_AVAILABLE:
            console.print(f"[red]Failed to start backend: {exc}[/]")
        else:
            print(f"Failed to start backend: {exc}")
        handle_shutdown()
        sys.exit(1)

    # Start ngrok tunnel
    start_ngrok()
    time.sleep(2)

    # Fetch ngrok URL
    ngrok_url = fetch_ngrok_url(retries=10, delay=0.5)
    if ngrok_url:
        if RICH_AVAILABLE:
            console.print(f"✓ Ngrok tunnel ready: {ngrok_url}", style="green")
        else:
            print(f"✓ Ngrok tunnel ready: {ngrok_url}")
    else:
        if RICH_AVAILABLE:
            console.print("⚠️  Could not get ngrok URL", style="yellow")
        else:
            print("⚠️  Could not get ngrok URL")

    # Print status
    print_status(ngrok_url)

    # Keep alive
    try:
        while True:
            time.sleep(1.0)
            # Check if backend died
            if _backend_proc and _backend_proc.poll() is not None:
                if RICH_AVAILABLE:
                    console.print("[red]Backend died![/]")
                else:
                    print("Backend died!")
                handle_shutdown()
    except KeyboardInterrupt:
        handle_shutdown()


if __name__ == "__main__":
    main()
