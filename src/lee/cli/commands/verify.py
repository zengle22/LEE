"""
LEE Verify Command
"""

import os
import click
from pathlib import Path

from lee.orchestrator.execution.receipt import ReceiptStore, ReceiptVerifier


@click.command()
@click.argument("run_id")
@click.option("--step", default=None, help="Specific step ID to verify")
@click.option("--project-root", default=None, help="Project root directory")
def verify(run_id: str, step: str, project_root: str) -> None:
    """验证运行凭证 (P0-4 Receipts)"""
    root = project_root or os.getcwd()
    runs_root = str(Path(root) / ".lee" / "runs")
    
    store = ReceiptStore(runs_root)
    receipts = store.load_by_run(run_id)
    
    if not receipts:
        click.echo(f"No receipts found for run {run_id} in {runs_root}")
        return

    verifier = ReceiptVerifier()
    
    click.echo(f"Verifying run: {run_id}")
    click.echo(f"{'Step ID':<20} | {'Repo':<15} | {'Integrity':<10} | {'Time'}")
    click.echo("-" * 70)
    
    passed_count = 0
    total_count = 0

    for r in receipts:
        if step and r.step_id != step:
            continue
            
        total_count += 1
        is_valid = verifier.verify(r)
        if is_valid:
            passed_count += 1
            
        status = "PASS ✅" if is_valid else "FAIL ❌"
        repo = r.repo_id if r.repo_id else "-"
        
        click.echo(f"{r.step_id:<20} | {repo:<15} | {status:<10} | {r.timestamp}")

    click.echo("-" * 70)
    click.echo(f"Total: {total_count}, Passed: {passed_count}, Failed: {total_count - passed_count}")
