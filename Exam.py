# Exam.py
import re
import urllib.parse
from pathlib import Path
from typing import List, Dict

import streamlit as st
import streamlit.components.v1 as components

from core import (
    Option,
    Question,
    parse_exam,
    build_prompt,
    LANGS,
)


# ========================= Caching & IO ========================= #

@st.cache_data(show_spinner=False)
def load_exam_files(exam_folder: Path) -> List[str]:
    if not exam_folder.exists():
        return []
    return sorted(
        [f.name for f in exam_folder.glob("*.md")],
        key=lambda s: int(re.search(r"(\d+)", s).group(1)) if re.search(r"(\d+)", s) else 0,
    )


@st.cache_resource(show_spinner=False)
def load_questions(path: Path) -> List[Question]:
    text = path.read_text(encoding="utf-8")
    return parse_exam(text)


# ========================= UI ========================= #

def main():
    st.set_page_config(page_title="AWS Exam Practice", layout="wide")

    version = Path("version.txt").read_text(encoding="utf-8").strip() if Path("version.txt").exists() else "dev"
    st.title(f"📘 AWS Certified Cloud Practitioner Practice Exam  (v{version})")

    # Sidebar
    with st.sidebar:
        st.header("Settings")
        lang = st.selectbox("🌐 Explanation language", LANGS, index=LANGS.index("English") if "English" in LANGS else 0)
        mode = st.radio("Mode", ["Practice", "Exam"], horizontal=True, index=0)

        exam_folder = Path("exams")
        files = load_exam_files(exam_folder)
        if not files:
            st.error("The exams folder is empty or missing. Add .md files with exams.")
            st.stop()
        selected_file = st.selectbox("Exam file", files)

    # ===== Bug report banner & floating action button =====
    REPO = "https://github.com/k30medvedev/aws-clf-exam-prep"

    def make_bug_url(version_str: str, exam_file: str) -> str:
        title = f"[bug] v{version_str} · {exam_file}"
        body = f"""**Version**: v{version_str}
**Exam file**: {exam_file}

**Steps to reproduce**
1.
2.

**Expected**
-

**Actual**
-

**Screenshots / logs**
-"""
        return (
            f"{REPO}/issues/new"
            f"?labels=bug"
            f"&title={urllib.parse.quote_plus(title)}"
            f"&body={urllib.parse.quote_plus(body)}"
        )

    bug_url = make_bug_url(version, selected_file)

    st.info(f"🐞 Found a typo or bug? [Create an issue]({bug_url}) — it takes a minute.")

    components.html(f"""
    <style>
    .bug-fab {{
      position: fixed; right: 18px; bottom: 18px; z-index: 9999;
      background: #ef4444; color: #fff; padding: 10px 14px; border-radius: 9999px;
      font: 600 14px/1.1 system-ui,-apple-system,Segoe UI,Roboto,Ubuntu;
      box-shadow: 0 6px 16px rgba(0,0,0,.2); text-decoration: none;
    }}
    .bug-fab:hover {{ opacity:.92 }}
    </style>
    <a class="bug-fab" href="{bug_url}" target="_blank" rel="noopener">🐞 Report a bug</a>
    """, height=0)

    # Init state on file change
    if st.session_state.get("last_exam") != selected_file:
        qs = load_questions(Path("exams") / selected_file)
        st.session_state.questions = qs
        st.session_state.current = 0
        st.session_state.answers_by_num = {}  # number -> answer dict
        st.session_state.score = 0
        st.session_state.last_exam = selected_file
        st.session_state.show_answer = False
        st.session_state.selections = {}  # question_number -> list[str]

    questions: List[Question] = st.session_state.get("questions", [])
    if not questions:
        st.warning("Failed to parse questions. Check the .md format.")
        st.stop()

    current = st.session_state.current

    # Progress + restart
    a, b = st.columns([3, 1])
    with a:
        st.write(f"Progress: **{min(current + 1, len(questions))} / {len(questions)}**")
        st.progress((current) / max(len(questions), 1))
    with b:
        if st.button("🔁 Restart exam", use_container_width=True):
            for k in list(st.session_state.keys()):
                del st.session_state[k]
            st.rerun()

    # ===== Render current question =====
    if current < len(questions):
        q = questions[current]
        st.subheader(f"Question {q.number}")
        st.write(q.question)

        is_multi = len(q.correct) > 1
        if is_multi:
            st.caption(f"Correct count: choose {len(q.correct)}")

        # Pretty labels
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
                def_idx = letters.index(default[0]) if default and default[0] in letters else 0
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

        # Persist selection
        st.session_state.selections[q.number] = selected_letters

        # Controls
        if peek and mode == "Practice":
            st.session_state.show_answer = True

        if prev and mode == "Practice":
            st.session_state.show_answer = False
            st.session_state.current = max(0, current - 1)
            st.rerun()

        if st.session_state.get("show_answer", False) and mode == "Practice":
            st.info(f"💡 **Correct answer:** {', '.join(q.correct)}")

        def do_submit(sel_letters: List[str]):
            if is_multi and not sel_letters:
                st.warning("You have not selected any options.")
                return
            correct_set = set(q.correct)
            user_set = set(sel_letters)
            is_correct = user_set == correct_set

            payload = {
                "number": q.number,
                "question": q.question,
                "options": [f"{o.letter}. {o.text}" for o in q.options],
                "selected": sel_letters,
                "correct": q.correct,
                "is_correct": is_correct,
            }
            st.session_state.answers_by_num[q.number] = payload
            st.session_state.score = sum(1 for v in st.session_state.answers_by_num.values() if v["is_correct"])
            st.session_state.current += 1
            st.session_state.show_answer = False
            st.rerun()

        if submit:
            do_submit(selected_letters)

        # Copy prompt
        st.markdown("---")
        st.markdown("**Need help understanding this question?**")
        prompt = build_prompt(q, lang)
        safe_prompt = prompt.replace("</", "</ ")

        components.html(
            f"""
            <textarea id="prompt-text" style="position:absolute; left:-9999px;">{safe_prompt}</textarea>
            <button id="copy-btn" style="margin-top:10px;">📋 Copy prompt</button>
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

    # ===== Results =====
    else:
        st.success("✅ Exam Completed!")
        total = len(questions)
        answered = len(st.session_state.answers_by_num)
        correct = st.session_state.score
        percent = (correct / total) * 100 if total else 0.0
        st.write(f"**Answered:** {answered} / {total}")
        st.write(f"**Correct:** {correct} / {total}")
        st.write(f"**Percentage:** {percent:.2f}%")
        if percent >= 75:
            st.success("🎉 You passed the exam!")
        else:
            st.warning("❌ You did not reach the passing score (75%).")

        st.markdown("---")
        st.subheader("📋 Review of Your Answers")
        show_only_incorrect = st.checkbox("Show only incorrect answers")

        for num in sorted(st.session_state.answers_by_num.keys()):
            ans = st.session_state.answers_by_num[num]
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

        if st.button("🔁 Restart Exam"):
            for key in list(st.session_state.keys()):
                del st.session_state[key]
            st.rerun()


if __name__ == "__main__":
    main()
