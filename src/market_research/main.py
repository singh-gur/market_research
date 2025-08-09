#!/usr/bin/env python
import logging
import warnings

import click

from market_research.crew import MarketResearch

warnings.filterwarnings("ignore", category=SyntaxWarning, module="pysbd")

# Set up logging
logging.basicConfig(
    level=logging.INFO, format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)


@click.group()
@click.version_option()
def cli():
    """Market Research CLI - Analyze financial markets using AI agents."""
    pass


@cli.command()
@click.option(
    "--ticker",
    "-t",
    default="TLN",
    help="Stock ticker symbol to analyze (e.g., AAPL, TSLA)",
    show_default=True,
)
def run(ticker: str):
    """Run the market research crew with the specified ticker."""
    inputs = {"ticker": ticker.upper()}

    try:
        click.echo(f"🚀 Starting market research for ticker: {ticker.upper()}")
        MarketResearch().crew().kickoff(inputs=inputs)
        click.echo("✅ Market research completed successfully!")
    except Exception as e:
        click.echo(f"❌ An error occurred while running the crew: {e}", err=True)
        raise click.ClickException(str(e))


@cli.command()
@click.option(
    "--ticker",
    "-t",
    default="TLN",
    help="Stock ticker symbol to analyze",
    show_default=True,
)
@click.option(
    "--iterations",
    "-n",
    type=int,
    required=True,
    help="Number of training iterations to run",
)
@click.option(
    "--filename",
    "-f",
    required=True,
    help="Filename to save training results",
)
def train(ticker: str, iterations: int, filename: str):
    """Train the crew for a specified number of iterations."""
    inputs = {"ticker": ticker.upper()}

    try:
        click.echo(
            f"🎯 Training crew for {iterations} iterations with ticker: {ticker.upper()}"
        )
        MarketResearch().crew().train(
            n_iterations=iterations, filename=filename, inputs=inputs
        )
        click.echo(f"✅ Training completed! Results saved to: {filename}")
    except Exception as e:
        click.echo(f"❌ An error occurred while training the crew: {e}", err=True)
        raise click.ClickException(str(e))


@cli.command()
@click.argument("task_id", required=True)
def replay(task_id: str):
    """Replay the crew execution from a specific task ID."""
    try:
        click.echo(f"🔄 Replaying task: {task_id}")
        MarketResearch().crew().replay(task_id=task_id)
        click.echo("✅ Replay completed successfully!")
    except Exception as e:
        click.echo(f"❌ An error occurred while replaying the crew: {e}", err=True)
        raise click.ClickException(str(e))


@cli.command()
@click.option(
    "--ticker",
    "-t",
    default="TLN",
    help="Stock ticker symbol to analyze",
    show_default=True,
)
@click.option(
    "--iterations",
    "-n",
    type=int,
    required=True,
    help="Number of test iterations to run",
)
@click.option(
    "--eval-llm",
    "-e",
    required=True,
    help="LLM model to use for evaluation",
)
def test(ticker: str, iterations: int, eval_llm: str):
    """Test the crew execution and return the results."""
    inputs = {"ticker": ticker.upper()}

    try:
        click.echo(
            f"🧪 Testing crew for {iterations} iterations with ticker: {ticker.upper()}"
        )
        MarketResearch().crew().test(
            n_iterations=iterations, eval_llm=eval_llm, inputs=inputs
        )
        click.echo("✅ Testing completed successfully!")
    except Exception as e:
        click.echo(f"❌ An error occurred while testing the crew: {e}", err=True)
        raise click.ClickException(str(e))


if __name__ == "__main__":
    cli()
