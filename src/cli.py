import asyncio
import os
from urllib.parse import urlparse

from dotenv import load_dotenv

from .downloader import download_many
from .llm_query import generate_queries
from .metadata import init_db, insert_metadata
from .searcher import search_pdfs
from .storage import ensure_bucket, make_minio_client, upload_file


def heuristics_sector_from_url(url: str) -> str:
    dom = urlparse(url).netloc.lower()
    if dom.endswith('.gov') or '.gov.' in dom:
        return 'government'
    if 'health' in dom or 'hhs' in dom:
        return 'health'
    if 'edu' in dom:
        return 'education'
    return 'unknown'

async def run(query: str):
    init_db()
    results = search_pdfs(query, max_results=30)
    urls = [r['url'] for r in results]
    downloaded = await download_many(urls)
    for res, meta in zip(results, downloaded):
        if not meta:
            continue
        # if skipped and exists, still ensure metadata present
        filename = meta['path'].split('/')[-1]
        insert_metadata(filename=filename, url=res['url'], sha256=meta['sha256'], title=res.get('title',''),
                        sector=heuristics_sector_from_url(res['url']), size=meta.get('size', 0))


async def run_with_upload(query: str, minio_endpoint: str, minio_access: str, minio_secret: str, bucket: str):
    init_db()
    client = make_minio_client(minio_endpoint, minio_access, minio_secret)
    ensure_bucket(client, bucket)
    results = search_pdfs(query, max_results=30)
    urls = [r['url'] for r in results]
    downloaded = await download_many(urls)
    for res, meta in zip(results, downloaded):
        if not meta:
            continue
        filename = meta['path'].split('/')[-1]
        # upload
        ok = upload_file(client, bucket, filename, meta['path'])
        if ok:
            print(f'Uploaded {filename} to {bucket}')
        insert_metadata(filename=filename, url=res['url'], sha256=meta['sha256'], title=res.get('title',''),
                        sector=heuristics_sector_from_url(res['url']), size=meta.get('size', 0))

def main():
    # load environment variables from .env if present
    load_dotenv()
    import argparse
    p = argparse.ArgumentParser()
    p.add_argument('query', nargs='?')
    p.add_argument('--smart', action='store_true', help='Use LLM to generate multiple search queries for the target topics')
    p.add_argument('--limit', type=int, default=1000, help='Max number of PDFs to download')
    p.add_argument('--minio-endpoint')
    p.add_argument('--minio-access')
    p.add_argument('--minio-secret')
    p.add_argument('--minio-bucket')
    args = p.parse_args()
    if args.smart:
        # generate queries for multiple topics
        topics = [
            'finance sector account opening form',
            'insurance claim form',
            'income tax return form',
            'marriage certificate application form',
            'caste certificate application form',
            'income certificate application form',
            'birth certificate application form',
            'death certificate application form',
            'PAN card application form',
            'voter ID application form',
            'driving license application form',
            'passport application form',
            'Aadhaar card application form',
            'loan application form',
            'student visa application form',
            'work visa application form',
            'residency permit application form',
            'social security application form',
            'disability certificate application form',
            'unemployment benefits application form',
            'food security application form',
            'health insurance application form',
            'child care application form',
        ]
        queries = generate_queries(topics)
        print('Generated queries:', len(queries))
        # aggregate results
        seen_urls = []
        for q in queries:
            print('Searching:', q)
            res = search_pdfs(q, max_results=20)
            for r in res:
                u = r.get('url')
                if u and u not in seen_urls:
                    seen_urls.append(u)
                if len(seen_urls) >= args.limit:
                    break
            if len(seen_urls) >= args.limit:
                break

        print('Total candidate PDF URLs:', len(seen_urls))
        # download aggregated list
        if args.minio_endpoint and args.minio_access and args.minio_secret and args.minio_bucket:
            # upload path
            asyncio.run(run_with_upload_batch(seen_urls, args.minio_endpoint, args.minio_access, args.minio_secret, args.minio_bucket))
        else:
            asyncio.run(run_batch(seen_urls))
    else:
        if args.minio_endpoint and args.minio_access and args.minio_secret and args.minio_bucket:
            asyncio.run(run_with_upload(args.query, args.minio_endpoint, args.minio_access, args.minio_secret, args.minio_bucket))
        else:
            asyncio.run(run(args.query))


async def run_batch(urls):
    init_db()
    downloaded = await download_many(urls)
    for url, meta in zip(urls, downloaded):
        if not meta:
            continue
        filename = meta['path'].split('/')[-1]
        insert_metadata(filename=filename, url=url, sha256=meta['sha256'], title='', sector=heuristics_sector_from_url(url), size=meta.get('size', 0))


async def run_with_upload_batch(urls, minio_endpoint, minio_access, minio_secret, bucket):
    init_db()
    client = make_minio_client(minio_endpoint, minio_access, minio_secret)
    ensure_bucket(client, bucket)
    downloaded = await download_many(urls)
    for url, meta in zip(urls, downloaded):
        if not meta:
            continue
        filename = meta['path'].split('/')[-1]
        ok = upload_file(client, bucket, filename, meta['path'])
        if ok:
            print(f'Uploaded {filename} to {bucket}')
        insert_metadata(filename=filename, url=url, sha256=meta['sha256'], title='', sector=heuristics_sector_from_url(url), size=meta.get('size', 0))

if __name__ == '__main__':
    main()
