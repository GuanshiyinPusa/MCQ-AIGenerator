import streamlit as st
from PyPDF2 import PdfReader
import openai
import json
from streamlit_js_eval import streamlit_js_eval


def load_environment():
    openai.api_key = st.secrets["api_key"]


def initialize_streamlit():
    st.title("Quiz Generator🤖")
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "model" not in st.session_state:
        st.session_state.model = "gpt-3.5-turbo-16k"
    if "response_content" not in st.session_state:
        st.session_state.response_content = ""


def display_previous_messages():
    # for message in st.session_state["messages"]:
    #     with st.chat_message(message["role"]):
    #         st.markdown(message["content"])
    return


def get_user_input(num_questions):
    fixed_prompt = """
    Based on the provided information, you MUST generate {num_questions} multiple choice questions in the following JSON format:

    Format:
    [{{  # <-- notice the double curly braces
        "question": "Sample question?",
        "options": {{
            "A": "Option A",
            "B": "Option B",
            "C": "Option C",
            "D": "Option D"
        }},
        "correct_answer": "A) Option A",
        "explanation": "Explanation for the correct answer."
    }},
        ...
    ]

    Provided Information:
    """
    # num_questions is now an argument, so no need for st.number_input here

    if user_prompt := st.text_area("Enter content:", value="", height=300):
        return fixed_prompt.format(num_questions=num_questions) + user_prompt
    return None


def chat_with_gpt(user_input):
    # Check if user message is already in session state to prevent adding it again
    if not any(msg["role"] == "user" and msg["content"] == user_input for msg in st.session_state.messages):
        st.session_state.messages.append(
            {"role": "user", "content": user_input})

    with st.spinner('Generating questions...'):
        full_response = ""
        for response in openai.ChatCompletion.create(
            model=st.session_state.model,
            temperature=0.1,
            messages=[
                {"role": m["role"], "content": m["content"]}
                for m in st.session_state.messages
            ],
            stream=True
        ):
            full_response += response.choices[0].delta.get("content", "")

    # Check if assistant message is already in session state to prevent adding it again
    if not any(msg["role"] == "assistant" and msg["content"] == full_response for msg in st.session_state.messages):
        st.session_state.messages.append(
            {"role": "assistant", "content": full_response})

    # Assuming you want to return the full response for further processing
    return full_response


def parse_content(content):
    # Print content to the console for inspection
    print(content)

    try:
        # Parse the JSON content
        questions_json = json.loads(content)
    except json.JSONDecodeError as e:
        st.error(f"Failed to parse JSON: {e}")
        return []

    # Convert the JSON structure to the desired format
    parsed_questions = []
    for q in questions_json:
        parsed_questions.append({
            "question": q["question"],
            "options": [f"{key}) {value}" for key, value in q["options"].items()],
            "correct_answer": q["correct_answer"],
            "explanation": q["explanation"]
        })
    return parsed_questions


def display_questions(parsed_questions):
    for idx, q in enumerate(parsed_questions):
        st.write(f"**{q['question']}**")
        answer_key = f"answer_{idx}"
        submitted_key = f"submitted_{idx}"

        # Display the radio buttons
        answer = st.radio("Select an option:",
                          q['options'], key=f'radio_{idx}')

        # Check if the user has made a selection and submitted
        if st.button('Submit', key=f'button_{idx}'):
            # Save the answer to session state
            st.session_state[answer_key] = answer
            # Mark the question as answered
            st.session_state[submitted_key] = True

        # If the question is already answered, display the selected answer and its explanation
        if st.session_state.get(submitted_key, False):
            selected_answer = st.session_state.get(answer_key, "")
            # Bold and emphasized text
            st.markdown(
                f"**You selected:** ***{selected_answer}***", unsafe_allow_html=True)
            if selected_answer == q['correct_answer']:
                st.write("Correct! 🎉")
                st.write(q['explanation'])
            else:
                st.write("Oops! That's not correct. 😞")
                st.write(q['explanation'])


def get_content_from_pdf(uploaded_file):
    """Extract content from the uploaded PDF."""
    pdf = PdfReader(uploaded_file)
    content = ""
    for page in pdf.pages:
        content += page.extract_text()  # Changed method name here
    return content


def get_content_from_json(uploaded_file):
    """Extract content from the uploaded JSON file."""
    content = json.load(uploaded_file)
    return json.dumps(content)


def chatbot_page():
    display_previous_messages()

    input_method = st.selectbox('Choose input method:', [
                                'Text Input', 'File Upload'])

    num_questions = st.number_input('Number of Questions:', min_value=1,
                                    max_value=50, value=5, step=1, key='num_questions_chatbot_page')

    if input_method == 'File Upload':
        uploaded_file = st.file_uploader(
            "Upload a PDF or JSON", type=["pdf", "json"])

        if uploaded_file:
            if uploaded_file.type == "application/pdf":
                user_input = get_content_from_pdf(uploaded_file)
            elif uploaded_file.type == "application/json":
                user_input = get_content_from_json(uploaded_file)
        else:
            user_input = None
    else:
        user_input = get_user_input(num_questions)

    if user_input and input_method == 'File Upload':
        fixed_prompt = """
        Based on the provided information, please generate {num_questions} multiple choice questions in the specified JSON format:

        Format:
        [{{  # <-- notice the double curly braces
            "question": "Sample question?",
            "options": {{
                "A": "Option A",
                "B": "Option B",
                "C": "Option C",
                "D": "Option D"
            }},
            "correct_answer": "A) Option A",
            "explanation": "Explanation for the correct answer."
        }},
            ...
        ]

        Provided Information:
        """
        user_input = fixed_prompt.format(
            num_questions=num_questions) + user_input

    if st.button('Generate Questions'):  # New line to add a button
        if user_input:
            response_content = chat_with_gpt(user_input)
            st.session_state.response_content = response_content

    # Parsing and displaying questions right after the chat_with_gpt function
    if st.session_state.response_content:
        parsed_questions = parse_content(st.session_state.response_content)
        st.write(f"Number of parsed questions: {len(parsed_questions)}")
        display_questions(parsed_questions)
    else:
        st.warning("Please chat with OpenAI first to generate questions.")

    if st.button("Reload page"):
        streamlit_js_eval(js_expressions="parent.window.location.reload()")


def main():
    load_environment()
    initialize_streamlit()

    # Call chatbot_page directly since there's only one page now
    chatbot_page()


if __name__ == "__main__":
    main()
