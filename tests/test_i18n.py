import json

from core import load_i18n_prompts, build_prompt, Question, Option


def test_i18n_overrides_merge(monkeypatch, tmp_path):
    (tmp_path / "i18n").mkdir()
    (tmp_path / "i18n" / "expl_prompts.json").write_text(
        json.dumps({"Polish": "Pytanie:\n{question}\nOpcje:\n{options}\nPoprawna: {correct}"}),
        encoding="utf-8"
    )
    monkeypatch.chdir(tmp_path)
    prompts = load_i18n_prompts()
    assert "Polish" in prompts and "Poprawna:" in prompts["Polish"]


def test_build_prompt_fills_placeholders():
    q = Question(1, "What is AWS?", [Option("A", "A cloud provider"), Option("B", "A database")], ["A"])
    txt = build_prompt(q, "English")
    assert "What is AWS?" in txt and "A. A cloud provider" in txt and "Correct answer: A" in txt
    assert "{" not in txt
