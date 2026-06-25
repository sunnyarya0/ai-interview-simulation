from functools import lru_cache

import chromadb
from chromadb.api import ClientAPI
from chromadb.api.models.Collection import Collection
from chromadb.utils import embedding_functions

from app.core.config import settings

RESUME_COLLECTION = "resumes"

# all-MiniLM-L6-v2 via ONNX (bundled with chromadb — no torch dependency).
_embedding_fn = embedding_functions.DefaultEmbeddingFunction()


@lru_cache
def get_chroma_client() -> ClientAPI:
    return chromadb.PersistentClient(path=settings.CHROMA_PATH)


def get_resume_collection() -> Collection:
    return get_chroma_client().get_or_create_collection(
        name=RESUME_COLLECTION,
        embedding_function=_embedding_fn,
    )


if __name__ == "__main__":
    col = get_chroma_client().get_or_create_collection(
        name="smoke_test", embedding_function=_embedding_fn
    )
    col.upsert(
        ids=["a", "b"],
        documents=["Experienced Python developer", "Professional football player"],
    )
    res = col.query(query_texts=["python programming"], n_results=2)
    top = res["documents"][0][0]
    print("top match:", top)
    assert "Python" in top, "expected the python doc to rank first"
    print("OK")
    get_chroma_client().delete_collection("smoke_test")
