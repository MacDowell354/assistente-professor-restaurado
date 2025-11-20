import os
from llama_index.core import (
    SimpleDirectoryReader,
    GPTVectorStoreIndex,
    StorageContext,
    load_index_from_storage,
    Settings,
)
from llama_index.embeddings.openai import OpenAIEmbedding

# 📁 Diretório e caminho do índice
INDEX_DIR = "storage"
INDEX_FILE = os.path.join(INDEX_DIR, "index.json")

# 🔑 Configura a API Key da OpenAI
api_key = os.getenv("OPENAI_API_KEY")
if not api_key:
    raise ValueError("❌ OPENAI_API_KEY não encontrada nas variáveis de ambiente.")

# 🤖 Define o modelo de embedding
Settings.embed_model = OpenAIEmbedding(
    model="text-embedding-3-small",
    api_key=api_key,
)

def load_or_build_index():
    """Carrega o índice existente ou cria um novo a partir de transcricoes.txt."""
    if os.path.exists(INDEX_FILE):
        print("📁 Índice encontrado. Carregando do disco...")
        storage_context = StorageContext.from_defaults(persist_dir=INDEX_DIR)
        return load_index_from_storage(storage_context)
    else:
        print("⚙️ Índice não encontrado. Construindo novo...")
        docs = SimpleDirectoryReader(input_files=["transcricoes.txt"]).load_data()
        index = GPTVectorStoreIndex.from_documents(docs)
        index.storage_context.persist(persist_dir=INDEX_DIR)
        print(f"✅ Índice construído com {len(docs)} documentos.")
        return index

# ⚡ Inicializa o índice na importação deste módulo
index = load_or_build_index()

def retrieve_relevant_context(
    question: str,
    top_k: int = 3,
    chunk_size: int = 512
) -> str:
    """
    Busca no índice até `top_k` trechos que respondam à `question`.
    Usa `chunk_size` para controlar o tamanho dos blocos de texto.
    Retorna string vazia se não encontrar algo relevante.
    """
    # DEBUG: confira nos logs qual pergunta chegou
    print("🔎 DEBUG — Pergunta para contexto:", question)

    # cria um engine de consulta ajustado
    engine = index.as_query_engine(
        similarity_top_k=top_k,
        chunk_size=chunk_size
    )

    response = engine.query(question)
    response_str = str(response).strip()
    # DEBUG: confira o texto bruto retornado
    print("🔎 DEBUG — Contexto bruto retornado:", response_str)

    lower = response_str.lower()
    # se vazio ou sem sentido
    if not lower or lower in ("none", "null"):
        print("🔎 DEBUG — Contexto vazio após normalização")
        return ""

    # bloqueia respostas genéricas
    for frase in ("não tenho certeza", "desculpe", "não sei"):
        if frase in lower:
            print("🔎 DEBUG — Contexto bloqueado por frase de incerteza")
            return ""

    # filtra termos fora de escopo
    proibidos = [
        "instagram", "vídeos para instagram", "celular para gravar", "smartphone",
        "tiktok", "post viral", "gravar vídeos", "microfone", "câmera",
        "edição de vídeo", "hashtags", "stories", "marketing de conteúdo",
        "produção de vídeo", "influencer"
    ]
    if any(tp in lower for tp in proibidos):
        print("🔎 DEBUG — Contexto bloqueado por termo proibido")
        return ""

    # DEBUG: contexto aprovado
    print("🔎 DEBUG — Contexto final aceito:", response_str)
    return response_str
