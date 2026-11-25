import sys, asyncio, certifi
certifi.where = lambda: "/root/.ccr/ca-bundle.crt"
import edge_tts
voz, texto, saida = sys.argv[1], sys.argv[2], sys.argv[3]
asyncio.run(edge_tts.Communicate(texto, voz, rate="+5%").save(saida))
