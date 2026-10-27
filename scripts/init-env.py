from pathlib import Path
import secrets
root=Path(__file__).resolve().parents[1]
target=root/'.env'
if target.exists():raise SystemExit('.env já existe; não sobrescrito')
text=(root/'.env.example').read_text().replace('replace-with-a-random-secret-at-least-32-characters',secrets.token_hex(48)).replace('replace-with-a-separate-random-password',secrets.token_hex(24))
target.write_text(text);print('.env criado com segredos aleatórios. Não versionar.')
