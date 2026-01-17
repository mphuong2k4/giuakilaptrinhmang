import json
from common.protocol import Message, loads_line

def test_message_roundtrip():
    m = Message(action="ping", data={"x": 1})
    line = m.to_json_line()
    obj = loads_line(line.strip())
    assert obj["action"] == "ping"
    assert obj["data"]["x"] == 1
