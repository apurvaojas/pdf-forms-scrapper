import os
from typing import List

from dotenv import load_dotenv


def generate_queries(topics: List[str]) -> List[str]:
    """Generate search queries for given topical areas.

    Loads `OPENAI_API_KEY` from `.env` automatically (via python-dotenv) and, if present,
    uses OpenAI to paraphrase and expand queries. Otherwise falls back to deterministic templates.
    """
    # ensure environment variables from .env are loaded
    load_dotenv()
    OPENAI_KEY = os.getenv('OPENAI_API_KEY')
    """Generate search queries for given topical areas.

    If OPENAI_API_KEY is set, use OpenAI to paraphrase and expand queries; otherwise use deterministic templates.
    """
    templates = [
        '{topic} filetype:pdf "application form"',
        '{topic} filetype:pdf "application"',
        '{topic} filetype:pdf "form"',
        '{topic} filetype:pdf "claim form"',
    ]
    out = []
    if OPENAI_KEY:
        try:
            import openai
            openai.api_key = OPENAI_KEY
            prompt = 'Generate 8 concise search queries for finding PDF forms online for these topics: ' + ', '.join(topics)
            # use a stable chat model name; if unavailable, the API will raise and we fallback
            resp = openai.ChatCompletion.create(model='gpt-3.5-turbo', messages=[{'role':'user','content':prompt}], max_tokens=300)
            # OpenAI response parsing
            text = resp.choices[0].message.content if hasattr(resp.choices[0], 'message') else resp.choices[0].text
            # crude split
            for line in text.splitlines():
                line = line.strip('- ').strip()
                if 'filetype:pdf' in line.lower():
                    out.append(line)
            if out:
                return out
        except Exception:
            pass

    # fallback
    for t in topics:
        for tpl in templates:
            out.append(tpl.format(topic=t))
    # dedupe
    seen = set()
    res = []
    for q in out:
        if q not in seen:
            seen.add(q)
            res.append(q)
    return res
