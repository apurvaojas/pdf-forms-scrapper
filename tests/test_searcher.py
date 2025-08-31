import importlib.util
import sys
from pathlib import Path

spec = importlib.util.spec_from_file_location('searcher', str(Path(__file__).parents[1] / 'src' / 'searcher.py'))
mod = importlib.util.module_from_spec(spec)
spec.loader.exec_module(mod)


def test_search_pdfs_no_crash():
    res = mod.search_pdfs('site:.gov application form', max_results=5)
    assert isinstance(res, list)
