import asyncio
import importlib.util
import os
from pathlib import Path

import pytest

spec = importlib.util.spec_from_file_location('downloader', str(Path(__file__).parents[1] / 'src' / 'downloader.py'))
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)

sha256_bytes = mod.sha256_bytes
save_bytes_to_file = mod.save_bytes_to_file


def test_sha256():
    data = b'hello'
    h = sha256_bytes(data)
    assert len(h) == 64


@pytest.mark.asyncio
async def test_save(tmp_path):
    p = tmp_path / 'out.bin'
    path = await save_bytes_to_file(b'abc', str(p))
    assert os.path.exists(path)
