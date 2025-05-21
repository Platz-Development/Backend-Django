from django.http import JsonResponse
import re

class BrowserCompatibilityMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        user_agent = request.META.get('HTTP_USER_AGENT', '').lower()
        response = self.get_response(request)

        # Skip API requests and non-browser clients
        if request.path.startswith('/api/') or not user_agent:
            return response

        # Browser checks
        is_unsupported = False
        browser_warnings = []

        # Safari (including iOS)
        if 'safari' in user_agent and 'chrome' not in user_agent:
            if 'version/' in user_agent:
                safari_version = re.search(r'version/(\d+)', user_agent).group(1)
                if int(safari_version) < 13:
                    is_unsupported = True
                    browser_warnings.append("Safari <13 has limited WebRTC support")

        # Firefox
        if 'firefox' in user_agent:
            ff_version = re.search(r'firefox/(\d+)', user_agent).group(1)
            if int(ff_version) < 76:
                is_unsupported = True
                browser_warnings.append("Firefox <76 lacks full H.264 support")

        # Edge Legacy (pre-Chromium)
        if 'edge/' in user_agent and 'edg/' not in user_agent:
            is_unsupported = True
            browser_warnings.append("Legacy Edge is not supported")

        if is_unsupported:
            return JsonResponse({
                "error": "UnsupportedBrowser",
                "message": "Your browser has compatibility issues",
                "details": browser_warnings,
                "recommended": "Chrome/Edge 80+, Firefox 76+, Safari 13+"
            }, status=400)

        return response