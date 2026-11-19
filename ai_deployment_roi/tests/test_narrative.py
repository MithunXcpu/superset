# Licensed to the Apache Software Foundation (ASF) under one
# or more contributor license agreements.  See the NOTICE file
# distributed with this work for additional information
# regarding copyright ownership.  The ASF licenses this file
# to you under the Apache License, Version 2.0 (the
# "License"); you may not use this file except in compliance
# with the License.  You may obtain a copy of the License at
#
#   http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing,
# software distributed under the License is distributed on an
# "AS IS" BASIS, WITHOUT WARRANTIES OR CONDITIONS OF ANY
# KIND, either express or implied.  See the License for the
# specific language governing permissions and limitations
# under the License.
"""Checks for the offline narrative and the NVIDIA request builder."""

from __future__ import annotations

import io
import json
import sys
from pathlib import Path
from unittest.mock import patch
from urllib.error import HTTPError

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

import llm_client  # noqa: E402
import narrative  # noqa: E402
from metrics import DATA_LABEL, narrative_payload  # noqa: E402


def test_offline_summary_includes_the_sample_economics(capsys) -> None:  # type: ignore[no-untyped-def]
    """The mock draft is a one-pager grounded in the seed."""
    exit_code = narrative.main(["--offline"])
    captured = capsys.readouterr()
    assert exit_code == 0
    assert "narrative_source=mock" in captured.err
    assert DATA_LABEL in captured.out
    assert "Narrative source: mock" in captured.out
    payload = narrative_payload()
    assert payload["kpis"]["roi_pct"] in captured.out
    assert payload["kpis"]["payback_months"] in captured.out
    assert "Support L1" in captured.out
    assert "Finance Ops" in captured.out
    assert "time study" in captured.out


def test_missing_database_url_is_an_error(capsys) -> None:  # type: ignore[no-untyped-def]
    """A live read needs a URL; the offline flag is the no-database path."""
    with patch.dict("os.environ", {"AI_ROI_DATABASE_URL": ""}, clear=False):
        exit_code = narrative.main([])
    captured = capsys.readouterr()
    assert exit_code == 2
    assert "AI_ROI_DATABASE_URL" in captured.err


def test_auto_provider_without_a_key_is_mock() -> None:
    """No key means the offline template, not a network call."""
    env = {"LLM_PROVIDER": "auto", "NVIDIA_API_KEY": ""}
    with patch.dict("os.environ", env, clear=False):
        assert llm_client.resolve_provider() == "mock"


def test_nvidia_request_uses_the_configured_endpoint() -> None:
    """The client posts to the NVIDIA-compatible chat completions URL."""
    payload = narrative_payload()
    response = io.BytesIO(
        json.dumps(
            {"choices": [{"message": {"content": "Draft from the sample JSON."}}]}
        ).encode("utf-8")
    )
    request_holder: dict[str, object] = {}

    class _Response:
        def __enter__(self) -> io.BytesIO:
            return response

        def __exit__(self, *args: object) -> None:
            return None

    def _urlopen(request, timeout=0):  # type: ignore[no-untyped-def]
        request_holder["url"] = request.full_url
        request_holder["body"] = json.loads(request.data.decode("utf-8"))
        request_holder["timeout"] = timeout
        return _Response()

    env = {
        "LLM_PROVIDER": "nvidia",
        "NVIDIA_API_KEY": "test-key-not-real",
        "LLM_BASE_URL": "https://integrate.api.nvidia.com/v1",
        "LLM_MODEL": "meta/llama-3.3-70b-instruct",
        "LLM_FALLBACK": "error",
    }
    with patch.dict("os.environ", env, clear=False):
        with patch("llm_client.urllib.request.urlopen", _urlopen):
            markdown, source = llm_client.draft_summary(payload)
    assert source == "nvidia"
    assert (
        request_holder["url"] == "https://integrate.api.nvidia.com/v1/chat/completions"
    )
    body = request_holder["body"]
    assert isinstance(body, dict)
    assert body["model"] == "meta/llama-3.3-70b-instruct"
    assert "test-key-not-real" not in json.dumps(body)
    assert DATA_LABEL in markdown
    assert "Narrative source: nvidia" in markdown
    assert "Draft from the sample JSON." in markdown


def test_nvidia_http_error_falls_back_to_the_template() -> None:
    """A failed model call still returns the offline one-pager."""
    payload = narrative_payload()

    def _urlopen(request, timeout=0):  # type: ignore[no-untyped-def]
        raise HTTPError(
            request.full_url,
            401,
            "unauthorized",
            hdrs=None,  # type: ignore[arg-type]
            fp=io.BytesIO(b"nope"),
        )

    env = {
        "LLM_PROVIDER": "nvidia",
        "NVIDIA_API_KEY": "test-key-not-real",
        "LLM_FALLBACK": "mock",
    }
    with patch.dict("os.environ", env, clear=False):
        with patch("llm_client.urllib.request.urlopen", _urlopen):
            markdown, source = llm_client.draft_summary(payload)
    assert source == "mock"
    assert payload["kpis"]["roi_pct"] in markdown
    assert "NVIDIA draft was unavailable" in markdown
