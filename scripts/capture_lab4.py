"""Optional browser proof: uv run --no-project --with playwright python scripts/capture_lab4.py.

Uses the installed Microsoft Edge browser; the operational stack must be running.
"""
import json
from pathlib import Path

from playwright.sync_api import sync_playwright

root = Path(__file__).resolve().parents[1]
out = root / 'reports' / 'lab4'
out.mkdir(parents=True, exist_ok=True)
with sync_playwright() as browser_tools:
    browser = browser_tools.chromium.launch(channel='msedge', headless=True)
    page = browser.new_page(viewport={'width': 1100, 'height': 900}, device_scale_factor=1)
    page.goto('http://127.0.0.1:8501/', wait_until='networkidle')
    page.locator('input[type=file]').set_input_files(root / 'data_preview' / 'class_0.jpg')
    page.get_by_role('button', name='Analyser la photo').click()
    page.get_by_text('Catégorie :', exact=False).wait_for(timeout=60000)
    result = page.get_by_text('Catégorie :', exact=False).inner_text()
    page.screenshot(path=str(out / 'frontend-demo.png'), full_page=True)
    (out / 'browser.json').write_text(json.dumps({'url': page.url, 'uploaded': 'class_0.jpg',
                                                 'result': result, 'browser': 'Microsoft Edge'}, indent=2), encoding='utf-8')
    print(result)
    browser.close()
