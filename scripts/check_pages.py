"""Check the published HTML and crawl graph before uploading the Pages build."""

import argparse
import re
from html.parser import HTMLParser
from pathlib import Path
from urllib.parse import urljoin, urlsplit
from xml.etree import ElementTree

from backend.server import PAGES, PRIVATE_PAGES

SITE = "https://5bmath.vn/"


class PageHTML(HTMLParser):
    def __init__(self, html):
        super().__init__()
        self.links = []
        self.canonicals = []
        self.meta = {}
        self.base = ""
        self.route = None
        self.grading = None
        self.feed(html)

    def handle_starttag(self, tag, attributes):
        attrs = dict(attributes)
        if tag == "a" and "href" in attrs:
            self.links.append(attrs["href"])
        elif tag == "base":
            self.base = attrs["href"]
        elif tag == "link" and attrs.get("rel") == "canonical":
            self.canonicals.append(attrs["href"])
        elif tag == "meta" and "name" in attrs:
            self.meta[attrs["name"]] = attrs["content"]
        elif tag == "html":
            self.route = attrs.get("data-page")
            self.grading = attrs.get("data-grading")


def check(output, target):
    routes = {"/": "home", **PAGES}
    titles = set()
    descriptions = set()
    graph = {}
    public = {route for route, name in routes.items() if name not in PRIVATE_PAGES}
    mount = "/5b" if target == "github" else ""
    for route, name in routes.items():
        html = (output / route.strip("/") / "index.html").read_text(encoding="utf-8")
        page = PageHTML(html)
        assert page.route == name and page.grading == ("server" if target in ("python", "cloudflare-live") else "browser"), route
        main = re.search(r'<main id="app">([\s\S]*?)</main>', html)
        assert main and len(re.findall(r"<h1\b", main[1])) == 1, route
        if route not in public:
            assert page.meta.get("robots") == "noindex" and not page.canonicals, route
            continue
        assert page.canonicals == [urljoin(SITE, route)], route
        assert "noindex" not in page.meta.get("robots", ""), route
        title = re.search(r"<title>([^<]+)</title>", html)[1]
        description = page.meta["description"]
        assert title not in titles and description and description not in descriptions, route
        titles.add(title)
        descriptions.add(description)

        url = "https://test.invalid" + mount + route
        base = urljoin(url, page.base)
        graph[route] = set()
        for href in page.links:
            link = urlsplit(urljoin(base, href))
            if link.netloc == "test.invalid":
                assert link.path.startswith(mount + "/"), (route, href)
                destination = link.path.removeprefix(mount)
                assert destination in routes, (route, href)
                if destination in public:
                    graph[route].add(destination)

    found = {"/"}
    pending = ["/"]
    while pending:
        destinations = graph[pending.pop()] - found
        found.update(destinations)
        pending.extend(destinations)
    assert found == public, f"Unlinked pages: {public - found}"

    error = PageHTML((output / "404.html").read_text(encoding="utf-8"))
    assert error.meta.get("robots") == "noindex"
    assert mount + "/" in error.links
    if target != "github":
        robots = (output / "robots.txt").read_text(encoding="utf-8")
        assert "Sitemap: " + SITE + "sitemap.xml" in robots
        sitemap = ElementTree.parse(output / "sitemap.xml")
        locations = [node.text for node in sitemap.findall("{*}url/{*}loc")]
        assert len(locations) == len(public)
        assert set(locations) == {urljoin(SITE, route) for route in public}
    print(f"{target}: {len(public)} crawlable pages, canonical URLs and 404 verified")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("output", type=Path)
    parser.add_argument("target", choices=["cloudflare", "github", "python", "cloudflare-live"], nargs="?", default="cloudflare")
    args = parser.parse_args()
    check(args.output, args.target)
