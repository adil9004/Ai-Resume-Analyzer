# Resume Analyzer - built with Cline + FreeLLMAPI

import streamlit as st
import pdfplumber
import os
import time
from dotenv import load_dotenv
from google import genai
from database import init_db, save_analysis, get_all_analyses, delete_analysis
from agent import run_agent_steps
from qa_chatbot import ask_document_question

# Load environment variables and initialize database
load_dotenv()
init_db()

client = genai.Client(api_key=os.getenv("GEMINI_API_KEY"))

st.set_page_config(page_title="AI Resume Analyzer", page_icon="📄", layout="wide")
st.title("📄 AI Resume Analyzer")
st.markdown("##### Welcome! This friendly tool uses AI to analyze your resume, highlight your strengths, suggest improvements, and help you tailor your application for your dream job.")

# Create tabs for navigation
tab1, tab2, tab3, tab4 = st.tabs(["🔍 Analyze Resume", "📜 Analysis History", "🤖 Job Application Assistant", "💬 Document Q&A Chatbot"] )

def extract_text_from_pdf(file):
    """Reads a PDF file and pulls out all the text from every page."""
    try:
        text = ""
        with pdfplumber.open(file) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text()
                if page_text:
                    text += page_text + "\n"
        return text
    except Exception:
        return None


def analyze_resume(resume_text):
    """Sends resume text to Gemini and asks for structured feedback."""
    prompt = f"""
    You are an expert resume reviewer and career coach.
    Analyze the following resume and respond in this exact structure:

    ## Overall Score
    Give a score out of 100 based on clarity, structure, and impact.

    ## Top 3 Strengths
    List them as bullet points.

    ## Top 3 Areas for Improvement
    List them as bullet points.

    ## Missing Keywords / Skills
    Suggest keywords that could help this resume pass ATS (Applicant
    Tracking System) filters for relevant roles.

    ## Example Rewrite
    Pick one weak bullet point from the resume and rewrite it to be
    stronger, showing a "Before" and "After".

    Resume:
    {resume_text}
    """

    try:
        response = client.models.generate_content(
            model="gemini-3.5-flash",
            contents=prompt,
        )
        return response.text
    except Exception as e:
        raise RuntimeError("Something went wrong while analyzing. Please try again in a moment.") from e


# Tab 1: Analyze Resume
with tab1:
    col1, col2 = st.columns([2, 1], gap="large")
    
    with col1:
        st.subheader("📤 Upload Resume")
        st.write("Upload your resume in PDF format to receive comprehensive, AI-powered feedback.")
        uploaded_file = st.file_uploader("Upload your resume (PDF only)", type=["pdf"])
        
    with col2:
        st.subheader("💡 Tips for Best Results")
        st.markdown("""
        - **Format:** Ensure your resume is in **PDF** format.
        - **Readable Text:** Avoid scanned, image-only PDFs so our AI can read the text.
        - **Size Limit:** Keep your file size **under 10MB**.
        - **Content:** Include clear details about your experience, achievements, and key skills.
        """)
        
    st.divider()

    if uploaded_file is not None:
        if uploaded_file.size > 10 * 1024 * 1024:
            st.error("The uploaded file is too large. Please upload a PDF under 10MB.")
        else:
            file_key = f"analyze_{uploaded_file.name}_{uploaded_file.size}"
            
            if "extracted_text_cache" not in st.session_state:
                st.session_state.extracted_text_cache = {}
                
            if file_key not in st.session_state.extracted_text_cache:
                with st.spinner("🔍 Reading your resume..."):
                    resume_text = extract_text_from_pdf(uploaded_file)
                    st.session_state.extracted_text_cache[file_key] = resume_text
            else:
                resume_text = st.session_state.extracted_text_cache[file_key]

            if resume_text is None or resume_text.strip() == "":
                st.error("We couldn't read this PDF. Please try a different file or make sure it's not a scanned image.")
            else:
                st.success("Resume text extracted successfully!")

                # Check if we have already analyzed this resume to prevent duplicate API runs on page reruns
                if "analyses_cache" not in st.session_state:
                    st.session_state.analyses_cache = {}

                if file_key not in st.session_state.analyses_cache:
                    with st.spinner("🤖 Consulting our AI career experts... Almost there!"):
                        try:
                            result = analyze_resume(resume_text)
                            if result:
                                # Save the analysis result to database
                                save_analysis(uploaded_file.name, resume_text, result)
                                st.session_state.analyses_cache[file_key] = result
                            else:
                                st.error("Something went wrong while analyzing. Please try again in a moment.")
                        except Exception as e:
                            st.error("Something went wrong while analyzing. Please try again in a moment.")
                            result = None
                else:
                    result = st.session_state.analyses_cache[file_key]

                if result:
                    st.subheader("📊 Analysis Result")
                    st.markdown(result)
    else:
        st.info("Upload a PDF resume above to get started.")


# Tab 2: Analysis History
with tab2:
    st.subheader("📜 Saved Analyses")
    st.write("View and manage your past resume analyses stored in your local database.")
    st.divider()
    
    # Retrieve records from the database
    analyses = get_all_analyses()
    
    if not analyses:
        st.info("No past analyses found. Start by analyzing a resume in the first tab!")
    else:
        for row in analyses:
            # Display each analysis in an expander
            record_title = f"📄 {row['filename']} — {row['timestamp']}"
            with st.expander(record_title):
                st.markdown("### 📊 AI Analysis Report")
                st.markdown(row['analysis_result'])
                
                # Option to view the original resume text
                with st.expander("🔍 View Original Resume Text", expanded=False):
                    st.text(row['resume_text'])
                
                st.divider()
                # Delete button
                if st.button("Delete this analysis", key=f"del_{row['id']}"):
                    delete_analysis(row['id'])
                    st.success(f"Deleted analysis for {row['filename']}!")
                    st.rerun()



# Tab 3: Job Application Assistant
with tab3:
    st.subheader("🤖 Job Application Assistant")
    st.write("Run a 4-step AI agent process that helps you align your resume to a job description, write a tailored cover letter, and refine your resume bullets.")
    st.divider()
    
    col1, col2 = st.columns([1, 1], gap="medium")
    
    with col1:
        st.subheader("📋 Job Description")
        job_desc = st.text_area("Paste the job description from the job posting:", height=250, placeholder="Paste job description here...")
        
    with col2:
        st.subheader("📤 Resume")
        assistant_file = st.file_uploader("Upload your resume (PDF only)", type=["pdf"], key="assistant_resume_uploader")
        
        assistant_resume_text = ""
        if assistant_file is not None:
            if assistant_file.size > 10 * 1024 * 1024:
                st.error("The uploaded file is too large. Please upload a PDF under 10MB.")
            else:
                file_key = f"assistant_{assistant_file.name}_{assistant_file.size}"
                
                if "extracted_text_cache" not in st.session_state:
                    st.session_state.extracted_text_cache = {}
                    
                if file_key not in st.session_state.extracted_text_cache:
                    with st.spinner("🔍 Reading your resume..."):
                        assistant_resume_text = extract_text_from_pdf(assistant_file)
                        st.session_state.extracted_text_cache[file_key] = assistant_resume_text
                else:
                    assistant_resume_text = st.session_state.extracted_text_cache[file_key]
                    
                if assistant_resume_text is None or assistant_resume_text.strip() == "":
                    st.error("We couldn't read this PDF. Please try a different file or make sure it's not a scanned image.")
                else:
                    st.success("Resume text extracted successfully!")

    # Set up session state for storing assistant analysis results so they persist across reruns
    if "assistant_results" not in st.session_state:
        st.session_state.assistant_results = None

    # Disable the assistant button if the necessary inputs are not provided
    btn_disabled = not (job_desc.strip() and assistant_resume_text.strip())

    st.divider()
    
    # Elegant centered button layout
    btn_col1, btn_col2, btn_col3 = st.columns([1, 1, 1])
    with btn_col2:
        run_btn = st.button("🚀 Run Application Assistant", key="run_assistant_btn", disabled=btn_disabled, use_container_width=True)

    if run_btn:
        # Reset the results in state while running
        st.session_state.assistant_results = None
        
        # Start the generator from agent.py
        agent_generator = run_agent_steps(client, job_desc, assistant_resume_text)
        try:
            step_msg, results = next(agent_generator)
            while step_msg != "Complete":
                # Create a spinner for the active step and step through the generator
                with st.spinner(step_msg):
                    step_msg, results = next(agent_generator)
            st.session_state.assistant_results = results
            st.success("Job Application Assistant completed all steps successfully!")
        except Exception as e:
            st.error("Something went wrong while analyzing. Please try again in a moment.")

    # Display results when they are available in session state
    if st.session_state.assistant_results is not None:
        res = st.session_state.assistant_results
        
        st.subheader("🎯 Assistant Results")
        
        with st.expander("📋 Step 1: Key Requirements & Skills", expanded=True):
            st.markdown(res.get("step1", ""))
            
        with st.expander("⚖️ Step 2: Compare with Resume (Matches & Gaps)", expanded=True):
            st.markdown(res.get("step2", ""))
            
        with st.expander("✉️ Step 3: Tailored Cover Letter", expanded=True):
            st.markdown(res.get("step3", ""))
            
        with st.expander("✍️ Step 4: Suggested Resume Bullet-Point Edits", expanded=True):
            st.markdown(res.get("step4", ""))


# Tab 4: Document Q&A Chatbot
with tab4:
    st.subheader("💬 Document Q&A Chatbot")
    st.write("Upload a document to chat with it.")
    
    qa_file = st.file_uploader("Upload a document (PDF)", type=["pdf"], key="qa_uploader")
    
    qa_document_text = ""
    if qa_file is not None:
        if qa_file.size > 10 * 1024 * 1024:
            st.error("The uploaded file is too large. Please upload a PDF under 10MB.")
        else:
            file_key = f"qa_{qa_file.name}_{qa_file.size}"
            
            if "extracted_text_cache" not in st.session_state:
                st.session_state.extracted_text_cache = {}
                
            if file_key not in st.session_state.extracted_text_cache:
                with st.spinner("🔍 Reading your document..."):
                    qa_document_text = extract_text_from_pdf(qa_file)
                    st.session_state.extracted_text_cache[file_key] = qa_document_text
            else:
                qa_document_text = st.session_state.extracted_text_cache[file_key]
                
            if qa_document_text is None or qa_document_text.strip() == "":
                st.error("We couldn't read this PDF. Please try a different file or make sure it's not a scanned image.")
            else:
                st.success("Document text extracted successfully!")
                
                # Initialize chat history
                if "qa_messages" not in st.session_state:
                    st.session_state.qa_messages = []
                
                # Render the message history inside an st.container() above st.chat_input,
                # so the input box always stays below the conversation.
                chat_container = st.container()
                
                with chat_container:
                    # Display chat history
                    for message in st.session_state.qa_messages:
                        with st.chat_message(message["role"]):
                            st.markdown(message["content"])
                
                # Chat input
                if prompt := st.chat_input("Ask a question about your document..."):
                    st.session_state.qa_messages.append({"role": "user", "content": prompt})
                    with chat_container:
                        with st.chat_message("user"):
                            st.markdown(prompt)
                        
                        with st.chat_message("assistant"):
                            with st.spinner("Thinking..."):
                                max_retries = 2
                                response = None
                                error_to_show = None
                                
                                for attempt in range(max_retries + 1):
                                    try:
                                        response = ask_document_question(client, qa_document_text, prompt, st.session_state.qa_messages[:-1])
                                        break
                                    except Exception as e:
                                        err_str = str(e)
                                        if e.__cause__:
                                            err_str += " " + str(e.__cause__)
                                        
                                        is_retryable = "503" in err_str or "429" in err_str
                                        if is_retryable and attempt < max_retries:
                                            time.sleep(2)
                                            continue
                                        else:
                                            error_to_show = e
                                            break
                                
                                if response is not None:
                                    st.markdown(response)
                                    st.session_state.qa_messages.append({"role": "assistant", "content": response})
                                else:
                                    friendly_error = "⚠️ I'm sorry, but I'm having trouble connecting to the service right now. Please try asking your question again in a moment."
                                    st.error(friendly_error)
                                    st.session_state.qa_messages.append({"role": "assistant", "content": friendly_error})

