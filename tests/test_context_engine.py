"""ContextCompressor: compresses the middle, protects head (cache prefix) + recent turns."""
from edith.core.context_engine import ContextCompressor, estimate_tokens
from edith.core.llm import Message


def _msgs(n):
    out = [Message("system", "SYS")]
    for i in range(n):
        out.append(Message("user" if i % 2 == 0 else "assistant", f"message number {i} " * 50))
    return out


def test_no_compress_when_small():
    eng = ContextCompressor()
    m = _msgs(4)
    assert not eng.should_compress(m)
    assert eng.compress(m) == m


def test_compress_protects_head_and_tail():
    eng = ContextCompressor(protect_first_n=2, protect_last_n=3)
    m = _msgs(30)
    out = eng.compress(m)
    assert out[0].role == "system" and out[0].content == "SYS"   # cache prefix intact
    assert out[1].content == m[1].content                         # first protected verbatim
    assert out[-3:] == m[-3:]                                     # last 3 verbatim
    assert any("context compacted" in x.content for x in out)     # summary inserted
    assert len(out) < len(m)                                      # actually shrank


def test_threshold_triggers():
    eng = ContextCompressor(max_tokens=200, threshold_percent=0.5)
    assert eng.should_compress(_msgs(20))
