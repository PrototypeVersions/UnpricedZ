"""Verify that Pages serves the exact display files just deployed."""
import hashlib
import sys
import time
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path


def verify(url, attempts=12):
    parsed = urllib.parse.urlsplit(url)
    if parsed.scheme != 'https' or parsed.hostname != 'prototypeversions.github.io':
        raise ValueError('Unexpected Pages publication URL')
    root = Path(__file__).resolve().parents[1] / 'site'
    expected = {name: hashlib.sha256((root / name).read_bytes()).hexdigest()
                for name in ['index.html', 'app.js', 'risk.js', 'guide.js', 'styles.css', 'data/risk.json', 'data/presentation.json', 'data/reader.json', 'reference/index.html', 'reference/docs/RISK_PROTOCOL.html']}
    pending = dict(expected)
    for attempt in range(attempts):
        for name, digest in list(pending.items()):
            resource = urllib.parse.urljoin(url.rstrip('/') + '/', name) + '?revision=' + digest[:16]
            try:
                request = urllib.request.Request(resource, headers={'Accept-Encoding': 'identity', 'User-Agent': 'UnpricedZ-site-check'})
                with urllib.request.urlopen(request, timeout=20) as response:
                    if hashlib.sha256(response.read()).hexdigest() == digest:
                        del pending[name]
            except (urllib.error.URLError, TimeoutError):
                pass
        if not pending:
            print('Verified live HTML, scripts, palette, forecasts, display context and on-site documents against the deployed artifact.')
            return
        if attempt < attempts - 1:
            time.sleep(10)
    raise RuntimeError('Pages has not served the expected files: ' + ', '.join(pending))


if __name__ == '__main__':
    verify(sys.argv[1])
