# Validação — 27/10/2026

## Executado com sucesso

- Backend: 18 testes pytest aprovados (cadastro, validação de senha/termos, login, logout, refresh/replay, pareamento, recusa/autorização, tentativa inválida, código sem expiração por dez anos simulados e substituição de código, pausa, envio, histórico, exclusão, isolamento de contas, revogação, JWT expirado, bloqueio de papel admin, CSRF e recuperação).
- Frontend: TypeScript sem erros e build Vite concluído. Tela de login inspecionada no navegador desktop. Sem dados simulados no painel.
- Android: assembleDebug, assembleQa, assembleRelease e bundleRelease concluídos. lintVitalRelease aprovado. APK debug e QA assinados com chave de desenvolvimento local; release APK/AAB sem assinatura de produção.
- Migration inicial executada em SQLite; esquema inicial congelado na revisão 001.
- HTTPS local: certificado/CA de desenvolvimento gerados e requisições verificadas com CA explícita, sem desativar TLS.
- Cloudflare: túnel criado; painel retornou HTTP 200, `/api/health` retornou `{"status":"ok"}` via HTTPS público. Login exibido no navegador nesse endereço.

## Não executado neste ambiente

- Instalação e teste de GPS em aparelho físico/emulador; testes de permissão, pausa e comportamento de fabricantes precisam ser feitos no aparelho.
- Docker/PostgreSQL (Docker não disponível), SMTP real e assinatura com keystore privada de produção.
- Pentest, carga, varredura integral de dependências e inspeção visual de todas as telas/breakpoints.

O build web informa bundle acima de 500 kB por incluir leitor QR; é uma oportunidade de divisão de código, sem impedir a compilação. O pytest emite aviso de depreciação no TestClient/AnyIO, sem falhas.

## Arquivos gerados

`APKs/RastrearMB-debug.apk`, `RastrearMB-teste.apk`, `RastrearMB-release-unsigned.apk` e `RastrearMB-release-unsigned.aab`. Os arquivos release exigem assinatura própria antes de instalação/publicação. Não há keystore privada no pacote fonte.

## Atualização: pareamento por prazo indeterminado

Migration 002 aplicada ao SQLite ativo, removendo a expiração dos códigos pendentes. Código e QR continuam válidos até uso, recusa ou substituição por outro. Sessões e recuperação de senha mantêm suas expirações. APKs recompilados e download público atualizado.
