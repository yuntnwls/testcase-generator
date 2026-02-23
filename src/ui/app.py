import streamlit as st
import pandas as pd
import tempfile
import time
import os
import sys

# 프로젝트 루트를 PYTHONPATH에 추가하여 임포트 가능하도록 설정
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

from src.core.engine import CoreEngine

st.set_page_config(page_title="Universal Test Script Generator", layout="wide")

st.title("🚗 Auto Test Script Generator")
st.markdown("Automatically convert natural language Test Cases (TCs) into target test scripts.")

# Sidebar Settings
with st.sidebar:
    st.header("⚙️ Configuration")
    llm_type = st.selectbox("LLM Type", ["mock", "local", "openai", "gemini"], index=1)
    
    st.info(f"Selected LLM: **{llm_type.upper()}**")
    st.divider()
    st.info("💡 **How to use**\n1. Upload your Excel/TSV file.\n2. Click 'Run Conversion'.\n3. Download the generated Python script.")

st.subheader("1. TC File Upload")
uploaded_file = st.file_uploader("Upload TC File (.tsv, .csv, .xlsx)", type=['tsv', 'csv', 'xlsx'])

if uploaded_file is not None:
    # Preview Dataframe
    if uploaded_file.name.endswith('.tsv'):
        df = pd.read_csv(uploaded_file, sep='\t')
    elif uploaded_file.name.endswith('.csv'):
        df = pd.read_csv(uploaded_file)
    else:
        df = pd.read_excel(uploaded_file)
        
    st.write("### Data Preview")
    # st.dataframe은 셀 내 줄바꿈(\n)을 무시하므로, 표시용 복사본을 만들어 줄바꿈을 <br>로 변환 후 HTML로 출력
    display_df = df.copy().fillna("")
    # 모든 문자열 셀 내부의 \n을 <br>로 변환
    display_df = display_df.astype(str).replace({"\n": "<br>"}, regex=True)
    
    preview_html = display_df.to_html(escape=False, index=False)
    st.markdown(
        f'<div style="overflow-x:auto;">{preview_html}</div>', 
        unsafe_allow_html=True
    )
    # 여백 추가
    st.write("")
    
    # TC 선택 UI 추가
    tc_column = "T/Case ID" if "T/Case ID" in df.columns else df.columns[0]
    available_tcs = df[tc_column].unique().tolist()
    selected_tcs = st.multiselect("Select TCs to Convert", options=available_tcs, default=available_tcs)
    
    if st.button("🚀 Run Conversion", type="primary"):
        if not selected_tcs:
            st.warning("Please select at least one TC to convert.")
            st.stop()
            
        # Save to temp file
        with tempfile.NamedTemporaryFile(delete=False, suffix=".tsv") as tmp_file:
            tmp_file.write(uploaded_file.getvalue())
            tmp_path = tmp_file.name
            
        st.write("---")
        st.subheader("2. Real-time Conversion Progress")
        
        # UI Layout Containers
        status_text = st.empty()
        progress_bar = st.progress(0)
        log_container = st.empty()
        
        # Inject dynamic LLM provider from UI
        from src.core.config_loader import get_config
        from src.core.llm_provider import LLMFactory
        
        dynamic_config = get_config()
        dynamic_config["llm"]["type"] = llm_type
        custom_llm = LLMFactory.create_provider(dynamic_config["llm"])
        
        # Initialize CoreEngine
        engine = CoreEngine(llm_provider=custom_llm)
        logs = []
        final_code = ""
        current_trace_id = ""
        
        try:
            for event in engine.process_file_stream(tmp_path, selected_tc_ids=selected_tcs):
                evt_type = event.get("type")
                tc_idx = event.get("tc_index", 1)
                total_tcs = event.get("total_tcs", 1)
                
                # Update Trace ID
                if "trace_id" in event:
                    current_trace_id = event["trace_id"]
                    
                if evt_type == "info":
                    msg = f"ℹ️ {event.get('message')}"
                    status_text.text(msg)
                    logs.append(msg)
                    
                elif evt_type == "progress":
                    cur = event.get("current", 0)
                    tot = event.get("total", 1)
                    # Global progress calculation
                    global_prog = (tc_idx - 1) / total_tcs + (cur / tot) * (0.5 / total_tcs)
                    progress_bar.progress(min(global_prog, 0.99), text=f"Step {tc_idx}/{total_tcs}: Parsing {cur}/{tot}...")
                    logs.append(f"✅ {event.get('message')}")
                    
                elif evt_type == "adapter_progress":
                    cur = event.get("current", 0)
                    tot = event.get("total", 1)
                    global_prog = (tc_idx - 1) / total_tcs + 0.5/total_tcs + (cur / tot) * (0.5 / total_tcs)
                    progress_bar.progress(min(global_prog, 0.99), text=f"Step {tc_idx}/{total_tcs}: Adapting {cur}/{tot}...")
                    
                elif evt_type == "error":
                    msg = f"❌ ERROR [TC {tc_idx}/{total_tcs}]: {event.get('message')}"
                    logs.append(msg)
                    st.error(msg)
                    
                elif evt_type == "success":
                    new_code = event.get("code_output", "")
                    if new_code:
                        if final_code:
                            final_code += "\n\n" + new_code
                        else:
                            final_code = new_code
                    
                    global_prog = tc_idx / total_tcs
                    progress_bar.progress(min(global_prog, 1.0), text=f"Completed {tc_idx}/{total_tcs}")
                    status_text.success(f"🎉 [TC {tc_idx}/{total_tcs}] Completed: {current_trace_id[:8]}")
                    
                # Real-time log update
                log_container.code("\n".join(logs[-10:]), language="text")
                time.sleep(0.01)
                
        except Exception as e:
            st.error(f"Pipeline crashed: {str(e)}")
        finally:
            os.remove(tmp_path)
            
        st.write("---")
        st.subheader("3. Generated Script")
        if final_code:
            # Topic 5. 자동 파일 저장 기능 구현
            results_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '../../results'))
            if not os.path.exists(results_dir):
                os.makedirs(results_dir)
            
            timestamp = time.strftime("%Y%m%d_%H%M%S")
            base_name = os.path.splitext(uploaded_file.name)[0]
            save_filename = f"gen_{base_name}_{timestamp}.py"
            save_path = os.path.join(results_dir, save_filename)
            
            with open(save_path, "w", encoding="utf-8") as f:
                f.write(final_code)
            
            st.success(f"💾 **Auto-saved to:** `{save_path}`")
            
            st.code(final_code, language="python")
            
            st.download_button(
                label="📥 Download Python Script",
                data=final_code,
                file_name=save_filename,
                mime="text/x-python",
            )
        else:
            st.warning(f"No code generated. Please check the logs. Trace ID: `{current_trace_id}`")

