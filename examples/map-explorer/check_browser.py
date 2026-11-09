"""Optional local Playwright display/navigation check; no browser dependency in the map tools."""
import argparse
import json
from pathlib import Path


def check(packet, out, browser):
    from playwright.sync_api import sync_playwright
    packet, out = Path(packet).resolve(), Path(out).resolve()
    out.mkdir(parents=True, exist_ok=False)
    results = []
    with sync_playwright() as p:
        b = p.chromium.launch(executable_path=browser, headless=True)
        for width in (1500, 420):
            page = b.new_page(viewport={'width': width, 'height': 950})
            errors, requests = [], []
            page.on('pageerror', lambda error: errors.append(str(error)))
            page.on('request', lambda request: requests.append(request.url))
            page.goto((packet / 'index.html').as_uri())
            page.locator('#detail h2').first.wait_for()
            assert page.locator('#detail').inner_text().strip()
            page.screenshot(path=str(out / f'{width}-initial.png'))
            page.locator('#search').fill('P-101')
            buttons = page.locator('#items button').all_text_contents()
            if any('S1/P2/300/P-101' in x for x in buttons):
                page.locator('#items').get_by_role('button', name='P-101 · S1/P2/300/P-101', exact=True).click()
                assert 'S1/P2/300/P-101' in page.locator('#detail').inner_text()
                page.locator('#items').get_by_role('button', name='P-101 · S1/P1/200/P-101', exact=True).click()
                assert '45 m3/h' in page.locator('#detail').inner_text()
                page.locator('#detail').get_by_role('button', name='V-204 · S1/P1/200/V-204', exact=True).first.click()
                assert page.locator('#detail h2').first.inner_text() == 'V-204'
            if page.locator('#snapshot option').count() == 2:
                page.locator('#search').fill('TT-2208')
                page.locator('#items').get_by_role('button', name='TT-2208 · S1/P1/PAST1/TT-2208', exact=True).click()
                page.locator('#snapshot').select_option('previous')
                assert 'absent in this snapshot' in page.locator('#detail').inner_text()
                page.locator('#snapshot').select_option('current')
                assert page.locator('#detail h2').first.inner_text() == 'TT-2208'
            dimensions = page.evaluate('({width:innerWidth,scroll:document.documentElement.scrollWidth})')
            assert dimensions['scroll'] <= dimensions['width'], dimensions
            assert not errors, errors
            assert not any(x.startswith(('http:', 'https:')) for x in requests), requests
            page.screenshot(path=str(out / f'{width}.png'), full_page=True)
            results.append({'browser': b.version, 'viewport': dimensions, 'page_errors': errors,
                            'requests': requests, 'matching_P101_buttons': buttons,
                            'headings': page.locator('h2').all_text_contents()})
            page.close()
        b.close()
    (out / 'VISUAL-QA.json').write_text(json.dumps(results, indent=2) + '\n', encoding='utf-8', newline='\n')


if __name__ == '__main__':
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument('--packet', required=True)
    p.add_argument('--out', required=True)
    p.add_argument('--browser', required=True, help='installed Chromium/Edge executable')
    a = p.parse_args()
    check(a.packet, a.out, a.browser)
