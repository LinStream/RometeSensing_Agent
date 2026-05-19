# 阶段 3 补充：基于 file_md5 防止重复上传

## 为什么要改

原来项目可以重复上传同一份文件，原因是：

1. `documents` 表只记录了文件名、路径、状态，没有记录文件内容指纹。
2. 上传接口没有先判断“同内容文件是否已成功入库”。
3. `md5.text` 只在向量库层面跳过重复入库，但不能阻止 MySQL 新增重复文档记录。

所以现在增加 `file_md5` 字段，把“业务层去重”放到 MySQL 中。

## 改动内容

### 1. `backend/app/db/models.py`

`Document` 增加：

```python
file_md5: Mapped[Optional[str]] = mapped_column(String(64), nullable=True, index=True)
```

### 2. `backend/app/crud/document.py`

`create_document()` 增加 `file_md5` 参数。

新增：

```python
get_indexed_document_by_md5(db, file_md5)
```

只查询 `status == "indexed"` 的文档。之前失败的文档允许重新上传。

### 3. `backend/app/api/rag.py`

上传流程变成：

```text
保存文件
↓
计算 MD5
↓
查 MySQL 是否已有相同 file_md5 且 status=indexed 的文档
↓
如果有：删除刚保存的重复文件，返回 409
↓
如果没有：创建 document 记录，写入 Chroma，更新状态 indexed
```

## 已有数据库需要手动加字段

如果你的 MySQL 表已经存在，`create_all()` 不会自动给旧表加列。

请手动执行：

```sql
ALTER TABLE documents ADD COLUMN file_md5 VARCHAR(64) NULL COMMENT '文件MD5，用于判断重复上传';
CREATE INDEX idx_documents_file_md5 ON documents(file_md5);
```

如果你的表里已经有测试数据，建议先清空旧数据并重新测试：

```sql
TRUNCATE TABLE documents;
```

同时清空 Chroma 和 `md5.text`，避免旧状态干扰。

## 测试方式

1. 上传一个 PDF/TXT，应该成功。
2. 再上传同一份文件，应该返回 409。
3. 删除该文档。
4. 再上传同一份文件，应该允许重新上传。
