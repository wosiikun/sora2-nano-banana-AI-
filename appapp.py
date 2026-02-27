"""
app.py - Streamlit 显示界面
"""
import streamlit as st
import subprocess
import json
import time
import os
import tempfile
from datetime import datetime

st.set_page_config(page_title="Sora", page_icon="🎬", layout="wide")

LOG_FILE = "logs.json"
ALL_APIS = ["yuansora", "yunwusora"]

def read_logs():
    if os.path.exists(LOG_FILE):
        try:
            with open(LOG_FILE, 'r', encoding='utf-8') as f:
                return json.load(f)
        except:
            return {}
    return {}

def clear_task_logs(task_type):
    """清空指定任务的日志"""
    logs = read_logs()
    for api in ALL_APIS:
        key = f"{task_type}_{api}"
        if key in logs:
            del logs[key]
    with open(LOG_FILE, 'w', encoding='utf-8') as f:
        json.dump(logs, f, ensure_ascii=False, indent=2)

def start_worker(task_id, api_name, prompt, duration, orientation, style, image_path):
    """启动独立worker进程"""
    cmd = [
        "python", "worker.py",
        task_id, api_name, prompt, str(duration), orientation, style,
        image_path if image_path else "None"
    ]
    subprocess.Popen(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)

# ==================== UI ====================

st.title("🎬 Sora 多API测试")

mode = st.radio("模式", ["串行", "并行"], horizontal=True)

col1, col2 = st.columns(2)

# 文生视频
with col1:
    st.subheader("📝 文生视频")
    tp = st.text_area("提示词", key="tp", height=60, placeholder="a cat walking")
    
    tc1, tc2, tc3 = st.columns(3)
    with tc1:
        td = st.selectbox("时长", [10, 15], key="td")
    with tc2:
        to = st.selectbox("方向", ["portrait", "landscape"], key="to")
    with tc3:
        ts = st.selectbox("风格", ["none", "comic", "anime"], key="ts")
    
    if st.button("🚀 生成", key="tb", type="primary"):
        if tp:
            clear_task_logs("text")
            
            if mode == "并行":
                # 并行：同时启动所有API
                for api in ALL_APIS:
                    task_id = f"text_{api}"
                    start_worker(task_id, api, tp, td, to, ts, None)
                st.success(f"✅ 已启动 {len(ALL_APIS)} 个任务")
            else:
                # 串行：只启动第一个
                task_id = f"text_{ALL_APIS[0]}"
                start_worker(task_id, ALL_APIS[0], tp, td, to, ts, None)
                st.success(f"✅ 已启动 {ALL_APIS[0]}")

# 图生视频
with col2:
    st.subheader("🖼️ 图生视频")
    ip = st.text_area("提示词", key="ip", height=60, placeholder="make it move")
    ifile = st.file_uploader("图片", type=["jpg", "png"], key="if")
    
    ic1, ic2, ic3 = st.columns(3)
    with ic1:
        id_ = st.selectbox("时长", [10, 15], key="id")
    with ic2:
        io = st.selectbox("方向", ["portrait", "landscape"], key="io")
    with ic3:
        is_ = st.selectbox("风格", ["none", "comic", "anime"], key="is")
    
    if st.button("🚀 生成", key="ib", type="primary"):
        if ip and ifile:
            # 保存图片
            with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp:
                tmp.write(ifile.getvalue())
                img_path = tmp.name
            
            clear_task_logs("image")
            
            if mode == "并行":
                for api in ALL_APIS:
                    task_id = f"image_{api}"
                    start_worker(task_id, api, ip, id_, io, is_, img_path)
                st.success(f"✅ 已启动 {len(ALL_APIS)} 个任务")
            else:
                task_id = f"image_{ALL_APIS[0]}"
                start_worker(task_id, ALL_APIS[0], ip, id_, io, is_, img_path)
                st.success(f"✅ 已启动 {ALL_APIS[0]}")
        else:
            st.error("❌ 需要提示词和图片")

# 显示日志
st.markdown("---")
st.header("📊 实时日志")

logs = read_logs()

lc1, lc2 = st.columns(2)

with lc1:
    st.subheader("📝 文生视频")
    for api in ALL_APIS:
        key = f"text_{api}"
        if key in logs:
            task = logs[key]
            with st.expander(f"🔹 {api} - {task['status']}", expanded=True):
                # 显示日志
                for line in task["logs"][-20:]:
                    st.text(line)
                
                # 显示结果
                if task["status"] == "success" and task["result"]:
                    st.success("✅ 成功")
                    st.video(task["result"]["video_url"])
                    st.caption(f"ID: {task['result'].get('task_id', '')}")
                elif task["status"] == "failed" and task["result"]:
                    st.error(f"❌ {task['result'].get('error', '')}")

with lc2:
    st.subheader("🖼️ 图生视频")
    for api in ALL_APIS:
        key = f"image_{api}"
        if key in logs:
            task = logs[key]
            with st.expander(f"🔹 {api} - {task['status']}", expanded=True):
                # 显示日志
                for line in task["logs"][-20:]:
                    st.text(line)
                
                # 显示结果
                if task["status"] == "success" and task["result"]:
                    st.success("✅ 成功")
                    st.video(task["result"]["video_url"])
                    st.caption(f"ID: {task['result'].get('task_id', '')}")
                elif task["status"] == "failed" and task["result"]:
                    st.error(f"❌ {task['result'].get('error', '')}")

# 自动刷新（仅当有运行中的任务时）
has_running = any(task.get("status") == "running" for task in logs.values())

if has_running:
    time.sleep(3)
    st.rerun()
else:
    # 显示刷新按钮
    if st.button("🔄 手动刷新"):
        st.rerun()