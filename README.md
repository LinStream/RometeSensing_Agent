# 遥感资料 RAG 问答系统

## 1. RAG 部分思路沿用参考项目

本项目 RAG 部分主要用：

```text
ChatTongyi
DashScopeEmbeddings
Chroma
RecursiveCharacterTextSplitter
PyPDFLoader
TextLoader
PromptTemplate
StrOutputParser
```

## 2. 项目结构

```text
rs_rag_fastapi_streamlit_ref_agent/
├── backend/
│   └── app/
│       ├── main.py
│       ├── api/rag.py
│       └── schemas/rag.py
├── frontend/
│   └── streamlit_app.py
├── rag/
│   ├── vector_store.py
│   └── rag_service.py
├── model/
│   └── factory.py
├── utils/
│   ├── config_handler.py
│   ├── file_handler.py
│   ├── logger_handler.py
│   ├── path_tool.py
│   └── prompt_loader.py
├── config/
│   ├── rag.yml
│   ├── chroma.yml
│   └── prompts.yml
├── prompts/
│   └── rag_summarize.txt
├── data/
├── chroma_db/
├── logs/
├── docs/
├── requirements.txt
└── .env.example
```

## 3. 配置 API Key

推荐设置：

```env
DASHSCOPE_API_KEY=你的百炼key
```

如果你已经设置了：

```env
OPENAI_API_KEY=你的百炼key
```

本项目也做了兼容，会自动复制到 `DASHSCOPE_API_KEY`。

## 4. 安装依赖

```bash
conda create -n rs-rag python=3.11 -y
conda activate rs-rag
pip install -r requirements.txt
```

## 5. 启动后端

```bash
uvicorn backend.app.main:app --reload --port 8000
```

接口文档：

```text
http://127.0.0.1:8000/docs
```

## 6. 启动前端

另开一个终端：

```bash
streamlit run frontend/streamlit_app.py
```

## 7. 测试顺序

```text
1. 测试后端连接
2. 上传 PDF/TXT
3. 查看知识库状态
4. 提问测试
```

## 8. 和参考项目的对应关系（参考了黑马的agent+rag项目）

| 参考项目 | 当前项目 |
|---|---|
| `model/factory.py` | 保留并适配 |
| `rag/vector_store.py` | 保留结构，增加 `load_single_file()` |
| `rag/rag_service.py` | 保留 `PromptTemplate | model | StrOutputParser` 链 |
| `utils/config_handler.py` | 保留 YAML 配置方式 |
| `utils/file_handler.py` | 保留 loader / md5 思路 |
| `app.py` Streamlit 单体 | 改成 Streamlit + FastAPI 分离 |
