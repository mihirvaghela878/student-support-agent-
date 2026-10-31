"""Streamlit chat UI. Run with: streamlit run app.py"""
import os, uuid, streamlit as st
from database.seed import seed
from database.db import connect
from config.settings import get_chat_model
from agent.graph import build_graph, run_agent
from rag.retrieval import PolicyRetriever
from memory.store import list_memories, save_memory, delete_memory
from memory.policies import classify_memory
from observability.tracing import write_trace

st.set_page_config(page_title="Student Support Agent",page_icon="🎓",layout="wide")
st.title("🎓 Intelligent Student Support Agent")
st.caption("Local teaching demo using synthetic student records. Select a demo identity to begin.")
seed()
with connect() as db:
    students = [
        dict(row)
        for row in db.execute(
            "SELECT student_id,display_name,programme,semester FROM students ORDER BY student_id"
        ).fetchall()
    ]
with st.sidebar:
    who=st.selectbox("Demo student",students,format_func=lambda x:f"{x['display_name']} · {x['student_id']}")
    if "session_id" not in st.session_state: st.session_state.session_id=str(uuid.uuid4())
    st.caption("Conversation session: "+st.session_state.session_id[:8])
    if st.button("New conversation session"): st.session_state.session_id=str(uuid.uuid4()); st.session_state.chat=[]
    st.subheader("Long-term memory")
    memories=list_memories(who['student_id'])
    for m in memories:
        c1,c2=st.columns([4,1]); c1.write(m['fact'])
        if c2.button("Delete",key=f"del-{m['memory_id']}"): delete_memory(who['student_id'],m['memory_id']); st.rerun()
    with st.expander("Save a stable preference or study fact"):
        fact=st.text_input("Fact")
        if st.button("Save memory") and fact:
            result=save_memory(who['student_id'],fact)
            st.info(result['reason']); st.rerun()
if "chat" not in st.session_state: st.session_state.chat=[]
for item in st.session_state.chat:
    with st.chat_message(item['role']): st.markdown(item['content'])
question=st.chat_input("Ask about fees, scholarships, courses, policies, or support")
if question:
    st.session_state.chat.append({"role":"user","content":question})
    with st.chat_message("user"): st.markdown(question)
    with st.chat_message("assistant"):
        try:
            allowed, _ = classify_memory(question)
            if allowed:
                save_memory(who['student_id'], question)
            model=get_chat_model(); graph=build_graph(model,PolicyRetriever(os.getenv("STUDENT_AGENT_POLICY","rag/sample_handbook.md")))
            result=run_agent(graph,question,who['student_id'],st.session_state.session_id)
            st.markdown(result['answer']); st.session_state.chat.append({"role":"assistant","content":result['answer']})
            write_trace(result['trace'],question,result['answer'])
            with st.expander("Run trace and evidence"):
                st.json(result['trace'])
                for item in result['policy']: st.markdown(f"**{item['chunk_id']}** · {item['source']}\n\n{item['text']}")
                if result['memories']: st.write("Relevant memory IDs:", [m['memory_id'] for m in result['memories']])
        except Exception as exc:
            st.error("The agent could not complete this request. Check model availability and configuration, then retry.")
            st.caption(str(exc))
