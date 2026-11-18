"""Testa o cliente contra um servidor falso local. NÃO prova compatibilidade com o ACE-Step real."""
import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest

import acestep_client as ac


class Fake(BaseHTTPRequestHandler):
    polls = 0
    fail = False

    def log_message(self, *a):
        pass

    def _send(self, obj, code=200, raw=None):
        body = raw if raw is not None else json.dumps(obj).encode()
        self.send_response(code)
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path == "/health":
            self._send({"data": {"status": "ok"}, "code": 200})
        elif self.path.startswith("/v1/audio"):
            self._send(None, raw=b"RIFFfakewav")
        else:
            self._send({}, 404)

    def do_POST(self):
        n = int(self.headers.get("Content-Length", 0))
        body = json.loads(self.rfile.read(n) or b"{}")
        if self.path == "/release_task":
            self.server.last_payload = body
            self._send({"data": {"task_id": "t1", "status": "queued"}, "code": 200})
        elif self.path == "/query_result":
            Fake.polls += 1
            if Fake.fail:
                self._send({"data": [{"task_id": "t1", "status": 2}]})
            elif Fake.polls < 2:
                self._send({"data": [{"task_id": "t1", "status": 0}]})
            else:
                res = json.dumps([{"file": "/v1/audio?path=%2Ftmp%2Fa.wav", "seed_value": 11},
                                  {"file": "/v1/audio?path=%2Ftmp%2Fb.wav", "seed_value": 12}])
                self._send({"data": [{"task_id": "t1", "status": 1, "result": res}]})


@pytest.fixture()
def server():
    Fake.polls, Fake.fail = 0, False
    srv = HTTPServer(("127.0.0.1", 0), Fake)
    t = threading.Thread(target=srv.serve_forever, daemon=True)
    t.start()
    yield srv, f"http://127.0.0.1:{srv.server_port}"
    srv.shutdown()


def test_build_payload_validation():
    p = ac.build_payload("floresta", duration=60, bpm=90, seed=5, batch=2)
    assert p["audio_duration"] == 60 and p["use_random_seed"] is False and p["seed"] == 5
    for bad in (dict(prompt=""), dict(prompt="x", duration=5), dict(prompt="x", bpm=500), dict(prompt="x", batch=9)):
        with pytest.raises(ValueError):
            ac.build_payload(**bad)


def test_health_and_generate(server, tmp_path):
    srv, url = server
    assert ac.health(url)["code"] == 200
    files = ac.generate(ac.build_payload("combate", 30, 140, batch=2), tmp_path, url, poll=0.01, stem="c")
    assert [f.name for f in files] == ["c_01.wav", "c_02.wav"]
    assert files[0].read_bytes().startswith(b"RIFF")
    meta = json.loads(files[0].with_suffix(".json").read_text(encoding="utf-8"))
    assert meta["generator_name"] == "ACE-Step" and meta["entry"]["seed_value"] == 11
    assert srv.last_payload["bpm"] == 140


def test_failed_task_raises(server, tmp_path):
    Fake.fail = True
    with pytest.raises(ac.AceStepError):
        ac.generate(ac.build_payload("x", 30), tmp_path, server[1], poll=0.01)


def test_unreachable_server_is_clear_error():
    with pytest.raises(ac.AceStepError):
        ac.health("http://127.0.0.1:1")
    assert ac.main(["--url", "http://127.0.0.1:1", "health"]) == 2
