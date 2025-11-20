import os
import shutil
from llama_index.core import (
    SimpleDirectoryReader,
    GPTVectorStoreIndex,
    Settings
)
from llama_index.embeddings.openai import OpenAIEmbedding

# Caminho de saída
INDEX_DIR = "storage"

# Apaga índice antigo (importante!)
if os.path.exists(INDEX_DIR):
    print("🧹 Limpando índice anterior...")
    shutil.rmtree(INDEX_DIR)

# Carrega a chave da API da OpenAI
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    raise ValueError("❌ OPENAI_API_KEY não encontrada nas variáveis de ambiente.")

# Define o modelo de embedding
Settings.embed_model = OpenAIEmbedding(
    model="text-embedding-3-small",
    api_key=api_key,
)

# Lê os dados da transcrição
print("📄 Lendo o arquivo transcricoes.txt...")
documents = SimpleDirectoryReader(input_files=["transcricoes.txt"]).load_data()

# Gera o índice
print("⚙️ Gerando o índice vetorial...")
index = GPTVectorStoreIndex.from_documents(documents)

# Persiste no diretório
print(f"💾 Salvando índice em: {INDEX_DIR}")
index.storage_context.persist(persist_dir=INDEX_DIR)

print("✅ Índice criado com sucesso.")
