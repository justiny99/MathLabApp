from backend.ingest.crawl import crawl_url

def test_crawl_url():
    url = "https://web.archive.org/web/20230210115222/https://realnotcomplex.com/"
    result = crawl_url(url)