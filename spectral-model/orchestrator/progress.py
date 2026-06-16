"""Rich progress display for pipeline runs."""

import logging
from typing import Optional

logger = logging.getLogger(__name__)


class PipelineProgress:
    """
    Rich-based progress display for pipeline execution.

    Uses Rich's Progress with columns for task name, progress bar, count, and status.
    """

    def __init__(self):
        self._progress = None
        self._tasks: dict[str, object] = {}
        self._console = None

    def _ensure_initialized(self) -> None:
        if self._progress is not None:
            return

        try:
            from rich.progress import (
                Progress,
                SpinnerColumn,
                TextColumn,
                BarColumn,
                TaskProgressColumn,
                TimeElapsedColumn,
                MofNCompleteColumn,
            )
            from rich.console import Console

            self._console = Console()
            self._progress = Progress(
                SpinnerColumn(),
                TextColumn("[bold blue]{task.description}"),
                BarColumn(),
                MofNCompleteColumn(),
                TaskProgressColumn(),
                TimeElapsedColumn(),
                TextColumn("[green]{task.fields[status]}"),
                console=self._console,
            )
        except ImportError:
            logger.warning("Rich not available; using simple progress logging")

    def __enter__(self):
        self._ensure_initialized()
        if self._progress:
            self._progress.__enter__()
        return self

    def __exit__(self, *args):
        if self._progress:
            self._progress.__exit__(*args)

    def add_task(self, name: str, total: int) -> str:
        """
        Add a new progress task.

        Args:
            name: Display name for the task
            total: Total number of items to process

        Returns:
            Task ID string
        """
        self._ensure_initialized()
        if self._progress:
            task_id = self._progress.add_task(name, total=total, status="running")
            self._tasks[name] = task_id
            return str(task_id)
        else:
            logger.info(f"Starting task: {name} ({total} items)")
            return name

    def update(
        self,
        task_id: str,
        advance: int = 1,
        status: str = "",
        total: Optional[int] = None,
    ) -> None:
        """
        Update progress for a task.

        Args:
            task_id: Task ID returned by add_task
            advance: Number of steps to advance
            status: Status message to display
            total: Update total if provided
        """
        if self._progress:
            kwargs = {"advance": advance}
            if status:
                kwargs["status"] = status
            if total is not None:
                kwargs["total"] = total
            try:
                self._progress.update(int(task_id), **kwargs)
            except (ValueError, TypeError):
                pass
        else:
            if status:
                logger.info(f"Task {task_id}: {status} (advance={advance})")

    def complete_task(self, task_id: str, message: str = "Done") -> None:
        """Mark a task as complete."""
        if self._progress:
            try:
                self._progress.update(
                    int(task_id),
                    status=f"[green]{message}[/green]",
                    completed=True,
                )
            except (ValueError, TypeError):
                pass
        else:
            logger.info(f"Task {task_id} complete: {message}")

    def fail_task(self, task_id: str, message: str = "Failed") -> None:
        """Mark a task as failed."""
        if self._progress:
            try:
                self._progress.update(
                    int(task_id),
                    status=f"[red]{message}[/red]",
                )
            except (ValueError, TypeError):
                pass
        else:
            logger.error(f"Task {task_id} failed: {message}")

    def print(self, message: str) -> None:
        """Print a message outside the progress display."""
        if self._console:
            self._console.print(message)
        else:
            logger.info(message)

    def print_summary(self, stats: dict) -> None:
        """
        Print a formatted summary table of pipeline statistics.

        Args:
            stats: Dict with stats to display (typically from Database.get_stats())
        """
        try:
            from rich.console import Console
            from rich.table import Table
            from rich import box

            console = self._console or Console()

            console.print("\n")
            console.print("[bold green]Spectral-IAM Pipeline Summary[/bold green]")
            console.print("=" * 60)

            # Total pairs table
            total_table = Table(
                title="Overall Statistics",
                box=box.ROUNDED,
                show_header=True,
                header_style="bold cyan",
            )
            total_table.add_column("Metric", style="bold")
            total_table.add_column("Value", justify="right")

            total_table.add_row("Total Final Pairs", str(stats.get("total_final_pairs", 0)))
            total_table.add_row("Total Candidate Pairs", str(stats.get("total_candidate_pairs", 0)))
            total_table.add_row("Total Sources", str(stats.get("total_sources", 0)))

            quality = stats.get("quality_scores", {})
            total_table.add_row(
                "Avg Quality Score",
                f"{quality.get('avg', 0):.4f}",
            )
            total_table.add_row(
                "Min Quality Score",
                f"{quality.get('min', 0):.4f}",
            )
            total_table.add_row(
                "Max Quality Score",
                f"{quality.get('max', 0):.4f}",
            )

            console.print(total_table)

            # Domain breakdown
            pairs_by_domain = stats.get("pairs_by_domain", {})
            if pairs_by_domain:
                domain_table = Table(
                    title="Pairs by Domain",
                    box=box.ROUNDED,
                    show_header=True,
                    header_style="bold cyan",
                )
                domain_table.add_column("Domain", style="bold")
                domain_table.add_column("Pairs", justify="right")

                for domain, count in sorted(
                    pairs_by_domain.items(), key=lambda x: x[1], reverse=True
                ):
                    domain_table.add_row(domain, str(count))

                console.print(domain_table)

            # Pipeline breakdown
            pairs_by_pipeline = stats.get("pairs_by_pipeline", {})
            if pairs_by_pipeline:
                pipeline_table = Table(
                    title="Pairs by Pipeline",
                    box=box.ROUNDED,
                    show_header=True,
                    header_style="bold cyan",
                )
                pipeline_table.add_column("Pipeline", style="bold")
                pipeline_table.add_column("Pairs", justify="right")

                for pipeline, count in sorted(
                    pairs_by_pipeline.items(), key=lambda x: x[1], reverse=True
                ):
                    pipeline_table.add_row(pipeline, str(count))

                console.print(pipeline_table)

            # Recent runs
            recent_runs = stats.get("recent_runs", [])
            if recent_runs:
                runs_table = Table(
                    title="Recent Pipeline Runs",
                    box=box.ROUNDED,
                    show_header=True,
                    header_style="bold cyan",
                )
                runs_table.add_column("Pipeline")
                runs_table.add_column("Started")
                runs_table.add_column("Generated", justify="right")
                runs_table.add_column("Accepted", justify="right")
                runs_table.add_column("Rejected", justify="right")
                runs_table.add_column("Status")

                for run in recent_runs[:5]:
                    status = "OK" if not run.get("error") else f"ERROR: {run['error'][:30]}"
                    runs_table.add_row(
                        run.get("pipeline_id", ""),
                        (run.get("started_at", "")[:16] if run.get("started_at") else ""),
                        str(run.get("pairs_generated", 0)),
                        str(run.get("pairs_accepted", 0)),
                        str(run.get("pairs_rejected", 0)),
                        status,
                    )

                console.print(runs_table)

        except ImportError:
            # Plain text fallback
            logger.info("Pipeline Summary:")
            logger.info(f"  Total final pairs: {stats.get('total_final_pairs', 0)}")
            logger.info(f"  Total sources: {stats.get('total_sources', 0)}")
            for domain, count in stats.get("pairs_by_domain", {}).items():
                logger.info(f"  {domain}: {count} pairs")
