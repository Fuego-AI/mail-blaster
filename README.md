╔══════════════════════════════════════════════════════════════════╗
║              📧  MAIL BLASTER — GUIA DE CONFIGURAÇÃO            ║
╚══════════════════════════════════════════════════════════════════╝

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 REQUISITOS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

• Python 3.8 ou superior
• Instalador de pacotes pip

━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 PASSO 1 — INSTALAR DEPENDÊNCIAS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Abra o terminal/prompt na pasta do aplicativo e execute:

    pip install -r requirements.txt


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 PASSO 2 — CONFIGURAR ACESSO AO GOOGLE SHEETS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

O app usa OAuth2 para acessar o Google Sheets com a sua própria
conta do Google (a mesma que tem acesso à planilha).

2.1) Acesse: https://console.cloud.google.com/

2.2) Crie um projeto novo (ou use um existente)

2.3) Ative as APIs:
     • Google Sheets API
     • Google Drive API

2.4) Vá em "Credenciais" → "Criar credenciais" → "ID do cliente OAuth"
     • Tipo de aplicativo: "App para computador"
     • Nome: Mail Blaster (ou qualquer nome)

2.5) Baixe o JSON gerado e renomeie para:
         client_secret.json

2.6) Coloque o arquivo client_secret.json na mesma pasta que app.py

2.7) Na primeira execução, um navegador será aberto pedindo que você
     autorize o acesso com sua conta Google. Após autorizar, um
     arquivo token.pickle será criado e não precisará autorizar de novo.


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 PASSO 3 — FORMATO DA PLANILHA GOOGLE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

A planilha (primeira aba) deve ter EXATAMENTE estas colunas na
linha 1:

    | A       | B            | C       |
    |---------|--------------|---------|
    | Nome    | E-mail       | Status  |
    | João    | joao@ex.com  |         |
    | Maria   | maria@ex.com |         |

• A coluna Status será preenchida automaticamente com:
  - "Enviado"  → e-mail enviado com sucesso
  - "Falhou"   → erro ao enviar
  - (vazio)    → pendente (ainda não processado)

• O app pula automaticamente linhas já marcadas como "Enviado",
  permitindo retomar envios interrompidos sem duplicar.

• Na mensagem, você pode usar {nome} e {email} para personalizar:
  Ex.: "Olá {nome}, seu cadastro com e-mail {email} foi confirmado."


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 PASSO 4 — CONFIGURAR E-MAIL REMETENTE
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

O servidor SMTP é detectado automaticamente pelo domínio do e-mail.

● GMAIL:
  - Ative a verificação em 2 etapas na sua conta Google
  - Gere uma "Senha de App" em:
    https://myaccount.google.com/apppasswords
  - Use essa senha no campo Senha (não a senha normal da conta)

● OUTLOOK / HOTMAIL:
  - Use sua senha normal ou senha de app se tiver 2FA ativado

● OUTROS:
  - Se seu servidor não for detectado, o app tentará smtp.<domínio>:587


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 EXECUTAR O APLICATIVO
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    python app.py


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 ESTRUTURA DE ARQUIVOS
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

    📁 pasta_do_app/
    ├── app.py              ← Aplicativo principal
    ├── requirements.txt    ← Dependências Python
    ├── client_secret.json  ← ⚠ Você precisa criar (Passo 2)
    ├── token.pickle        ← Criado automaticamente após login
    └── README.txt          ← Este arquivo


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 DICAS DE USO
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

• Você pode pausar e retomar o envio a qualquer momento
• Se parar no meio, basta reiniciar — linhas já "Enviado" são puladas
• O lote e o intervalo podem ser ajustados antes de iniciar
• Para campanhas grandes, recomenda-se lotes de 10 a cada 5-10 segundos
• O log mostra cada envio em tempo real com horário


━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
 SUPORTE A PROVEDORES
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

Gmail, Yahoo, Outlook, Hotmail, Live, iCloud,
UOL, BOL, Terra, IG — e qualquer provedor com SMTP padrão.
