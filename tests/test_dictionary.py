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


def test_utf8_entries_survive_a_reload(tmp_path):
    # Windows defaults to the ANSI code page (cp1252) for text files, so
    # Chinese entries used to raise UnicodeDecodeError at startup.
    path = tmp_path / "dictionary.txt"
    path.write_text("云 -> Cloud\n大模型\n", encoding="utf-8")
    d = Dictionary(path)
    d.reload()
    assert d.apply("我用云服务") == "我用Cloud服务"
    assert "大模型" in d.prompt_hint()


def test_ensure_file_writes_utf8(tmp_path):
    path = tmp_path / "sub" / "dictionary.txt"
    d = Dictionary(path)
    d.ensure_file()
    with path.open("a", encoding="utf-8") as f:
        f.write("云 -> Cloud\n")
    d.reload()
    assert d.corrections == [("云", "Cloud")]


def test_replacement_backslashes_are_literal(tmp_path):
    d = make_dict(tmp_path, "temp folder -> C:\\Temp\\new\nsmiley -> \\o/\n")
    assert d.apply("open temp folder") == "open C:\\Temp\\new"
    assert d.apply("smiley") == "\\o/"
