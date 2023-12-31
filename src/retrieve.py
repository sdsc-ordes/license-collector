#!/usr/bin/env python
"""Download paperswithcode data, select and save usable projects."""

import requests
import gzip
import json
from pathlib import Path
import random
import re

from prefect import flow, task  # type: ignore

from config import Config, Location


@task
def download_paper_list(url: str, target_path: Path):
    """Download the list of projects from the PWC website"""
    response = requests.get(url, stream=True)
    with open(target_path, "wb") as f:
        for chunk in response.iter_content(chunk_size=1024):
            f.write(chunk)


@task
def read_papers(path: Path) -> list[dict]:
    """Read the paperswithcode from a gzipped json file"""
    with gzip.open(path, "r") as f:
        return json.load(f)


@task
def filter_papers(
        papers: list[dict],
        max_papers: int | None = None,
        exclude: set[str] | None = None
) -> list[dict]:
    """Filter papers to only include those with a GitHub or GitLab repo"""
    repo_pattern = re.compile(r"^https?://(www\.)?(github|gitlab)\.com/")
    
    if exclude is not None:
        papers = [paper for paper in papers if paper["repo_url"] not in exclude]
    if max_papers is not None:
        # Papers shuffled in place to avoid bias
        random.shuffle(papers)
        papers = papers[:max_papers]
    filtered = filter(lambda x: re.search(repo_pattern, x["repo_url"]), papers)
    return list(filtered)


@task
def save_papers(papers: list[dict], target_path: Path):
    """Save the filtered paperswithcode to a gzipped json file"""
    with gzip.open(str(target_path), "wt") as f:
        json.dump(papers, f)


@flow
def retrieve_flow(config: Config = Config(), location: Location = Location()):
    if not location.pwc_json.exists():
        download_paper_list(location.pwc_url, location.pwc_json)
    papers = read_papers(location.pwc_json)
    if location.exclude_list is None:
        exclude = None
    else:
        exclude = set([url.strip() for url in open(location.exclude_list)])
    papers = filter_papers(papers, max_papers=config.max_papers, exclude=exclude)
    save_papers(papers, location.pwc_filtered_json)


if __name__ == "__main__":
    retrieve_flow()
