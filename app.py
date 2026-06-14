import tkinter as tk
from tkinter import ttk, filedialog, messagebox, scrolledtext
import threading
import smtplib
import time
import os
import re
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from email.mime.base import MIMEBase
from email import encoders
import gspread
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
from google_auth_oauthlib.flow import InstalledAppFlow
import pickle
import webbrowser
from datetime import datetime
import json
import mimetypes

# ─────────────────────────────────────────────
# Google Sheets Auth (via OAuth do usuário logado)
# ─────────────────────────────────────────────
SCOPES_SHEETS = [
    'https://www.googleapis.com/auth/spreadsheets',
    'https://www.googleapis.com/auth/drive.readonly'
]

def get_google_creds(token_path='token.pickle'):
    creds = None
    if os.path.exists(token_path):
        with open(token_path, 'rb') as f:
            creds = pickle.load(f)
    if not creds or not creds.valid:
        if creds and creds.expired and creds.refresh_token:
            creds.refresh(Request())
        else:
            # Usa client_secret.json se disponível, senão fallback manual
            if not os.path.exists('client_secret.json'):
                raise FileNotFoundError(
                    "Arquivo 'client_secret.json' não encontrado.\n"
                    "Consulte o README.txt para configurar o acesso ao Google Sheets."
                )
            flow = InstalledAppFlow.from_client_secrets_file('client_secret.json', SCOPES_SHEETS)
            creds = flow.run_local_server(port=0)
        with open(token_path, 'wb') as f:
            pickle.dump(creds, f)
    return creds


def extract_sheet_id(url):
    match = re.search(r'/spreadsheets/d/([a-zA-Z0-9-_]+)', url)
    if match:
        return match.group(1)
    return None


def load_emails_from_sheet(sheet_url, creds):
    sheet_id = extract_sheet_id(sheet_url)
    if not sheet_id:
        raise ValueError("URL da planilha inválida.")
    gc = gspread.authorize(creds)
    sh = gc.open_by_key(sheet_id)
    ws = sh.sheet1
    records = ws.get_all_records()
    return ws, records, sh


def update_status(ws, row_index, status):
    # Assume col 1=nome, col 2=email, col 3=status (linha 1 = cabeçalho)
    ws.update_cell(row_index + 2, 3, status)


# ─────────────────────────────────────────────
# Email sending
# ─────────────────────────────────────────────

def detect_smtp(email):
    domain = email.split('@')[-1].lower()
    configs = {
        'gmail.com':     ('smtp.gmail.com', 587),
        'yahoo.com':     ('smtp.mail.yahoo.com', 587),
        'outlook.com':   ('smtp-mail.outlook.com', 587),
        'hotmail.com':   ('smtp-mail.outlook.com', 587),
        'live.com':      ('smtp-mail.outlook.com', 587),
        'icloud.com':    ('smtp.mail.me.com', 587),
        'uol.com.br':    ('smtp.uol.com.br', 587),
        'bol.com.br':    ('smtp.bol.com.br', 587),
        'terra.com.br':  ('smtp.terra.com.br', 587),
        'ig.com.br':     ('smtp.ig.com.br', 587),
    }
    return configs.get(domain, ('smtp.' + domain, 587))


def send_email(smtp_server, smtp_port, sender_email, password, recipient_email,
               personalized_subject, personalized_body, attachment_path=None):
    msg = MIMEMultipart()
    msg['From'] = sender_email
    msg['To'] = recipient_email
    msg['Subject'] = personalized_subject
    msg.attach(MIMEText(personalized_body, 'plain', 'utf-8'))
    
    
    if attachment_path and os.path.exists(attachment_path):
        
        filename = os.path.basename(attachment_path)
        
        mime_type, _ = mimetypes.guess_type(attachment_path)
        
        if mime_type is None:
            mime_type = 'application/octet-stream'
        
        mime_main, mime_sub = mime_type.split('/', 1)
        
        with open(attachment_path, 'rb') as f:
            part = MIMEBase(mime_main, mime_sub)
            part.set_payload(f.read())
            
        encoders.encode_base64(part)
        
        part.add_header('Content-Disposition', 'attachment', filename=filename)
        
        msg.attach(part)
    
    print("CONECTANDO SMTP")
    server = smtplib.SMTP(smtp_server, smtp_port, timeout=60)
    print("EHLO")
    server.ehlo()
    print("STARTTLS")
    server.starttls()
    print("login")
    server.login(sender_email, password)
    print("enviando")
    text = msg.as_string()
    print(f"TAMANHO E-MAIL: {len(text)/1024/1024:.2f} MB")
    server.sendmail(sender_email, recipient_email, text.encode('utf-8'))
    print("quit")
    server.quit()
    print("sucesso")


# ─────────────────────────────────────────────
# GUI Application
# ─────────────────────────────────────────────

class EmailSenderApp:
    def __init__(self, root):
        self.root = root
        self.root.title("📧 Disparador de E-mails em Massa")
        self.root.geometry("820x780")
        self.root.configure(bg="#0d0d0d")
        self.root.resizable(True, True)

        self.attachment_path = tk.StringVar()
        self.is_running = False
        self.pause_event = threading.Event()
        self.stop_event = threading.Event()
        self.pause_event.set()

        self._setup_styles()
        self._build_ui()

    def _setup_styles(self):
        style = ttk.Style()
        style.theme_use('clam')

        style.configure('TFrame', background='#0d0d0d')
        style.configure('Card.TFrame', background='#161616', relief='flat')

        style.configure('TLabel',
            background='#0d0d0d', foreground='#e0e0e0',
            font=('Courier New', 10))

        style.configure('Header.TLabel',
            background='#0d0d0d', foreground='#00ff88',
            font=('Courier New', 22, 'bold'))

        style.configure('Sub.TLabel',
            background='#0d0d0d', foreground='#666666',
            font=('Courier New', 9))

        style.configure('Section.TLabel',
            background='#161616', foreground='#00ff88',
            font=('Courier New', 10, 'bold'))

        style.configure('TEntry',
            fieldbackground='#1e1e1e', foreground='#e0e0e0',
            insertcolor='#00ff88', borderwidth=0,
            font=('Courier New', 10))

        style.configure('Green.TButton',
            background='#00ff88', foreground='#0d0d0d',
            font=('Courier New', 11, 'bold'),
            borderwidth=0, focuscolor='none', padding=(14, 8))
        style.map('Green.TButton',
            background=[('active', '#00cc6a'), ('disabled', '#1a3d2b')],
            foreground=[('disabled', '#0d0d0d')])

        style.configure('Red.TButton',
            background='#ff3355', foreground='#ffffff',
            font=('Courier New', 11, 'bold'),
            borderwidth=0, focuscolor='none', padding=(14, 8))
        style.map('Red.TButton',
            background=[('active', '#cc2244')])

        style.configure('Gray.TButton',
            background='#2a2a2a', foreground='#aaaaaa',
            font=('Courier New', 10),
            borderwidth=0, focuscolor='none', padding=(10, 6))
        style.map('Gray.TButton',
            background=[('active', '#333333')])

        style.configure('TProgressbar',
            background='#00ff88', troughcolor='#1e1e1e',
            borderwidth=0, thickness=6)

    def _build_ui(self):
        # ── HEADER ──
        header_frame = tk.Frame(self.root, bg='#0d0d0d')
        header_frame.pack(fill='x', padx=28, pady=(22, 0))

        tk.Label(header_frame, text="▸ MAIL BLASTER",
                 bg='#0d0d0d', fg='#00ff88',
                 font=('Courier New', 22, 'bold')).pack(side='left')

        tk.Label(header_frame, text="v1.0 - Powered by Lorenço - Gain Academy",
                 bg='#0d0d0d', fg='#333333',
                 font=('Courier New', 10)).pack(side='left', padx=(8, 0), pady=(8, 0))

        tk.Label(self.root,
                 text="Envio massivo com controle de ritmo • Google Sheets integrado",
                 bg='#0d0d0d', fg='#444444',
                 font=('Courier New', 9)).pack(anchor='w', padx=28)

        # ── SEPARATOR ──
        tk.Frame(self.root, bg='#1a1a1a', height=1).pack(fill='x', padx=28, pady=(12, 18))

        # ── SCROLL CONTAINER ──
        canvas = tk.Canvas(self.root, bg='#0d0d0d', highlightthickness=0)
        scrollbar = ttk.Scrollbar(self.root, orient='vertical', command=canvas.yview)
        self.scroll_frame = tk.Frame(canvas, bg='#0d0d0d')

        self.scroll_frame.bind('<Configure>',
            lambda e: canvas.configure(scrollregion=canvas.bbox('all')))

        canvas.create_window((0, 0), window=self.scroll_frame, anchor='nw')
        canvas.configure(yscrollcommand=scrollbar.set)

        canvas.pack(side='left', fill='both', expand=True, padx=(28, 0))
        scrollbar.pack(side='right', fill='y', padx=(0, 8))

        self.root.bind_all('<MouseWheel>',
            lambda e: canvas.yview_scroll(int(-1*(e.delta/120)), 'units'))

        self._build_form(self.scroll_frame)

    def _card(self, parent, title, pady=(0, 14)):
        outer = tk.Frame(parent, bg='#0d0d0d')
        outer.pack(fill='x', pady=pady)

        tk.Label(outer, text=title,
                 bg='#0d0d0d', fg='#00ff88',
                 font=('Courier New', 9, 'bold')).pack(anchor='w', pady=(0, 5))

        card = tk.Frame(outer, bg='#161616', padx=18, pady=14)
        card.pack(fill='x')
        return card

    def _field(self, parent, label, var=None, show=None, row=0, placeholder=''):
        tk.Label(parent, text=label,
                 bg='#161616', fg='#888888',
                 font=('Courier New', 9)).grid(row=row, column=0, sticky='w', pady=(0, 2))

        entry_frame = tk.Frame(parent, bg='#1e1e1e')
        entry_frame.grid(row=row, column=1, sticky='ew', padx=(10, 0), pady=(0, 8))
        parent.columnconfigure(1, weight=1)

        entry = tk.Entry(entry_frame,
                         textvariable=var,
                         show=show or '',
                         bg='#1e1e1e', fg='#e0e0e0',
                         insertbackground='#00ff88',
                         relief='flat',
                         font=('Courier New', 10),
                         bd=6)
        entry.pack(fill='x')

        if placeholder and var:
            if not var.get():
                entry.insert(0, placeholder)
                entry.config(fg='#444444')
                def on_focus_in(e, _e=entry, _v=var, _p=placeholder):
                    if _e.get() == _p:
                        _e.delete(0, 'end')
                        _e.config(fg='#e0e0e0')
                def on_focus_out(e, _e=entry, _v=var, _p=placeholder):
                    if not _e.get():
                        _e.insert(0, _p)
                        _e.config(fg='#444444')
                entry.bind('<FocusIn>', on_focus_in)
                entry.bind('<FocusOut>', on_focus_out)

        return entry

    def _build_form(self, parent):
        # ─── SEÇÃO 1: Credenciais ───
        card1 = self._card(parent, "01 ── CREDENCIAIS DO REMETENTE")

        self.email_var = tk.StringVar()
        self.password_var = tk.StringVar()

        self._field(card1, "E-mail:", self.email_var, row=0,
                    placeholder="seu@email.com")
        self._field(card1, "Senha:", self.password_var, show='●', row=1,
                    placeholder="Senha ou App Password")

        note = tk.Label(card1,
            text="⚠  Gmail: use uma Senha de App (myaccount.google.com/apppasswords)",
            bg='#161616', fg='#555555', font=('Courier New', 8))
        note.grid(row=2, column=0, columnspan=2, sticky='w', pady=(2, 0))

        # ─── SEÇÃO 2: Planilha ───
        card2 = self._card(parent, "02 ── GOOGLE SHEETS")

        self.sheet_url_var = tk.StringVar()
        self._field(card2, "URL da planilha:", self.sheet_url_var, row=0,
                    placeholder="https://docs.google.com/spreadsheets/d/...")

        note2 = tk.Label(card2,
            text="ℹ  A planilha deve ter colunas: Nome | E-mail | Status\n"
                 "   Na primeira execução, o Google pedirá autorização no navegador.",
            bg='#161616', fg='#555555', font=('Courier New', 8),
            justify='left')
        note2.grid(row=1, column=0, columnspan=2, sticky='w', pady=(4, 0))

        # ─── SEÇÃO 3: Conteúdo ───
        card3 = self._card(parent, "03 ── CONTEÚDO DO E-MAIL")

        self.subject_var = tk.StringVar()
        self._field(card3, "Assunto:", self.subject_var, row=0,
                    placeholder="Assunto do e-mail")

        tk.Label(card3, text="Mensagem:",
                 bg='#161616', fg='#888888',
                 font=('Courier New', 9)).grid(row=1, column=0, sticky='nw', pady=(4, 2))

        body_frame = tk.Frame(card3, bg='#1e1e1e')
        body_frame.grid(row=1, column=1, sticky='ew', padx=(10, 0), pady=(0, 8))
        card3.columnconfigure(1, weight=1)

        self.body_text = tk.Text(body_frame,
                                 bg='#1e1e1e', fg='#e0e0e0',
                                 insertbackground='#00ff88',
                                 relief='flat', bd=6,
                                 font=('Courier New', 10),
                                 height=7, wrap='word')
        self.body_text.pack(fill='x')
        self.body_text.insert('1.0', 'Digite a mensagem aqui...')
        self.body_text.config(fg='#444444')

        def body_focus_in(e):
            if self.body_text.get('1.0', 'end-1c') == 'Digite a mensagem aqui...':
                self.body_text.delete('1.0', 'end')
                self.body_text.config(fg='#e0e0e0')
        def body_focus_out(e):
            if not self.body_text.get('1.0', 'end-1c').strip():
                self.body_text.insert('1.0', 'Digite a mensagem aqui...')
                self.body_text.config(fg='#444444')
        self.body_text.bind('<FocusIn>', body_focus_in)
        self.body_text.bind('<FocusOut>', body_focus_out)

        # ─── SEÇÃO 4: Anexo ───
        card4 = self._card(parent, "04 ── ANEXO  (opcional)")

        attach_row = tk.Frame(card4, bg='#161616')
        attach_row.pack(fill='x')

        self.attach_label = tk.Label(attach_row,
            text="Nenhum arquivo selecionado",
            bg='#1e1e1e', fg='#555555',
            font=('Courier New', 9), anchor='w', padx=8)
        self.attach_label.pack(side='left', fill='x', expand=True, ipady=7)

        ttk.Button(attach_row, text="Selecionar arquivo",
                   style='Gray.TButton',
                   command=self._pick_file).pack(side='right', padx=(8, 0))

        # ─── SEÇÃO 5: Controles ───
        card5 = self._card(parent, "05 ── CONTROLE DE ENVIO", pady=(0, 10))

        rate_row = tk.Frame(card5, bg='#161616')
        rate_row.pack(fill='x', pady=(0, 12))

        tk.Label(rate_row, text="Ritmo:",
                 bg='#161616', fg='#888888',
                 font=('Courier New', 9)).pack(side='left')

        self.batch_var = tk.IntVar(value=10)
        self.interval_var = tk.IntVar(value=5)

        tk.Label(rate_row, text="  Lote:",
                 bg='#161616', fg='#666666',
                 font=('Courier New', 9)).pack(side='left')
        tk.Spinbox(rate_row, from_=1, to=50, textvariable=self.batch_var,
                   width=4, bg='#1e1e1e', fg='#e0e0e0',
                   buttonbackground='#2a2a2a', relief='flat',
                   font=('Courier New', 10)).pack(side='left', padx=(4, 0))

        tk.Label(rate_row, text="  e-mails a cada",
                 bg='#161616', fg='#666666',
                 font=('Courier New', 9)).pack(side='left', padx=(6, 0))
        tk.Spinbox(rate_row, from_=1, to=60, textvariable=self.interval_var,
                   width=4, bg='#1e1e1e', fg='#e0e0e0',
                   buttonbackground='#2a2a2a', relief='flat',
                   font=('Courier New', 10)).pack(side='left', padx=(4, 0))
        tk.Label(rate_row, text="  segundos",
                 bg='#161616', fg='#666666',
                 font=('Courier New', 9)).pack(side='left', padx=(4, 0))

        btn_row = tk.Frame(card5, bg='#161616')
        btn_row.pack(fill='x')

        self.start_btn = ttk.Button(btn_row, text="▶  INICIAR ENVIO",
                                    style='Green.TButton',
                                    command=self._start_sending)
        self.start_btn.pack(side='left', padx=(0, 8))

        self.pause_btn = ttk.Button(btn_row, text="⏸  PAUSAR",
                                    style='Gray.TButton',
                                    command=self._toggle_pause,
                                    state='disabled')
        self.pause_btn.pack(side='left', padx=(0, 8))

        self.stop_btn = ttk.Button(btn_row, text="⏹  PARAR",
                                   style='Red.TButton',
                                   command=self._stop_sending,
                                   state='disabled')
        self.stop_btn.pack(side='left')

        # ─── SEÇÃO 6: Progresso ───
        prog_card = self._card(parent, "06 ── PROGRESSO", pady=(6, 10))

        stat_row = tk.Frame(prog_card, bg='#161616')
        stat_row.pack(fill='x', pady=(0, 8))

        def stat_badge(parent, label, color):
            f = tk.Frame(parent, bg='#1a1a1a', padx=12, pady=6)
            f.pack(side='left', padx=(0, 8))
            tk.Label(f, text=label, bg='#1a1a1a', fg='#555555',
                     font=('Courier New', 8)).pack()
            v = tk.StringVar(value='0')
            lbl = tk.Label(f, textvariable=v, bg='#1a1a1a', fg=color,
                           font=('Courier New', 16, 'bold'))
            lbl.pack()
            return v

        self.sent_var    = stat_badge(stat_row, "ENVIADOS",  '#00ff88')
        self.pending_var = stat_badge(stat_row, "PENDENTES", '#ffcc00')
        self.failed_var  = stat_badge(stat_row, "FALHAS",    '#ff3355')
        self.total_var   = stat_badge(stat_row, "TOTAL",     '#aaaaaa')

        self.progress = ttk.Progressbar(prog_card, orient='horizontal',
                                        mode='determinate', style='TProgressbar')
        self.progress.pack(fill='x', pady=(0, 8))

        self.status_var = tk.StringVar(value="Aguardando início...")
        tk.Label(prog_card, textvariable=self.status_var,
                 bg='#161616', fg='#555555',
                 font=('Courier New', 9)).pack(anchor='w')

        # ─── LOG ───
        log_card = self._card(parent, "07 ── LOG DE ATIVIDADE", pady=(6, 20))

        self.log_text = tk.Text(log_card,
                                bg='#0a0a0a', fg='#00ff88',
                                insertbackground='#00ff88',
                                relief='flat', bd=6,
                                font=('Courier New', 9),
                                height=12, state='disabled',
                                wrap='word')
        self.log_text.pack(fill='x')

        self._log("Sistema iniciado. Configure os campos e clique em INICIAR.")

    def _pick_file(self):
        path = filedialog.askopenfilename(title="Selecionar anexo")
        if path:
            self.attachment_path.set(path)
            name = os.path.basename(path)
            self.attach_label.config(text=f"📎  {name}", fg='#00ff88')

    def _log(self, message, color='#00ff88'):
        ts = datetime.now().strftime('%H:%M:%S')
        self.log_text.config(state='normal')
        self.log_text.insert('end', f"[{ts}] {message}\n")
        self.log_text.config(state='disabled')
        self.log_text.see('end')

    def _update_stats(self, sent, pending, failed, total):
        self.sent_var.set(str(sent))
        self.pending_var.set(str(pending))
        self.failed_var.set(str(failed))
        self.total_var.set(str(total))
        if total > 0:
            self.progress['value'] = (sent + failed) / total * 100

    def _toggle_pause(self):
        if self.pause_event.is_set():
            self.pause_event.clear()
            self.pause_btn.config(text="▶  RETOMAR")
            self.status_var.set("⏸  Pausado")
            self._log("Envio pausado pelo usuário.")
        else:
            self.pause_event.set()
            self.pause_btn.config(text="⏸  PAUSAR")
            self.status_var.set("▶  Retomando...")
            self._log("Envio retomado.")

    def _stop_sending(self):
        self.stop_event.set()
        self.pause_event.set()
        self._log("⏹  Parando envio...")

    def _start_sending(self):
        email = self.email_var.get().strip()
        password = self.password_var.get().strip()
        sheet_url = self.sheet_url_var.get().strip()
        subject = self.subject_var.get().strip()
        body = self.body_text.get('1.0', 'end-1c').strip()
        attachment = self.attachment_path.get().strip()
        batch = self.batch_var.get()
        interval = self.interval_var.get()

        if body == 'Digite a mensagem aqui...':
            body = ''

        # Validações
        errors = []
        if not email or '@' not in email:
            errors.append("• E-mail inválido")
        if not password:
            errors.append("• Senha obrigatória")
        if not sheet_url:
            errors.append("• URL da planilha obrigatória")
        if not subject:
            errors.append("• Assunto obrigatório")
        if not body:
            errors.append("• Mensagem obrigatória")

        if errors:
            messagebox.showerror("Campos obrigatórios", "\n".join(errors))
            return

        self.start_btn.config(state='disabled')
        self.pause_btn.config(state='normal')
        self.stop_btn.config(state='normal')
        self.is_running = True
        self.stop_event.clear()
        self.pause_event.set()

        thread = threading.Thread(
            target=self._send_loop,
            args=(email, password, sheet_url, subject, body, attachment, batch, interval),
            daemon=True
        )
        thread.start()

    def _send_loop(self, email, password, sheet_url, subject, body, attachment, batch, interval):
        def ui(fn): self.root.after(0, fn)

        try:
            ui(lambda: self.status_var.set("🔑 Autenticando com Google Sheets..."))
            ui(lambda: self._log("Conectando ao Google Sheets..."))

            creds = get_google_creds()
            ws, records, sh = load_emails_from_sheet(sheet_url, creds)

            smtp_host, smtp_port = detect_smtp(email)
            ui(lambda: self._log(f"SMTP detectado: {smtp_host}:{smtp_port}"))

            total = len(records)
            ui(lambda: self.total_var.set(str(total)))
            ui(lambda: self._log(f"Total de destinatários encontrados: {total}"))

            sent = sum(1 for r in records if str(r.get('Status', '')).lower() == 'enviado')
            failed = sum(1 for r in records if str(r.get('Status', '')).lower() == 'falhou')
            pending = total - sent - failed

            ui(lambda: self._update_stats(sent, pending, failed, total))

            batch_count = 0

            for idx, record in enumerate(records):
                if self.stop_event.is_set():
                    break

                self.pause_event.wait()

                if self.stop_event.is_set():
                    break

                status = str(record.get('status', '')).strip().lower()
                if status == 'enviado':
                    continue 
                
                print(record)
                
                recipient = str(record.get('e-mail', record.get('email', record.get('Email', '')))).strip()
                name = str(record.get('Nome', record.get('nome', record.get('Name', '')))).strip()
                
                
                if not recipient or '@' not in recipient:
                    ui(lambda n=name, r=recipient, i=idx: self._log(f"⚠  Linha {i+2}: e-mail inválido ({r}) — pulando"))
                    update_status(ws, idx, 'Falhou')
                    failed += 1
                    pending = max(0, pending - 1)
                    ui(lambda s=sent, p=pending, f=failed, t=total: self._update_stats(s, p, f, t))
                    continue

                personalized_body = body.replace('{nome}', name).replace('{e-mail}', recipient)
                personalized_subject = subject.replace('{nome}', name).replace('{e-mail}', recipient)

                try:
                    ui(lambda r=recipient: self.status_var.set(f"Enviando → {r}"))
                    send_email(smtp_host, smtp_port, email, password,
                               recipient, personalized_subject, personalized_body,
                               attachment if attachment else None)

                    update_status(ws, idx, 'Enviado')
                    sent += 1
                    pending = max(0, pending - 1)
                    ui(lambda n=name, r=recipient: self._log(f"✓  Enviado: {n} <{r}>"))

                except Exception as e:
                    import traceback
                    traceback.print_exc()
                    update_status(ws, idx, 'Falhou')
                    failed += 1
                    pending = max(0, pending - 1)
                    ui(lambda r=recipient, err=str(e): self._log(f"✗  Falha: {r} — {err}"))

                ui(lambda s=sent, p=pending, f=failed, t=total: self._update_stats(s, p, f, t))

                batch_count += 1
                if batch_count >= batch:
                    batch_count = 0
                    ui(lambda iv=interval: self.status_var.set(f"⏱  Aguardando {iv}s antes do próximo lote..."))
                    ui(lambda iv=interval: self._log(f"Lote concluído. Aguardando {iv} segundos..."))
                    for _ in range(interval * 10):
                        if self.stop_event.is_set():
                            break
                        self.pause_event.wait()
                        time.sleep(0.1)

            if self.stop_event.is_set():
                ui(lambda: self.status_var.set("⏹  Envio interrompido pelo usuário."))
                ui(lambda: self._log("Envio interrompido."))
            else:
                ui(lambda: self.status_var.set(f"✅  Concluído! {sent} enviados, {failed} falhas."))
                ui(lambda s=sent, f=failed: self._log(f"✅ Envio finalizado! {s} enviados, {f} falhas."))

        except FileNotFoundError as e:
            ui(lambda err=str(e): messagebox.showerror("Configuração necessária", err))
            ui(lambda: self._log(f"ERRO DE CONFIG: {e}"))
        except Exception as e:
            ui(lambda err=str(e): messagebox.showerror("Erro", f"Erro inesperado:\n{err}"))
            ui(lambda err=str(e): self._log(f"ERRO: {err}"))
        finally:
            ui(lambda: self.start_btn.config(state='normal'))
            ui(lambda: self.pause_btn.config(state='disabled', text="⏸  PAUSAR"))
            ui(lambda: self.stop_btn.config(state='disabled'))
            self.is_running = False


def main():
    root = tk.Tk()
    app = EmailSenderApp(root)
    root.mainloop()


if __name__ == '__main__':
    main()
