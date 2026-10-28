# Publicar SetRastrear

Repositório: https://github.com/PedroSetti/SetRastrear

## Arquitetura

O deploy está em **https://setrastrear.onrender.com**, com painel React e API FastAPI no mesmo serviço Docker gratuito e PostgreSQL gratuito na rede privada. O computador pode ficar desligado. O app Android 1.2.0 tem esse endereço público como padrão.

GitHub armazena código e executa CI. Netlify é uma alternativa opcional: hospeda o painel e encaminha `/api` ao FastAPI. Os passos Netlify abaixo só são necessários se optar por separar o painel.

GitHub Pages não executa Uvicorn/PostgreSQL. Netlify estático também não executa esse backend Python contínuo. O projeto permanece FastAPI, com `render.yaml` para o servidor e `netlify.toml` para o painel. Não há dependência de Cloudflare no deploy permanente.

### Alternativa: painel e API juntos no Render

O `Dockerfile` da raiz compila o painel e o serve no mesmo processo FastAPI, via `WEB_DIST=/app/web/dist`. O navegador e o Android usam a mesma origem HTTPS, e a variável automática `RENDER_EXTERNAL_URL` autoriza essa origem exata. Não é necessário Netlify nessa opção. Crie um web service Docker a partir da raiz do repositório, configure `DATABASE_URL`, `APP_ENV=production` e um `JWT_SECRET` aleatório de pelo menos 32 caracteres. As migrations executam antes do Uvicorn, usando a porta `PORT` do provedor.

Plano gratuito só para testes: a API pode suspender por inatividade, e o PostgreSQL gratuito expira após 30 dias. Revise limites de uso e exporte os dados antes da expiração. O Blueprint `render.yaml` agora descreve a mesma arquitetura gratuita. O serviço desta sessão é gerenciado diretamente, não por Blueprint; não aplique em paralelo para evitar recursos duplicados.

## 1. Enviar ao GitHub

Execute dentro da pasta SetRastrear (não na pasta que contém outputs):

```powershell
git init -b main
git add .
git commit -m "Configura SetRastrear para Netlify, Render e Android"
git remote add origin https://github.com/PedroSetti/SetRastrear.git
git push -u origin main
```

Caso `origin` já exista, confira `git remote -v` e use `git remote set-url origin URL` somente para corrigir o destino. Não use force push para substituir histórico remoto. Autentique pelo mecanismo seguro do GitHub; não inclua tokens em URL ou no repositório. `.gitignore` exclui `.env`, banco, certificados privados, keystores e artefatos gerados.

## 2. Criar o site Netlify e reservar sua URL

Em Netlify, importe o repositório GitHub. Base directory: raiz do repositório. O arquivo `netlify.toml` já define:

- Build command: `node scripts/build-netlify.mjs`.
- Publish directory: `web/dist`.
- Node 22 / pnpm 11.25.0.

Anote a URL real do site, por exemplo `https://SEU-SITE.netlify.app`. O primeiro build pode falhar até RMB_API_ORIGIN ser definido; isso é proposital para evitar publicar painel sem backend. Não há wildcard de CORS para previews.

## 3. Backend e banco no Render

No Render, use New → Blueprint e selecione o repositório. O `render.yaml` declara API, PostgreSQL persistente, health check, segredo JWT gerado pelo provedor, build e migrations anteriores ao deploy.

**O Blueprint seleciona planos gratuitos de testes**, com Docker para painel+API e PostgreSQL com expiração de 30 dias. Migrations executam na entrada do container porque pre-deploy separado exige plano compatível. Confira os limites da conta; não é ambiente de produção comercial permanente.

Preencha quando o Blueprint solicitar:

```text
CORS_ORIGINS=https://SEU-SITE.netlify.app
PUBLIC_URL=https://SEU-SITE.netlify.app
```

Use a URL efetiva, sem barra final. Para vários domínios autorizados, separe por vírgulas; não use `*`. `PUBLIC_URL` é usado nas mensagens de recuperação. JWT_SECRET é gerado, DATABASE_URL vem do banco e APP_ENV=production impede SQLite efêmero. URLs `postgres://` e `postgresql://` são convertidas para o driver psycopg.

O comando de início é:

```sh
python -m uvicorn app.main:app --host 0.0.0.0 --port "$PORT" --workers 1 --no-proxy-headers
```

Migrations: `python -m alembic upgrade head`. A limitação por IP considera o proxy como origem; limites por identidade também permanecem ativos. Antes de múltiplas instâncias, use rate limiting centralizado. Não confie em X-Forwarded-For sem restringir proxies confiáveis.

Anote a URL real da API, por exemplo `https://SEU-BACKEND.onrender.com`, e confira `/api/health`. O nome atribuído pode diferir de `setrastrear-api`; use o endereço retornado pelo provedor, não um nome presumido.

## 4. Concluir o deploy no Netlify

Em Environment variables do site:

```text
RMB_API_ORIGIN=https://SEU-BACKEND.onrender.com
```

Esse valor é uma origem pública HTTPS sem caminho, credenciais ou query. O build valida a variável e gera `_redirects` nesta ordem:

```text
/api/*  https://SEU-BACKEND.onrender.com/api/:splat  200!
/*  /index.html  200
```

Publique novamente. No navegador, `/api` permanece na origem do painel, permitindo cookie HttpOnly/Secure/SameSite=Strict e refresh sem cookies entre domínios. A API ainda valida Origin contra CORS_ORIGINS. A regra SPA não deve preceder o proxy, senão chamadas API retornam HTML.

Opcional: `VITE_ANDROID_DOWNLOAD_URL` pode apontar para um APK publicado em um GitHub Release seu. Sem essa variável, o painel hospedado omite o download para evitar link quebrado. APKs de Actions são artefatos do workflow, não são automaticamente GitHub Releases.

Via CLI Netlify instalada e autenticada, a partir da raiz:

```powershell
$env:RMB_API_ORIGIN="https://SEU-BACKEND.onrender.com"
netlify link
netlify deploy --build --prod
```

O `netlify link` deve selecionar o site correto. Para apenas validar build local: `node scripts/build-netlify.mjs`, com pnpm no PATH.

## 5. Android com conexão automática

Não é necessário digitar servidor no aplicativo. O endereço é embutido no APK com BuildConfig.SERVER_URL. Depois do consentimento inicial, o app conecta automaticamente e tenta novamente em falhas de rede, com espera progressiva até 60 segundos. Conectar não ativa localização automaticamente: vínculo, confirmação, permissões e ativação continuam explícitos.

É preferível apontar o Android diretamente para a API para evitar o proxy adicional. Também funciona apontar para o painel Netlify com proxy `/api`. Escolha uma origem estável:

```powershell
$env:RMB_SERVER_URL="https://SEU-BACKEND.onrender.com"
cd android
.\gradlew.bat assembleDebug assembleQa assembleRelease bundleRelease
```

Alternativa: `-PRMB_SERVER_URL=https://SEU-BACKEND.onrender.com` no comando Gradle. A URL padrão versionada em android/gradle.properties é https://setrastrear.onrender.com. A variável de ambiente RMB_SERVER_URL tem prioridade e permite substituí-la. Se ambas forem removidas, release falha e debug mostra erro de configuração. O APK desta sessão já usa Render, sem depender de túnel.

No GitHub, Actions → Compilar Android → Run workflow → informe `server_url`. Ao concluir, baixe `RastrearMB-Android`. Debug e QA são instaláveis; release APK/AAB exigem sua assinatura privada, conforme README. Nenhuma chave privada é enviada ao GitHub.

Ao mudar o servidor em uma nova versão, o app descarta a credencial da origem anterior e exige novo pareamento, para não transmitir um token ao destino diferente. Atualizar o APK com a mesma URL preserva a credencial. Migrar os dispositivos já existentes exige migrar também o banco e preservar a origem; não houve cópia automática dos dados locais para a nuvem.

## 6. Conferir após publicação

1. `/api/health` no painel e na API deve retornar JSON com status ok.
2. Faça cadastro/login e recarregue a página para testar renovação por cookie.
3. Instale APK compilado com a URL permanente. Após consentir, confira conexão automática.
4. Gere código, solicite vínculo no painel e autorize no celular. Os códigos continuam sem prazo automático.
5. Ative compartilhamento e confira mapa, pausa, histórico e remoção.
6. Configure SMTP, rotina de purge, backups e os dados reais do operador nos termos/privacidade.

## Fontes oficiais

- https://docs.netlify.com/manage/routing/redirects/rewrites-proxies/
- https://render.com/docs/blueprint-spec
