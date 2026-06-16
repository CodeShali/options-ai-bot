"""Spectral-IAM Training Pipeline CLI."""

import asyncio
import logging
import sys
from pathlib import Path
from typing import Optional

import typer
from rich.console import Console
from rich.logging import RichHandler

app = typer.Typer(
    name="spectral",
    help="Spectral-IAM: Multi-source training data pipeline for IAM AI model",
    no_args_is_help=True,
)
console = Console()


def setup_logging(log_level: str = "INFO") -> None:
    """Configure rich logging."""
    logging.basicConfig(
        level=getattr(logging, log_level.upper(), logging.INFO),
        format="%(message)s",
        datefmt="[%X]",
        handlers=[RichHandler(console=console, rich_tracebacks=True)],
    )


def get_runner():
    """Build and return a PipelineRunner with all dependencies."""
    from pipelines.shared.claude_client import ClaudeClient
    from pipelines.shared.dedup import SemanticDedup
    from pipelines.shared.quality_filter import QualityFilter
    from storage.db import Database
    from storage.jsonl_writer import JSONLWriter
    from orchestrator.pipeline_runner import PipelineRunner
    from config.settings import settings

    db = Database(settings.db_path)

    async def _init_db():
        await db.initialize()

    asyncio.run(_init_db())

    claude = ClaudeClient()
    dedup = SemanticDedup()
    quality = QualityFilter()
    writer = JSONLWriter()

    return PipelineRunner(claude, dedup, quality, writer, db), db


@app.command("fetch-rfcs")
def fetch_rfcs(
    rfc_ids: list[str] = typer.Argument(..., help="RFC IDs to fetch (e.g. RFC4511 RFC6749)"),
    log_level: str = typer.Option("INFO", "--log-level", "-l", help="Log level"),
):
    """Fetch RFC documents and generate training pairs from them."""
    setup_logging(log_level)

    async def run():
        runner, db = get_runner()
        try:
            console.print(f"[bold cyan]Fetching {len(rfc_ids)} RFCs...[/bold cyan]")
            accepted = await runner.run_p1_rfcs(rfc_ids)
            console.print(f"[bold green]Done! Accepted {accepted} training pairs.[/bold green]")
            return accepted
        finally:
            await db.close()

    result = asyncio.run(run())
    raise typer.Exit(0 if result >= 0 else 1)


@app.command("scrape-vendor")
def scrape_vendor(
    vendor: str = typer.Argument(..., help="Vendor name (e.g. 'Okta')"),
    start_url: str = typer.Argument(..., help="Starting URL for crawl"),
    domain: str = typer.Argument(..., help="IAM domain (e.g. 'okta', 'ldap', 'oauth')"),
    product: Optional[str] = typer.Option(None, "--product", "-p", help="Product name"),
    max_depth: int = typer.Option(3, "--depth", "-d", help="Crawl depth"),
    path_prefix: str = typer.Option("/", "--prefix", help="URL path prefix to restrict crawl"),
    max_pages: int = typer.Option(50, "--max-pages", help="Maximum pages to crawl"),
    log_level: str = typer.Option("INFO", "--log-level", "-l"),
):
    """Crawl vendor documentation and generate training pairs."""
    setup_logging(log_level)

    async def run():
        from schemas.enums import Domain
        try:
            domain_enum = Domain(domain)
        except ValueError:
            console.print(f"[red]Invalid domain: {domain}[/red]")
            console.print(f"Valid domains: {[d.value for d in Domain]}")
            raise typer.Exit(1)

        runner, db = get_runner()
        try:
            console.print(f"[bold cyan]Crawling {vendor} docs from {start_url}...[/bold cyan]")
            accepted = await runner.run_p2_vendor(
                vendor_name=vendor,
                start_url=start_url,
                domain=domain_enum,
                product_name=product,
                max_depth=max_depth,
                allowed_path_prefix=path_prefix,
                max_pages=max_pages,
            )
            console.print(f"[bold green]Done! Accepted {accepted} training pairs.[/bold green]")
            return accepted
        finally:
            await db.close()

    asyncio.run(run())


@app.command("build-corpus")
def build_corpus(
    protocol: str = typer.Argument(
        ...,
        help="Protocol to build corpus for (currently: 'ldap')"
    ),
    n_per_subtopic: int = typer.Option(5, "--n", help="Pairs per subtopic"),
    log_level: str = typer.Option("INFO", "--log-level", "-l"),
):
    """Build a protocol corpus from the topic taxonomy."""
    setup_logging(log_level)

    async def run():
        runner, db = get_runner()
        try:
            if protocol.lower() == "ldap":
                console.print(
                    f"[bold cyan]Building LDAP corpus "
                    f"({n_per_subtopic} pairs per subtopic)...[/bold cyan]"
                )
                accepted = await runner.run_p3_ldap(n_per_subtopic=n_per_subtopic)
                console.print(
                    f"[bold green]Done! Accepted {accepted} LDAP training pairs.[/bold green]"
                )
            else:
                console.print(f"[red]Unknown protocol: {protocol}[/red]")
                console.print("Currently supported: ldap")
                raise typer.Exit(1)
            return accepted
        finally:
            await db.close()

    asyncio.run(run())


@app.command("synthetic-loop")
def synthetic_loop(
    domain: str = typer.Argument(..., help="IAM domain (e.g. 'oauth', 'ldap')"),
    count: int = typer.Argument(50, help="Number of pairs to generate"),
    difficulty: str = typer.Option("intermediate", "--difficulty", "-d"),
    log_level: str = typer.Option("INFO", "--log-level", "-l"),
):
    """Run the synthetic generation loop for a domain."""
    setup_logging(log_level)

    async def run():
        from schemas.enums import Domain
        try:
            Domain(domain)
        except ValueError:
            console.print(f"[red]Invalid domain: {domain}[/red]")
            from schemas.enums import Domain as D
            console.print(f"Valid: {[d.value for d in D]}")
            raise typer.Exit(1)

        runner, db = get_runner()
        try:
            console.print(
                f"[bold cyan]Running synthetic loop: {domain} × {count} pairs "
                f"(difficulty={difficulty})...[/bold cyan]"
            )
            accepted = await runner.run_p5_synthetic(
                domain=domain,
                count=count,
                difficulty=difficulty,
            )
            console.print(
                f"[bold green]Done! Accepted {accepted}/{count} synthetic pairs.[/bold green]"
            )
            return accepted
        finally:
            await db.close()

    asyncio.run(run())


@app.command("stackoverflow")
def stackoverflow(
    tags: list[str] = typer.Argument(..., help="Stack Overflow tags to fetch"),
    min_score: int = typer.Option(5, "--min-score", help="Minimum question score"),
    log_level: str = typer.Option("INFO", "--log-level", "-l"),
):
    """Fetch Stack Overflow IAM questions and convert to training pairs."""
    setup_logging(log_level)

    async def run():
        runner, db = get_runner()
        try:
            console.print(
                f"[bold cyan]Fetching Stack Overflow [{', '.join(tags)}]...[/bold cyan]"
            )
            accepted = await runner.run_p4_stackoverflow(
                tags=tags,
                min_score=min_score,
            )
            console.print(
                f"[bold green]Done! Accepted {accepted} training pairs.[/bold green]"
            )
            return accepted
        finally:
            await db.close()

    asyncio.run(run())


@app.command("week1-full")
def week1_full(
    log_level: str = typer.Option("INFO", "--log-level", "-l"),
):
    """Run the complete Week 1 pipeline (RFCs + LDAP corpus + SO + synthetic)."""
    setup_logging(log_level)

    async def run():
        from orchestrator.main import build_week1
        console.print(
            "[bold cyan]Starting Spectral-IAM Week 1 Pipeline...[/bold cyan]"
        )
        console.print("This will:")
        console.print("  • P1: Fetch 10 core RFCs (LDAP, OAuth 2.0, SCIM)")
        console.print("  • P3: Build LDAP corpus from topic taxonomy")
        console.print("  • P4: Fetch Stack Overflow IAM questions")
        console.print("  • P5: Run synthetic loop for OAuth (50 pairs)")
        console.print("")

        stats = await build_week1()

        console.print("\n[bold green]Week 1 Pipeline Complete![/bold green]")
        console.print(f"  P1 RFCs: {stats.get('p1_rfcs', 0)} pairs")
        console.print(f"  P3 LDAP: {stats.get('p3_ldap', 0)} pairs")
        console.print(f"  P4 SO:   {stats.get('p4_stackoverflow', 0)} pairs")
        console.print(f"  P5 Synth: {stats.get('p5_synthetic', 0)} pairs")

        db_stats = stats.get("db_stats", {})
        total = db_stats.get("total_final_pairs", 0)
        console.print(f"\n[bold]Total pairs in database: {total}[/bold]")

        from config.settings import settings
        full_jsonl = settings.processed_dir / "spectral_iam_full.jsonl"
        if full_jsonl.exists():
            line_count = sum(1 for _ in open(full_jsonl))
            console.print(f"[bold]Total pairs in JSONL: {line_count}[/bold]")

        return stats

    asyncio.run(run())


@app.command("report")
def report(
    log_level: str = typer.Option("INFO", "--log-level", "-l"),
):
    """Print a Rich report of pipeline statistics from the database."""
    setup_logging(log_level)

    async def run():
        from storage.db import Database
        from orchestrator.progress import PipelineProgress
        from config.settings import settings

        db = Database(settings.db_path)
        try:
            await db.initialize()
            stats = await db.get_stats()
        finally:
            await db.close()

        progress = PipelineProgress()
        progress.print_summary(stats)

        # Also show JSONL file sizes
        from config.settings import settings
        if settings.processed_dir.exists():
            console.print("\n[bold cyan]JSONL Output Files:[/bold cyan]")
            from rich.table import Table
            from rich import box
            table = Table(box=box.SIMPLE)
            table.add_column("File")
            table.add_column("Pairs", justify="right")
            table.add_column("Size")

            for f in sorted(settings.processed_dir.glob("*.jsonl")):
                try:
                    line_count = sum(1 for _ in open(f))
                    size_kb = f.stat().st_size / 1024
                    table.add_row(f.name, str(line_count), f"{size_kb:.1f} KB")
                except Exception:
                    table.add_row(f.name, "?", "?")

            console.print(table)

    asyncio.run(run())


@app.command("validate")
def validate(
    jsonl_file: Optional[str] = typer.Argument(None, help="JSONL file to validate"),
    log_level: str = typer.Option("INFO", "--log-level", "-l"),
):
    """Validate JSONL output files for schema compliance."""
    setup_logging(log_level)
    from config.settings import settings

    if jsonl_file:
        files = [Path(jsonl_file)]
    else:
        files = list(settings.processed_dir.glob("*.jsonl"))

    if not files:
        console.print("[yellow]No JSONL files found.[/yellow]")
        raise typer.Exit(0)

    total_valid = 0
    total_invalid = 0

    import json
    for f in files:
        valid = 0
        invalid = 0
        try:
            with open(f, "r", encoding="utf-8") as fp:
                for line_num, line in enumerate(fp, 1):
                    line = line.strip()
                    if not line:
                        continue
                    try:
                        record = json.loads(line)
                        # Basic validation
                        assert "id" in record
                        assert "domain" in record
                        assert "messages" in record
                        assert len(record["messages"]) == 3
                        valid += 1
                    except Exception as e:
                        console.print(
                            f"[red]Invalid record in {f.name} line {line_num}: {e}[/red]"
                        )
                        invalid += 1
        except Exception as e:
            console.print(f"[red]Error reading {f}: {e}[/red]")
            continue

        total_valid += valid
        total_invalid += invalid
        status = "[green]OK[/green]" if invalid == 0 else f"[red]{invalid} INVALID[/red]"
        console.print(f"{f.name}: {valid} valid, {status}")

    console.print(f"\nTotal: {total_valid} valid, {total_invalid} invalid")
    raise typer.Exit(0 if total_invalid == 0 else 1)


if __name__ == "__main__":
    app()
