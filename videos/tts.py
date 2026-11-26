"""
Gera a narração de uma cena em MP3.
Uso: python tts.py <voz> <texto> <arquivo_saida.mp3>

Dois motores:
- ElevenLabs (voz mais humana, pago): usado quando a variável ELEVENLABS_API_KEY existe
  e <voz> é o ID de uma voz do ElevenLabs (ex.: VOZ_PT=21m00Tcm4TlvDq8ikWAM).
- Edge TTS (grátis): usado quando <voz> é um nome da Microsoft, que termina em "Neural"
  (ex.: pt-BR-ThalitaMultilingualNeural).
"""

import asyncio
import json
import os
import sys
import urllib.error
import urllib.request

voz, texto, saida = sys.argv[1], sys.argv[2], sys.argv[3]
chave = os.environ.get("ELEVENLABS_API_KEY", "").strip()


def elevenlabs():
    url = f"https://api.elevenlabs.io/v1/text-to-speech/{voz}?output_format=mp3_44100_128"
    corpo = {
        "text": texto,
        # Fala português e inglês com a mesma voz
        "model_id": os.environ.get("ELEVENLABS_MODELO", "eleven_multilingual_v2"),
        "voice_settings": {
            "stability": 0.45,         # menor = mais expressivo; maior = mais constante
            "similarity_boost": 0.8,
            "style": 0.2,
            "use_speaker_boost": True,
        },
    }
    pedido = urllib.request.Request(
        url, data=json.dumps(corpo).encode("utf-8"), method="POST",
        headers={"xi-api-key": chave, "Content-Type": "application/json", "Accept": "audio/mpeg"},
    )
    try:
        with urllib.request.urlopen(pedido, timeout=120) as resposta, open(saida, "wb") as arq:
            arq.write(resposta.read())
    except urllib.error.HTTPError as erro:
        detalhe = erro.read().decode("utf-8", "replace")[:300]
        sys.exit(f"ElevenLabs recusou o pedido ({erro.code}): {detalhe}")


def edge():
    import certifi
    # Certificado extra só existe no ambiente Linux onde os vídeos foram gravados pela primeira vez
    ca = "/root/.ccr/ca-bundle.crt"
    if os.path.exists(ca):
        certifi.where = lambda: ca
    import edge_tts
    asyncio.run(edge_tts.Communicate(texto, voz, rate=os.environ.get("TTS_RATE", "+5%")).save(saida))


if voz.endswith("Neural"):
    edge()
elif chave:
    elevenlabs()
else:
    sys.exit(f'"{voz}" parece uma voz do ElevenLabs, mas a variável ELEVENLABS_API_KEY não está definida.')
