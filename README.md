# SetRastrear • Rastrear MB

**Hospedagem permanente e conexão automática do Android:** siga [docs/DEPLOY.md](docs/DEPLOY.md). Versão 1.1.0. Os trechos de teste local abaixo são opcionais.

Plataforma executável de localização consentida: API FastAPI, painel React/TypeScript/Leaflet e Android Kotlin/Compose. O aparelho confirma cada vínculo, mostra uma notificação persistente durante o compartilhamento e pode interrompê-lo. Não há rastreamento oculto.

## Teste pela Cloudflare

Endereço da sessão de teste de 27/10/2026: **https://nokia-loop-placement-lover.trycloudflare.com**.

O APK de teste desta sessão conecta automaticamente a esse endereço depois do consentimento. O endereço é temporário; para hospedagem permanente, compile o APK com RMB_SERVER_URL conforme docs/DEPLOY.md. Não é uma VM hospedada na Cloudflare: o túnel fornece HTTPS público para a API e painel executados no computador. O computador, backend, origem HTTP e `cloudflared` precisam continuar ativos. Não exige certificado de desenvolvimento no celular.

Crie sua conta pelo painel; não existe senha administrativa padrão. O banco começa sem dispositivos e sem localizações de demonstração. Para obter um novo endereço, veja `docs/CLOUDFLARE.md`.

## 1. Requisitos

- Python 3.12; Node.js 22 com npm; JDK 17; Android SDK 35 e Build Tools; Android Studio opcional.
- Android 8/API 26 ou superior para instalar; alvo Android 15/API 35.
- Docker Desktop + Compose para a opção PostgreSQL em containers.
- `cloudflared` oficial para testes públicos via Cloudflare.
- Dispositivo com localização habilitada e conexão de rede.

## 2. Instalação

No PowerShell, dentro da pasta SetRastrear:

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r backend/requirements.txt
python scripts/init-env.py
cd web
npm install
npm run build
cd ..
```

Se `.env` já existir, o inicializador não o sobrescreve. O arquivo não integra o ZIP e deve ser criado em cada instalação. Segredos são gerados por CSPRNG. Nunca publique `.env`, certificados privados, banco ou keystore.

## 3. Banco e migrations

Para SQLite, mantenha `DATABASE_URL=sqlite:///./rastrear.db`. O arquivo é relativo ao diretório `backend`.

```powershell
.\scripts\dev.ps1 backend
```

O script carrega `.env`, executa `python -m alembic upgrade head` e inicia Uvicorn. PostgreSQL usa `postgresql+psycopg://usuario:senha@host/banco`. O Compose configura essa URL automaticamente. Credenciais geradas usam hexadecimal para evitar caracteres reservados na URL.

As migrations estão em `backend/migrations`. A revisão inicial cria o esquema ORM; futuras alterações precisam de revisões novas, preservando a revisão inicial. A revisão inicial contém uma cópia congelada do esquema.

## 4. Backend

Variáveis em `.env.example`: `JWT_SECRET`, `DATABASE_URL`, `CORS_ORIGINS`, `PUBLIC_URL` e SMTP. JWT_SECRET precisa ter no mínimo 32 caracteres. `CORS_ORIGINS` deve listar origens exatas separadas por vírgulas, sem barra final; não use `*`.

O backend escuta apenas em `127.0.0.1:8000` no fluxo manual. Use o proxy HTTPS ou Cloudflare para acesso externo. Comando equivalente, após carregar variáveis:

```powershell
cd backend
python -m alembic upgrade head
python -m uvicorn app.main:app --host 127.0.0.1 --port 8000
```

O envio de recuperação exige SMTP com STARTTLS. Configure SMTP_HOST/PORT/USER/PASSWORD/FROM e PUBLIC_URL. A resposta não revela se o e-mail existe. Não há envio de e-mail sem provedor configurado. O token dura 15 minutos e só pode ser usado uma vez; redefinir senha revoga sessões.

## 5. Frontend

React + TypeScript, tema escuro/claro, layout responsivo, Leaflet/OpenStreetMap. O frontend consulta a mesma origem em `/api`; não há URL privada ou token fixo no bundle. O painel começa vazio e mostra apenas dispositivos realmente vinculados.

```powershell
cd web
npm install
npm run build
```

Para editar com hot reload: `npm run dev`, adicionando explicitamente `http://127.0.0.1:5173` ao CORS local. O Vite faz proxy de `/api`; esse modo serve apenas para desenvolvimento e não substitui o acesso HTTPS público.

## 6. HTTPS local (opção secundária)

```powershell
python scripts/create-dev-cert.py 192.168.1.20
python scripts/local-https.py
```

Substitua o IP pelo IPv4 do computador (`ipconfig`). O script cria uma CA exclusivamente de desenvolvimento e certificado de servidor com SAN para localhost, emulador e IP informado. Não sobrescreve uma CA existente. As chaves ficam em `certs-dev`, ignoradas pelo Git e excluídas do ZIP. O certificado do servidor expira em 90 dias.

Instale somente `certs-dev/ca.crt` na loja de CAs confiáveis do Windows e, para debug local, nas configurações de certificados do Android. Faça isso apenas no ambiente de testes sob seu controle. Não distribua `ca-key.pem` ou `server-key.pem`. O aplicativo valida TLS normalmente; debug/QA aceita CAs de usuário, release aceita apenas CAs do sistema.

## 7. Iniciar o ambiente

Preferência para acesso público: `docs/CLOUDFLARE.md`.

Opção Docker local:

```powershell
python scripts/init-env.py
python scripts/create-dev-cert.py 192.168.1.20
docker compose up --build -d
docker compose logs -f backend
```

PostgreSQL tem volume persistente e health check. Apenas a porta HTTPS 8443 é publicada; banco e backend permanecem na rede interna. Nenhum secret real está no Compose. Para parar preservando o banco: `docker compose down`.

## 8. Acessar pelo Windows

Abra o endereço público Cloudflare, cadastre nome/e-mail/senha de pelo menos 12 caracteres e aceite os termos. Faça login. Em Dispositivos → Adicionar dispositivo, informe o código de pareamento mostrado no Android. Aguarde a confirmação no aparelho.

Se optar por ambiente local e confiar na CA, use `https://localhost:8443`. Swagger fica em `/docs`, OpenAPI em `/openapi.json`. A porta 443 padrão também pode ser mapeada no Compose se estiver livre.

## 9. Testar pelo celular

1. Instale o APK debug ou QA em um aparelho próprio/autorizado.
2. Abra Rastrear MB; o servidor já está configurado na compilação.
3. Leia a explicação e confirme a configuração.
4. Gere o código em Vincular dispositivo. Validade indeterminada, até uso, recusa ou geração de outro código. O QR contém somente o código de pareamento.
5. No painel, solicite o vínculo digitando o código ou escaneando o QR com a câmera do navegador.
6. Mantenha o app aberto. Ele consulta pedidos a cada cinco segundos e mostra o nome de quem solicitou. Selecione AUTORIZAR ou RECUSAR.
7. Escolha o intervalo, toque ATIVAR COMPARTILHAMENTO e conceda localização e notificações quando solicitadas.
8. Vá ao mapa do painel. Sem fix de GPS, nenhuma coordenada é inventada.
9. Use PAUSAR, a ação Pausar na notificação ou remova o vínculo para interromper.

Sem Cloudflare: ambos na mesma rede, URL `https://IP_DO_PC:8443`, CA confiável no debug e IP no SAN. `localhost` no Android representa o próprio celular; `10.0.2.2` é o host do emulador. Configure CORS para a URL do painel e permita a porta necessária no firewall da rede privada. Não é necessário abrir portas no roteador para Cloudflare Tunnel.

O serviço de localização é iniciado por ação do usuário com o app visível. Não reinicia escondido no boot nem após force-stop. Em segundo plano, continua como foreground service com notificação. Precisão e frequência dependem do GPS, permissões, economia de energia e regras do fabricante; “tempo real” significa melhor esforço com mínimo de cinco segundos, sem garantia rígida. Polling de solicitação remota só funciona com compartilhamento ativo; não ativa o rastreamento remotamente.

## 10. Gerar APK debug e QA

```powershell
cd android
.\gradlew.bat assembleDebug assembleQa
```

- `app/build/outputs/apk/debug/app-debug.apk` → RastrearMB-debug.apk
- `app/build/outputs/apk/qa/app-qa.apk` → RastrearMB-teste.apk (applicationId com `.qa`, pode coexistir)

O Gradle Wrapper 8.9 está incluído. Primeiro build exige internet e SDK. Defina RMB_SERVER_URL antes de compilar (veja docs/DEPLOY.md). Se o SDK não for localizado, defina ANDROID_HOME ou crie `local.properties` com `sdk.dir=C:/Users/SEU_USUARIO/AppData/Local/Android/Sdk`.

Instalação via USB com depuração autorizada: `adb install -r RastrearMB-debug.apk`. Alternativa: copie o APK, abra no gerenciador de arquivos e autorize temporariamente a instalação pela fonte escolhida. A instalação e as permissões precisam ser confirmadas pelo proprietário.

## 11. Release, AAB e assinatura

Os arquivos release entregues estão **sem assinatura de produção**. O APK não é instalável até ser assinado. Não foi criada nem incluída uma keystore privada de produção.

Crie sua chave fora do repositório (o keytool solicita as senhas interativamente):

```powershell
keytool -genkeypair -v -keystore C:\CAMINHO_SEGURO\rastrear-release.jks -alias rastrear -keyalg RSA -keysize 3072 -validity 10000
```

Configure no ambiente seguro de build `RMB_KEYSTORE` (caminho absoluto), `RMB_STORE_PASSWORD`, `RMB_KEY_ALIAS` e `RMB_KEY_PASSWORD`. Evite gravar senhas no histórico; prefira segredos de CI ou entrada protegida. O Gradle detecta essas variáveis.

```powershell
cd android
.\gradlew.bat assembleRelease bundleRelease
```

Saídas: `app/build/outputs/apk/release/app-release.apk` (quando há configuração de assinatura) e `app/build/outputs/bundle/release/app-release.aab`. Sem variáveis, o APK sai como `app-release-unsigned.apk` e o AAB também fica sem assinatura de produção. Verifique com `apksigner verify --verbose caminho.apk` e `jarsigner -verify caminho.aab`. Para publicação real, use URL estável, certificados públicos, Play App Signing e declarações de localização/foreground service aplicáveis. Guarde chave e senhas em armazenamento seguro com backup separado.

## 12. Estrutura do banco

`users` → `devices` → `device_locations`. `device_pairings` guarda hash do código de pareamento, expiração, pretendente e nome. `sessions` controla expiração/revogação; `refresh_tokens` guarda hashes rotativos; `security_logs` registra auditoria; `notifications` registra avisos; `password_resets` guarda hashes de recuperação.

O identificador da instalação é UUID aleatório; o segredo tem 48 bytes aleatórios antes da codificação. Não se usa IMEI, MAC ou telefone. O servidor guarda apenas o hash do segredo do aparelho; o app o cifra com AES-GCM usando Android Keystore. Remover vínculo apaga o registro da instalação e todas as posições: a credencial deixa de ser aceita imediatamente. Para vincular novamente, faça nova conexão no app.

## 13. API e autorização

Swagger em `/docs`, esquema em `/openapi.json`. Conta/painel usa Bearer JWT de dez minutos; aparelho usa Bearer com segredo exclusivo e revogável, sem acesso às APIs da conta. Endpoints de confirmação exigem a credencial do próprio dispositivo. Toda consulta/remoção de posição valida a propriedade no servidor.

Principais rotas: `/api/auth/{register,login,refresh,logout,forgot,reset}`, `/api/device/{install,pairing,status,settings,location,link}`, `/api/devices`, `/api/devices/pair`, `/api/devices/pair/confirm`, `/api/devices/{id}/{location,history,request}`, `/api/account`, `/api/sessions`, `/api/notifications`, `/api/admin/overview`.

Login retorna access_token; refresh é cookie HttpOnly, Secure e SameSite=Strict com rotação. O painel mantém JWT apenas em memória. Cookies não autorizam ações da conta, exceto renovação; origem é validada nas mutações, além do SameSite, para proteção CSRF. Encerrar/revogar sessão invalida também JWTs ainda não expirados.

## 14. Solução de problemas

| Problema | Verificação |
| --- | --- |
| Link Cloudflare expirou | Reinicie túnel, atualize CORS_ORIGINS/PUBLIC_URL e o campo de URL do APK. |
| HTTP 403 no login | A origem HTTPS precisa estar exatamente em CORS_ORIGINS; reinicie o backend. |
| Código inválido | Gere outro; não expira, mas só aceita um pretendente e é invalidado ao gerar outro. |
| Nenhum pedido no celular | Abra o app e confira URL, conectividade e token da instalação. |
| Mapa vazio | Autorize vínculo, ative compartilhamento e aguarde fix de localização. |
| Falha TLS local | CA confiável + SAN com IP correto; não desative validação TLS. |
| Notificação ausente | Confira permissão de notificações no Android 13+; autorize nas configurações. |
| Erro de banco | Rode migrations e confirme URL/credenciais; SQLite e PostgreSQL usam URLs distintas. |
| Senha não chega por e-mail | Configure SMTP com STARTTLS e PUBLIC_URL; consulte erros operacionais. |
| Gradle não compila | JDK 17, SDK 35, internet e caminho do SDK; abra `android` no Android Studio. |
| `npm` ausente | Instale Node.js oficial com npm; não é exigido para usar os APKs já gerados. |

## Administração e retenção

Cadastre a conta normalmente; um operador com acesso ao servidor concede o papel:

```powershell
cd backend
python -m app.manage admin administrador@exemplo.com
```

Recarregue o painel: Administração aparece somente para administradores. A API administra usuários, bloqueios, contagens, sessões e auditoria sem retornar coordenadas. Permissões administrativas não substituem propriedade de dispositivos. Bloquear conta revoga sessões e impede uploads. Logs de erro detalhados são operacionais no Uvicorn; eventos genéricos `server_error` entram na auditoria sem payloads ou credenciais.

Retenção padrão de 30 dias, ajustável de 1 a 365 em Configurações. Consultas filtram dados vencidos, novos uploads limpam dados antigos e a mudança de retenção aplica exclusão imediata. Agende diariamente `python -m app.manage purge` para excluir fisicamente dados de aparelhos inativos. Exclusão de histórico e conta é permanente no banco ativo; defina ciclo de expiração de backups separadamente.

## Testes e estado da entrega

```powershell
cd backend
python -m pytest -q
```

Veja `docs/VALIDACAO.md` para resultados e limites da validação. Esta entrega permite testar o fluxo integrado; não representa certificação de segurança ou homologação em todos os fabricantes Android. O limitador atual é por processo: mantenha um worker no teste. Para múltiplas réplicas, use armazenamento compartilhado e rate limiting também na borda. Termos/privacidade fornecidos precisam dos dados reais do operador antes de disponibilização comercial.
