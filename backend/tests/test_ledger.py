from app.ledger import Ledger


def test_chain_verifies_and_tamper_is_caught():
    led = Ledger()
    led.record("a", {"x": 1})
    led.record("b", {"y": [1, 2]})
    assert all(r["payload_ok"] and r["link_ok"] for r in led.verify())
    assert led.tamper()
    res = led.verify()
    assert not res[0]["payload_ok"]
    assert led.restore()
    assert all(r["payload_ok"] and r["link_ok"] for r in led.verify())


def test_payload_is_copied_not_aliased():
    led, payload = Ledger(), {"k": "v"}
    led.record("t", payload)
    payload["k"] = "changed"
    assert all(r["payload_ok"] for r in led.verify())


def test_broken_link_detected():
    led = Ledger()
    led.record("a", {})
    led.record("b", {})
    led.entries[1].prev = "f" * 64
    assert not led.verify()[1]["link_ok"]


def test_topic_and_tx_shape():
    led = Ledger()
    e = led.record("a", {})
    assert led.topic.startswith("0.0.") and e.tx.startswith(led.topic + "@")
