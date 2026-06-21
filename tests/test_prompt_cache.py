"""Sacred prompt caching: <=4 breakpoints, system + last-3, no input mutation."""
from edith.core.prompt_cache import prepare_anthropic_caching


def _count_markers(blocks):
    n = 0
    for b in blocks or []:
        if isinstance(b, dict) and "cache_control" in b:
            n += 1
    return n


def test_system_and_last_three_are_marked():
    convo = [{"role": "user", "content": f"m{i}"} for i in range(6)]
    sysp, out = prepare_anthropic_caching("SYS", convo)
    assert _count_markers(sysp) == 1                      # system cached
    marked_msgs = sum(1 for m in out if _count_markers(m["content"]))
    assert marked_msgs == 3                               # last 3 only -> 4 total breakpoints


def test_no_system_uses_four_message_breakpoints():
    convo = [{"role": "user", "content": f"m{i}"} for i in range(6)]
    sysp, out = prepare_anthropic_caching(None, convo)
    assert sysp is None
    assert sum(1 for m in out if _count_markers(m["content"])) == 4


def test_does_not_mutate_input():
    convo = [{"role": "user", "content": "hello"}]
    prepare_anthropic_caching("SYS", convo)
    assert convo[0]["content"] == "hello"                 # original untouched


def test_string_content_wrapped_into_block():
    _, out = prepare_anthropic_caching(None, [{"role": "user", "content": "hi"}])
    block = out[0]["content"]
    assert isinstance(block, list) and block[0]["text"] == "hi"
    assert block[0]["cache_control"]["type"] == "ephemeral"
