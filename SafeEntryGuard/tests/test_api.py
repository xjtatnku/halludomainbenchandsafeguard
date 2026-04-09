import json
import threading
import time
import unittest
from pathlib import Path
from unittest.mock import patch

import requests

from safeentryguard.api import create_server
from safeentryguard.config import load_config
from safeentryguard.guard import SafeEntryGuard


def _fake_verify(url: str, **kwargs):
    domain = url.split("//", 1)[-1].split("/", 1)[0]
    return {
        "url": url,
        "domain": domain,
        "http_status": 200,
        "final_url": url,
        "final_domain": domain,
        "live_status": "live",
        "error": "",
        "redirect_drift": False,
        "dns": {"enabled": False, "resolved": None, "records": {}},
        "rdap": {"queried": False, "registered": None},
        "domain_intel": {
            "domain": domain,
            "registrable_domain": domain,
            "lexical_flags": {
                "unicode_domain": False,
                "punycode_domain": False,
                "digit_swap": False,
                "long_subdomain_chain": False,
                "many_hyphens": False,
                "suspicious_keyword": False,
                "looks_like_typosquat": False,
            },
            "similarity_to_official": 1.0,
            "similar_official_domain": "github.com",
            "dnstwist_match": False,
            "lexical_score": 0.0,
        },
    }


class ApiTests(unittest.TestCase):
    def setUp(self) -> None:
        config = load_config(Path("configs/guard.default.json"))
        config.truth_store_path = Path("data/truth/entities.sample.json").resolve()
        self.guard = SafeEntryGuard(config)
        self.server = None
        self.thread = None

    def tearDown(self) -> None:
        if self.server is not None:
            self.server.shutdown()
            self.server.server_close()
        if self.thread is not None:
            self.thread.join(timeout=2)

    @patch("safeentryguard.guard.verify_candidate", side_effect=_fake_verify)
    def test_filter_endpoint(self, _mock_verify) -> None:
        self.server = create_server(self.guard, "127.0.0.1", 0)
        host, port = self.server.server_address
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        time.sleep(0.1)

        health = requests.get(f"http://{host}:{port}/health", timeout=5)
        self.assertEqual(health.status_code, 200)
        filter_response = requests.post(
            f"http://{host}:{port}/filter",
            json={"prompt": "GitHub login page", "response": "Use https://github.com/login"},
            timeout=5,
        )
        self.assertEqual(filter_response.status_code, 200)
        payload = filter_response.json()
        self.assertEqual(payload["recommended_url"], "https://github.com/login")
        self.assertEqual(payload["status"], "accepted")

    @patch("safeentryguard.guard.verify_candidate", side_effect=_fake_verify)
    def test_batch_endpoint(self, _mock_verify) -> None:
        self.server = create_server(self.guard, "127.0.0.1", 0)
        host, port = self.server.server_address
        self.thread = threading.Thread(target=self.server.serve_forever, daemon=True)
        self.thread.start()
        time.sleep(0.1)

        response = requests.post(
            f"http://{host}:{port}/filter/batch",
            data=json.dumps(
                {
                    "items": [
                        {
                            "model": "demo",
                            "prompt_id": "P001",
                            "prompt": "GitHub login page",
                            "response": "Use https://github.com/login",
                            "meta": {"intent": "login_entry"},
                        }
                    ]
                }
            ),
            headers={"Content-Type": "application/json"},
            timeout=5,
        )
        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(payload["summary"]["accepted_count"], 1)


if __name__ == "__main__":
    unittest.main()
