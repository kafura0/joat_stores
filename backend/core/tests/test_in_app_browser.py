"""
Tests for Story 4.9 — InAppBrowserMiddleware.

Server-side UA detection; sets X-In-App-Browser: true response header.
"""

import pytest
from django.test import RequestFactory, TestCase
from django.http import HttpResponse

from core.middleware import InAppBrowserMiddleware


class TestInAppBrowserMiddleware(TestCase):
    def setUp(self):
        self.factory = RequestFactory()
        self.middleware = InAppBrowserMiddleware(get_response=lambda r: HttpResponse())

    def _call(self, user_agent: str) -> HttpResponse:
        request = self.factory.get("/")
        request.META["HTTP_USER_AGENT"] = user_agent
        self.middleware.process_request(request)
        response = HttpResponse()
        return self.middleware.process_response(request, response)

    # --- Detection: in-app browsers ---

    def test_whatsapp_ua_detected(self):
        ua = "Mozilla/5.0 (iPhone; CPU iPhone OS 15_0) WhatsApp/22.1.0 A"
        resp = self._call(ua)
        assert resp["X-In-App-Browser"] == "true"

    def test_facebook_fban_detected(self):
        ua = "Mozilla/5.0 FBAN/FBIOS;FBDV/iPhone14,3"
        resp = self._call(ua)
        assert resp["X-In-App-Browser"] == "true"

    def test_facebook_fbav_detected(self):
        ua = "Mozilla/5.0 FBAV/100.0.0.0"
        resp = self._call(ua)
        assert resp["X-In-App-Browser"] == "true"

    def test_facebook_fb_iab_detected(self):
        ua = "Mozilla/5.0 FB_IAB/FB4A;FBDV/Pixel6"
        resp = self._call(ua)
        assert resp["X-In-App-Browser"] == "true"

    def test_instagram_detected(self):
        ua = "Mozilla/5.0 (Linux; Android 11) Instagram 195.0.0"
        resp = self._call(ua)
        assert resp["X-In-App-Browser"] == "true"

    def test_line_detected(self):
        ua = "Mozilla/5.0 (iPhone) Line/10.22.0"
        resp = self._call(ua)
        assert resp["X-In-App-Browser"] == "true"

    # --- Non-detection: normal browsers ---

    def test_chrome_not_detected(self):
        ua = "Mozilla/5.0 (Linux; Android 10) AppleWebKit/537.36 Chrome/100"
        resp = self._call(ua)
        assert "X-In-App-Browser" not in resp

    def test_safari_not_detected(self):
        ua = "Mozilla/5.0 (iPhone; CPU iPhone OS 15_0) AppleWebKit/605.1.15 Safari/604.1"
        resp = self._call(ua)
        assert "X-In-App-Browser" not in resp

    def test_firefox_not_detected(self):
        ua = "Mozilla/5.0 (Android 11; Mobile) Gecko/120 Firefox/120.0"
        resp = self._call(ua)
        assert "X-In-App-Browser" not in resp

    def test_empty_ua_not_detected(self):
        resp = self._call("")
        assert "X-In-App-Browser" not in resp

    # --- is_in_app_browser attribute ---

    def test_is_in_app_browser_set_true_for_whatsapp(self):
        request = self.factory.get("/")
        request.META["HTTP_USER_AGENT"] = "WhatsApp/22"
        self.middleware.process_request(request)
        assert request.is_in_app_browser is True

    def test_is_in_app_browser_set_false_for_chrome(self):
        request = self.factory.get("/")
        request.META["HTTP_USER_AGENT"] = "Chrome/100"
        self.middleware.process_request(request)
        assert request.is_in_app_browser is False

    def test_missing_ua_header_sets_false(self):
        request = self.factory.get("/")
        # No HTTP_USER_AGENT set
        request.META.pop("HTTP_USER_AGENT", None)
        self.middleware.process_request(request)
        assert request.is_in_app_browser is False
