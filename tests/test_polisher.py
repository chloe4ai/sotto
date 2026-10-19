from sotto.config import Config
from sotto.polisher import Polisher, local_polish


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


class _Block:
    def __init__(self, text):
        self.text = text


class _Response:
    def __init__(self, text, stop_reason="end_turn"):
        self.content = [_Block(text)]
        self.stop_reason = stop_reason


class _FakeMessages:
    def __init__(self, response=None, error=None):
        self.response = response
        self.error = error
        self.calls = []

    def create(self, **kwargs):
        self.calls.append(kwargs)
        if self.error is not None:
            raise self.error
        return self.response


class _FakeClient:
    def __init__(self, **kwargs):
        self.messages = _FakeMessages(**kwargs)


def _ai_polisher(client):
    polisher = Polisher(Config(polish="ai"))
    polisher._client = client
    return polisher


def test_ai_polish_returns_the_rewrite():
    client = _FakeClient(response=_Response("Ship it on Friday."))
    assert _ai_polisher(client).polish("um ship it on friday") == "Ship it on Friday."


def test_output_budget_scales_with_input_and_is_capped():
    short = _FakeClient(response=_Response("ok"))
    _ai_polisher(short).polish("hi")
    assert short.messages.calls[0]["max_tokens"] == 1024

    medium = _FakeClient(response=_Response("ok"))
    _ai_polisher(medium).polish("a" * 1000)
    assert medium.messages.calls[0]["max_tokens"] == 3000

    huge = _FakeClient(response=_Response("ok"))
    _ai_polisher(huge).polish("a" * 10_000)
    assert huge.messages.calls[0]["max_tokens"] == 8192


def test_truncated_ai_output_falls_back_to_local(capsys):
    text = "um so the the plan is " + "we ship and then we measure " * 50
    client = _FakeClient(
        response=_Response("So the plan is we ship", stop_reason="max_tokens")
    )

    assert _ai_polisher(client).polish(text) == local_polish(text)
    assert "output limit" in capsys.readouterr().err


def test_ai_error_falls_back_to_local_and_is_logged(capsys):
    client = _FakeClient(error=RuntimeError("connection reset"))

    assert _ai_polisher(client).polish("um, hello there") == "Hello there"
    err = capsys.readouterr().err
    assert "AI polish failed" in err and "connection reset" in err
