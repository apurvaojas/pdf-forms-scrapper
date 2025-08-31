import asyncio
import hashlib
import os
from typing import Optional

import aiofiles
import httpx

DOWNLOAD_DIR = os.path.join(os.path.dirname(__file__), '..', 'downloads')
os.makedirs(DOWNLOAD_DIR, exist_ok=True)

async def fetch_pdf(client: httpx.AsyncClient, url: str) -> Optional[bytes]:
    try:
        resp = await client.get(url, follow_redirects=True, timeout=30.0)
        resp.raise_for_status()
        content_type = resp.headers.get('content-type', '')
        if 'pdf' not in content_type.lower() and not url.lower().endswith('.pdf'):
            return None
        return resp.content
    except Exception:
        return None

def sha256_bytes(b: bytes) -> str:
    return hashlib.sha256(b).hexdigest()

async def save_bytes_to_file(b: bytes, filename: str) -> str:
    path = os.path.abspath(filename)
    async with aiofiles.open(path, 'wb') as f:
        await f.write(b)
    return path

async def download_and_save(url: str, client: Optional[httpx.AsyncClient] = None) -> Optional[dict]:
    close_client = False
    if client is None:
        client = httpx.AsyncClient(http2=True)
        close_client = True
    try:
        data = await fetch_pdf(client, url)
        if not data:
            return None
        h = sha256_bytes(data)
        fname = f'{h[:16]}.pdf'
        out_path = os.path.join(DOWNLOAD_DIR, fname)
        if os.path.exists(out_path):
            size = os.path.getsize(out_path)
            return {'path': out_path, 'sha256': h, 'size': size, 'url': url, 'skipped': True}
        await save_bytes_to_file(data, out_path)
        size = os.path.getsize(out_path)
        return {'path': out_path, 'sha256': h, 'size': size, 'url': url, 'skipped': False}
    finally:
        if close_client:
            await client.aclose()

async def download_many(urls):
    async with httpx.AsyncClient(http2=True, timeout=30.0) as client:
        tasks = [download_and_save(u, client) for u in urls]
        return await asyncio.gather(*tasks)
