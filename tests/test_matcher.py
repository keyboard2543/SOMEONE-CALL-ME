"""Quick tests for name matcher (no mic / no model required)."""

from someone_call_me.matcher import NameMatcher


def test_thai_name_exact_and_affixes():
    m = NameMatcher(["สมชาย"], sensitivity=68)
    assert m.score_text("สมชาย").matched
    assert m.score_text("คุณสมชายครับ").matched
    assert m.score_text("พี่สมชาย").matched
    assert m.score_text("สมชายอยู่ไหม").matched


def test_thai_similar_and_unrelated():
    m = NameMatcher(["สมชาย"], sensitivity=68)
    assert m.score_text("สมชัย").matched  # similar pronunciation
    assert not m.score_text("สมศักดิ์").matched
    assert not m.score_text("สม").matched


def test_english_name():
    m = NameMatcher(["John"], sensitivity=68)
    assert m.score_text("hey john").matched
    assert m.score_text("jon").matched
    assert m.score_text("please call john now").matched
    assert not m.score_text("hello world").matched
    assert not m.score_text("something completely different").matched


if __name__ == "__main__":
    test_thai_name_exact_and_affixes()
    test_thai_similar_and_unrelated()
    test_english_name()
    print("all matcher tests passed")
