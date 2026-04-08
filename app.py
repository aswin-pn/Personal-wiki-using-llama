import streamlit as st
import os
from datetime import datetime
from src.config import ensure_directories, WIKI_DIR, WIKI_PAGES_DIR
from src.wiki_manager import save_to_raw, get_relevant_files, synthesize_answer

# UI Configuration
st.set_page_config(page_title="LLM Wiki", page_icon="🧠", layout="wide")

st.markdown("""
<style>
/* Style headings specifically to look like MediaWiki */
h1, h2, h3, h4, h5, h6 {
    font-family: 'Linux Libertine', 'Georgia', 'Times', serif !important;
    font-weight: normal;
}
h1, h2 {
    border-bottom: 1px solid #a2a9b1;
    padding-bottom: 0.25em;
    margin-bottom: 0.25em;
}
/* Change link color to Wikipedia Blue */
a {
    color: #0645ad !important;
    text-decoration: none;
}
a:hover {
    text-decoration: underline;
}
/* Style sidebar border */
[data-testid="stSidebar"] {
    border-right: 1px solid #a2a9b1;
}
/* Infobox styling for codeblocks/quotes to emulate wiki boxes */
pre {
    background-color: #f8f9fa !important;
    border: 1px solid #a2a9b1 !important;
    border-radius: 2px !important;
    padding: 10px !important;
}
</style>
""", unsafe_allow_html=True)

ensure_directories()
st.sidebar.title("🧠 My LLM Wiki")
mode = st.sidebar.radio("Navigation", ["💬 Chat with Wiki", "📖 Show My Wiki"])

# ----------------- UPLOAD SECTION -----------------
st.sidebar.divider()
st.sidebar.subheader("📥 Upload Knowledge")
upload_type = st.sidebar.selectbox("Input Type", ["File Upload", "Paste Text/Link"])

if upload_type == "File Upload":
    uploaded_file = st.sidebar.file_uploader("Drop a file here", type=["txt", "pdf", "docx", "png", "jpg", "jpeg"])
    if st.sidebar.button("Send") and uploaded_file:
        save_to_raw(uploaded_file.getvalue(), uploaded_file.name)
        st.sidebar.success(f"Sent '{uploaded_file.name}' to raw folder!")
    st.sidebar.caption("Sending this will automatically generate a file inside your wiki folder.")
else:
    pasted_data = st.sidebar.text_area("Paste text or URL")
    if st.sidebar.button("Send") and pasted_data:
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        save_to_raw(pasted_data, f"pasted_note_{timestamp}.txt")
        st.sidebar.success("Note sent to raw folder!")
    st.sidebar.caption("Sending this will automatically generate a file inside your wiki folder.")

# ----------------- MAIN VIEWS -----------------
if mode == "💬 Chat with Wiki":
    st.title("Chat with your Wiki")
    
    if "messages" not in st.session_state:
        st.session_state.messages = []

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    if user_input := st.chat_input("Ask your wiki anything..."):
        st.session_state.messages.append({"role": "user", "content": user_input})
        with st.chat_message("user"):
            st.markdown(user_input)
            
        with st.chat_message("assistant"):
            with st.spinner("Librarian is searching the Wikipedia index..."):
                files = get_relevant_files(user_input)
            
            if files:
                st.info(f"📚 Reading wiki pages: {', '.join(files)}")
                with st.spinner("Synthesizing answer..."):
                    answer = synthesize_answer(user_input, files)
            else:
                answer = "I couldn't find any relevant pages in the wiki to answer this question. Try uploading some context to the sidebar!"
                
            st.markdown(answer)
            st.session_state.messages.append({"role": "assistant", "content": answer})

elif mode == "📖 Show My Wiki":
    st.title("Wiki Browser")
    
    pages = [f for f in os.listdir(WIKI_PAGES_DIR) if f.endswith(".md")]
    core_files = ["index.md", "log.md"]
    valid_core = [f for f in core_files if os.path.exists(os.path.join(WIKI_DIR, f))]
    all_viewable = valid_core + pages
    
    if not all_viewable:
        st.warning("Your wiki is empty! Drop some files in the sidebar and wait for the background LLM to compile them.")
    else:
        # Check URL query params for external/internal link routing
        url_page = st.query_params.get("page", None)
        default_idx = all_viewable.index(url_page) if url_page in all_viewable else (all_viewable.index("index.md") if "index.md" in all_viewable else 0)
        
        selected_page = st.selectbox("Search or view a Wiki Page:", all_viewable, index=default_idx)
        
        # Update URL parameter when selection changes
        st.query_params["page"] = selected_page
        
        if selected_page in core_files:
            filepath = os.path.join(WIKI_DIR, selected_page)
        else:
            filepath = os.path.join(WIKI_PAGES_DIR, selected_page)
            
        with open(filepath, "r") as f:
            content = f.read()
            
        # Rewrite standard (filename.md) markdown links into Streamlit query parameter links
        import re
        content = re.sub(r'\]\((?!http)(.*?\.md)\)', r'](/?page=\1)', content)
            
        st.divider()
        # Streamlit perfectly renders standard markdown format (bullets, checkboxes, links)
        st.markdown(content)
