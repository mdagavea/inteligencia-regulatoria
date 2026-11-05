# Passagem para o Gemini: e-mail do clipping não saiu em 05/11/2026

Análise feita pelo Claude em 05/11/2026, conferida com o log local e com o histórico do GitHub Actions. O Claude não alterou nenhum arquivo de código. Cabe ao Gemini aplicar.

## 1. O que aconteceu

- A tarefa do Windows `ClippingDiario_DECON_MPOR` rodou às 07:50 (`clipping\executar_automatico.bat`), gerou a edição do dia e publicou `historico/clipping_2026-11-05.html` no GitHub. O log está em `clipping\ultimo_log_agendador.txt`.
- A execução local nunca envia e-mail. O log diz: "E-mail nao enviado em execucao local: o envio ocorre apenas no workflow da nuvem".
- O workflow `clipping_diario_nuvem.yml` não rodou às 07:30 (cron `30 10 * * 1-5`, em UTC, que equivale a 07:30 em Brasília; a configuração está correta). Até as 09:00 não havia execução da nuvem hoje.
- Quando a nuvem rodar, o passo "Verificar se a edição de hoje já foi publicada" vai achar o arquivo do dia, marcar `ja_existe=true` e pular tudo, inclusive o envio do e-mail.

## 2. Causa

Duas coisas somadas:

1. **O agendamento do GitHub é pouco confiável.** Ontem (04/11) a execução agendada veio às 18:06 UTC (15:06 em Brasília), cerca de 7h30 depois do previsto. Em 03/11 não houve execução agendada. Hoje não houve até as 09:00. Não é questão de fuso horário.
2. **A trava anti-duplicidade olha só se o arquivo existe.** Como a tarefa local publica o arquivo antes da nuvem, a trava interpreta "arquivo existe" como "e-mail já enviado". Isso é falso.

Se a nuvem tivesse rodado às 07:30, teria gerado e enviado, e a tarefa local das 07:50 teria pulado a geração. O problema só aparece quando a nuvem atrasa.

## 3. Ação imediata (hoje)

Disparar o workflow manualmente. **Pergunte ao Marcos antes se o envio vai para a lista oficial ou só para um e-mail de teste.**

- Lista oficial: `gh workflow run clipping_diario_nuvem.yml --repo mdagavea/inteligencia-regulatoria -f forcar_reexecucao=true`
- Só teste: acrescentar `-f destinatario_teste=<e-mail do Marcos>`

Sem `destinatario_teste`, o boletim vai para toda a lista `EMAIL_DESTINATARIOS`.

## 4. Correção definitiva (recomendada)

**Opção A, recomendada: a tarefa local passa a disparar a nuvem em vez de gerar a edição.**

- Em `executar_automatico.bat`, trocar a chamada de `gerar_clipping.py --skip-if-exists --no-browser` por `gh workflow run clipping_diario_nuvem.yml --repo mdagavea/inteligencia-regulatoria`.
- Usa a porta 443, que funciona nesta rede. O `gh` já está autenticado nesta máquina.
- O e-mail deixa de depender do atraso do cron do GitHub.
- Se o workflow já tiver rodado no dia, a trava atual evita duplicidade. Isso continua válido neste desenho, porque quem publica o arquivo passa a ser sempre a nuvem.
- Mantém a decisão de 04/11 de deixar o envio só na nuvem.

**Opção B, complementar: tornar a trava mais robusta.**

- Hoje a trava diz "arquivo existe, então já foi enviado". Trocar por um marcador de que o e-mail foi enviado (por exemplo, um arquivo `historico/.enviado_AAAA-MM-DD` criado só depois do passo SMTP, ou um campo no próprio commit).
- Assim, mesmo que alguém publique o arquivo do dia por outro caminho, o e-mail ainda sai.
- O marcador não deve conter e-mails de destinatários (o repositório é público).

**Opção C: apenas desligar a tarefa local.** Elimina a concorrência, mas não resolve o atraso do GitHub. O e-mail continuaria chegando em horário imprevisível.

## 4.1. Como contornar a fila do agendamento do GitHub

Não dá para eliminar a fila do cron, mas dá para contorná-la. Recomendação do Claude: combinar os itens 1 e 2, com a trava melhorada da Opção B.

1. **Disparo manual não passa pela fila do cron.** Em 03/11 o `workflow_dispatch` rodou na hora (7 segundos). Por isso a Opção A (tarefa local chamando `gh workflow run` às 07:50) é o contorno mais confiável: a máquina local vira só o "despertador" e o envio continua na nuvem.
2. **Mudar o minuto do cron.** O GitHub avisa que os agendamentos atrasam mais em horários de pico, especialmente na virada da hora cheia e em minutos redondos (`:00`, `:30`). O cron atual é `30 10 * * 1-5`. Trocar por um minuto "quebrado", por exemplo `17 10 * * 1-5` (07:17 em Brasília) ou `43 9 * * 1-5` (06:43 em Brasília). Não garante pontualidade, mas é gratuito. Lembrar que o cron é em UTC (Brasília = UTC menos 3).
3. **Manter os dois caminhos (cron + disparo da tarefa local) como redundância.** O primeiro que rodar gera e envia, e o outro pula. Isso só funciona sem duplicar e-mail se a trava passar a olhar o marcador de "e-mail enviado" (Opção B), e não só a existência do arquivo.

Observações:
- Em repositório público, o GitHub desativa os agendamentos depois de 60 dias sem atividade no repositório. Não é problema enquanto o clipping publicar todo dia, mas vale saber se o projeto ficar parado.
- Não usar serviço externo de agendamento (como cron-job.org) que exija guardar token de acesso ao GitHub fora desta máquina e dos secrets do repositório.

## 5. O que NÃO fazer

- **Não enviar e-mail direto pela máquina local via SMTP (porta 465).** O log de hoje mostra que a rede do ministério bloqueia a porta 993 (IMAP). É provável que bloqueie a 465 também, e a falha seria silenciosa. Além disso, volta a colocar senha e envio no computador, contra a decisão de 04/11, e pode gerar e-mail duplicado se local e nuvem rodarem quase juntos. Se mesmo assim for tentar, testar antes se a porta 465 abre nesta rede.
- Não incluir `email_dispatch.json` em commit (contém os e-mails, repositório público).
- Não recriar `GEMINI_API_KEY` sem decisão expressa.
- Manter o aviso de projeto piloto em qualquer layout novo.

## 6. Ao concluir

- Registrar a mudança em `clipping\MEMORIA_PROJETO.md` e subir com `python3.12 ..\sincronizar_nuvem.py push "..."`.
- Conferir no dia seguinte (06/11, sexta) se o e-mail chegou até as 08:00.
