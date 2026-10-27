# Testes públicos com Cloudflare

URL desta sessão: https://nokia-loop-placement-lover.trycloudflare.com

Cloudflare Tunnel foi escolhido para manter FastAPI/PostgreSQL/Android nativo, fornecendo HTTPS público sem alterar a stack. O código Python não foi convertido para Workers; o banco continua sob seu controle. Quick Tunnel é temporário e não exige uma conta Cloudflare.

## Recriar o ambiente

1. Instale Python/Node e dependências conforme README, crie `.env` com `python scripts/init-env.py` e compile o painel.
2. Terminal 1: `.\scripts\dev.ps1 backend`.
3. Terminal 2: `python scripts/local-https.py --http`. A origem fica apenas em `127.0.0.1:8080`.
4. Instale `cloudflared` pela distribuição oficial da Cloudflare. Terminal 3: `cloudflared tunnel --url http://127.0.0.1:8080 --no-autoupdate`.
5. Copie a URL `https://....trycloudflare.com` retornada. Em `.env`, configure `PUBLIC_URL` com essa URL e `CORS_ORIGINS` com a mesma origem exata. Preserve outras origens de desenvolvimento somente se necessárias.
6. Reinicie somente o backend do terminal 1 para carregar as novas variáveis; preserve o túnel.
7. Abra a URL no Windows/celular. No aplicativo, preencha o mesmo endereço em Servidor HTTPS e conecte.

Não exponha o Vite, o banco, Swagger com dados sensíveis, pasta do projeto ou `.env` como origem. O proxy entrega somente `web/dist` e encaminha API. O HTTP interno é restrito ao loopback; externamente o transporte é HTTPS público válido. A Cloudflare termina TLS na borda e, como provedora de proxy, processa as requisições. Use somente dados de testes consentidos neste ambiente.

O endereço para de funcionar quando o túnel ou o computador é desligado. Não é uma hospedagem independente, VM ou serviço com garantia de disponibilidade.

## Hospedagem permanente

Para URL estável, use domínio e túnel nomeado na sua conta Cloudflare, apontando para a origem protegida. O token deve ser secret de ambiente/secret manager; não inclua no código. Uma VM/VPS ou servidor sempre ligado deverá executar FastAPI e PostgreSQL. Cloudflare Workers não executa este backend Uvicorn como uma VM tradicional. Configure origem exata, URL pública e SMTP, backups, monitoração, limpeza periódica e rate limiting compartilhado antes de ampliar o uso.

Documentação oficial: https://developers.cloudflare.com/tunnel/get-started/quick-tunnels/

Alternativa automática no Windows, após instalar dependências e compilar o painel: execute scripts/start-cloudflare.ps1. O script inicia os processos ocultos, obtém a URL, atualiza .env, aplica migrations e inicia a API. Não execute com as portas 8000/8080 já ocupadas. Opcionalmente use -Cloudflared e -Python com caminhos absolutos.
