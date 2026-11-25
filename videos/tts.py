import sys, os, asyncio, certifi
# Certificado extra só existe no ambiente Linux onde os vídeos foram gravados pela primeira vez
_ca = "/root/.ccr/ca-bundle.crt"
if os.path.exists(_ca):
    certifi.where = lambda: _ca
import edge_tts
voz, texto, saida = sys.argv[1], sys.argv[2], sys.argv[3]
asyncio.run(edge_tts.Communicate(texto, voz, rate=os.environ.get("TTS_RATE", "+5%")).save(saida))
