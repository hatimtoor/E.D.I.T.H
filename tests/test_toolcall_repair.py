"""Tool-call repair: recover tool calls models emit as text (owl-alpha/LongCat, Hermes, fenced)."""
from edith.core.toolcall_repair import parse_text_tool_calls, strip_tool_call_text


def test_longcat_format():
    txt = ("Let me search.\n<longcat_tool_call>web_search\n"
           "<longcat_arg_key>query</longcat_arg_key>\n"
           "<longcat_arg_value>Eiffel Tower height</longcat_arg_value>\n</longcat_tool_call>")
    calls = parse_text_tool_calls(txt)
    assert calls == [{"name": "web_search",
                      "arguments": {"query": "Eiffel Tower height"}, "id": "rep0"}]
    assert "longcat" not in strip_tool_call_text(txt)


def test_hermes_xml_json():
    txt = '<tool_call>{"name": "remember", "arguments": {"text": "x"}}</tool_call>'
    calls = parse_text_tool_calls(txt)
    assert calls[0]["name"] == "remember" and calls[0]["arguments"] == {"text": "x"}


def test_fenced_json():
    txt = 'Sure.\n```json\n{"name": "web_search", "arguments": {"query": "cats"}}\n```'
    calls = parse_text_tool_calls(txt)
    assert calls[0]["name"] == "web_search"


def test_plain_text_is_not_a_tool_call():
    assert parse_text_tool_calls("The Eiffel Tower is 330m tall.") == []


def test_llm_response_repairs(monkeypatch):
    # _repair_if_needed wires it into the response path
    from edith.core.llm import _repair_if_needed
    txt = ("<longcat_tool_call>recall<longcat_arg_key>query</longcat_arg_key>"
           "<longcat_arg_value>budget</longcat_arg_value></longcat_tool_call>")
    out_text, calls = _repair_if_needed(txt, [])
    assert calls and calls[0]["name"] == "recall"
