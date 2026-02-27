"""
图生图测试 - 简洁版
支持sora-image和nano-banana
支持多图生图
"""
import streamlit as st
import requests
import time
from pathlib import Path


# 配置
API_KEY = "sk-ca999d825073499cbe1a0a724f91461c"
API_HOST = "https://grsai.dakka.com.cn"
PROXY_URL = "http://43.143.145.118:8085"


def upload_image(image_path):
    """上传图片到代理服务器"""
    url = f"{PROXY_URL}/upload/image"
    
    # 检测文件扩展名
    ext = Path(image_path).suffix.lower()
    if ext == '.png':
        mime_type = 'image/png'
    elif ext in ['.jpg', '.jpeg']:
        mime_type = 'image/jpeg'
    elif ext == '.gif':
        mime_type = 'image/gif'
    elif ext == '.webp':
        mime_type = 'image/webp'
    else:
        mime_type = 'image/png'  # 默认
    
    with open(image_path, 'rb') as f:
        files = {'image': (Path(image_path).name, f, mime_type)}
        resp = requests.post(url, files=files, timeout=60)
    
    if resp.status_code == 200:
        result = resp.json()
        return result.get('url') or result.get('data', {}).get('url')
    raise Exception(f"上传失败: {resp.status_code} - {resp.text}")


def poll_result(task_id):
    """轮询结果"""
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {API_KEY}"}
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    for _ in range(150):  # 最多5分钟
        resp = requests.post(f"{API_HOST}/v1/draw/result", json={"id": task_id}, headers=headers, timeout=10)
        data = resp.json()["data"]
        
        progress = data.get("progress", 0)
        status = data.get("status")
        
        progress_bar.progress(progress / 100)
        status_text.info(f"⏳ {progress}%")
        
        if status == "succeeded":
            progress_bar.empty()
            status_text.empty()
            return data
        elif status == "failed":
            raise Exception(f"{data.get('failure_reason')}: {data.get('error')}")
        
        time.sleep(2)
    
    raise TimeoutError("生成超时")


def generate(prompt, model, size, ref_urls=None):
    """生成图片"""
    headers = {"Content-Type": "application/json", "Authorization": f"Bearer {API_KEY}"}
    
    # GPT模型 (sora-image, gpt-image-1.5)
    if model in ["sora-image", "gpt-image-1.5"]:
        payload = {
            "model": model,
            "prompt": prompt,
            "size": size,
            "variants": 1,
            "webHook": "-1",
            "shutProgress": False
        }
        if ref_urls:
            payload["urls"] = ref_urls
        endpoint = f"{API_HOST}/v1/draw/completions"
    
    # Banana模型
    else:
        payload = {
            "model": model,
            "prompt": prompt,
            "aspectRatio": size,
            "imageSize": "2K",
            "webHook": "-1",
            "shutProgress": False
        }
        if ref_urls:
            payload["urls"] = ref_urls
        endpoint = f"{API_HOST}/v1/draw/nano-banana"
    
    # 提交任务
    st.info(f"📤 提交任务: {model}")
    with st.expander("请求详情"):
        st.json(payload)
    
    resp = requests.post(endpoint, json=payload, headers=headers, timeout=30)
    result = resp.json()
    
    if result.get("code") != 0:
        raise Exception(f"API错误: {result.get('msg')}")
    
    task_id = result["data"]["id"]
    st.success(f"✅ 任务ID: {task_id}")
    
    # 轮询结果
    data = poll_result(task_id)
    
    # 获取图片URL
    if model in ["sora-image", "gpt-image-1.5"]:
        img_url = data.get("url")
    else:
        results = data.get("results", [])
        img_url = results[0].get("url") if results else None
    
    if not img_url:
        raise Exception("未获取到图片URL")
    
    # 下载
    img_data = requests.get(img_url, timeout=60).content
    save_dir = Path("test_results")
    save_dir.mkdir(exist_ok=True)
    save_path = save_dir / f"{model}_{int(time.time())}.png"
    save_path.write_bytes(img_data)
    
    return str(save_path), img_url


# UI
st.set_page_config(page_title="图生图测试", page_icon="🎨", layout="wide")
st.title("🎨 图生图测试")

# 测试代理服务器
with st.expander("🔧 测试代理服务器"):
    if st.button("测试连接"):
        try:
            resp = requests.get(f"{PROXY_URL}/health", timeout=5)
            st.success(f"✅ 连接成功: {resp.status_code}")
        except Exception as e:
            st.error(f"❌ 连接失败: {e}")

tab1, tab2 = st.tabs(["📝 纯文生图", "🖼️ 图生图"])

# Tab1: 纯文生图
with tab1:
    st.subheader("📝 纯文生图")
    
    prompt1 = st.text_area("提示词", "a beautiful anime girl, high quality", height=80)
    
    col1, col2 = st.columns(2)
    with col1:
        model1 = st.selectbox("模型", ["sora-image", "gpt-image-1.5", "nano-banana-fast", "nano-banana-pro"])
    with col2:
        size1 = st.selectbox("尺寸", ["1:1", "16:9", "9:16", "2:3", "3:2"])
    
    if st.button("🚀 生成", type="primary", key="btn1"):
        try:
            save_path, url = generate(prompt1, model1, size1)
            st.success("✅ 生成成功")
            st.image(save_path, use_column_width=True)
            
            # 保存供图生图使用
            if 'ref_images' not in st.session_state:
                st.session_state.ref_images = []
            st.session_state.ref_images.append(save_path)
            
            st.info(f"💾 已保存到参考图库 (共{len(st.session_state.ref_images)}张)")
        except Exception as e:
            st.error(f"❌ 失败: {e}")


# Tab2: 图生图
with tab2:
    st.subheader("🖼️ 图生图 (支持多图)")
    
    # 上传参考图
    st.markdown("### 1️⃣ 准备参考图")
    
    uploaded_files = st.file_uploader(
        "上传参考图 (可多选)",
        type=["png", "jpg", "jpeg"],
        accept_multiple_files=True
    )
    
    if uploaded_files:
        upload_dir = Path("uploaded_refs")
        upload_dir.mkdir(exist_ok=True)
        
        if 'ref_images' not in st.session_state:
            st.session_state.ref_images = []
        
        for file in uploaded_files:
            path = upload_dir / file.name
            path.write_bytes(file.getbuffer())
            if str(path) not in st.session_state.ref_images:
                st.session_state.ref_images.append(str(path))
    
    # 显示参考图库
    if st.session_state.get('ref_images'):
        st.success(f"📚 参考图库: {len(st.session_state.ref_images)} 张")
        
        cols = st.columns(min(len(st.session_state.ref_images), 4))
        for idx, img_path in enumerate(st.session_state.ref_images):
            with cols[idx % 4]:
                st.image(img_path, caption=f"参考图{idx+1}", use_column_width=True)
        
        if st.button("🗑️ 清空参考图库"):
            st.session_state.ref_images = []
            st.rerun()
    else:
        st.info("💡 请上传图片或在Tab1生成图片")
    
    # 上传到代理服务器
    st.markdown("### 2️⃣ 上传到代理服务器")
    
    if st.button("📤 上传所有参考图", key="btn_upload"):
        if not st.session_state.get('ref_images'):
            st.error("❌ 没有参考图")
        else:
            urls = []
            progress = st.progress(0)
            
            for idx, img_path in enumerate(st.session_state.ref_images):
                try:
                    st.info(f"📤 上传 {idx+1}/{len(st.session_state.ref_images)}: {Path(img_path).name}")
                    url = upload_image(img_path)
                    urls.append(url)
                    st.success(f"✅ {Path(img_path).name} → {url}")
                except Exception as e:
                    st.error(f"❌ {Path(img_path).name}: {e}")
                    # 显示详细错误
                    with st.expander("错误详情"):
                        st.code(str(e))
                
                progress.progress((idx + 1) / len(st.session_state.ref_images))
            
            if urls:
                st.session_state.ref_urls = urls
                st.success(f"✅ 共上传 {len(urls)} 张")
            
            progress.empty()
    
    if st.session_state.get('ref_urls'):
        st.code("\n".join(st.session_state.ref_urls))
    
    # 图生图
    st.markdown("### 3️⃣ 图生图生成")
    
    prompt2 = st.text_area(
        "新提示词",
        "same style, different scene, standing in garden",
        height=80
    )
    
    col1, col2 = st.columns(2)
    with col1:
        model2 = st.selectbox(
            "模型",
            ["sora-image", "gpt-image-1.5", "nano-banana-fast", "nano-banana-pro"],
            key="model2"
        )
    with col2:
        size2 = st.selectbox("尺寸", ["16:9", "1:1", "9:16", "2:3"], key="size2")
    
    if st.button("🎨 图生图", type="primary", key="btn2"):
        if not st.session_state.get('ref_urls'):
            st.error("❌ 请先上传参考图到代理服务器")
        else:
            try:
                save_path, url = generate(prompt2, model2, size2, st.session_state.ref_urls)
                st.success("✅ 图生图成功")
                
                # 对比展示
                st.markdown("### 📊 对比")
                cols = st.columns([1, 2])
                
                with cols[0]:
                    st.markdown("**参考图**")
                    for img in st.session_state.ref_images:
                        st.image(img, use_column_width=True)
                
                with cols[1]:
                    st.markdown("**生成结果**")
                    st.image(save_path, use_column_width=True)
            
            except Exception as e:
                st.error(f"❌ 失败: {e}")
                st.code(str(e))


# 底部说明
st.markdown("---")
st.info("""
💡 **快速测试流程:**
1. Tab1: 生成1-2张基础图 (自动加入参考图库)
2. Tab2: 点击"上传所有参考图"
3. Tab2: 输入新提示词,点击"图生图"
4. 对比查看结果

🔧 **多图生图:**
- 可上传/生成多张参考图
- 一次性上传所有参考图
- API会综合所有参考图生成
""")