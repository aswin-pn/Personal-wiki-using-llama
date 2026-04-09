import os
import requests
import json
import re

from src.config import OLLAMA_API, MODEL_NAME

def query_ollama(prompt):
    try:
        response = requests.post(OLLAMA_API, json={
            "model": MODEL_NAME,
            "prompt": prompt,
            "stream": False
        })
        if response.status_code == 200:
            return response.json().get("response", "").strip()
        else:
            return f"Error: {response.text}"
    except Exception as e:
        return f"Connection error: {e}"

def get_relevant_files(question):
    print("[*] Consulting the wiki index...")
    index_path = os.path.join("wiki", "index.md")
    if not os.path.exists(index_path):
        print("[-] Error: No index.md found. Add some files to 'raw/' first!")
        return []
        
    with open(index_path, "r") as f:
        index_content = f.read()
        
    prompt = f"""You are a helpful librarian. Look at this index of wiki files:

{index_content}

The user is asking: "{question}"

Based on the summaries in the index, which markdown file(s) contain the answer? 
Return a strict JSON list of filenames (e.g. ["example.md", "topic.md"]).
Important: Return ONLY the raw JSON list format, no introductory text, no markdown code block backticks."""

    response = query_ollama(prompt)
    
    # Try to parse JSON strictly or fallback to extracting arrays
    try:
        # Strip markdown formatting if the LLM hallucinated ```json [...] ```
        cleaned = re.sub(r'```(?:json)?\n?(.*?)\n?```', r'\1', response, flags=re.DOTALL).strip()
        files = json.loads(cleaned)
        if isinstance(files, list):
            return files
        return []
    except json.JSONDecodeError:
        print(f"[-] Could not parse JSON from LLM: {response}")
        return []

def answer_question(question, files):
    if not files:
        return "I couldn't find any relevant files in the wiki index to answer that question."
        
    print(f"[*] Reading files: {', '.join(files)}...")
    combined_content = ""
    for file in files:
        filepath = os.path.join("wiki", file)
        if os.path.exists(filepath):
            with open(filepath, "r") as f:
                combined_content += f"\n--- {file} ---\n{f.read()}\n"
        else:
            print(f"[-] Warning: File {filepath} does not exist.")
            
    if not combined_content:
        return "None of the selected files could be found."

    prompt = f"""You are answering a question based ONLY on the following WIKI DOCUMENTS.
If the documents do not contain the answer, say so. Do not use outside knowledge.

WIKI DOCUMENTS:
{combined_content}

USER QUESTION: {question}

Please provide a detailed, well-formatted markdown answer."""

    print("[*] Synthesizing final answer...")
    return query_ollama(prompt)

if __name__ == "__main__":
    print("=======================================")
    print(" LLM Wiki - Document Q&A (No Database)")
    print("=======================================\n")
    
    while True:
        try:
            question = input("\nAsk your wiki (or 'quit'): ")
            if question.lower() in ['quit', 'exit', 'q']:
                break
                
            if not question.strip():
                continue
                
            files_to_read = get_relevant_files(question)
            if files_to_read:
                print(f"[+] Found relevant topics: {files_to_read}")
                answer = answer_question(question, files_to_read)
                print("\n" + "="*50)
                print(answer)
                print("="*50 + "\n")
            else:
                print("[-] No relevant files found in the index.")
        except KeyboardInterrupt:
            break
