import os
import streamlit as st
import requests
import uuid

BASE_URL = os.getenv("BACKEND_URL", "http://127.0.0.1:8000")


if "current_blog" not in st.session_state:
    st.session_state.current_blog = None


with st.sidebar:
    st.header("Blog History")
    
    if st.button("New Blog", use_container_width=True, type="primary"):
        st.session_state.current_blog = None
        st.rerun()
        
    st.markdown("---")
    
    try:
        res = requests.get(f"{BASE_URL}/blog-ids")
        if res.status_code == 200:
            res_lists = res.json()
            
            if not res_lists:
                st.caption("Not blogs saved yet.")
                
            for item in res_lists:
                b_id = item["blog_id"]
                topic_title = item.get("topic", b_id)
                
                col_btn, col_del = st.columns([5, 1])
                
                with col_btn:
                    if st.button(f"{topic_title}", key=f"view_{b_id}", use_container_width=True):
                        detailed_res = requests.get(f"{BASE_URL}/blog-ids/{b_id}")
                        if detailed_res.status_code == 200:
                            st.session_state.current_blog = detailed_res.json()
                            st.rerun()
                
                with col_del:
                    if st.button("🗑️", key=f"del_{b_id}", help="Delete blog"):
                        del_res = requests.delete(f"{BASE_URL}/delete-blog/{b_id}")
                        if del_res.status_code == 200:
                            if st.session_state.current_blog and st.session_state.current_blog.get("blog_id") == b_id:
                                st.session_state.current_blog = None
                            st.toast("Blog deleted!", icon="🗑️")
                            st.rerun()
        else:
            st.error("Failed to load history from backend.")
    except Exception as e:
        st.error(f"Backend is Offline : str({e})")
        
    
if st.session_state.current_blog:
    blog_data = st.session_state.current_blog
    st.subheader(f"Topic: {blog_data.get('topic')}")
    st.caption(f"Created At: {blog_data.get('created_at', 'N/A')}")
    
    with st.expander("View Outline", expanded=False):
        st.markdown(blog_data.get("outline", ""))
        
    st.markdown("### Full Blog")
    st.markdown(blog_data.get("blog", ""))
    
    web_links_str = blog_data.get("web_links", "")
    if web_links_str:
        st.markdown("---")
        st.subheader("Sources & Web References")
        links = [l.strip() for l in web_links_str.split(",") if l.strip()]
        for idx, link in enumerate(links):
            st.markdown(f"{idx}. [{link}]({link})")
    
else:
    topic = st.text_input("Enter Topic for the Blog:", placeholder="e.g. Impact of Artificial Intelligence in Healthcare")
    if st.button("Generate Blog", type="primary"):
        if not topic.strip():
            st.warning("Please enter a topic first.")
        else:
            new_blog_id = str(uuid.uuid4())
            
            st.markdown("#### Generating Blog...")
            
            try:
                res = requests.post(f"{BASE_URL}/write-blog?blog_id={new_blog_id}&topic={topic}", stream=True)
                
                def stream_generator():
                    for chunk in res.iter_content(chunk_size=None, decode_unicode=True):
                        yield chunk
                        
                full_blog_text = st.write_stream(stream_generator)
                new_blog_res = requests.get(f"{BASE_URL}/blog-ids/{new_blog_id}")
                if new_blog_res.status_code == 200:
                    st.session_state.current_blog = new_blog_res.json()
                    st.rerun()
            except Exception as e:
                st.error(f"Error during generation: {e}")
