import os
import streamlit as st
import json
import numpy as np
from huggingface_hub import hf_hub_download, HfApi, RepoFile
import requests
import re
import pandas as pd
from typing import List, Optional

def extract_file_timestamp(filename):
    match = re.search(r'(\d{4}-\d{2}-\d{2}_\d{2}-\d{2}-\d{2})', filename)
    if match:
        return match.group(1)
    else:
        raise ValueError(f"Kein gültiger Timestamp im Dateinamen: {filename}")




def hf_download_all_contributing_rounds(
    repo_id: str,
    local_base_dir: str = "/tmp/AllContributingRounds",
) -> list[str]:
    """
    Lädt alle JSON-Dateien aus dem Ordner
    AllContributingRounds/ im Dataset herunter
    und speichert sie lokal zwischen.
    Rückgabe:
        Liste aller lokalen Dateipfade
    """

    api = HfApi()

    os.makedirs(local_base_dir, exist_ok=True)

    # Repo-Baum lesen
    tree = api.list_repo_tree(
        repo_id=repo_id,
        repo_type="dataset",
        recursive=True
    )

    downloaded_files = []


    for item in tree:
        if (
            isinstance(item, RepoFile)
            and item.path.startswith("AllContributingRounds/")
            and item.path.endswith(".json")
        ):
            local_path = hf_hub_download(
                repo_id=repo_id,
                repo_type="dataset",
                filename=item.path,
                local_dir=local_base_dir,
                local_dir_use_symlinks=False
            )
    
            downloaded_files.append(local_path)    


    return downloaded_files




def collect_all_json_files(base_dir: str) -> list[str]:
    files = []
    for root, _, filenames in os.walk(base_dir):
        for f in filenames:
            if f.endswith(".json"):
                files.append(os.path.join(root, f))
    return files

    


def hf_upload_file(
    repo_id: str,
    local_path: str,
    path_in_repo: str,
    hf_token: str,
    commit_message: str = "Upload via Space"
):
    if not os.path.exists(local_path):
        raise FileNotFoundError(f"Datei existiert nicht: {local_path}")

    if not os.path.isfile(local_path):
        raise ValueError(f"Pfad ist keine Datei: {local_path}")

    api = HfApi(token=hf_token)

    api.upload_file(
        path_or_fileobj=local_path,
        path_in_repo=path_in_repo,
        repo_id=repo_id,
        repo_type="dataset",
        commit_message=commit_message
    )

