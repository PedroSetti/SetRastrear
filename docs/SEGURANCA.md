# Modelo de segurança

- Senhas Argon2, JWT HMAC com segredo externo, access token de dez minutos, sessão revogável, refresh em cookie HttpOnly Secure SameSite Strict com rotação e detecção de replay.
- ORM SQLAlchemy e validação Pydantic no servidor. Frontend usa escape React; textos de popup são inseridos com textContent.
- Código de pareamento CSPRNG com 60 bits aleatórios, hash no banco, sem expiração automática e confirmação com credencial do aparelho. QR não inclui identidade, JWT ou senha.
- Tokens distintos entre usuário e dispositivo; admin não possui bypass de propriedade.
- Segredo mobile cifrado AES-GCM com Android Keystore e backups do app desativados. Revogação do vínculo elimina a credencial no servidor.
- CORS explícito, checagem de origem nas mutações, SameSite e ausência de ações por GET; TLS obrigatório no app.
- Limitadores de cadastro/login/recuperação/pareamento/upload. Configuração atual é por processo; o proxy de desenvolvimento agrega IPs, então o limite por IP é conservador e compartilhado entre visitantes. O limite por identidade também se aplica. Para escala, configure proxy confiável e limitação centralizada, sem confiar em cabeçalhos enviados pelo cliente.
- Logs não devem incluir credenciais, códigos de pareamento ou payloads de posição; o proxy de testes não registra queries.

## Limitações operacionais explícitas

O ambiente publicado usa um worker e PostgreSQL no Render gratuito. SQLite e túnel temporário são opções de desenvolvimento. Docker foi executado pelo Render; não foi executado localmente. Não foi realizado pentest, teste de carga, teste instrumental Android ou teste físico de 24 horas. SMTP requer configuração real; não foi enviado e-mail. Sem push: confirmação aparece por polling enquanto o app está aberto, e pedidos remotos são consultados enquanto o foreground service está ativo. A partir da versão 1.2.0, a retomada após reiniciar é opcional, exige permissão apropriada e mostra notificação. Parada forçada não é contornada.

A exclusão do banco ativo não apaga cópias de backup já existentes. Defina retenção de logs, backups, criptografia de disco, restauração e procedimento de incidentes para a infraestrutura escolhida. A retenção de localizações inativas exige executar a rotina purge periodicamente.

Antes de produção, revise dependências, configure servidor de origem gerenciado, armazenamento compartilhado para rate limiting, TLS público, keystore própria, SMTP e dados reais do controlador nos textos legais.

Fontes oficiais utilizadas: https://fastapi.tiangolo.com/tutorial/security/oauth2-jwt/ e https://developer.android.com/develop/background-work/services/fgs/restrictions-bg-start
