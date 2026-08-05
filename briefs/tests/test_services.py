import json
from unittest.mock import Mock

import httpx
from django.test import SimpleTestCase, override_settings

from briefs.services import (
    AIAuthenticationError,
    AIConfigurationError,
    AIInvalidResponseError,
    AIProviderUnavailableError,
    AIQuotaError,
)
from briefs.services.providers import DemoProvider, OllamaProvider, OpenAICompatibleProvider, get_provider
from briefs.services.schema import validate_analysis_payload


def valid_analysis():
    return {
        "summary": "Une synthèse concise.",
        "objectives": ["Valider le besoin"],
        "deliverables": ["Un prototype"],
        "risks": ["Un calendrier serré"],
        "next_steps": ["Interroger les utilisateurs"],
    }


def provider(client):
    return OpenAICompatibleProvider(
        name="mistral",
        base_url="https://api.example.test/v1",
        api_key="test-secret-key",
        model="test-model",
        timeout=1,
        client=client,
    )


def ollama_provider(client):
    return OllamaProvider(
        base_url="http://ollama.test:11434",
        model="qwen2.5:0.5b",
        timeout=5,
        num_ctx=2048,
        keep_alive="1m",
        client=client,
    )


def analyse_with(provider_instance):
    return provider_instance.analyse(
        title="Portail partenaire",
        raw_idea="Centraliser toutes les demandes dans un espace unique.",
        audience="Partenaires",
        constraints="Délai de huit semaines",
    )


class AnalysisSchemaTests(SimpleTestCase):
    def test_valid_payload_is_normalized(self):
        data = valid_analysis()
        data["objectives"] = ["  Valider le besoin  "]

        result = validate_analysis_payload(data)

        self.assertEqual(result.objectives, ["Valider le besoin"])

    def test_missing_list_is_rejected(self):
        data = valid_analysis()
        del data["risks"]

        with self.assertRaises(AIInvalidResponseError):
            validate_analysis_payload(data)

    def test_non_string_list_item_is_rejected(self):
        data = valid_analysis()
        data["risks"] = [{"value": "not text"}]

        with self.assertRaises(AIInvalidResponseError):
            validate_analysis_payload(data)


class DemoProviderTests(SimpleTestCase):
    def test_demo_provider_is_deterministic_and_offline(self):
        demo = DemoProvider()

        first = analyse_with(demo)
        second = analyse_with(demo)

        self.assertEqual(first, second)
        self.assertEqual(first.raw_response["provider"], "demo")
        self.assertGreater(len(first.payload.next_steps), 0)


class OpenAICompatibleProviderTests(SimpleTestCase):
    def test_structured_response_and_usage_are_parsed(self):
        client = Mock()
        response = Mock()
        response.raise_for_status.return_value = None
        response.json.return_value = {
            "choices": [{"message": {"content": json.dumps(valid_analysis())}}],
            "usage": {"total_tokens": 321},
        }
        client.post.return_value = response

        result = analyse_with(provider(client))

        self.assertEqual(result.payload.summary, "Une synthèse concise.")
        self.assertEqual(result.tokens_used, 321)
        request_kwargs = client.post.call_args.kwargs
        self.assertEqual(request_kwargs["headers"]["Authorization"], "Bearer test-secret-key")
        self.assertEqual(request_kwargs["json"]["model"], "test-model")

    def test_json_markdown_fence_is_tolerated(self):
        client = Mock()
        response = Mock()
        response.raise_for_status.return_value = None
        response.json.return_value = {
            "choices": [{"message": {"content": f"```json\n{json.dumps(valid_analysis())}\n```"}}]
        }
        client.post.return_value = response

        result = analyse_with(provider(client))

        self.assertEqual(result.payload.deliverables, ["Un prototype"])

    def test_malformed_response_is_cleanly_rejected(self):
        client = Mock()
        response = Mock()
        response.raise_for_status.return_value = None
        response.json.return_value = {"choices": []}
        client.post.return_value = response

        with self.assertRaises(AIInvalidResponseError):
            analyse_with(provider(client))

    def test_authentication_status_has_stable_error(self):
        self._assert_http_error(401, AIAuthenticationError, "provider_authentication")

    def test_quota_status_has_stable_error(self):
        self._assert_http_error(429, AIQuotaError, "provider_quota")

    def test_server_status_is_retryable(self):
        error = self._assert_http_error(503, AIProviderUnavailableError, "provider_unavailable")
        self.assertTrue(error.retryable)

    def _assert_http_error(self, status_code, exception_class, code):
        client = Mock()
        response = httpx.Response(
            status_code,
            request=httpx.Request("POST", "https://api.example.test/v1/chat/completions"),
        )
        client.post.return_value = response

        with self.assertRaises(exception_class) as captured:
            analyse_with(provider(client))
        self.assertEqual(captured.exception.code, code)
        return captured.exception

    def test_timeout_becomes_provider_unavailable(self):
        client = Mock()
        client.post.side_effect = httpx.ConnectTimeout("timed out")

        with self.assertRaises(AIProviderUnavailableError):
            analyse_with(provider(client))


class OllamaProviderTests(SimpleTestCase):
    def test_native_structured_response_and_usage_are_parsed(self):
        client = Mock()
        response = Mock()
        response.raise_for_status.return_value = None
        response.json.return_value = {
            "model": "qwen2.5:0.5b",
            "done": True,
            "message": {"role": "assistant", "content": json.dumps(valid_analysis())},
            "prompt_eval_count": 41,
            "eval_count": 29,
        }
        client.post.return_value = response

        result = analyse_with(ollama_provider(client))

        self.assertEqual(result.payload.summary, "Une synthèse concise.")
        self.assertEqual(result.tokens_used, 70)
        call = client.post.call_args
        self.assertEqual(call.args[0], "http://ollama.test:11434/api/chat")
        request_body = call.kwargs["json"]
        self.assertFalse(request_body["stream"])
        self.assertEqual(request_body["format"]["required"], list(valid_analysis()))
        self.assertEqual(request_body["options"]["num_ctx"], 2048)
        self.assertEqual(request_body["keep_alive"], "1m")

    def test_incomplete_response_is_rejected(self):
        client = Mock()
        response = Mock()
        response.raise_for_status.return_value = None
        response.json.return_value = {
            "done": False,
            "message": {"content": json.dumps(valid_analysis())},
        }
        client.post.return_value = response

        with self.assertRaises(AIInvalidResponseError):
            analyse_with(ollama_provider(client))

    def test_missing_model_is_a_configuration_error(self):
        client = Mock()
        client.post.return_value = httpx.Response(
            404,
            request=httpx.Request("POST", "http://ollama.test:11434/api/chat"),
        )

        with self.assertRaises(AIConfigurationError):
            analyse_with(ollama_provider(client))

    def test_timeout_becomes_provider_unavailable(self):
        client = Mock()
        client.post.side_effect = httpx.ReadTimeout("model loading timed out")

        with self.assertRaises(AIProviderUnavailableError):
            analyse_with(ollama_provider(client))


class ProviderFactoryTests(SimpleTestCase):
    @override_settings(AI_PROVIDER="demo", AI_MODEL="demo-v2")
    def test_demo_is_the_safe_default(self):
        result = get_provider()

        self.assertIsInstance(result, DemoProvider)
        self.assertEqual(result.model, "demo-v2")

    @override_settings(
        AI_PROVIDER="mistral",
        AI_MODEL="mistral-small-latest",
        AI_API_KEY="",
        AI_BASE_URL="https://api.mistral.ai/v1",
        AI_TIMEOUT_SECONDS=10,
    )
    def test_remote_provider_requires_api_key(self):
        with self.assertRaises(AIConfigurationError):
            get_provider()

    @override_settings(
        AI_PROVIDER="groq",
        AI_MODEL="openai/gpt-oss-20b",
        AI_API_KEY="test-key",
        GROQ_BASE_URL="https://api.groq.com/openai/v1",
        GROQ_TIMEOUT_SECONDS=45,
    )
    def test_groq_uses_the_openai_compatible_adapter(self):
        result = get_provider()

        self.assertIsInstance(result, OpenAICompatibleProvider)
        self.assertEqual(result.name, "groq")
        self.assertEqual(result.base_url, "https://api.groq.com/openai/v1")
        self.assertEqual(result.model, "openai/gpt-oss-20b")
        self.assertEqual(result.timeout, 45)

    @override_settings(
        AI_PROVIDER="ollama",
        AI_MODEL="qwen2.5:0.5b",
        OLLAMA_BASE_URL="http://ollama:11434",
        OLLAMA_TIMEOUT_SECONDS=120,
        OLLAMA_NUM_CTX=4096,
        OLLAMA_KEEP_ALIVE="1m",
    )
    def test_ollama_does_not_require_an_api_key(self):
        result = get_provider()

        self.assertIsInstance(result, OllamaProvider)
        self.assertEqual(result.base_url, "http://ollama:11434")
        self.assertEqual(result.model, "qwen2.5:0.5b")
        self.assertEqual(result.num_ctx, 4096)

    @override_settings(AI_PROVIDER="unknown")
    def test_unknown_provider_is_rejected(self):
        with self.assertRaises(AIConfigurationError):
            get_provider()
