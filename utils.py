import streamlit as st
from PyPDF2 import PdfReader
import openai
import json

def display_previous_messages():
    for message in st.session_state["messages"]:
        with st.chat_message(message["role"]):
            st.markdown(message["content"])

def get_user_input(num_questions):
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
    # num_questions is now an argument, so no need for st.number_input here
    
    if user_prompt := st.text_area("Enter content:", value="", height=300):
        return fixed_prompt.format(num_questions=num_questions) + user_prompt
    return None

def chat_with_gpt(user_input):
    # Check if user message is already in session state to prevent adding it again
    if not any(msg["role"] == "user" and msg["content"] == user_input for msg in st.session_state.messages):
        st.session_state.messages.append({"role": "user", "content": user_input})

    with st.spinner('Generating questions...'):
        full_response = ""
        for response in openai.ChatCompletion.create(
            model=st.session_state.model,
            messages=[
                {"role": m["role"], "content": m["content"]}
                for m in st.session_state.messages
            ],
            stream=True,
        ):
            full_response += response.choices[0].delta.get("content", "")

    # Check if assistant message is already in session state to prevent adding it again
    if not any(msg["role"] == "assistant" and msg["content"] == full_response for msg in st.session_state.messages):
        st.session_state.messages.append({"role": "assistant", "content": full_response})

    return full_response  # Assuming you want to return the full response for further processing

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
        answer = st.radio("Select an option:", q['options'], key=f'radio_{idx}')

        # Check if the user has made a selection and submitted
        if st.button('Submit', key=f'button_{idx}'):
            st.session_state[answer_key] = answer  # Save the answer to session state
            st.session_state[submitted_key] = True  # Mark the question as answered

        # If the question is already answered, display the selected answer and its explanation
        if st.session_state.get(submitted_key, False):
            selected_answer = st.session_state.get(answer_key, "")
            st.markdown(f"**You selected:** ***{selected_answer}***", unsafe_allow_html=True)  # Bold and emphasized text
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
