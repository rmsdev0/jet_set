from __future__ import annotations

import asyncio
import csv
from pathlib import Path
from typing import Optional

import typer
from sqlalchemy import func, select

from app.db import AsyncSessionLocal
from app.models import Prospect


app = typer.Typer(help="Lodge acquisition tooling.")
outreach_app = typer.Typer(help="Outreach sequence operations.")
prospects_app = typer.Typer(help="Prospect list and export operations.")
app.add_typer(outreach_app, name="outreach")
app.add_typer(prospects_app, name="prospects")


def run_async(coro):
    return asyncio.run(coro)


@app.command()
def discover(region: str = typer.Option(...), sport: str = typer.Option(...), source: str = typer.Option("all")) -> None:
    typer.echo(f"Discovery scaffold ready for region={region} sport={sport} source={source}")


@app.command()
def scrape(prospect_id: Optional[str] = typer.Option(None), batch: bool = typer.Option(False), limit: int = 20) -> None:
    typer.echo(f"Scrape scaffold ready prospect_id={prospect_id} batch={batch} limit={limit}")


@app.command()
def enrich(prospect_id: Optional[str] = typer.Option(None), batch: bool = typer.Option(False), limit: int = 50) -> None:
    typer.echo(f"Enrichment scaffold ready prospect_id={prospect_id} batch={batch} limit={limit}")


@app.command("generate-profile")
def generate_profile(prospect_id: Optional[str] = typer.Option(None), batch: bool = typer.Option(False)) -> None:
    typer.echo(f"Profile generation scaffold ready prospect_id={prospect_id} batch={batch}")


@outreach_app.command("send")
def outreach_send(prospect_id: Optional[str] = typer.Option(None), template: str = typer.Option("email_1")) -> None:
    typer.echo(f"Outreach send scaffold ready prospect_id={prospect_id} template={template}")


@outreach_app.command("advance")
def outreach_advance() -> None:
    typer.echo("Outreach advancement scaffold ready")


@outreach_app.command("status")
def outreach_status() -> None:
    typer.echo("Outreach status scaffold ready")


@outreach_app.command("hot-leads")
def hot_leads(format: str = typer.Option("csv")) -> None:
    typer.echo(f"Hot leads scaffold ready format={format}")


@prospects_app.command("list")
def prospects_list(region: Optional[str] = typer.Option(None), status: Optional[str] = typer.Option(None)) -> None:
    run_async(_prospects_list(region, status))


@prospects_app.command("export")
def prospects_export(path: str = typer.Option("prospects.csv"), region: Optional[str] = typer.Option(None)) -> None:
    run_async(_prospects_export(Path(path), region))


@app.command()
def stats() -> None:
    run_async(_stats())


async def _prospects_list(region: Optional[str], status: Optional[str]) -> None:
    async with AsyncSessionLocal() as db:
        query = select(Prospect).order_by(Prospect.created_at.desc()).limit(50)
        if region:
            query = query.where(Prospect.region.ilike(f"%{region}%"))
        if status:
            query = query.where(Prospect.outreach_status == status)
        items = list((await db.execute(query)).scalars().all())
        for item in items:
            typer.echo(f"{item.id} | {item.name} | {item.region} | {item.outreach_status.value}")


async def _prospects_export(path: Path, region: Optional[str]) -> None:
    async with AsyncSessionLocal() as db:
        query = select(Prospect).order_by(Prospect.created_at.desc())
        if region:
            query = query.where(Prospect.region.ilike(f"%{region}%"))
        items = list((await db.execute(query)).scalars().all())
        with path.open("w", newline="") as handle:
            writer = csv.writer(handle)
            writer.writerow(["id", "name", "region", "country", "website_url", "contact_email"])
            for item in items:
                writer.writerow([item.id, item.name, item.region, item.country, item.website_url, item.contact_email])
        typer.echo(f"Exported {len(items)} prospects to {path}")


async def _stats() -> None:
    async with AsyncSessionLocal() as db:
        total = await db.scalar(select(func.count(Prospect.id)))
        typer.echo(f"Prospects: {int(total or 0)}")
