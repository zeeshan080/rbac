import asyncio
import typer
from typing_extensions import Annotated # For Typer 0.9+ style
from sqlmodel.ext.asyncio.session import AsyncSession # For type hint, though session is created from factory

from app.core.logging_config import get_logger
from app.db.seed import seed_initial_data
from app.database import AsyncSessionLocal # Import session factory

# Initialize logger for CLI
logger = get_logger(__name__) # Use __name__ for consistent logger naming (e.g., app.cli)
cli_app = typer.Typer(
    name="RBAC App CLI",
    help="Command Line Interface for the FastAPI RBAC Application.",
    add_completion=False # Disable shell completion for simplicity in this context
)

@cli_app.command(name="seed-data") # Explicit command name
def seed_data_command(
    # Typer Context is not strictly needed here unless passing complex objects or using callbacks
    # ctx: typer.Context,
):
    """
    Populates the database with initial data: default permissions, roles,
    role-permission assignments, and a default superuser.

    Requires DEFAULT_SUPERUSER_PASSWORD environment variable to be set in .env.
    The application settings (including DB connection) are loaded from .env.
    """
    logger.info("CLI command 'seed-data' invoked.")
    typer.secho("Starting initial data seeding process...", fg=typer.colors.BLUE)

    async def _seed():
        logger.info("Attempting to connect to database and run seeder...")
        db_session: AsyncSession | None = None # Ensure db_session is defined for finally block
        try:
            # Create a new session for this operation
            db_session = AsyncSessionLocal()
            await seed_initial_data(db_session)
            # seed_initial_data should handle its own commits or rollbacks internally for atomicity.
            # If it doesn't, a final commit would be: await db_session.commit()
            logger.info("Data seeding process completed successfully via CLI.")
            typer.secho("Initial data seeding process completed successfully.", fg=typer.colors.GREEN)
        except Exception as e:
            logger.error(f"CLI: An error occurred during data seeding: {e}", exc_info=True)
            # If seed_initial_data handles its own transactions, rollback here might be redundant or interfere.
            # However, if an error happens outside its transactional scope, this could be useful.
            # if db_session and db_session.is_active: # Check if session is active before rollback
            #     await db_session.rollback()
            typer.secho(f"Error during data seeding: {e}", fg=typer.colors.RED, err=True)
            raise typer.Exit(code=1)
        finally:
            if db_session:
                await db_session.close()
                logger.info("CLI: Database session closed.")

    asyncio.run(_seed())

@cli_app.command()
def example_command(
    name: Annotated[str, typer.Option(help="The name to greet.")] = "World",
    count: Annotated[int, typer.Option(help="Number of times to greet.", min=1, max=5, clamp=True)] = 1,
    is_formal: Annotated[bool, typer.Option(help="Use a formal greeting.")] = False
):
    """
    An example Typer command with more options.
    """
    greeting = "Goodbye" if is_formal else "Yo" # Just kidding, make it formal
    greeting = "Greetings" if is_formal else "Hello"

    for i in range(count):
        typer.secho(f"{greeting}, {name}! (Invocation {i+1})", fg=typer.colors.CYAN)
    typer.secho("Example command finished.", fg=typer.colors.BRIGHT_BLACK)


if __name__ == "__main__":
    # This allows running: python app/cli.py seed-data
    # Or: python app/cli.py example-command --name "YourName" --count 3 --is-formal
    cli_app()
