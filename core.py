# core.py
import json
import re
from dataclasses import dataclass
from pathlib import Path
from typing import List


# ---- types ----
@dataclass
class Option:  letter: str; text: str


@dataclass
class Question:
    number: int;
    question: str;
    options: List[Option];
    correct: List[str]


# ---- regex ----
OPTION_LINE_RE = re.compile(r"^\s*[-*]?\s*([A-Fa-f])[\.)]\s*(.+?)\s*$")
QUESTION_BLOCK_RE = re.compile(
    r"(\d+)\.\s*(.*?)\n(.*?)<details[^>]*?>\s*<summary[^>]*?>\s*Answer\s*</summary>(.*?)</details>",
    re.DOTALL | re.IGNORECASE,
)
CORRECT_RE = re.compile(r"Correct\s*answer\s*:\s*([A-Za-z,\s]+)", re.IGNORECASE)


# ---- parsing ----
def parse_options(options_raw: str) -> List[Option]:
    options: List[Option] = []
    for line in options_raw.strip().splitlines():
        line = line.rstrip()
        if not line: continue
        m = OPTION_LINE_RE.match(line)
        if m:
            letter, text = m.group(1).upper(), m.group(2).strip()
            options.append(Option(letter, text))
        else:
            letter = chr(ord("A") + len(options))
            options.append(Option(letter, line.lstrip("-* ").strip()))
    return options


def parse_exam(markdown_text: str) -> List[Question]:
    out: List[Question] = []
    for number_str, q_text, options_raw, details_raw in QUESTION_BLOCK_RE.findall(markdown_text):
        options = parse_options(options_raw)
        m = CORRECT_RE.search(details_raw)
        letters = re.sub(r"[^A-Za-z]", "", (m.group(1) if m else details_raw)).upper()
        correct = list(dict.fromkeys(list(letters)))
        out.append(Question(number=int(number_str), question=q_text.strip(), options=options, correct=correct))
    return out


# ---- i18n ----
def load_i18n_prompts():
    defaults = {
        "English": (
            "You are an AWS expert preparing a student for the AWS-Certified-Cloud-Practitioner (CLF-C02) exam.\n"
            "Please explain the following exam question and why the correct answers are correct (and others incorrect).\n\n"
            "Question:\n{question}\n\nOptions:\n{options}\n\nCorrect answer: {correct}\n\n"
            "Give a clear and detailed explanation with reasoning and practical examples if possible."),
        "Russian": (
            "Ты являешься экспертом AWS, готовящим студента к экзамену AWS-Certified-Cloud-Practitioner (CLF-C02).\n"
            "Пожалуйста, объясни следующий экзаменационный вопрос: почему правильные ответы являются верными, а остальные — нет.\n\n"
            "Вопрос:\n{question}\n\nВарианты ответа:\n{options}\n\nПравильный ответ: {correct}\n\n"
            "Объясни понятно, подробно и с пояснениями. Приводи примеры, если уместно."),
        "Polish": (
            "Jesteś ekspertem AWS przygotowującym studenta do egzaminu AWS Certified Cloud Practitioner (CLF-C02).\n"
            "Wyjaśnij poniższe pytanie egzaminacyjne oraz dlaczego poprawne odpowiedzi są poprawne (a pozostałe nie).\n\n"
            "Pytanie:\n{question}\n\nOpcje:\n{options}\n\nPoprawna odpowiedź: {correct}\n\n"
            "Podaj jasne i szczegółowe wyjaśnienie z uzasadnieniem i praktycznymi przykładami."),
        "Spanish": (
            "Eres un experto de AWS que prepara a un estudiante para el examen AWS Certified Cloud Practitioner (CLF-C02).\n"
            "Explica la siguiente pregunta de examen y por qué las respuestas correctas lo son (y las demás no).\n\n"
            "Pregunta:\n{question}\n\nOpciones:\n{options}\n\nRespuesta correcta: {correct}\n\n"
            "Ofrece una explicación clara y detallada con razonamiento y ejemplos prácticos."),
        "German": (
            "Du bist ein AWS-Experte und bereitest einen Studenten auf die Prüfung zum AWS Certified Cloud Practitioner (CLF-C02) vor.\n"
            "Erkläre die folgende Prüfungsfrage und warum die richtigen Antworten richtig sind (und die anderen nicht).\n\n"
            "Frage:\n{question}\n\nOptionen:\n{options}\n\nRichtige Antwort: {correct}\n\n"
            "Gib eine klare und detaillierte Erklärung mit Begründung und praktischen Beispielen."),
        "Italian": (
            "Sei un esperto AWS che prepara uno studente all’esame AWS Certified Cloud Practitioner (CLF-C02).\n"
            "Spiega la seguente domanda d’esame e perché le risposte corrette sono corrette (e le altre no).\n\n"
            "Domanda:\n{question}\n\nOpzioni:\n{options}\n\nRisposta corretta: {correct}\n\n"
            "Fornisci una spiegazione chiara e dettagliata con ragionamenti ed esempi pratici."),
        "French": (
            "Tu es un expert AWS qui prépare un étudiant à l’examen AWS Certified Cloud Practitioner (CLF-C02).\n"
            "Explique la question ci-dessous et pourquoi les bonnes réponses sont correctes (et les autres non).\n\n"
            "Question :\n{question}\n\nOptions :\n{options}\n\nBonne réponse : {correct}\n\n"
            "Donne une explication claire et détaillée avec raisonnement et exemples pratiques."),
    }
    try:
        p = Path("i18n/expl_prompts.json")
        if p.exists():
            overrides = json.loads(p.read_text(encoding="utf-8"))
            if isinstance(overrides, dict):
                defaults.update(overrides)
    except Exception:
        pass
    return defaults


PROMPT_TEMPLATES = load_i18n_prompts()
LANGS = list(PROMPT_TEMPLATES.keys())


def build_prompt(q: Question, lang: str) -> str:
    opts_text = "\n".join(f"{o.letter}. {o.text}" for o in q.options)
    template = PROMPT_TEMPLATES.get(lang) or PROMPT_TEMPLATES["English"]
    return template.format(question=q.question, options=opts_text, correct=", ".join(q.correct))
