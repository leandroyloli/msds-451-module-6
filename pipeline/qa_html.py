"""Confere o HTML local no desktop e no celular, sem servidor ou publicação."""
from pathlib import Path
from urllib.parse import unquote, urlsplit
import argparse
import hashlib
import json

from playwright.sync_api import sync_playwright


def run(root):
    root = Path(root).resolve()
    report = root / "report/checkpoint-b.html"
    out = root / "output/qa"
    out.mkdir(parents=True, exist_ok=True)
    records = []
    with sync_playwright() as p:
        browser = p.chromium.launch(
            executable_path=r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
            headless=True,
        )
        for width, height, label in [(1280, 1000, "desktop"), (390, 844, "mobile")]:
            page = browser.new_page(viewport={"width": width, "height": height}, device_scale_factor=1)
            errors = []
            page.on("pageerror", lambda error: errors.append(str(error)))
            page.goto(report.as_uri(), wait_until="load")
            assert page.locator("html").get_attribute("lang") == "en"
            ids = page.locator("[id]").evaluate_all("els => els.map(e => e.id)")
            assert len(ids) == len(set(ids)), "Há IDs duplicados no HTML/SVG"
            figures = page.locator("figure svg").evaluate_all(
                "els => els.map(e => ({width:e.getBoundingClientRect().width,height:e.getBoundingClientRect().height}))"
            )
            assert len(figures) == 3 and all(f["width"] > 0 and f["height"] > 0 for f in figures)
            equations = page.locator(".equation svg")
            assert equations.count() == 4
            page.locator(".math").screenshot(path=str(out / f"{label}-equation.png"))
            assert not page.evaluate("document.documentElement.scrollWidth > innerWidth"), label
            links = page.locator("a[href]").evaluate_all("els => els.map(e => e.getAttribute('href'))")
            local_count = 0
            for href in links:
                parsed = urlsplit(href)
                if parsed.scheme or parsed.netloc:
                    continue
                if parsed.path:
                    target = (report.parent / unquote(parsed.path)).resolve()
                    assert target.exists(), f"Link local ausente: {href}"
                    local_count += 1
                elif parsed.fragment:
                    assert unquote(parsed.fragment) in ids, f"Âncora ausente: {href}"
            page.screenshot(path=str(out / f"{label}-inicio.png"))
            for section in ["results", "conclusions"]:
                page.locator("#" + section).scroll_into_view_if_needed()
                page.screenshot(path=str(out / f"{label}-{section}.png"))
            catalog = page.locator("#data details").first
            catalog.locator("summary").click()
            count = catalog.locator("table tbody tr").count()
            assert count == 61, count
            assert not page.evaluate("document.documentElement.scrollWidth > innerWidth"), (label, "catálogo")
            assert not errors, errors
            records.append(dict(viewport=label, width=width, figures=len(figures), typeset_equations=4, candidate_rows=count,
                                local_links=local_count, duplicate_ids=False, horizontal_overflow=False,
                                javascript_errors=errors))
            page.close()
        browser.close()
    payload = dict(passed=True, html_sha256=hashlib.sha256(report.read_bytes()).hexdigest(), checks=records)
    (out / "visual-checks.json").write_text(json.dumps(payload, indent=2, ensure_ascii=False), encoding="utf-8")
    print(json.dumps(payload, ensure_ascii=False))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--root", required=True)
    run(parser.parse_args().root)
