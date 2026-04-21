from __future__ import annotations

import json
import os
import tempfile
import unittest
from pathlib import Path

from halludomainbench.models import ModelSpec
from halludomainbench.providers import load_api_keys, required_api_key_names, resolve_api_key_name


class ProviderTests(unittest.TestCase):
    def test_load_api_keys_reads_multiple_secret_keys_when_env_missing(self) -> None:
        original = os.environ.pop("SILICONFLOW_API_KEY", None)
        original_baidu = os.environ.pop("BAIDU_QIANFAN_API_KEY", None)
        try:
            with tempfile.TemporaryDirectory() as tmp_dir:
                secret_path = Path(tmp_dir) / "local.secrets.json"
                secret_path.write_text(
                    json.dumps(
                        {
                            "SILICONFLOW_API_KEY": "demo-key",
                            "BAIDU_QIANFAN_API_KEY": "demo-baidu-key",
                        },
                        ensure_ascii=False,
                    ),
                    encoding="utf-8",
                )

                keys = load_api_keys(["SILICONFLOW_API_KEY", "BAIDU_QIANFAN_API_KEY"], secret_path)

            self.assertEqual(keys["SILICONFLOW_API_KEY"], "demo-key")
            self.assertEqual(keys["BAIDU_QIANFAN_API_KEY"], "demo-baidu-key")
        finally:
            if original is not None:
                os.environ["SILICONFLOW_API_KEY"] = original
            if original_baidu is not None:
                os.environ["BAIDU_QIANFAN_API_KEY"] = original_baidu

    def test_required_api_key_names_follow_model_provider(self) -> None:
        specs = [
            ModelSpec(model_id="Qwen/Qwen3.5-397B-A17B", provider="siliconflow"),
            ModelSpec(model_id="baidu/ERNIE-4.5-300B-A47B", provider="baidu_qianfan"),
            ModelSpec(
                model_id="doubao-seed-character-251128",
                provider="volcengine_ark",
                api_key_name="CUSTOM_ARK_KEY",
            ),
        ]

        self.assertEqual(
            required_api_key_names(specs),
            ["SILICONFLOW_API_KEY", "BAIDU_QIANFAN_API_KEY", "CUSTOM_ARK_KEY"],
        )
        self.assertEqual(resolve_api_key_name(specs[-1]), "CUSTOM_ARK_KEY")


if __name__ == "__main__":
    unittest.main()
