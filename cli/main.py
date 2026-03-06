import typer
from rich.console import Console
from rich.table import Table

from app.services.downloader import ReleaseDownloader
from app.services.scraper import RIScraper

app = typer.Typer(name="smo-intel", help="SMO Intelligence CLI")
db_app = typer.Typer(name="db", help="Comandos de banco de dados")
app.add_typer(db_app, name="db")

console = Console()
scraper = RIScraper()


@app.command()
def download(
    grupo: str = typer.Option(None, "--grupo", "-g", help="Chave do grupo (ex: multiplan)"),
    forcar: bool = typer.Option(False, "--forcar", "-f", help="Forçar re-download"),
):
    """Baixa releases de resultados trimestrais."""
    downloader = ReleaseDownloader()
    grupos = [grupo] if grupo else scraper.listar_todos_os_grupos()

    for g in grupos:
        console.print(f"\n[bold blue]Baixando releases de {g}...[/bold blue]")
        resultado = downloader.baixar_grupo(g, forcar=forcar)

        table = Table(title=f"Resultado — {g}")
        table.add_column("Status", style="bold")
        table.add_column("Quantidade", justify="right")
        table.add_row("[green]OK[/green]", str(resultado["ok"]))
        table.add_row("[yellow]Já existe[/yellow]", str(resultado["ja_existe"]))
        table.add_row("[red]Erro[/red]", str(resultado["erro"]))
        table.add_row("[magenta]Inválido[/magenta]", str(resultado["invalido"]))
        table.add_row("[bold]Total[/bold]", str(resultado["total"]))
        console.print(table)


@app.command()
def listar(
    grupo: str = typer.Option(None, "--grupo", "-g", help="Chave do grupo"),
):
    """Lista releases disponíveis (dry-run, sem download)."""
    grupos = [grupo] if grupo else scraper.listar_todos_os_grupos()

    for g in grupos:
        releases = scraper.descobrir_releases(g)
        config = scraper.GRUPOS_CONFIG.get(g, {})

        table = Table(title=f"Releases — {config.get('nome', g)} ({config.get('ticker', '')})")
        table.add_column("#", justify="right", style="dim")
        table.add_column("Trimestre")
        table.add_column("Fonte")
        table.add_column("URL", max_width=80)

        for i, r in enumerate(releases, 1):
            tri = f"{r.get('trimestre', '?')}T{r.get('ano', '?')}"
            table.add_row(str(i), tri, r.get("fonte", ""), r["url"])

        console.print(table)
        console.print(f"Total: {len(releases)} releases\n")


@app.command()
def relatorio():
    """Exibe relatório de cobertura de downloads."""
    downloader = ReleaseDownloader()
    rel = downloader.manifesto.relatorio()

    table = Table(title="Relatório de Downloads")
    table.add_column("Métrica", style="bold")
    table.add_column("Valor", justify="right")
    table.add_row("[green]OK[/green]", str(rel["ok"]))
    table.add_row("[yellow]Já existe[/yellow]", str(rel["ja_existe"]))
    table.add_row("[red]Erro[/red]", str(rel["erro"]))
    table.add_row("[magenta]Inválido[/magenta]", str(rel["invalido"]))
    table.add_row("[bold]Total[/bold]", str(rel["total"]))
    console.print(table)


@db_app.command("seed")
def db_seed():
    """Popula dados iniciais no banco."""
    import asyncio
    from scripts.seed_db import seed

    console.print("[bold blue]Populando banco de dados...[/bold blue]")
    asyncio.run(seed())
    console.print("[bold green]Seed concluído![/bold green]")


@db_app.command("migrate")
def db_migrate():
    """Roda alembic upgrade head."""
    import subprocess

    console.print("[bold blue]Rodando migrations...[/bold blue]")
    result = subprocess.run(["alembic", "upgrade", "head"], capture_output=True, text=True)
    console.print(result.stdout)
    if result.returncode != 0:
        console.print(f"[bold red]Erro:[/bold red] {result.stderr}")
    else:
        console.print("[bold green]Migrations aplicadas![/bold green]")


if __name__ == "__main__":
    app()
