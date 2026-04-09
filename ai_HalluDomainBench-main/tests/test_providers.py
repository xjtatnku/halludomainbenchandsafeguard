from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path

from halludomainbench.providers import load_api_keys


class ProviderTests(unittest.TestCase):
    def test_load_api_keys_reads_local_secret_file_when_env_missing(self) -> None:
        original = os.environ.pop("SILICONFLOW_API_KEY", None)
        try:
            with tempfile.TemporaryDirectory() as tmp_dir:
                secret_path = Path(tmp_dir) / "local.secrets.json"
                secret_path.write_text(
                    json.dumps({"SILICONFLOW_API_KEY": "demo-key"}, ensure_ascii=False),
                    encoding="utf-8",
                )

                keys = load_api_keys("SILICONFLOW_API_KEY", secret_path)

            self.assertEqual(keys["SILICONFLOW_API_KEY"], "demo-key")
        finally:
            if original is not None:
                os.environ["SILICONFLOW_API_KEY"] = original


if __name__ == "__main__":
    unittest.main()
