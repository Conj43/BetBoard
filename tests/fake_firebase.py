"""
Lightweight Firebase stand-ins for tests.
"""
from __future__ import annotations


class FakeBlob:
    def __init__(self, name: str, text: str | None = None):
        self.name = name
        self.text = text
        self.uploads: list[dict] = []
        self.set_calls: list = []

    def exists(self) -> bool:
        return self.text is not None

    def download_as_text(self) -> str:
        return self.text or ""

    def download_as_string(self) -> bytes:
        return (self.text or "").encode()

    def upload_from_string(self, data, content_type: str | None = None) -> None:
        payload = data.decode() if isinstance(data, bytes) else data
        self.text = payload
        self.uploads.append({"data": payload, "content_type": content_type})

    def set(self, payload) -> None:
        self.set_calls.append(payload)


class FakeBucket:
    def __init__(self):
        self.blobs: dict[str, FakeBlob] = {}

    def blob(self, name: str) -> FakeBlob:
        if name not in self.blobs:
            self.blobs[name] = FakeBlob(name)
        return self.blobs[name]

    def set_blob(self, name: str, text: str) -> FakeBlob:
        blob = FakeBlob(name, text)
        self.blobs[name] = blob
        return blob


class FakeFirestoreDoc:
    def __init__(self, doc_id: str):
        self.doc_id = doc_id
        self.set_calls: list[dict] = []
        self.collections: dict[str, FakeFirestoreCollection] = {}

    def set(self, body, merge: bool = False):
        self.set_calls.append({"body": body, "merge": merge})

    def collection(self, name: str):
        if name not in self.collections:
            self.collections[name] = FakeFirestoreCollection(name)
        return self.collections[name]


class FakeFirestoreCollection:
    def __init__(self, name: str):
        self.name = name
        self.docs: dict[str, FakeFirestoreDoc] = {}

    def document(self, doc_id: str) -> FakeFirestoreDoc:
        if doc_id not in self.docs:
            self.docs[doc_id] = FakeFirestoreDoc(doc_id)
        return self.docs[doc_id]


class FakeFirestoreClient:
    def __init__(self):
        self.collections: dict[str, FakeFirestoreCollection] = {}

    def collection(self, name: str) -> FakeFirestoreCollection:
        if name not in self.collections:
            self.collections[name] = FakeFirestoreCollection(name)
        return self.collections[name]
