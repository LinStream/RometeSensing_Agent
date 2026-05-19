# rag_service 代码讲解文档

这份文档用于解释项目中 `rag_service.py` 或 `langchain_rag_service.py` 的作用。  
你可以把它理解成：**RAG 业务逻辑总控制器**。

---

## 1. rag_service 在项目中的位置

项目调用链大致是：

```text
Streamlit 前端
    ↓ requests.post()
FastAPI API 层
    ↓ 调用 service 函数
rag_service
    ↓
Loader / Splitter / Embedding / Chroma / Prompt / LLM
```

也就是说：

```text
前端负责页面；
FastAPI 负责接口；
rag_service 负责真正的 RAG 业务逻辑。
```

---

## 2. rag_service 的两条主线

### 2.1 文档入库线

```text
PDF 文件
    ↓
PyPDFLoader
    ↓
Document
    ↓
RecursiveCharacterTextSplitter
    ↓
Chunk Documents
    ↓
DashScopeEmbeddings
    ↓
Chroma
```

作用：

```text
把用户上传的 PDF 资料变成可以检索的向量知识库。
```

---

### 2.2 问答线

```text
用户问题
    ↓
Chroma 相似度检索
    ↓
相关 chunks
    ↓
PromptTemplate
    ↓
ChatTongyi
    ↓
StrOutputParser
    ↓
最终回答
```

作用：

```text
根据知识库检索相关资料，再让大模型基于资料回答。
```

---

## 3. 你应该先记住的总流程

```text
PDF
→ Document
→ Chunk Document
→ Embedding
→ Chroma
→ Retrieve
→ Prompt
→ LLM
→ Answer
```

这是整个 RAG 的主链路。

---

# 4. 常见导入解释

## 4.1 Python 基础库

```python
from pathlib import Path
from typing import Any, Dict, List
import shutil
```

| 导入 | 作用 |
|---|---|
| `Path` | 处理文件路径 |
| `Any / Dict / List` | 类型标注 |
| `shutil` | 删除文件夹、复制文件 |

---

## 4.2 LangChain 相关组件

```python
from langchain_community.document_loaders import PyPDFLoader
from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter
from langchain_chroma import Chroma
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import StrOutputParser
```

| 组件 | 作用 |
|---|---|
| `PyPDFLoader` | PDF 转 Document |
| `Document` | LangChain 的文本数据结构 |
| `RecursiveCharacterTextSplitter` | 文本切分 |
| `Chroma` | 向量数据库 |
| `PromptTemplate` | 构建提示词 |
| `StrOutputParser` | 把模型输出转成字符串 |

---

## 4.3 百炼 / 通义相关组件

```python
from langchain_community.chat_models import ChatTongyi
from langchain_community.embeddings import DashScopeEmbeddings
```

| 组件 | 作用 |
|---|---|
| `ChatTongyi` | 调用百炼/通义聊天模型 |
| `DashScopeEmbeddings` | 调用百炼 embedding 模型 |

---

# 5. 核心函数一：load_pdf()

## 作用

```text
把 PDF 文件转换成 LangChain Document。
```

也就是：

```text
文件 → Document
```

## 典型代码

```python
def load_pdf(pdf_path: Path) -> List[Document]:
    loader = PyPDFLoader(str(pdf_path))
    docs = loader.load()

    if not docs:
        raise ValueError("PDF 没有加载出任何文档内容。可能是扫描版 PDF，需要 OCR。")

    for doc in docs:
        doc.metadata["doc_name"] = pdf_path.name

    return docs
```

## 输入

```python
pdf_path: Path
```

示例：

```python
Path("data/uploads/遥感导论.pdf")
```

## 输出

```python
List[Document]
```

示例：

```python
[
    Document(
        page_content="遥感是指...",
        metadata={
            "source": "data/uploads/遥感导论.pdf",
            "page": 0,
            "doc_name": "遥感导论.pdf"
        }
    )
]
```

## 你要理解

`PyPDFLoader.load()` 返回的不是字符串，而是：

```text
List[Document]
```

每个 Document 有两部分：

```text
page_content：正文内容
metadata：来源信息，例如文件名、页码
```

---

# 6. 核心函数二：split_documents()

## 作用

```text
把长 Document 切成多个小 Document。
```

也就是：

```text
Document → Chunk Documents
```

## 典型代码

```python
def split_documents(docs: List[Document]) -> List[Document]:
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=settings.chunk_size,
        chunk_overlap=settings.chunk_overlap,
        separators=[
            "\n\n",
            "\n",
            "。",
            "！",
            "？",
            "；",
            "，",
            " ",
            "",
        ],
        length_function=len,
    )

    chunks = splitter.split_documents(docs)

    chunks = [
        chunk for chunk in chunks
        if isinstance(chunk.page_content, str) and chunk.page_content.strip()
    ]

    if not chunks:
        raise ValueError("文档切分后为空。")

    return chunks
```

## 输入

```python
docs: List[Document]
```

## 输出

```python
List[Document]
```

但此时这些 Document 是切分后的 chunk。

## 为什么要切分

```text
1. PDF 太长，不能整本直接 embedding；
2. 检索需要定位到局部内容；
3. 大模型上下文有限；
4. chunk 更适合做语义检索。
```

## 参数解释

```python
chunk_size = 700
```

每个 chunk 大约 700 个字符。

```python
chunk_overlap = 100
```

相邻 chunk 重叠 100 个字符。

重叠的作用：

```text
避免一句话或一个知识点刚好被切断。
```

---

# 7. 核心函数三：get_embeddings()

## 作用

```text
创建 embedding 模型对象。
```

## 典型代码

```python
def get_embeddings():
    return DashScopeEmbeddings(
        model=settings.embedding_model,
        dashscope_api_key=settings.openai_api_key,
    )
```

## 它负责什么

Embedding 模型负责：

```text
文本 → 向量
```

例如：

```text
“什么是遥感？”
```

会变成：

```text
[0.123, -0.542, ...]
```

这样才能和 Chroma 里的文档向量做相似度匹配。

---

# 8. 核心函数四：get_vector_store()

## 作用

```text
创建或获取 Chroma 向量数据库对象。
```

## 典型代码

```python
def get_vector_store() -> Chroma:
    return Chroma(
        collection_name=settings.chroma_collection_name,
        embedding_function=get_embeddings(),
        persist_directory=str(settings.chroma_path),
    )
```

## 参数解释

```python
collection_name
```

知识库名称。

```python
embedding_function
```

Chroma 用哪个 embedding 模型来生成向量。

```python
persist_directory
```

Chroma 数据保存到哪里。

## 你要理解

Chroma 存的不是普通文本，而是：

```text
文本
+
文本向量
+
metadata
```

---

# 9. 核心函数五：ingest_pdf()

## 作用

```text
完整执行 PDF 入库流程。
```

这是用户上传 PDF 后最核心的函数。

## 典型代码

```python
def ingest_pdf(pdf_path: Path) -> int:
    docs = load_pdf(pdf_path)
    chunks = split_documents(docs)

    vector_store = get_vector_store()
    vector_store.add_documents(chunks)

    return len(chunks)
```

## 输入

```python
pdf_path: Path
```

## 输出

```python
int
```

表示这个 PDF 被切成了多少个 chunks。

## 内部流程

```text
ingest_pdf(pdf_path)
    ↓
load_pdf(pdf_path)
    ↓
split_documents(docs)
    ↓
get_vector_store()
    ↓
vector_store.add_documents(chunks)
    ↓
return len(chunks)
```

## add_documents() 做了什么

```python
vector_store.add_documents(chunks)
```

LangChain 会自动：

```text
1. 读取 Document.page_content；
2. 调用 embedding_function；
3. 生成向量；
4. 把向量、文本、metadata 写入 Chroma。
```

---

# 10. 核心函数六：retrieve()

## 作用

```text
根据用户问题，从 Chroma 中检索相关 chunks。
```

## 典型代码

```python
def retrieve(question: str, top_k: int = 4):
    vector_store = get_vector_store()

    results = vector_store.similarity_search_with_score(
        query=question,
        k=top_k,
    )

    return results
```

## 输入

```python
question: str
top_k: int
```

## 输出

通常是：

```python
List[tuple[Document, float]]
```

例如：

```python
[
    (
        Document(page_content="遥感是指...", metadata={...}),
        0.234
    )
]
```

## 内部发生了什么

```text
用户问题
    ↓
embedding
    ↓
问题向量
    ↓
和 Chroma 中所有 chunk 向量计算相似度
    ↓
返回最相关的 top_k 个 chunk
```

---

# 11. 核心函数七：format_docs_for_prompt()

## 作用

```text
把检索出来的 Document 整理成可以放进 Prompt 的文本。
```

## 典型代码

```python
def format_docs_for_prompt(docs: List[Document]) -> str:
    parts = []

    for i, doc in enumerate(docs, start=1):
        doc_name = doc.metadata.get("doc_name")
        page = doc.metadata.get("page")

        title = f"资料{i}"

        if doc_name:
            title += f"｜{doc_name}"

        if page is not None:
            title += f"｜第{int(page) + 1}页"

        parts.append(f"【{title}】\n{doc.page_content}")

    return "\n\n".join(parts)
```

## 输入

```python
List[Document]
```

## 输出

```python
str
```

示例：

```text
【资料1｜遥感导论.pdf｜第12页】
遥感是指...

【资料2｜遥感原理.pdf｜第8页】
遥感系统包括...
```

## 为什么需要它

大模型不能直接理解 `Document` 对象。  
你必须把 Document 转成字符串，放进 Prompt。

---

# 12. 核心函数八：build_prompt()

## 作用

```text
创建 RAG Prompt 模板。
```

## 典型代码

```python
def build_prompt():
    return PromptTemplate.from_template(
        '''
你是一个严谨的遥感资料学习助手。

请只根据以下资料回答问题。
如果资料不足，请回答：资料中没有足够信息。
不要编造。

检索资料：
{context}

用户问题：
{question}

请给出适合考研复习的回答。
'''
    )
```

## Prompt 里通常包括

```text
角色设定
回答规则
检索资料
用户问题
输出要求
```

## RAG 为什么依赖 Prompt

大模型本身不知道你的 PDF。  
它只知道 Prompt 里给它的内容。

所以：

```text
检索结果必须拼进 Prompt
```

---

# 13. 核心函数九：get_llm()

## 作用

```text
创建聊天模型对象。
```

## 典型代码

```python
def get_llm():
    return ChatTongyi(
        model=settings.openai_model,
        dashscope_api_key=settings.openai_api_key,
        temperature=0.2,
    )
```

## 它负责什么

`ChatTongyi` 负责：

```text
根据 Prompt 生成最终回答。
```

---

# 14. 核心函数十：answer_question()

## 作用

```text
完整执行一次 RAG 问答。
```

这是问答接口最终调用的核心函数。

## 典型代码

```python
def answer_question(question: str, top_k: int = 4) -> Dict[str, Any]:
    results = retrieve(question, top_k=top_k)

    if not results:
        return {
            "answer": "知识库里还没有可检索内容，请先上传 PDF 并入库。",
            "sources": [],
        }

    docs = [doc for doc, score in results]
    context = format_docs_for_prompt(docs)

    prompt = build_prompt()
    model = get_llm()

    chain = prompt | model | StrOutputParser()

    answer = chain.invoke(
        {
            "question": question,
            "context": context,
        }
    )

    sources = []

    for doc, score in results:
        sources.append(
            {
                "doc_name": doc.metadata.get("doc_name"),
                "page": doc.metadata.get("page"),
                "score": float(score),
                "text": doc.page_content,
            }
        )

    return {
        "answer": answer,
        "sources": sources,
    }
```

## 输入

```python
question: str
top_k: int
```

## 输出

```python
Dict[str, Any]
```

示例：

```python
{
    "answer": "遥感是指...",
    "sources": [
        {
            "doc_name": "遥感导论.pdf",
            "page": 12,
            "score": 0.23,
            "text": "遥感是指..."
        }
    ]
}
```

## 内部流程

```text
answer_question()
    ↓
retrieve()
    ↓
拿到相关 Document
    ↓
format_docs_for_prompt()
    ↓
build_prompt()
    ↓
get_llm()
    ↓
prompt | model | StrOutputParser()
    ↓
返回 answer + sources
```

---

# 15. chain = prompt | model | StrOutputParser() 是什么意思

这是 LangChain 的 LCEL 写法。

```python
prompt
```

负责填充模板。

```python
model
```

负责调用大模型。

```python
StrOutputParser()
```

负责把模型输出转成普通字符串。

所以：

```python
chain = prompt | model | StrOutputParser()
```

意思是：

```text
Prompt 模板
    ↓
大模型
    ↓
字符串解析器
```

调用时：

```python
answer = chain.invoke(
    {
        "question": question,
        "context": context,
    }
)
```

意思是：

```text
把问题和检索资料传进 Prompt，
再让大模型生成回答。
```

---

# 16. 核心函数十一：get_stats()

## 作用

```text
查看当前知识库中有多少 chunks。
```

## 典型代码

```python
def get_stats():
    vector_store = get_vector_store()
    collection = vector_store._collection

    return {
        "collection_name": settings.chroma_collection_name,
        "chunks_count": collection.count(),
    }
```

## 前端显示示例

```text
Collection：remote_sensing_rag
Chunks：128
```

---

# 17. 核心函数十二：clear_knowledge_base()

## 作用

```text
清空知识库。
```

## 典型代码

```python
def clear_knowledge_base():
    if chroma_dir.exists():
        shutil.rmtree(chroma_dir)

    if upload_dir.exists():
        shutil.rmtree(upload_dir)

    chroma_dir.mkdir(parents=True, exist_ok=True)
    upload_dir.mkdir(parents=True, exist_ok=True)
```

## 清空内容

```text
1. Chroma 向量库目录
2. 上传 PDF 文件目录
```

## 注意

开发阶段这样清空可以。  
正式项目后续应该支持：

```text
删除指定文档
```

而不是只能全部清空。

---

# 18. 记忆方法

你可以把 `rag_service` 记成两条线。

## 18.1 入库线

```text
ingest_pdf()
    ↓
load_pdf()
    ↓
split_documents()
    ↓
get_vector_store()
    ↓
add_documents()
```

## 18.2 问答线

```text
answer_question()
    ↓
retrieve()
    ↓
format_docs_for_prompt()
    ↓
build_prompt()
    ↓
get_llm()
    ↓
chain.invoke()
```

---

# 19. 面试讲法

你可以这样讲：

```text
项目中的 rag_service 主要负责 RAG 主流程。文档上传后，系统使用 PyPDFLoader 将 PDF 转换为 LangChain Document，再通过 RecursiveCharacterTextSplitter 对文档进行递归切分，随后使用 DashScopeEmbeddings 生成文本向量，并通过 Chroma 持久化保存。用户提问时，系统基于 Chroma 进行相似度检索，获得相关文档片段后，将其格式化为上下文并拼接到 PromptTemplate 中，最后调用 ChatTongyi 生成回答，并返回答案及来源片段，实现了可追溯的领域知识库问答流程。
```

---

# 20. 你现在最应该掌握的点

不用背全部代码。  
你先重点掌握：

```text
1. Loader：文件转 Document
2. Splitter：Document 转 chunks
3. Embedding：文本转向量
4. Chroma：存储和检索向量
5. Prompt：问题 + 检索资料
6. LLM：生成回答
7. sources：回答来源追溯
```

这七个点掌握了，`rag_service` 就基本理解了。
