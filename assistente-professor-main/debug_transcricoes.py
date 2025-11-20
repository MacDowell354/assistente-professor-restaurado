# debug_transcricoes.py
# Script para verificar a leitura de transcricoes.txt e testar search_transcripts

import os
import re
from gpt_utils import search_transcripts, normalize_key

# Carrega diretamente o arquivo para debug
BASE_DIR = os.path.dirname(__file__)
try:
    with open(os.path.join(BASE_DIR, "transcricoes.txt"), encoding="utf-8") as f:
        txt = f.read()
except FileNotFoundError:
    txt = ""

# 1) Debug do carregamento do arquivo
print("[DEBUG] Tamanho do texto carregado:", len(txt), "caracteres")
print("[DEBUG] Primeiro trecho de 200 caracteres:\n", txt[:200])

# 2) Testes de busca de trechos
queries = [
    "decorar meu consultorio",
    "gatilho da reciprocidade",
    "atualização de valor de consulta",
    "patient letter formato digital vs manuscrita",
    "exemplo pratico"
]

print("\n[DEBUG] Testando search_transcripts para consultas-chave:")
for q in queries:
    result = search_transcripts(q, max_sentences=3)
    print(f"\nPergunta: {q}")
    if result:
        for idx, sent in enumerate(result.split('<br>')):
            print(f"  - Trecho {idx+1}: {sent}")
    else:
        print("  > Nenhum trecho encontrado.")
