# Compartilhamento contínuo — Android 1.2.0

O aplicativo não encerra o compartilhamento por atingir 24 horas. Enquanto ativado, executa um foreground service de localização com notificação visível e ação Pausar. Isso permite continuar com a tela bloqueada e a tela principal fechada, sujeito às regras do Android.

## Configuração no aparelho

1. Instale a versão 1.2.0 sobre a anterior, abra o app e mantenha seu vínculo existente no servidor Render.
2. Conceda localização e notificações; toque **ATIVAR COMPARTILHAMENTO**. Sem notificações autorizadas no Android 13+, o app pede habilitá-las antes de começar.
3. Escolha o intervalo. Um minuto ou cinco minutos consome menos bateria que cinco segundos; o intervalo define a frequência de envios, não um prazo para encerrar o serviço.
4. Confira a notificação **Rastrear MB — compartilhamento de localização ativo**. Bloquear a tela não equivale a pausar.
5. Em **PERMISSÕES E BATERIA DO APLICATIVO**, selecione Bateria → Sem restrições, se o fabricante oferecer essa opção. O app abre as configurações, mas não altera permissões ou proteção de bateria sozinho.
6. Opcionalmente habilite **Retomar após reiniciar**. Para essa opção no Android 10+, abra as permissões do app e conceda Localização → Permitir o tempo todo. Ela não é necessária apenas para continuar um serviço já iniciado com o app visível.

A retomada após reinício só ocorre se essa opção foi escolhida, o compartilhamento estava ativo, existe credencial válida e as permissões necessárias estão concedidas. Mostra a mesma notificação. Não há ícone oculto, reinício por alarmes ou tentativa de impedir pausa/desinstalação.

## Recuperação e interrupção

- Em falhas de rede/servidor, mantém a intenção de compartilhar e tenta novamente com espera progressiva de até 60 segundos. Não promete localização em tempo real enquanto não houver conexão e não inventa coordenadas.
- Se o Android recuperar memória encerrando o processo, START_STICKY permite a recriação do serviço quando o sistema autorizar. A decisão de compartilhar e as permissões são verificadas novamente.
- Pausar interrompe a coleta/envio local e a retomada automática. Se o servidor estiver inacessível, a pausa pendente é sincronizada quando o app reconectar.
- Remover vínculo ou receber revogação de credencial encerra o compartilhamento; não tenta contornar a revogação.
- Forçar parada, desligar o aparelho, revogar permissões, esgotar bateria ou bloquear execução nas configurações pode interromper o serviço. Parada forçada não é contornada. Ao detectar encerramento solicitado pelo usuário, o app desativa a intenção de retomar e exige nova ativação.
- Alguns fabricantes aplicam regras adicionais de economia de energia. Se a notificação desaparecer, abra o app e verifique o estado; o painel mostra o horário da última localização.

## Servidor gratuito

O usuário decidiu manter os planos gratuitos em 28/10/2026. Nenhum upgrade pago foi contratado. O banco Render permanece com expiração em **26/11/2026**, e o web service pode suspender por inatividade. Essas limitações do provedor não são removidas por uma alteração no Android. Para eliminá-las nessa infraestrutura, é necessário autorizar planos adequados ou escolher outra infraestrutura com suas próprias condições.

## Verificação necessária no aparelho

Build e análise estática não demonstram operação durante um dia inteiro. Valide por 24 horas em aparelho próprio/autorizado: tela bloqueada, Wi-Fi/dados, perda/retorno de internet, bateria, pausa pela notificação e reinício com e sem autorização opcional. Depois de pausar, confirme que não há novos envios; depois de revogar, a API deve rejeitar a credencial. Nenhum teste contínuo de 24 horas em aparelho físico foi executado nesta entrega.

Referências oficiais:

- https://developer.android.com/reference/android/app/Service#START_STICKY
- https://developer.android.com/develop/background-work/services/fgs/restrictions-bg-start
- https://developer.android.com/about/versions/15/behavior-changes-15#fgs-boot-completed
