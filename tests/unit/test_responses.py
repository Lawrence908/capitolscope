"""Tests for the standard API response envelope."""

import json

import pytest
from fastapi.responses import JSONResponse

from core.responses import (
    ResponseEnvelope,
    ResponseStatus,
    create_response,
    error_response,
    success_response,
)

pytestmark = pytest.mark.unit


def _body(resp: JSONResponse) -> dict:
    """Decode a JSONResponse body back into a dict."""
    return json.loads(resp.body.decode())


class TestResponseEnvelope:
    def test_success_envelope_serialization(self):
        env = ResponseEnvelope(status=ResponseStatus.SUCCESS, data={"x": 1})
        resp = env.to_response()
        assert isinstance(resp, JSONResponse)
        assert resp.status_code == 200
        body = _body(resp)
        assert body["status"] == "success"
        assert body["data"] == {"x": 1}

    def test_custom_status_code(self):
        env = ResponseEnvelope(status=ResponseStatus.SUCCESS, data=None)
        assert env.to_response(status_code=201).status_code == 201


class TestCreateResponse:
    def test_data_only_is_marked_success(self):
        resp = create_response(data={"a": 1})
        body = _body(resp)
        assert body["status"] == "success"
        assert body["error"] is None

    def test_error_payload_is_marked_error(self):
        resp = create_response(error={"message": "nope"}, status_code=400)
        body = _body(resp)
        assert body["status"] == "error"
        assert resp.status_code == 400

    def test_request_id_injected_into_meta(self):
        resp = create_response(data={"a": 1}, request_id="req-42")
        assert _body(resp)["meta"]["request_id"] == "req-42"


class TestConvenienceHelpers:
    def test_success_response(self):
        resp = success_response({"ok": True}, status_code=200)
        body = _body(resp)
        assert body["status"] == "success"
        assert body["data"] == {"ok": True}

    def test_error_response_shape(self):
        resp = error_response("bad input", error_code="validation", status_code=422)
        body = _body(resp)
        assert resp.status_code == 422
        assert body["status"] == "error"
        assert body["error"]["message"] == "bad input"
        assert body["error"]["code"] == "validation"

    def test_error_response_default_code(self):
        resp = error_response("something broke")
        assert _body(resp)["error"]["code"] == "unknown_error"
