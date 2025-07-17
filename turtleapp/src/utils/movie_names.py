import os
import re


def clean_movie_filename(filename: str) -> str:
    name_without_ext = os.path.splitext(filename)[0]
    clean = re.sub(r'[^a-zA-Z0-9\s]', '', name_without_ext)
    return re.sub(r'^(.{5}.*?\d{4}).*|^(.{30}).*', r'\1\2', clean)

