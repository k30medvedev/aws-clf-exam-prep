import os
import re
from datetime import datetime, timedelta
import urllib.parse
import streamlit as st
import streamlit.components.v1 as components


def parse_exam(markdown_text):
    pattern = re.compile(
        r"(\d+)\. (.*?)\n(.*?)<details[^>]*?>\s*<summary[^>]*?>Answer</summary>\s*Correct answer: (.*?)\s*</details>",
        re.DOTALL | re.IGNORECASE
    )
    matches = pattern.findall(markdown_text)

    questions = []
    for match in matches:
        number, question, options_raw, correct_raw = match
        options = [line.strip("- ").strip() for line in options_raw.strip().split("\n") if line.strip()]
        correct_raw = correct_raw.strip().upper().replace(",", "").replace(" ", "")
        correct_raw = re.match(r"^[A-E]+", correct_raw)
        correct = list(correct_raw.group(0)) if correct_raw else []
        questions.append({
            "number": int(number),
            "question": question.strip(),
            "options": options,
            "correct": correct
        })
    return questions


exam_folder = "exams"

def extract_exam_number(filename):
    match = re.search(r"(\d+)", filename)
    return int(match.group(1)) if match else 0

exam_files = sorted(
    [f for f in os.listdir(exam_folder) if f.endswith(".md")],
    key=extract_exam_number
)

st.set_page_config(page_title="AWS Exam Practice", layout="wide")
try:
    with open("version.txt", "r", encoding="utf-8") as vfile:
        version = vfile.read().strip()
except FileNotFoundError:
    version = "dev"

st.title(f"📘 AWS Certified Cloud Practitioner Practice Exam  (v{version})")

# Язык объяснений
if "prompt_lang" not in st.session_state:
    st.session_state.prompt_lang = "English"

st.session_state.prompt_lang = st.radio(
    "🌐 Select explanation language:",
    ["English", "Russian"],
    horizontal=True,
    index=0 if st.session_state.prompt_lang == "English" else 1
)

selected_exam_file = st.selectbox("Select an exam file", exam_files)

if "questions" not in st.session_state or st.session_state.get("last_exam") != selected_exam_file:
    with open(os.path.join(exam_folder, selected_exam_file), "r", encoding="utf-8") as f:
        content = f.read()
    st.session_state.questions = parse_exam(content)
    st.session_state.current = 0
    st.session_state.score = 0
    st.session_state.answers = []
    st.session_state.last_exam = selected_exam_file
    st.session_state.start_time = datetime.now()
    st.session_state.end_time = st.session_state.start_time + timedelta(minutes=90)

remaining = st.session_state.end_time - datetime.now()
if remaining.total_seconds() > 0:
    st.info(f"⏱ Time remaining: {str(remaining).split('.')[0]}")
else:
    st.error("⏰ Time is up! Exam has ended.")
    st.session_state.current = len(st.session_state.questions)

questions = st.session_state.questions
current = st.session_state.current

if current < len(questions):
    q = questions[current]
    st.subheader(f"Question {q['number']}: {q['question']}")

    selected_letters = []

    if len(q["correct"]) > 1:
        st.write("Select all that apply:")
        for i, opt in enumerate(q["options"]):
            if st.checkbox(opt, key=f"{current}_{i}"):
                selected_letters.append(opt.split(".")[0])
    else:
        selected_opt = st.radio("Select one answer:", q["options"], key=current)
        selected_letters.append(selected_opt.split(".")[0])

    # КНОПКА SUBMIT СРАЗУ ПОД ВАРИАНТАМИ
    if st.button("Submit Answer"):
        correct_set = set(q["correct"])
        user_set = set(selected_letters)
        is_correct = user_set == correct_set
        if is_correct:
            st.session_state.score += 1
        st.session_state.answers.append({
            "number": q["number"],
            "question": q["question"],
            "options": q["options"],
            "selected": selected_letters,
            "correct": q["correct"],
            "is_correct": is_correct
        })
        st.session_state.current += 1
        st.rerun()

    # PROMPT после вопроса
    st.markdown("---")
    st.markdown("**Need help understanding this question?**")

    opts_text = "\n".join(q["options"])
    if st.session_state.prompt_lang == "Russian":
        instant_prompt = f"""Ты являешься экспертом AWS, готовящим студента к экзамену AWS-Certified-Cloud-Practitioner (CLF-C02).

Пожалуйста, объясни следующий экзаменационный вопрос: почему правильные ответы являются верными, а остальные — нет.

Вопрос:
{q['question']}

Варианты ответа:
{opts_text}

Правильный ответ: {', '.join(q['correct'])}

Объясни понятно, подробно и с пояснениями. Приводи примеры, если уместно."""
    else:
        instant_prompt = f"""You are an AWS expert preparing a student for the AWS-Certified-Cloud-Practitioner (CLF-C02) exam.

Please explain the following exam question and why the correct answers are correct (and others incorrect).

Question:
{q['question']}

Options:
{opts_text}

Correct answer: {', '.join(q['correct'])}

Give a clear and detailed explanation with reasoning and practical examples if possible."""

    components.html(f"""
        <textarea id="prompt-text" style="position: absolute; left: -9999px;">{instant_prompt}</textarea>
        <button onclick="copyToClipboard()" style="margin-top: 10px;">📋 Copy to ask chatGPT</button>
        <script>
            function copyToClipboard() {{
                var copyText = document.getElementById("prompt-text");
                copyText.select();
                document.execCommand("copy");
            }}
        </script>
    """, height=50)

# ФИНАЛ
else:
    st.success("✅ Exam Completed!")
    total = len(questions)
    correct = st.session_state.score
    percent = (correct / total) * 100
    st.write(f"**Correct answers:** {correct} / {total}")
    st.write(f"**Percentage:** {percent:.2f}%")
    if percent >= 70:
        st.success("🎉 You passed the exam!")
    else:
        st.warning("❌ You did not reach the passing score (70%).")

    st.markdown("---")
    st.subheader("📋 Review of Your Answers:")
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

        opts_text = "\n".join(ans["options"])
        if st.session_state.prompt_lang == "Russian":
            prompt = f"""Ты являешься экспертом AWS, готовящим студента к экзамену AWS-Certified-Cloud-Practitioner (CLF-C02).\n\nПожалуйста, объясни следующий экзаменационный вопрос: почему правильные ответы являются верными, а остальные — нет.\n\nВопрос:\n{ans['question']}\n\nВарианты ответа:\n{opts_text}\n\nПравильный ответ: {', '.join(ans['correct'])}\n\nОбъясни понятно, подробно и с пояснениями. Приводи примеры, если уместно."""
        else:
            prompt = f"""You are an AWS expert preparing a student for the AWS-Certified-Cloud-Practitioner (CLF-C02) exam.\n\nPlease explain the following exam question and why the correct answers are correct (and others incorrect).\n\nQuestion:\n{ans['question']}\n\nOptions:\n{opts_text}\n\nCorrect answer: {', '.join(ans['correct'])}\n\nGive a clear and detailed explanation with reasoning and practical examples if possible."""

        chat_url = "https://chat.openai.com/?q=" + urllib.parse.quote(prompt)
        st.markdown(f"[💬 Ask ChatGPT for explanation]({chat_url})", unsafe_allow_html=True)
        st.markdown("---")

    # ТОЛЬКО В КОНЦЕ
    if st.button("Restart Exam"):
        for key in list(st.session_state.keys()):
            del st.session_state[key]
        st.rerun()
