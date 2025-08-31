import os
import re
from typing import Dict, List

import httpx
from duckduckgo_search import ddg


def _extract_pdfs_from_struct(item) -> List[Dict]:
    out = []
    try:
        txt = str(item)
        for m in re.findall(r"(https?://[^\s'\"]+\.pdf)", txt, flags=re.IGNORECASE):
            out.append({'title': '', 'url': m, 'snippet': ''})
    except Exception:
        pass
    return out


def search_pdfs(query: str, max_results: int = 20) -> List[Dict]:
    """Search the web for PDFs matching the query.

    If the environment variable `SERPAPI_API_KEY` is set, use SerpAPI (Google engine) to get structured
    results. Otherwise fall back to DuckDuckGo via `duckduckgo-search`.

    Returns a list of dicts with keys: 'title', 'url', 'snippet'.
    """
    key = os.getenv('SERPAPI_API_KEY')
    q = f"{query} filetype:pdf"
    out: List[Dict] = []

    if key:
        try:
            params = {
                'engine': 'google',
                'q': q,
                'api_key': key,
                'num': max_results,
            }
            resp = httpx.get('https://serpapi.com/search.json', params=params, timeout=20.0)
            resp.raise_for_status()
            j = resp.json()
            for r in j.get('organic_results', []) or []:
                link = r.get('link') or r.get('serpapi_link') or r.get('displayed_link')
                title = r.get('title') or ''
                snippet = r.get('snippet') or ''
                if link and link.lower().endswith('.pdf'):
                    out.append({'title': title, 'url': link, 'snippet': snippet})
                    continue
                # try to extract any pdf urls inside the result structure
                out.extend(_extract_pdfs_from_struct(r))
            # as a last resort scan other fields
            if not out:
                for field in ('related_results', 'related_questions', 'inline_links'):
                    for part in j.get(field, []) or []:
                        out.extend(_extract_pdfs_from_struct(part))
            if out:
                return out
        except Exception:
            # fallback to duckduckgo below
            pass

    # fallback to duckduckgo
    results = ddg(q, max_results=max_results) or []
    for r in results:
        url = r.get('href') or r.get('url') or r.get('link')
        title = r.get('title') or ''
        snippet = r.get('body') or r.get('snippet') or ''
        if url and url.lower().endswith('.pdf'):
            out.append({'title': title, 'url': url, 'snippet': snippet})
        else:
            out.extend(_extract_pdfs_from_struct(r))

    # dedupe by url preserving order
    seen = set()
    deduped = []
    for item in out:
        u = item.get('url')
        if not u or u in seen:
            continue
        seen.add(u)
        deduped.append(item)
    return deduped
