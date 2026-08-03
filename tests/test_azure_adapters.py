import json
import unittest
from types import SimpleNamespace
from unittest import mock

from core.ai.content_safety import AzureContentSafety
from core.ai.intent_parser import AzureOpenAIIntentParser
from core.api.server import create_kernel_from_config
from core.config import AppConfig
from core.database.ledger import CosmosAtomicLedger


class AzureAdapterTests(unittest.TestCase):
    def test_azure_openai_intent_parser_normalizes_json_response(self):
        fake_client = SimpleNamespace(
            chat=SimpleNamespace(
                completions=SimpleNamespace(
                    create=mock.Mock(
                        return_value=SimpleNamespace(
                            choices=[
                                SimpleNamespace(
                                    message=SimpleNamespace(
                                        content=json.dumps(
                                            {
                                                "action": "purchase",
                                                "normalized_text": "purchase limited item",
                                                "confidence": 0.82,
                                            }
                                        )
                                    )
                                )
                            ]
                        )
                    )
                )
            )
        )
        parser = AzureOpenAIIntentParser(
            endpoint="https://example.openai.azure.com",
            api_key="key",
            deployment="gpt-4o-mini",
            client=fake_client,
        )

        result = parser.parse("purchase limited item")

        self.assertEqual(result.action, "PURCHASE")
        self.assertEqual(result.normalized_text, "PURCHASE LIMITED ITEM")
        self.assertEqual(result.confidence, 0.82)
        fake_client.chat.completions.create.assert_called_once()

    def test_azure_content_safety_blocks_high_severity_categories(self):
        fake_client = SimpleNamespace(
            analyze_text=mock.Mock(
                return_value=SimpleNamespace(
                    categories_analysis=[
                        SimpleNamespace(category="Violence", severity=6),
                        SimpleNamespace(category="Hate", severity=0),
                    ]
                )
            )
        )
        checker = AzureContentSafety(
            endpoint="https://contentsafety.example.com",
            key="key",
            block_threshold=4,
            client=fake_client,
        )

        decision = checker.evaluate("unsafe text")

        self.assertFalse(decision.safe)
        self.assertIn("Violence=6", decision.reason)

    def test_cosmos_ledger_create_item_wins_lock(self):
        container = mock.Mock()
        ledger = CosmosAtomicLedger(
            endpoint="https://cosmos.example.com",
            key="key",
            database_name="loom",
            container_name="locks",
            container=container,
        )

        lock_success, owner = ledger.acquire_atomic_lock("DROP-1", "AGENT-A", 5000)

        self.assertTrue(lock_success)
        self.assertEqual(owner, "AGENT-A")
        container.create_item.assert_called_once()

    def test_cosmos_ledger_existing_active_lock_returns_conflict_owner(self):
        class CosmosResourceExistsError(Exception):
            pass

        container = mock.Mock()
        container.create_item.side_effect = CosmosResourceExistsError()
        container.read_item.return_value = {
            "id": "DROP-1",
            "agent_id": "AGENT-A",
            "expires_at": 9999999999999,
            "_etag": "etag-1",
        }
        ledger = CosmosAtomicLedger(
            endpoint="https://cosmos.example.com",
            key="key",
            database_name="loom",
            container_name="locks",
            container=container,
        )

        lock_success, owner = ledger.acquire_atomic_lock("DROP-1", "AGENT-B", 5000)

        self.assertFalse(lock_success)
        self.assertEqual(owner, "AGENT-A")
        container.replace_item.assert_not_called()

    def test_azure_mode_factory_wires_all_production_adapters(self):
        config = AppConfig(
            mode="azure",
            azure_openai_endpoint="https://example.openai.azure.com",
            azure_openai_api_key="key",
            azure_openai_deployment="gpt-4o-mini",
            content_safety_endpoint="https://contentsafety.example.com",
            content_safety_key="key",
            cosmos_endpoint="https://cosmos.example.com",
            cosmos_key="key",
            cosmos_database="loom",
            cosmos_container="locks",
        )

        with (
            mock.patch("core.api.server.AzureOpenAIIntentParser") as parser_cls,
            mock.patch("core.api.server.AzureContentSafety") as safety_cls,
            mock.patch("core.api.server.CosmosAtomicLedger") as ledger_cls,
        ):
            kernel = create_kernel_from_config(config)

        self.assertIs(kernel.intent_parser, parser_cls.return_value)
        self.assertIs(kernel.safety_checker, safety_cls.return_value)
        self.assertIs(kernel.db, ledger_cls.return_value)


if __name__ == "__main__":
    unittest.main()
