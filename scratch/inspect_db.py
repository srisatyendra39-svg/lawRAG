import sys
from pathlib import Path

# Add project root to python path
sys.path.append(str(Path(__file__).resolve().parent.parent))

from configs.settings import get_settings
from vectorstore.chroma_store import get_vector_store

vector_store = get_vector_store()
stats = vector_store.get_collection_stats()
print("Collection Stats:")
print(stats)

print("\n--- Retrieving All Chunks ---")
data = vector_store.collection.get()
print(f"Total retrieved from Chroma: {len(data['ids'])}")
for idx, (doc_id, metadata, document) in enumerate(zip(data['ids'], data['metadatas'], data['documents'])):
    print(f"\nChunk {idx+1}:")
    print(f"  ID: {doc_id}")
    print(f"  Metadata: {metadata}")
    print(f"  Snippet: {document[:200]}...")
