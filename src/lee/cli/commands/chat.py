"""
Lee Chat Command
PM Agent interactive interface (REPL).
"""
import asyncio
import click
import os
from pathlib import Path
from prompt_toolkit import PromptSession
from prompt_toolkit.styles import Style
from prompt_toolkit.formatted_text import HTML

from lee.orchestrator.execution.pm_agent_runtime import PMAgentRuntime
from lee.orchestrator.execution.orchestrator import Orchestrator
from lee.orchestrator.storage.sqlite_store import SQLiteStore as SQLiteWorkflowStore
# from lee.orchestrator.execution.executors import ExecutorFactory # Assuming factory exists

class LeeChatREPL:
    def __init__(self, project_dir: str):
        self.project_dir = Path(project_dir).resolve()
        self.db_path = self.project_dir / ".lee" / "lee.db"
        self.store = SQLiteWorkflowStore(str(self.db_path))
        
        # Initialize Orchestrator
        self.orchestrator = Orchestrator(self.store, project_root=str(self.project_dir))
        
        # Initialize Runtime
        # TODO: Inject real LLM executor when available
        self.llm_executor = None 
        self.runtime = PMAgentRuntime(self.orchestrator, self.llm_executor, self.store)
        
        self.session = PromptSession()
        self.style = Style.from_dict({
            'prompt': 'ansicyan bold',
            'pm': 'ansigreen',
        })

    async def run_loop(self):
        click.echo(HTML("<pm>Welcome to Lee Chat! (Type 'exit' to quit)</pm>"), style=self.style)
        
        while True:
            try:
                user_input = await self.session.prompt_async(
                    HTML("<prompt>Lee></prompt> "), 
                    style=self.style
                )
                
                user_input = user_input.strip()
                if not user_input:
                    continue
                    
                if user_input.lower() in ('exit', 'quit'):
                    click.echo("Goodbye!")
                    break
                    
                await self.handle_input(user_input)
                
            except KeyboardInterrupt:
                continue
            except EOFError:
                break
            except Exception as e:
                click.echo(f"Error: {e}", err=True)

    async def handle_input(self, text: str):
        """
        Process user input via PM Agent Runtime.
        """
        # Placeholder for full NL processing
        if text.startswith("/"):
            # Handle slash commands if any
            pass
            
        # For P2, we demonstrate basic interaction
        click.echo(HTML(f"<pm>PM Agent received: {text}</pm>"), style=self.style)
        
        # In P3/Full implementation:
        # params = await self.runtime.compile_prompt(text)
        # confirm = await self.runtime.handle_gate_request(...)
        # if confirm: execute...

@click.command()
@click.option("--project-dir", default=".", help="Project directory")
def chat(project_dir):
    """Start Lee Chat interactive session."""
    repl = LeeChatREPL(project_dir)
    asyncio.run(repl.run_loop())
