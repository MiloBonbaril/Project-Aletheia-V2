import discord, nacl
from discord import opus

print("Pycord:", discord.__version__)
print("PyNaCl:", getattr(nacl, "__version__", "unknown"))
print("Opus loaded?", opus.is_loaded())
if opus.is_loaded():
    print("Opus version:", opus._OpusStruct.get_opus_version())  # ok dans Py-Cord