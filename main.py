#!/usr/bin/env python3
"""
UI-Agent Entry Point

Usage:
  python main.py --task "Search for Python tutorials on Google"
  python main.py --task "Fill the login form" --headless
"""

import asyncio
import os
import sys
import click
from dotenv import load_dotenv
from rich.console import Console
from rich.panel import Panel
from rich.text import Text

load_dotenv()

console = Console()


@click.command()
@click.option("--task", "-t", required=True, help="Task description for the agent")
@click.option("--headless", is_flag=True, default=False, help="Run browser in headless mode")
@click.option("--max-steps", default=None, type=int, help="Maximum number of agent steps")
@click.option("--model", default=None, help="Override LLM model (e.g. gpt-4o)")
@click.option("--provider", default=None, help="Override LLM provider (openai/deepseek/ollama)")
@click.option("--config", default="config/config.yaml", help="Path to config file")
@click.option("--verbose", "-v", is_flag=True, default=False, help="Verbose output")
def main(task, headless, max_steps, model, provider, config, verbose):
    """UI-Agent: LLM-powered browser automation agent."""
    
    # Import here to avoid slow startup
    from agent.agent import UIAgent
    from agent.config import AgentConfig

    console.print(Panel(
        Text(f"Task: {task}", style="bold green"),
        title="[bold blue]UI-Agent[/bold blue]",
        subtitle="Powered by LLM + Playwright"
    ))

    # Build config overrides
    overrides = {}
    if headless:
        overrides["headless"] = True
    if max_steps:
        overrides["max_steps"] = max_steps
    if model:
        overrides["llm_model"] = model
    if provider:
        overrides["llm_provider"] = provider
    if verbose:
        overrides["log_level"] = "DEBUG"

    cfg = AgentConfig.from_file(config, overrides=overrides)
    agent = UIAgent(config=cfg)

    try:
        result = asyncio.run(agent.run(task))
        console.print(Panel(
            Text(str(result), style="bold"),
            title="[bold green]Task Result[/bold green]"
        ))
        sys.exit(0)
    except KeyboardInterrupt:
        console.print("\n[yellow]Interrupted by user[/yellow]")
        sys.exit(1)
    except Exception as e:
        console.print(f"[bold red]Error:[/bold red] {e}")
        if verbose:
            import traceback
            traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
