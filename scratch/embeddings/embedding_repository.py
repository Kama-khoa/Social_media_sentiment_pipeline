from __future__ import annotations

import json
import logging
import os
from typing import Optional

from dotenv import load_dotenv
from sqlalchemy import Column, String, Text, create_engine
from sqlalchemy.orm import declarative_base, sessionmaker

# Tải biến môi trường từ file .env
load_dotenv()

logger = logging.getLogger(__name__)

Base = declarative_base()

class EmbeddingRecord(Base):
    """
    Model lưu trữ dữ liệu Embedding.
    Bảng này có thể được tạo trên SQLite (local file) hoặc PostgreSQL.
    """
    __tablename__ = 'int_comment_embeddings'

    # Hash SHA256 của câu để tra cứu O(1) (Exact Match)
    text_hash = Column(String(64), primary_key=True)
    # Câu văn bản gốc đã chuẩn hóa
    sentence_text_norm = Column(Text, nullable=False)
    # Tên model sử dụng
    embedding_model = Column(String(100), nullable=False)
    # Lưu vector dưới dạng JSON string. 
    # Mẹo: Nếu dùng PostgreSQL thực tế, bạn có thể đổi kiểu này thành `Vector` của pgvector.
    embedding_vector_json = Column(Text, nullable=False)


class EmbeddingRepository:
    def __init__(self, db_url: Optional[str] = None) -> None:
        """
        Khởi tạo kết nối DB.
        Đọc POSTGRES_URL từ .env, nếu không có sẽ tự động dùng SQLite local file.
        Ví dụ trong .env: POSTGRES_URL=postgresql://user:pass@localhost:5432/dbname
        """
        if db_url is None:
            db_url = os.environ.get("POSTGRES_URL", "sqlite:///data/embeddings.db")
            
        logger.info(f"Kết nối Database sử dụng URL: {db_url}")
        self.engine = create_engine(db_url, echo=False)
        Base.metadata.create_all(self.engine)
        self.Session = sessionmaker(bind=self.engine)

    def get_by_hash(self, text_hash: str) -> Optional[list[float]]:
        """Lấy vector bằng mã Hash (Cache Hit O(1))."""
        with self.Session() as session:
            record = session.query(EmbeddingRecord).filter_by(text_hash=text_hash).first()
            if record:
                return json.loads(record.embedding_vector_json)
        return None

    def save(self, text_hash: str, text_norm: str, model_name: str, vector: list[float]) -> None:
        """Lưu một vector mới vào database."""
        with self.Session() as session:
            # Kiểm tra xem đã tồn tại chưa để tránh lỗi trùng khóa chính
            exists = session.query(EmbeddingRecord).filter_by(text_hash=text_hash).first()
            if not exists:
                new_record = EmbeddingRecord(
                    text_hash=text_hash,
                    sentence_text_norm=text_norm,
                    embedding_model=model_name,
                    embedding_vector_json=json.dumps(vector)
                )
                session.add(new_record)
                session.commit()

    def get_all_vectors(self) -> list[dict]:
        """
        Lấy toàn bộ vector để phục vụ tính toán Semantic Dedup (hoặc KNN) ở mem/local.
        Lưu ý: Nếu data quá lớn, không nên dùng hàm này mà nên dùng pgvector index trên PostgreSQL.
        """
        results = []
        with self.Session() as session:
            records = session.query(EmbeddingRecord).all()
            for r in records:
                results.append({
                    "hash": r.text_hash,
                    "text": r.sentence_text_norm,
                    "vector": json.loads(r.embedding_vector_json)
                })
        return results
