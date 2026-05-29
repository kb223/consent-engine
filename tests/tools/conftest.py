"""Pytest fixtures for tool integration tests."""

from __future__ import annotations

import threading
from collections.abc import Generator
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

# ---------------------------------------------------------------------------
# Minimal test pages (embedded — no external network required)
# ---------------------------------------------------------------------------

_BASIC_PAGE_HTML = b"""<!DOCTYPE html>
<html>
<head>
  <title>Test Page</title>
  <script>
    // Set a test cookie
    document.cookie = "test_cookie=hello_world; path=/";
    document.cookie = "another_cookie=value123; path=/";
  </script>
</head>
<body><h1>Test Page</h1></body>
</html>"""

_GTM_PAGE_HTML = b"""<!DOCTYPE html>
<html>
<head>
  <title>GTM Test Page</title>
  <script>
    // Simulate GTM container object (what window.google_tag_manager contains post-load)
    window.google_tag_manager = {"GTM-TESTONLY": {"dataLayer": {}, "id": "GTM-TESTONLY"}};
  </script>
  <!-- GTM snippet reference (no actual gtm.js loaded in tests) -->
  <script async src="https://www.googletagmanager.com/gtm.js?id=GTM-TESTONLY"></script>
</head>
<body><h1>GTM Test Page</h1></body>
</html>"""

_BANNER_SINGLE_PAGE_HTML = b"""<!DOCTYPE html>
<html>
<head><title>Single-Step Banner</title></head>
<body>
  <h1>Content</h1>
  <div id="cookie-banner" role="dialog" aria-label="Cookie Consent">
    <p>We use cookies.</p>
    <button id="accept-btn">Accept All</button>
    <button id="reject-btn">Reject All</button>
  </div>
  <script>
    document.getElementById('reject-btn').addEventListener('click', function() {
      document.getElementById('cookie-banner').remove();
      if (window.parent !== window) {
        window.parent.postMessage('close-banner', '*');
      }
    });
  </script>
</body>
</html>"""

_BANNER_TWO_STEP_PAGE_HTML = b"""<!DOCTYPE html>
<html>
<head><title>Two-Step Banner</title></head>
<body>
  <h1>Content</h1>
  <div id="cookie-banner" role="dialog" aria-label="Cookie Consent">
    <p>We use cookies.</p>
    <button id="accept-btn">Accept All</button>
    <button id="prefs-btn">Manage Preferences</button>
  </div>
  <div id="prefs-panel" role="dialog" aria-label="Preferences" style="display:none">
    <p>Choose your preferences.</p>
    <button id="save-btn">Save Preferences</button>
  </div>
  <script>
    document.getElementById('prefs-btn').addEventListener('click', function() {
      document.getElementById('cookie-banner').remove();
      document.getElementById('prefs-panel').style.display = 'block';
    });
    document.getElementById('save-btn').addEventListener('click', function() {
      document.getElementById('prefs-panel').remove();
    });
  </script>
</body>
</html>"""

_BANNER_WITH_GCS_PAGE_HTML = b"""<!DOCTYPE html>
<html>
<head><title>Banner With GCS</title></head>
<body>
  <div id="cookie-banner" role="dialog">
    <button id="reject-btn">Reject All</button>
  </div>
  <script>
    if (document.cookie.indexOf('consent=granted') === -1) {
        document.getElementById('reject-btn').addEventListener('click', function() {
          document.getElementById('cookie-banner').remove();
          document.cookie = "consent=granted; path=/";
          var img = new Image();
          img.src = '/gcs-beacon?gcs=G1--&tid=G-TEST';
        });
    } else {
        document.getElementById('cookie-banner').remove();
    }
  </script>
</body>
</html>"""

_CUSTOM_LOADER_JS = (
    b"// Custom GTM loader (Stape-style proxy - URL does not contain 'gtm.js')\n"
    b"var google_tag_manager = google_tag_manager || {};\n"
    b'google_tag_manager["GTM-CUSTOM1"] = {"dataLayer": {}};\n'
    b'var data = ({"resource":{"version":"1","macros":[],'
    b'"tags":[{"function":"__html","tag_id":1,"instance_name":"FB Pixel"}],'
    b'"predicates":[],"rules":[]}});\n'
)

_CUSTOM_LOADER_PAGE_HTML = (
    b"<!DOCTYPE html>\n<html>\n<head>\n"
    b"  <title>Custom Loader Page</title>\n"
    b'  <script src="/custom-loader.js"></script>\n'
    b"</head>\n<body><h1>Custom Loader Page</h1></body>\n</html>"
)

_COOKIEYES_PAGE_HTML = b"""<!DOCTYPE html><html><head><title>CookieYes Test</title></head>
<body>
  <script>
    // Simulate CookieYes loading: set global before networkidle
    window.getCkyConsent = function() {
      return {categories: {analytics: false, advertisement: false}};
    };
    window.cookieyes = {version: '3.x'};
  </script>
  <div id="cky-consent-bar" class="cky-consent-bar">Cookie banner</div>
</body></html>"""

# CookieYes (known CMP, cmp_injector HAS a plan) that ALSO fires a GCS=G111
# (granted) beacon on load and never flips it — the genuine wiring-broken
# signature: CMP recognised, denial injected, Consent Mode still GRANTED.
# (The plain /cmp-cookieyes page above emits NO GCS beacon at all, which is the
# distinct S3_NO_GOOGLE_CONSENT_MODE scenario.)
_COOKIEYES_GCS_GRANTED_PAGE_HTML = b"""<!DOCTYPE html><html><head><title>CookieYes GCS Granted</title></head>
<body>
  <script>
    window.getCkyConsent = function() {
      return {categories: {analytics: false, advertisement: false}};
    };
    window.cookieyes = {version: '3.x'};
    (function() {
      var img = new Image();
      img.src = '/gcs-beacon?gcs=G111&tid=G-TEST';
    })();
  </script>
  <div id="cky-consent-bar" class="cky-consent-bar">Cookie banner</div>
</body></html>"""

_USERCENTRICS_PAGE_HTML = b"""<!DOCTYPE html><html><head><title>Usercentrics Test</title></head>
<body>
  <script>
    window.UC_UI = {isInitialized: function() { return true; }, denyAllConsents: function() {}};
    window.usercentrics = {version: '2.x'};
  </script>
  <div id="usercentrics-root"></div>
</body></html>"""

_TRUSTARC_PAGE_HTML = b"""<!DOCTYPE html><html><head><title>TrustArc Test</title></head>
<body>
  <script>
    window.truste = {eu: {bindMap: {consentModel: 'opt-in'}}};
  </script>
  <iframe id="truste-consent-track" src="/basic" title="TrustArc Consent Manager"></iframe>
  <div id="truste-consent-content">Cookie banner</div>
</body></html>"""

_TCF_PAGE_HTML = b"""<!DOCTYPE html><html><head><title>IAB TCF Test</title></head>
<body>
  <script>
    window.__tcfapi = function(command, version, callback, parameter) {
      if (command === 'getTCData') {
        callback({tcString: '', gdprApplies: true, eventStatus: 'useractioncomplete'}, true);
      }
    };
    // No CMP-specific global - pure IAB TCF
  </script>
  <div role="dialog" id="consent-banner">IAB TCF Banner</div>
</body></html>"""

_DIDOMI_PAGE_HTML = b"""<!DOCTYPE html><html><head><title>Didomi Test</title></head>
<body>
  <script>
    window.Didomi = {
      isReady: function() { return true; },
      setUserDisagreeToAll: function() { return true; },
    };
    window.didomiOnReady = [];
  </script>
  <div id="didomi-popup" role="dialog">Didomi banner</div>
</body></html>"""

_IFRAME_BANNER_PAGE_HTML = b"""<!DOCTYPE html><html><head><title>iframe Banner</title></head>
<body>
  <div id="consent-wrapper">
    <iframe id="truste-consent-track" title="TrustArc Consent Manager"
            src="/banner-single" width="600" height="300">
    </iframe>
  </div>
  <script>
    window.addEventListener('message', function(event) {
        if (event.data === 'close-banner') {
            document.getElementById('consent-wrapper').remove();
        }
    });
  </script>
</body></html>"""

_TOGGLE_PANEL_PAGE_HTML = b"""<!DOCTYPE html><html><head><title>Toggle Panel</title></head>
<body>
  <div id="cookie-banner" role="dialog">
    <button id="settings-btn">Cookie Settings</button>
  </div>
  <div id="settings-panel" role="dialog" style="display:none">
    <label>Analytics <input type="checkbox" id="analytics" checked></label>
    <label>Marketing <input type="checkbox" id="marketing" checked></label>
    <button id="save-btn">Save Preferences</button>
  </div>
  <script>
    document.getElementById('settings-btn').addEventListener('click', function() {
      document.getElementById('cookie-banner').remove();
      document.getElementById('settings-panel').style.display = 'block';
    });
    document.getElementById('save-btn').addEventListener('click', function() {
      document.getElementById('settings-panel').remove();
    });
  </script>
</body></html>"""

_GPC_PAGE_HTML = b"""<!DOCTYPE html><html><head><title>GPC Test</title></head>
<body>
  <div id="cookie-banner" role="dialog">GPC Banner</div>
  <script>
    if (navigator.globalPrivacyControl === true) {
      document.getElementById('cookie-banner').remove();
    }
  </script>
</body></html>"""

_DIDOMI_API_PAGE_HTML = b"""<!DOCTYPE html><html><head><title>Didomi API Test</title></head>
<body>
  <div id="didomi-popup" role="dialog">Didomi Banner</div>
  <script>
    window.didomiOnReady = [];
    window.Didomi = {
      isReady: function() { return true; },
      setUserDisagreeToAll: function() {
        document.getElementById('didomi-popup').remove();
        return true;
      },
    };
  </script>
</body></html>"""

# Known CMP (OneTrust) that ALSO fires a denied GCS beacon immediately on load
# — used to exercise the "S3 definitive" path (known CMP + verified denied GCS).
_ONETRUST_DENIED_PAGE_HTML = b"""<!DOCTYPE html><html><head><title>OneTrust Denied</title></head>
<body>
  <script>
    // Expose OneTrust globals so cmp_detector returns "OneTrust" (known CMP).
    window.OneTrust = { RejectAll: function() {}, UpdateConsent: function() {} };
    window.OnetrustActiveGroups = ',C0001,';
    // Immediately fire a GCS=G1-- (denied) beacon so the injection-verification
    // check observes a denied Consent Mode signal.
    (function() {
      var img = new Image();
      img.src = '/gcs-beacon?gcs=G1--&tid=G-TEST';
    })();
  </script>
</body></html>"""

_PAGES = {
    "/basic": _BASIC_PAGE_HTML,
    "/gtm": _GTM_PAGE_HTML,
    "/banner-single": _BANNER_SINGLE_PAGE_HTML,
    "/banner-two-step": _BANNER_TWO_STEP_PAGE_HTML,
    "/banner-with-gcs": _BANNER_WITH_GCS_PAGE_HTML,
    "/custom-loader-page": _CUSTOM_LOADER_PAGE_HTML,
    "/cmp-cookieyes": _COOKIEYES_PAGE_HTML,
    "/cmp-cookieyes-gcs": _COOKIEYES_GCS_GRANTED_PAGE_HTML,
    "/cmp-usercentrics": _USERCENTRICS_PAGE_HTML,
    "/cmp-trustarc": _TRUSTARC_PAGE_HTML,
    "/cmp-tcf": _TCF_PAGE_HTML,
    "/cmp-didomi": _DIDOMI_PAGE_HTML,
    "/banner-iframe": _IFRAME_BANNER_PAGE_HTML,
    "/banner-toggles": _TOGGLE_PANEL_PAGE_HTML,
    "/banner-gpc": _GPC_PAGE_HTML,
    "/banner-didomi-api": _DIDOMI_API_PAGE_HTML,
    "/cmp-onetrust-denied": _ONETRUST_DENIED_PAGE_HTML,
}


class _StaticHandler(BaseHTTPRequestHandler):
    def do_GET(self) -> None:
        if self.path.startswith("/gcs-beacon"):
            self.send_response(200)
            self.send_header("Content-Type", "text/plain")
            self.end_headers()
            self.wfile.write(b"")
            return

        if self.path == "/custom-loader.js":
            self.send_response(200)
            self.send_header("Content-Type", "application/javascript")
            self.end_headers()
            self.wfile.write(_CUSTOM_LOADER_JS)
            return

        content = _PAGES.get(self.path, b"<html><body>Not found</body></html>")
        status = 200 if self.path in _PAGES else 404
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(content)

    def log_message(self, *args: object) -> None:
        pass  # suppress output during tests


@pytest.fixture(scope="session", autouse=True)
def _allow_internal_scans() -> Generator[None, None, None]:
    """Allow the scanner's SSRF guard to reach the loopback test server.

    The SSRF guard (consent_engine.security) blocks loopback / private IPs on
    every request and redirect. The test suite scans a localhost HTTP server,
    which is exactly the "self-hoster auditing their own internal staging"
    case the CONSENT_ENGINE_ALLOW_INTERNAL=1 override exists for. Set it for
    the whole session so the guard permits localhost.
    """
    import os

    prior = os.environ.get("CONSENT_ENGINE_ALLOW_INTERNAL")
    os.environ["CONSENT_ENGINE_ALLOW_INTERNAL"] = "1"
    yield
    if prior is None:
        os.environ.pop("CONSENT_ENGINE_ALLOW_INTERNAL", None)
    else:
        os.environ["CONSENT_ENGINE_ALLOW_INTERNAL"] = prior


@pytest.fixture(scope="session")
def local_server() -> Generator[str, None, None]:
    """Start a local HTTP server serving minimal test pages.

    Returns the base URL, e.g. 'http://localhost:PORT'.
    Pages available:
      /basic             — sets two test cookies via JS
      /gtm               — has window.google_tag_manager with GTM-TESTONLY
      /banner-single     — single-step consent banner with reject button
      /banner-two-step   — two-step banner with preferences panel
      /banner-with-gcs   — banner that fires a GCS=G1-- beacon on reject
      /custom-loader-page — loads /custom-loader.js (Track 2 fingerprint test)
    """
    server = HTTPServer(("localhost", 0), _StaticHandler)
    port = server.server_address[1]
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    yield f"http://localhost:{port}"
    server.shutdown()


_MOCK_GTM_JS = b"""
// Mock GTM container JS for testing
(function(w,d,s,l,i){
    w[l]=w[l]||[];
    w[l].push({'gtm.start': new Date().getTime(), event:'gtm.js'});
})(window,document,'script','dataLayer','GTM-MOCK99');
var google_tag_manager = {'GTM-MOCK99': {'dataLayer': {}}};
"""

# Expose the mock GTM JS so tests can reference the expected ID
MOCK_GTM_CONTAINER_ID = "GTM-MOCK99"
MOCK_GTM_JS_CONTENT = _MOCK_GTM_JS.decode()
