import streamlit as st
import requests
import os
from dotenv import load_dotenv

# 加载.env配置（与后端共用）
env_path = os.path.join(os.path.dirname(__file__), ".env")
load_dotenv(dotenv_path=env_path, override=True)

# 页面配置
st.set_page_config(page_title="🏫 智联校园 AI 助手", page_icon="🏫")
st.title("🏫 智联校园 AI 助手")

# 后端服务地址（可配置）
BACKEND_URL = "http://127.0.0.1:8001"

# 侧边栏：上传文件（对接后端 /upload 接口）
with st.sidebar:
    st.header("📚 知识库管理")
    st.caption("上传PDF文档后，即可基于文档内容问答")
    
    uploaded_file = st.file_uploader("上传PDF文档", type="pdf")
    
    if uploaded_file is not None:
        try:
            files = {"file": (uploaded_file.name, uploaded_file, "application/pdf")}
            
            with st.spinner("📤 正在上传并处理文档..."):
                response = requests.post(
                    f"{BACKEND_URL}/upload", 
                    files=files,
                    timeout=60  # 增大超时时间，适配大文件处理
                )
                
                if response.status_code == 200:
                    st.success("✅ 文档上传并处理成功！")
                else:
                    err_msg = response.json().get("error", f"状态码：{response.status_code}")
                    st.error(f"❌ 上传失败：{err_msg}")
                    
        except requests.exceptions.ConnectionError:
            st.error("❌ 无法连接到后端服务\n请先启动后端（端口8001）")
        except requests.exceptions.Timeout:
            st.error("❌ 上传超时，请检查文档大小或网络")
        except Exception as e:
            st.error(f"❌ 上传异常：{str(e)}")

# ---------------------
# 聊天界面（对接后端 /chat 接口，实现RAG问答）
# ---------------------
st.divider()
st.subheader("💬 智能问答")

# 初始化消息会话
if "messages" not in st.session_state:
    st.session_state.messages = [
        {"role": "assistant", "content": "你好！我是智联校园AI助手，上传PDF后可以向我提问～"}
    ]

# 显示历史消息
for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# 用户输入处理
prompt = st.chat_input("输入你的问题（例如：食堂有什么规定？）...")

if prompt:
    # 添加并显示用户消息
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    # 调用后端RAG问答接口
    with st.chat_message("assistant"):
        with st.spinner("🤔 AI正在检索并生成回答..."):
            try:
                # 调用后端/chat接口
                response = requests.post(
                    f"{BACKEND_URL}/chat",
                    data={"query": prompt},
                    timeout=30
                )
                
                if response.status_code == 200:
                    result = response.json()
                    answer = result["answer"]
                    st.markdown(answer)
                    
                    # 可选：显示参考的文档片段（折叠面板）
                    with st.expander("📄 查看参考资料"):
                        context = result.get("context_used", "无参考资料")
                        st.markdown(context)
                else:
                    err_detail = response.json().get("detail", f"状态码：{response.status_code}")
                    st.error(f"❌ 问答失败：{err_detail}")
                    
            except requests.exceptions.ConnectionError:
                st.error("❌ 无法连接到后端服务\n请先启动后端（端口8001）")
            except requests.exceptions.Timeout:
                st.error("❌ 问答超时，请重试")
            except Exception as e:
                st.error(f"❌ 问答异常：{str(e)}")
                answer = f"服务暂不可用：{str(e)}"
            
            # 记录AI回答到会话
            st.session_state.messages.append({"role": "assistant", "content": answer})

# 清空会话按钮
if st.button("🗑️ 清空聊天记录"):
    st.session_state.messages = [
        {"role": "assistant", "content": "你好！我是智联校园AI助手，上传PDF后可以向我提问～"}
    ]
    st.rerun()  # 刷新页面