# Guia do Sistema de Clipping Regulatório & Financeiro

Este sistema coleta, cura com IA e gera um dashboard executivo diário em HTML com notícias e atos regulatórios das suas 4 verticais de interesse:
1. **Infraestrutura & Outorgas** (PPPs, leilões, ANTT, ANAC, ANTAQ, rodovias, ferrovias, portos).
2. **Seguros de Grandes Riscos** (Seguro-garantia, performance bonds, regulação SUSEP, resseguro).
3. **Mercado de Carbono & Transição Climática** (SBCE, créditos de carbono, Fundo Clima).
4. **Instrumentos de Dívida & Mercado de Capitais** (Debêntures 12.431 e 14.801, CVM, ANBIMA).

---

## Passo 1: Obter a Chave Gratuita da API do Gemini (1 minuto)

O sistema utiliza a API do Gemini no plano gratuito oficial do Google (com limite de até 1.500 requisições/dia, você só usará 1 por dia = R$ 0,00):

1. Acesse: [https://aistudio.google.com/app/apikey](https://aistudio.google.com/app/apikey)
2. Faça login com sua conta Google (se já não estiver conectado).
3. Clique no botão azul **"Create API key"** (Criar chave de API).
4. Copie o código gerado.

---

## Passo 2: Configurar sua Chave

Abra o arquivo [.env](file:///C:/Users/marcos.castilho/testes-gemini/clipping/.env) nesta pasta e cole a sua chave após o sinal de igual:

```env
GEMINI_API_KEY=AIzaSy...sua_chave_aqui...
```
*(Salve o arquivo após colar).*

---

## Passo 3: Executar

Basta dar dois cliques no arquivo:
👉 [executar_clipping.bat](file:///C:/Users/marcos.castilho/testes-gemini/clipping/executar_clipping.bat)

O programa irá:
1. Buscar matérias recentes nas 4 verticais;
2. Enviar para o Gemini eliminar ruídos, organizar nas subseções e resumir cada fato;
3. Gerar o arquivo [clipping_atual.html](file:///C:/Users/marcos.castilho/testes-gemini/clipping/clipping_atual.html) e abrir automaticamente no seu navegador.

---

## Passo 4: Automação Total (Rodar Diariamente sem Clicar em Nada)

Para que o Windows execute esse script sozinho toda manhã:
1. Pressione a tecla **Windows** e digite `Agendador de Tarefas` (Task Scheduler).
2. No menu da direita, clique em **Criar Tarefa Básica**.
3. Nome: `Clipping Diário`.
4. Disparador: **Diariamente**, defina o horário (ex: `07:30:00`).
5. Ação: **Iniciar um programa**.
6. Programa/script: Selecione `C:\Users\marcos.castilho\testes-gemini\clipping\executar_clipping.bat`.
7. Conclua. A partir daí, toda manhã o clipping será gerado sozinho!
