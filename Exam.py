import json
import re
import urllib.parse
from dataclasses import dataclass
from pathlib import Path
from typing import List, Dict

import streamlit as st
import streamlit.components.v1 as components


# ========================= Utils & Types ========================= #

@dataclass
class Option:
    letter: str
    text: str


@dataclass
class Question:
    number: int
    question: str
    options: List[Option]
    correct: List[str]  # list of letters, e.g. ["A", "C"]


OPTION_LINE_RE = re.compile(r"^\s*[-*]?\s*([A-Fa-f])[\.)]\s*(.+?)\s*$")

QUESTION_BLOCK_RE = re.compile(
    # 1: number, 2: question text, 3: options block, 4: details block (incl. correct)
    r"(\d+)\.\s*(.*?)\n(.*?)<details[^>]*?>\s*<summary[^>]*?>\s*Answer\s*</summary>(.*?)</details>",
    re.DOTALL | re.IGNORECASE,
)

CORRECT_RE = re.compile(r"Correct\s*answer\s*:\s*([A-Za-z,\s]+)", re.IGNORECASE)


# ========================= Parsing ========================= #

def parse_options(options_raw: str) -> List[Option]:
    options: List[Option] = []
    for line in options_raw.strip().splitlines():
        line = line.rstrip()
        if not line:
            continue
        m = OPTION_LINE_RE.match(line)
        if m:
            letter, text = m.group(1).upper(), m.group(2).strip()
            options.append(Option(letter=letter, text=text))
        else:
            # Fallback: try to treat it as a bullet without letter (rare)
            # Assign synthetic letter based on current length (A, B, C...)
            letter = chr(ord('A') + len(options))
            clean = line.lstrip("-* ")
            options.append(Option(letter=letter, text=clean))
    return options


def parse_exam(markdown_text: str) -> List[Question]:
    questions: List[Question] = []
    for m in QUESTION_BLOCK_RE.findall(markdown_text):
        number_str, q_text, options_raw, details_raw = m
        number = int(number_str)
        q_text = q_text.strip()
        options = parse_options(options_raw)

        correct_match = CORRECT_RE.search(details_raw)
        correct_letters: List[str] = []
        if correct_match:
            # Normalize like "A, C" -> ["A", "C"]
            letters = re.sub(r"[^A-Za-z]", "", correct_match.group(1)).upper()
            correct_letters = list(dict.fromkeys(list(letters)))  # preserve order, unique
        else:
            # If not found, try the whole details block for letters
            letters = re.sub(r"[^A-Za-z]", "", details_raw).upper()
            correct_letters = list(dict.fromkeys(list(letters)))

        questions.append(Question(number=number, question=q_text, options=options, correct=correct_letters))

    return questions


# ========================= Data Loading (cached) ========================= #

@st.cache_data(show_spinner=False)
def load_exam_files(exam_folder: Path) -> List[str]:
    if not exam_folder.exists():
        return []
    return sorted([f.name for f in exam_folder.glob("*.md")],
                  key=lambda s: int(re.search(r"(\d+)", s).group(1)) if re.search(r"(\d+)", s) else 0)


@st.cache_resource(show_spinner=False)
def load_questions(path: Path) -> List[Question]:
    text = path.read_text(encoding="utf-8")
    return parse_exam(text)


# ========================= i18n & Prompt helpers ========================= #

def load_i18n_prompts():
    """Return a dict: language -> template string with {question}, {options}, {correct} placeholders.
    Optionally merges overrides from i18n/expl_prompts.json (if present)."""
    defaults = {
        "English": (
            "You are an AWS expert preparing a student for the AWS-Certified-Cloud-Practitioner (CLF-C02) exam.\n"
            "Please explain the following exam question and why the correct answers are correct (and others incorrect).\n\n"
            "Question:\n{question}\n\n"
            "Options:\n{options}\n\n"
            "Correct answer: {correct}\n\n"
            "Give a clear and detailed explanation with reasoning and practical examples if possible."
        ),
        "Russian": (
            "Ты являешься экспертом AWS, готовящим студента к экзамену AWS-Certified-Cloud-Practitioner (CLF-C02).\n"
            "Пожалуйста, объясни следующий экзаменационный вопрос: почему правильные ответы являются верными, а остальные — нет.\n\n"
            "Вопрос:\n{question}\n\n"
            "Варианты ответа:\n{options}\n\n"
            "Правильный ответ: {correct}\n\n"
            "Объясни понятно, подробно и с пояснениями. Приводи примеры, если уместно."
        ),
        "Polish": (
            "Jesteś ekspertem AWS przygotowującym studenta do egzaminu AWS Certified Cloud Practitioner (CLF-C02).\n"
            "Wyjaśnij poniższe pytanie egzaminacyjne oraz dlaczego poprawne odpowiedzi są poprawne (a pozostałe nie).\n\n"
            "Pytanie:\n{question}\n\n"
            "Opcje:\n{options}\n\n"
            "Poprawna odpowiedź: {correct}\n\n"
            "Podaj jasne i szczegółowe wyjaśnienie z uzasadnieniem i praktycznymi przykładami."
        ),
        "Spanish": (
            "Eres un experto de AWS que prepara a un estudiante para el examen AWS Certified Cloud Practitioner (CLF-C02).\n"
            "Explica la siguiente pregunta de examen y por qué las respuestas correctas lo son (y las demás no).\n\n"
            "Pregunta:\n{question}\n\n"
            "Opciones:\n{options}\n\n"
            "Respuesta correcta: {correct}\n\n"
            "Ofrece una explicación clara y detallada con razonamiento y ejemplos prácticos."
        ),
        "German": (
            "Du bist ein AWS-Experte und bereitest einen Studenten auf die Prüfung zum AWS Certified Cloud Practitioner (CLF-C02) vor.\n"
            "Erkläre die folgende Prüfungsfrage und warum die richtigen Antworten richtig sind (und die anderen nicht).\n\n"
            "Frage:\n{question}\n\n"
            "Optionen:\n{options}\n\n"
            "Richtige Antwort: {correct}\n\n"
            "Gib eine klare und detaillierte Erklärung mit Begründung und praktischen Beispielen."
        ),
        "Italian": (
            "Sei un esperto AWS che prepara uno studente all’esame AWS Certified Cloud Practitioner (CLF-C02).\n"
            "Spiega la seguente domanda d’esame e perché le risposte corrette sono corrette (e le altre no).\n\n"
            "Domanda:\n{question}\n\n"
            "Opzioni:\n{options}\n\n"
            "Risposta corretta: {correct}\n\n"
            "Fornisci una spiegazione chiara e dettagliata con ragionamenti ed esempi pratici."
        ),
        "French": (
            "Tu es un expert AWS qui prépare un étudiant à l’examen AWS Certified Cloud Practitioner (CLF-C02).\n"
            "Explique la question ci‑dessous et pourquoi les bonnes réponses sont correctes (et les autres non).\n\n"
            "Question :\n{question}\n\n"
            "Options :\n{options}\n\n"
            "Bonne réponse : {correct}\n\n"
            "Donne une explication claire et détaillée avec raisonnement et exemples pratiques."
        ),
    }
    try:
        p = Path("i18n/expl_prompts.json")
        if p.exists():
            overrides = json.loads(p.read_text(encoding="utf-8"))
            if isinstance(overrides, dict):
                defaults.update(overrides)
    except Exception:
        # ignore malformed overrides
        pass
    return defaults


PROMPT_TEMPLATES = load_i18n_prompts()
LANGS = list(PROMPT_TEMPLATES.keys())


def build_prompt(q: Question, lang: str) -> str:
    opts_lines = [f"{o.letter}. {o.text}" for o in q.options]
    opts_text = "\n".join(opts_lines)
    template = PROMPT_TEMPLATES.get(lang) or PROMPT_TEMPLATES.get("English")
    return template.format(question=q.question, options=opts_text, correct=", ".join(q.correct))


# ========================= App ========================= #

st.set_page_config(page_title="AWS Exam Practice", layout="wide")

# Version label (non-fatal)
version = Path("version.txt").read_text(encoding="utf-8").strip() if Path("version.txt").exists() else "dev"

st.title(f"📘 AWS Certified Cloud Practitioner Practice Exam  (v{version})")

# Sidebar controls
with st.sidebar:
    st.header("Settings")
    lang = st.selectbox("🌐 Explanation language", LANGS, index=LANGS.index("English") if "English" in LANGS else 0)
    mode = st.radio("Mode", ["Practice", "Exam"], horizontal=True, index=0)

    exam_folder = Path("exams")
    files = load_exam_files(exam_folder)
    if not files:
        st.error("The exams folder is empty or missing. Add .md files with exams")
        st.stop()

    selected_file = st.selectbox("Exam file", files)

# Init state when file changes
if st.session_state.get("last_exam") != selected_file:
    qs = load_questions(Path("exams") / selected_file)
    st.session_state.questions = qs
    st.session_state.current = 0
    st.session_state.score = 0
    st.session_state.answers = []
    st.session_state.last_exam = selected_file
    st.session_state.show_answer = False
    st.session_state.selections = {}  # question_number -> list[str]
    st.session_state.hk = ""

questions: List[Question] = st.session_state.get("questions", [])
if not questions:
    st.warning("Failed to parse questions. Check the format of the .md file")
    st.stop()

current = st.session_state.current

# hidden input for hotkeys (written by JS)
_ = st.text_input("Hotkey", st.session_state.get("hk", ""), key="hk", label_visibility="collapsed")

a, b = st.columns([3, 1])
with a:
    st.write(f"Progress: **{current + 1 if current < len(questions) else len(questions)} / {len(questions)}**")
    st.progress((current) / max(len(questions), 1))
with b:
    if st.button("🔄 Restart exam", use_container_width=True):
        for k in list(st.session_state.keys()):
            del st.session_state[k]
        st.rerun()

if current < len(questions):
    q = questions[current]
    st.subheader(f"Question {q.number}")
    st.write(q.question)

    is_multi = len(q.correct) > 1

    if is_multi:
        st.caption(f"Correct count: choose {len(q.correct)}")

    # Prepare mapping for pretty labels
    letter_to_text: Dict[str, str] = {o.letter: o.text for o in q.options}
    letters = [o.letter for o in q.options]

    with st.form(key=f"qform_{q.number}", clear_on_submit=False):
        if is_multi:
            default = st.session_state.selections.get(q.number, [])
            selected_letters = st.multiselect(
                "Select all that apply:",
                letters,
                default=default,
                format_func=lambda L: f"{L}. {letter_to_text[L]}",
            )
        else:
            default = st.session_state.selections.get(q.number, [letters[0]])
            # Convert default to index if present
            def_idx = 0
            if default and default[0] in letters:
                def_idx = letters.index(default[0])
            selected_letter = st.radio(
                "Select one answer:",
                letters,
                index=def_idx,
                format_func=lambda L: f"{L}. {letter_to_text[L]}",
            )
            selected_letters = [selected_letter]

        c1, c2, c3 = st.columns([1, 1, 1])
        peek = c1.form_submit_button("👁 Show answer", disabled=(mode != "Practice"))
        prev = c2.form_submit_button("◀ Previous", disabled=(current == 0 or mode != "Practice"))
        submit = c3.form_submit_button("Submit answer")

    # Persist selection immediately
    st.session_state.selections[q.number] = selected_letters

    if peek:
        st.session_state.show_answer = True

    if prev and mode == "Practice":
        st.session_state.show_answer = False
        st.session_state.current = max(0, current - 1)
        st.rerun()

    if st.session_state.get("show_answer", False) and mode == "Practice":
        st.info(f"💡 **Correct answer:** {', '.join(q.correct)}")


    def do_submit(sel_letters: List[str]):
        # Validate empty selection for multi
        if is_multi and not sel_letters:
            st.warning("You have not selected any options")
            return
        correct_set = set(q.correct)
        user_set = set(sel_letters)
        is_correct = user_set == correct_set
        if is_correct:
            st.session_state.score += 1
        st.session_state.answers.append({
            "number": q.number,
            "question": q.question,
            "options": [f"{o.letter}. {o.text}" for o in q.options],
            "selected": sel_letters,
            "correct": q.correct,
            "is_correct": is_correct,
        })
        st.session_state.current += 1
        st.session_state.show_answer = False
        st.rerun()


    if submit:
        do_submit(selected_letters)

    # Hotkeys: 1..9 toggle/select, Enter submits
    components.html(
        """
        <script>
        (function(){
          function send(v){
            const inputs = Array.from(parent.document.querySelectorAll('input'));
            const target = inputs.find(el => el.getAttribute('aria-label') === 'Hotkey');
            if(!target) return;
            target.value = v;
            target.dispatchEvent(new Event('input', { bubbles: true }));
          }
          window.addEventListener('keydown', function(e){
            if (e.isComposing) return;
            const tag = (e.target && e.target.tagName || '').toLowerCase();
            if (tag === 'input' || tag === 'textarea') return;
            if (e.key === 'Enter') { send('ENTER'); }
            else if (/^[1-9]$/.test(e.key)) { send('NUM:' + e.key); }
          });
        })();
        </script>
        """,
        height=0,
    )

    hk = st.session_state.get("hk", "")
    if hk:
        if hk.startswith("NUM:"):
            try:
                idx = int(hk.split(":", 1)[1]) - 1
                if 0 <= idx < len(letters):
                    if is_multi:
                        cur = set(st.session_state.selections.get(q.number, []))
                        letter = letters[idx]
                        if letter in cur:
                            cur.remove(letter)
                        else:
                            cur.add(letter)
                        st.session_state.selections[q.number] = list(cur)
                    else:
                        st.session_state.selections[q.number] = [letters[idx]]
                st.session_state.hk = ""
                st.rerun()
            except Exception:
                st.session_state.hk = ""
        elif hk == "ENTER":
            st.session_state.hk = ""
            sel = st.session_state.selections.get(q.number, selected_letters)
            do_submit(sel)

    # Build & copy prompt for ChatGPT
    st.markdown("---")
    st.markdown("**Need help understanding this question?**")

    prompt = build_prompt(q, lang)
    safe_prompt = prompt.replace("</", "</ ")  # slightly reduce risk inside HTML

    components.html(
        f"""
        <textarea id=\"prompt-text\" style=\"position:absolute; left:-9999px;\">{safe_prompt}</textarea>
        <button id=\"copy-btn\" style=\"margin-top:10px;\">📋 Copy prompt</button>
        <script>
        const btn = document.getElementById('copy-btn');
        btn.addEventListener('click', async () => {{
            const ta = document.getElementById('prompt-text');
            try {{
                await navigator.clipboard.writeText(ta.value);
                btn.innerText = '✅ Copied';
                setTimeout(() => btn.innerText = '📋 Copy prompt', 1500);
            }} catch (e) {{
                ta.select(); document.execCommand('copy');
                btn.innerText = '✅ Copied';
                setTimeout(() => btn.innerText = '📋 Copy prompt', 1500);
            }}
        }});
        </script>
        """,
        height=48,
    )

else:
    st.success("✅ Exam Completed!")
    total = len(questions)
    correct = st.session_state.score
    percent = (correct / total) * 100 if total else 0.0
    st.write(f"**Correct answers:** {correct} / {total}")
    st.write(f"**Percentage:** {percent:.2f}%")
    if percent >= 75:
        st.success("🎉 You passed the exam!")
    else:
        st.warning("❌ You did not reach the passing score (75%).")

    st.markdown("---")
    st.subheader("📋 Review of Your Answers")
    show_only_incorrect = st.checkbox("Show only incorrect answers")

    for ans in st.session_state.answers:
        if show_only_incorrect and ans["is_correct"]:
            continue

        st.markdown(f"### Question {ans['number']} — {'✅ Correct' if ans['is_correct'] else '❌ Incorrect'}")
        st.markdown(f"**{ans['question']}**")

        st.markdown("**Options:**")
        for opt in ans["options"]:
            letter = opt.split(".")[0]
            if letter in ans["correct"] and letter in ans["selected"]:
                st.markdown(f"- ✔️ **{opt}**")
            elif letter in ans["correct"]:
                st.markdown(f"- ✅ {opt}")
            elif letter in ans["selected"]:
                st.markdown(f"- ❌ {opt}")
            else:
                st.markdown(f"- {opt}")

        st.markdown(f"**Your answer:** {', '.join(ans['selected']) or '—'}")
        st.markdown(f"**Correct answer:** {', '.join(ans['correct'])}")

        # Build a fresh prompt for the review item
        q_for_prompt = Question(
            number=ans["number"],
            question=ans["question"],
            options=[Option(letter=o.split(".")[0], text=o.split(".", 1)[1].strip()) for o in ans["options"]],
            correct=ans["correct"],
        )
        prompt = build_prompt(q_for_prompt, lang)
        chat_url = "https://chat.openai.com/?q=" + urllib.parse.quote(prompt)
        st.markdown(f"[💬 Ask ChatGPT for explanation]({chat_url})", unsafe_allow_html=True)
        st.markdown("---")

    if st.button("🔄 Restart Exam"):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()
