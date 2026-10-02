import os
from google import genai

def ask_document_question(client, document_text, question, chat_history=None):
    """
    Sends the document text, question, and optional chat history to Gemini
    with strict system-style instructions to answer only based on the document content.
    """
    history_context = ""
    if chat_history:
        history_context = "Previous conversation history:\n"
        for msg in chat_history:
            role = "User" if msg.get("role") == "user" else "Assistant"
            history_context += f"{role}: {msg.get('content', '')}\n"
        history_context += "\n"

    prompt = f"""
You are an AI document assistant. Your task is to answer user questions accurately based on the provided document.

SYSTEM INSTRUCTIONS:
1. Answer strictly based on the content present in the Document Text provided below.
2. Do NOT use outside knowledge or make assumptions beyond what is explicitly stated in the document.
3. If the information needed to answer the question is not present in the document, you MUST explicitly state: "I don't see that information in this document" (or include that exact phrase clearly in your response).
4. Keep your response clear, concise, and direct.

Document Text:
{document_text}

{history_context}Current Question:
{question}
"""

    try:
        response = client.models.generate_content(
            model="gemini-3.5-flash",
            contents=prompt,
        )
        return response.text
    except Exception as e:
        print(f"Q&A error: {type(e).__name__}: {e}")
        raise RuntimeError("Something went wrong while generating an answer. Please try again in a moment.") from e
