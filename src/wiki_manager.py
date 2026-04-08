import os
import time
import shutil
import json
import re
from src.config import WIKI_DIR, WIKI_PAGES_DIR, ARCHIVE_DIR, load_schema
from src.llm_client import query_ollama

def save_to_raw(content, filename, raw_dir="raw"):
    filepath = os.path.join(raw_dir, filename)
    mode = "wb" if isinstance(content, bytes) else "w"
    with open(filepath, mode) as f:
        f.write(content)
    return filepath

def compile_wiki_page(filename, content):
    """Passes content to the LLM to generate formatted wiki markdown."""
    schema_text = load_schema()
    
    # Load existing index to help LLM interlink
    index_path = os.path.join(WIKI_DIR, "index.md")
    existing_pages = ""
    if os.path.exists(index_path):
        with open(index_path, "r") as f:
            existing_pages = f.read()

    # Step 1: Routing
    router_prompt = f"""You are a knowledge architect.
Here is the index of existing Wiki pages:
{existing_pages if existing_pages else 'No existing pages.'}

Here is new incoming information:
{content[:1000]}

DECISION: Does this new information belong as an update to an EXISTING page from the index, or should it be a NEW page?
If UPDATE, return: <action>UPDATE</action><filename>existing-page-name.md</filename>
If NEW, return: <action>NEW</action><filename>new-topic-name.md</filename>"""

    router_res = query_ollama(router_prompt)
    
    action, target_filename = "NEW", "untitled-page.md"
    action_match = re.search(r'<action>(.*?)</action>', router_res, re.IGNORECASE)
    file_match = re.search(r'<filename>(.*?)</filename>', router_res, re.IGNORECASE)
    
    if action_match: action = action_match.group(1).strip().upper()
    if file_match: target_filename = file_match.group(1).strip()
    
    # Clean up filename
    target_filename = re.sub(r'[^a-zA-Z0-9\-]', '', target_filename.lower().replace(' ', '-').replace('_', '-').replace('.md', '')) + ".md"

    target_filepath = os.path.join(WIKI_PAGES_DIR, target_filename)

    # Step 2: Generation
    if action == "UPDATE" and os.path.exists(target_filepath):
        with open(target_filepath, "r") as f:
            existing_content = f.read()
            
        prompt = f"""You are tasked with UPDATING an existing wiki page with new information. Follow these rules:
{schema_text}

EXISTING PAGE CONTENT:
{existing_content}

NEW INFORMATION TO WEAVE IN:
{content}

Use this index to hyperlink keywords correctly:
{existing_pages}

Rewrite the existing page to naturally incorporate the new information.
Remember to wrap your final markdown in <output> ... </output> tags."""
    else:
        prompt = f"""You are tasked with ingesting this file into a NEW wiki page. Follow these rules:
{schema_text}

RAW TEXT:
{content}

Use this index to hyperlink keywords correctly:
{existing_pages}

Generate the clean encyclopedic markdown page.
Remember to wrap your final markdown in <output> ... </output> tags."""

    output_txt = query_ollama(prompt)
    if "Connection error" in output_txt:
        print("[-] Could not connect to Ollama.")
        return False
        
    # Extract markdown dynamically via XML tags, ignoring any conversational filler natively!
    content_match = re.search(r'<output>(.*?)</output>', output_txt, re.DOTALL | re.IGNORECASE)
    if content_match:
        final_markdown = content_match.group(1).strip()
    else:
        # Fallback if LLM forgets tags
        final_markdown = output_txt.strip()
        final_markdown = re.sub(r'(?i)^(Here is .*|Sure.*)\n+', '', final_markdown)
        if final_markdown.startswith("```"):
            final_markdown = re.sub(r'^```(?:markdown)?\n', '', final_markdown)
            final_markdown = re.sub(r'\n```$', '', final_markdown)
            
    final_markdown = final_markdown.strip()

    # Save Markdown to pages folder
    with open(target_filepath, "w") as f:
        f.write(final_markdown)
        
    llm_name = target_filename.replace('.md', '')
    
    # Generate index summary
    index_prompt = f"Write exactly one concise sentence summarizing this text for a wiki index catalog: {content[:2000]}"
    summary = query_ollama(index_prompt).replace('\n', ' ')
    
    # Update core wiki structure
    _update_index(llm_name, target_filename, summary)
    _update_log(filename, target_filename)
    
    return True

def archive_raw_file(filepath):
    filename = os.path.basename(filepath)
    shutil.move(filepath, os.path.join(ARCHIVE_DIR, filename))

def _update_index(topic, wiki_file_name, summary):
    index_path = os.path.join(WIKI_DIR, "index.md")
    if not os.path.exists(index_path):
        with open(index_path, "w") as f:
            f.write("# Wiki Index\n\n")
    with open(index_path, "a") as f:
        relative_path = f"pages/{wiki_file_name}"
        f.write(f"- [{topic}]({relative_path}): {summary}\n")

def _update_log(raw_filename, new_filename):
    log_path = os.path.join(WIKI_DIR, "log.md")
    if not os.path.exists(log_path):
        with open(log_path, "w") as f:
            f.write("# Ingestion Log\n\n")
    timestamp = time.strftime("%Y-%m-%d %H:%M:%S")
    with open(log_path, "a") as f:
        f.write(f"## [{timestamp}] ingest | {raw_filename} -> {new_filename}\n")

def get_relevant_files(question):
    """Scans the index to find relevant files."""
    index_path = os.path.join(WIKI_DIR, "index.md")
    if not os.path.exists(index_path):
        return []
        
    with open(index_path, "r") as f:
        index_content = f.read()
        
    prompt = f"Look at this wiki index:\n{index_content}\nUser asks: '{question}'. Which markdown files contain the answer? Return strict JSON array of filenames. Example: [\"topic.md\"]. ONLY return the array."
    response = query_ollama(prompt)
    
    try:
        cleaned = re.sub(r'```(?:json)?\n?(.*?)\n?```', r'\1', response, flags=re.DOTALL).strip()
        files = json.loads(cleaned)
        return [f for f in files if isinstance(f, str)]
    except json.JSONDecodeError:
        return []

def synthesize_answer(question, files):
    """Reads specific files and generates an answer."""
    combined_content = ""
    for file in files:
        file_base = os.path.basename(file) # Clean paths like "pages/filename.md" 
        filepath = os.path.join(WIKI_PAGES_DIR, file_base)
        if os.path.exists(filepath):
            with open(filepath, "r") as f:
                combined_content += f"\n--- {file_base} ---\n{f.read()}\n"
                
    if not combined_content:
        return "I don't have enough information in the wiki to answer that yet."
        
    prompt = f"Based ONLY on these WIKI DOCUMENTS:\n{combined_content}\n\nUSER QUESTION: {question}\n\nProvide a detailed, well-formatted markdown answer."
    return query_ollama(prompt)
