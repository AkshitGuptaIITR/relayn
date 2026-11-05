import secrets
import typer
from argon2 import PasswordHasher
from rich.console import Console
from rich.panel import Panel

app = typer.Typer(
    help="Relayn CLI: Operational management, secret generation, and password hashing.",
    no_args_is_help=True,
)
console = Console()
ph = PasswordHasher()


@app.command()
def generate_secret():
    """Generate a cryptographically secure 32-byte hex secret for RELAYN_SESSION_SECRET."""
    secret = secrets.token_hex(32)
    console.print(Panel(
        f"[bold green]{secret}[/bold green]",
        title="Generated Session Secret (AES-256-GCM)",
        subtitle="Set this as RELAYN_SESSION_SECRET in your .env",
    ))


@app.command()
def hash_password(
    password: str = typer.Option(
        None,
        "--password",
        "-p",
        prompt=True,
        hide_input=True,
        confirmation_prompt=True,
        help="Owner password to hash with Argon2id",
    )
):
    """Hash a password using Argon2id for RELAYN_PASSWORD_HASH."""
    if not password:
        console.print("[bold red]Password cannot be empty.[/bold red]")
        raise typer.Exit(code=1)

    password_hash = ph.hash(password)
    console.print(Panel(
        f"[bold green]{password_hash}[/bold green]",
        title="Argon2id Password Hash",
        subtitle="Set this as RELAYN_PASSWORD_HASH in your .env",
    ))


@app.command()
def verify_password(
    password: str = typer.Option(..., prompt=True, hide_input=True),
    hash_to_verify: str = typer.Option(..., prompt=True),
):
    """Verify if a plaintext password matches an existing Argon2id hash."""
    try:
        ph.verify(hash_to_verify, password)
        console.print("[bold green]Password verified successfully![/bold green]")
    except Exception:
        console.print("[bold red]Verification failed! Password does not match hash.[/bold red]")
        raise typer.Exit(code=1)


if __name__ == "__main__":
    app()
