from sotto.polisher import local_polish


def test_removes_english_fillers():
    assert local_polish("um, so I think, uh, we should ship it") == (
        "So I think, we should ship it"
    )


def test_removes_chinese_fillers():
    assert local_polish("嗯，我觉得这个方案可以") == "我觉得这个方案可以"


def test_collapses_repeated_words():
    assert local_polish("we should should ship it") == "We should ship it"


def test_capitalizes_and_tightens_punctuation():
    assert local_polish("hello , world .") == "Hello, world."


def test_keeps_meaningful_words():
    text = "I like this design because it is humble"
    assert local_polish(text) == "I like this design because it is humble"


def test_empty_input():
    assert local_polish("") == ""
