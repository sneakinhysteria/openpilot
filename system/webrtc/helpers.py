"""Client helpers for talking to webrtcd, backported from upstream openpilot.

Konik's Stable app moved to upstream's `startStream` flow, where the browser
sends the offer and the device answers. hoofpilot still carries the older
flow in system/athena/streamer.py, where the device offers first. Both can
coexist — this only adds the browser-offer path.

Adapted in two places, because this tree's webrtcd is a little older than the
one upstream's helpers were written against:

  - the request body takes a `cameras` list and has no `enabled` field
  - /schema requires a `services` query parameter, so the readiness probe
    passes an empty one rather than requesting the bare path
"""
import time
import requests
from dataclasses import asdict, dataclass, field

WEBRTCD_PORT = 5001


@dataclass
class StreamRequestBody:
  sdp: str
  cameras: list[str]
  bridge_services_in: list[str] = field(default_factory=list)
  bridge_services_out: list[str] = field(default_factory=list)


def post_stream_request(body: StreamRequestBody) -> dict:
  t_start = time.monotonic()
  try:
    resp = requests.post(f"http://localhost:{WEBRTCD_PORT}/stream", json=asdict(body), timeout=10)
    t_end = time.monotonic()
    ret = resp.json()
    ret["time"] = (t_end - t_start) * 1000
    return ret
  except requests.ConnectTimeout as e:
    raise Exception("webrtc took too long to respond.") from e
  except requests.ConnectionError as e:
    raise Exception("webrtc server on device is not running.") from e


def wait_for_webrtcd(max_retries: float = 10) -> None:
  attempts = 0
  while attempts < max_retries:
    try:
      if requests.get(f"http://localhost:{WEBRTCD_PORT}/schema?services=", timeout=1).ok:
        return
    except requests.ConnectionError:
      attempts += 1
      time.sleep(0.5)
  raise TimeoutError("webrtcd did not initialize in time.")
