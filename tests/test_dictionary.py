from sotto.dictionary import Dictionary


def make_dict(tmp_path, content):
    path = tmp_path / "dictionary.txt"
    path.write_text(content)
    return Dictionary(path)


def test_corrections_applied_case_insensitive(tmp_path):
    d = make_dict(tmp_path, "cloudy tan -> Chloe Tan\n")
    assert d.apply("hi Cloudy Tan!") == "hi Chloe Tan!"


def test_terms_feed_prompt_hint(tmp_path):
    d = make_dict(tmp_path, "Kubernetes\nTypeless\nwrong -> Right\n")
    hint = d.prompt_hint()
    assert "Kubernetes" in hint and "Right" in hint


def test_comments_and_blank_lines_ignored(tmp_path):
    d = make_dict(tmp_path, "# comment\n\nKubernetes  # inline\n")
    assert d.terms == ["Kubernetes"]


def test_missing_file(tmp_path):
    d = Dictionary(tmp_path / "nope.txt")
    assert d.apply("unchanged") == "unchanged"
    assert d.prompt_hint() == ""
