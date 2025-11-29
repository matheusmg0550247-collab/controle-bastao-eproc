# ============================================
# 1. IMPORTS E DEFINIÇÕES GLOBAIS
# ============================================
import streamlit as st
import pandas as pd
import requests
from datetime import datetime, timedelta, date, time
from operator import itemgetter
from streamlit_autorefresh import st_autorefresh
import json 
import re 

# --- Constantes de Consultores ---
CONSULTORES = sorted([
    "Alex Paulo da Silva",
    "Dirceu Gonçalves Siqueira Neto",
    "Douglas de Souza Gonçalves",
    "Farley Leandro de Oliveira Juliano", 
    "Gleis da Silva Rodrigues",
    "Hugo Leonardo Murta",
    "Igor Dayrell Gonçalves Correa",
    "Jerry Marcos dos Santos Neto",
    "Jonatas Gomes Saraiva",
    "Leandro Victor Catharino",
    "Luiz Henrique Barros Oliveira",
    "Marcelo dos Santos Dutra",
    "Marina Silva Marques",
    "Marina Torres do Amaral",
    "Vanessa Ligiane Pimenta Santos"

])

# --- FUNÇÃO DE CACHE GLOBAL ---
@st.cache_resource(show_spinner=False)
def get_global_state_cache():
    """Inicializa e retorna o dicionário de estado GLOBAL compartilhado."""
    print("--- Inicializando o Cache de Estado GLOBAL (Executa Apenas 1x) ---")
    return {
        'status_texto': {nome: 'Indisponível' for nome in CONSULTORES},
        'bastao_queue': [],
        'skip_flags': {},
        'bastao_start_time': None,
        'current_status_starts': {nome: datetime.now() for nome in CONSULTORES},
        'report_last_run_date': datetime.min,
        'bastao_counts': {nome: 0 for nome in CONSULTORES},
        'priority_return_queue': [],
        'rotation_gif_start_time': None,
        'lunch_warning_info': None, # Aviso de almoço Global
        'auxilio_ativo': False, # Estado do botão de auxílio
        'daily_logs': [] # Log persistente para o relatório
    }

# --- Constantes (Webhooks) ---
GOOGLE_CHAT_WEBHOOK_BACKUP = "https://chat.googleapis.com/v1/spaces/AAQA0V8TAhs/messages?key=AIzaSyDdI0hCZtE6vySjMm-WEfRq3CPzqKqqsHI&token=Zl7KMv0PLrm5c7IMZZdaclfYoc-je9ilDDAlDfqDMAU"
CHAT_WEBHOOK_BASTAO = "https://chat.googleapis.com/v1/spaces/AAQA5CyNolU/messages?key=AIzaSyDdI0hCZtE6vySjMm-WEfRq3CPzqKqqsHI&token=Zolqmc0YfJ5bPzsqLrefwn8yBbNQLLfFBzLTwIkr7W4" 
GOOGLE_CHAT_WEBHOOK_REGISTRO = "https://chat.googleapis.com/v1/spaces/AAQAVvsU4Lg/messages?key=AIzaSyDdI0hCZtE6vySjMm-WEfRq3CPzqKqqsHI&token=hSghjEZq8-1EmlfHdSoPRq_nTSpYc0usCs23RJOD-yk"
GOOGLE_CHAT_WEBHOOK_CHAMADO = "https://chat.googleapis.com/v1/spaces/AAQAPPWlpW8/messages?key=AIzaSyDdI0hCZtE6vySjMm-WEfRq3CPzqKqqsHI&token=jMg2PkqtpIe3JbG_SZG_ZhcfuQQII9RXM0rZQienUZk"
GOOGLE_CHAT_WEBHOOK_SESSAO = "https://chat.googleapis.com/v1/spaces/AAQAWs1zqNM/messages?key=AIzaSyDdI0hCZtE6vySjMm-WEfRq3CPzqKqqsHI&token=hIxKd9f35kKdJqWUNjttzRBfCsxomK0OJ3AkH9DJmxY"
GOOGLE_CHAT_WEBHOOK_CHECKLIST_HTML = "https://chat.googleapis.com/v1/spaces/AAQAXbwpQHY/messages?key=AIzaSyDdI0hCZtE6vySjMm-WEfRq3CPzqKqqsHI&token=7AQaoGHiWIfv3eczQzVZ-fbQdBqSBOh1CyQ854o1f7k"

# Dados das Câmaras
CAMARAS_DICT = {
    "Cartório da 1ª Câmara Cível": "caciv1@tjmg.jus.br", "Cartório da 2ª Câmara Cível": "caciv2@tjmg.jus.br",
    "Cartório da 3ª Câmara Cível": "caciv3@tjmg.jus.br", "Cartório da 4ª Câmara Cível": "caciv4@tjmg.jus.br",
    "Cartório da 5ª Câmara Cível": "caciv5@tjmg.jus.br", "Cartório da 6ª Câmara Cível": "caciv6@tjmg.jus.br",
    "Cartório da 7ª Câmara Cível": "caciv7@tjmg.jus.br", "Cartório da 8ª Câmara Cível": "caciv8@tjmg.jus.br",
    "Cartório da 9ª Câmara Cível": "caciv9@tjmg.jus.br", "Cartório da 10ª Câmara Cível": "caciv10@tjmg.jus.br",
    "Cartório da 11ª Câmara Cível": "caciv11@tjmg.jus.br", "Cartório da 12ª Câmara Cível": "caciv12@tjmg.jus.br",
    "Cartório da 13ª Câmara Cível": "caciv13@tjmg.jus.br", "Cartório da 14ª Câmara Cível": "caciv14@tjmg.jus.br",
    "Cartório da 15ª Câmara Cível": "caciv15@tjmg.jus.br", "Cartório da 16ª Câmara Cível": "caciv16@tjmg.jus.br",
    "Cartório da 17ª Câmara Cível": "caciv17@tjmg.jus.br", "Cartório da 18ª Câmara Cível": "caciv18@tjmg.jus.br",
    "Cartório da 19ª Câmara Cível": "caciv19@tjmg.jus.br", "Cartório da 20ª Câmara Cível": "caciv20@tjmg.jus.br",
    "Cartório da 21ª Câmara Cível": "caciv21@tjmg.jus.br"
}
CAMARAS_OPCOES = sorted(list(CAMARAS_DICT.keys()))

# --- NOVAS CONSTANTES SOLICITADAS ---
OPCOES_ATIVIDADES_STATUS = [
    "HP", "E-mail", "WhatsApp Plantão", 
    "Treinamento", "Homologação", "Redação Documentos", "Reunião", "Outros"
]
GIF_BASTAO_HOLDER = "https://media2.giphy.com/media/v1.Y2lkPTc5MGI3NjExa3Uwazd5cnNra2oxdDkydjZkcHdqcWN2cng0Y2N0cmNmN21vYXVzMiZlcD12MV9pbnRlcm5uYWxfZ2lmX2J5X2lkJmN0PWc/3rXs5J0hZkXwTZjuvM/giphy.gif"

# AQUI MUDOU O EMOJI
BASTAO_EMOJI = "🎄" 

APP_URL_CLOUD = 'https://controle-bastao-cesupe.streamlit.app'
STATUS_SAIDA_PRIORIDADE = ['Saída rápida']
STATUSES_DE_SAIDA = ['Atendimento', 'Almoço', 'Saída rápida', 'Ausente', 'Sessão'] 
GIF_URL_WARNING = 'https://media0.giphy.com/media/v1.Y2lkPTc5MGI3NjExY2pjMDN0NGlvdXp1aHZ1ejJqMnY5MG1yZmN0d3NqcDl1bTU1dDJrciZlcD12MV9pbnRlcm5uYWxfZ2lmX2J5X2lkJmN0PWc/fXnRObM8Q0RkOmR5nf/giphy.gif'
GIF_URL_ROTATION = 'https://media0.giphy.com/media/v1.Y2lkPTc5MGI3NjExdmx4azVxbGt4Mnk1cjMzZm5sMmp1YThteGJsMzcyYmhsdmFoczV0aSZlcD12MV9pbnRlcm5uYWxfZ2lmX2J5X2lkJmN0PWc/JpkZEKWY0s9QI4DGvF/giphy.gif'
GIF_URL_LUNCH_WARNING = 'https://media3.giphy.com/media/v1.Y2lkPTc5MGI3NjExMGZlbHN1azB3b2drdTI1eG10cDEzeWpmcmtwenZxNTV0bnc2OWgzZSYlcD12MV9pbnRlcm5uYWxfZ2lmX2J5X2lkJmN0PWc/bNlqpmBJRDMpxulfFB/giphy.gif'
GIF_URL_NEDRY = 'https://media0.giphy.com/media/v1.Y2lkPTc5MGI3NjExMGNkMGx3YnNkcXQ2bHJmNTZtZThraHhuNmVoOTNmbG0wcDloOXAybiZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/7kyWoqTue3po4/giphy.gif'
SOUND_URL = "https://github.com/matheusmg0550247-collab/controle-bastao-eproc2/raw/main/doorbell-223669.mp3"

# --- IMAGEM DE NATAL (PUGNOEL) ---
PUGNOEL_URL = "https://github.com/matheusmg0550247-collab/controle-bastao-eproc2/raw/main/Pugnoel.png"

# ============================================
# 2. FUNÇÕES AUXILIARES GLOBAIS
# ============================================

def date_serializer(obj):
    if isinstance(obj, datetime): return obj.isoformat()
    if isinstance(obj, timedelta): return obj.total_seconds()
    if isinstance(obj, (date, time)): return obj.isoformat()
    return str(obj)

def save_state():
    """Salva o estado da sessão local (st.session_state) no cache GLOBAL."""
    global_data = get_global_state_cache()
    try:
        global_data['status_texto'] = st.session_state.status_texto.copy()
        global_data['bastao_queue'] = st.session_state.bastao_queue.copy()
        global_data['skip_flags'] = st.session_state.skip_flags.copy()
        global_data['current_status_starts'] = st.session_state.current_status_starts.copy()
        global_data['bastao_counts'] = st.session_state.bastao_counts.copy()
        global_data['priority_return_queue'] = st.session_state.priority_return_queue.copy()
        global_data['bastao_start_time'] = st.session_state.bastao_start_time
        global_data['report_last_run_date'] = st.session_state.report_last_run_date
        global_data['rotation_gif_start_time'] = st.session_state.get('rotation_gif_start_time')
        global_data['lunch_warning_info'] = st.session_state.get('lunch_warning_info')
        global_data['auxilio_ativo'] = st.session_state.get('auxilio_ativo', False)
        global_data['daily_logs'] = json.loads(json.dumps(st.session_state.daily_logs, default=date_serializer))
    except Exception as e: 
        print(f'Erro ao salvar estado GLOBAL: {e}')

def load_state():
    """Carrega o estado do cache GLOBAL."""
    global_data = get_global_state_cache()
    
    loaded_logs = global_data.get('daily_logs', [])
    if loaded_logs and isinstance(loaded_logs[0], dict):
             deserialized_logs = loaded_logs
    else:
        try: 
             deserialized_logs = json.loads(loaded_logs)
        except: 
             deserialized_logs = loaded_logs 
    
    final_logs = []
    for log in deserialized_logs:
        if isinstance(log, dict):
            if 'duration' in log and not isinstance(log['duration'], timedelta):
                try: log['duration'] = timedelta(seconds=float(log['duration']))
                except: log['duration'] = timedelta(0)
            if 'timestamp' in log and isinstance(log['timestamp'], str):
                try: log['timestamp'] = datetime.fromisoformat(log['timestamp'])
                except: log['timestamp'] = datetime.min
            final_logs.append(log)

    loaded_data = {k: v for k, v in global_data.items() if k != 'daily_logs'}
    loaded_data['daily_logs'] = final_logs
    
    return loaded_data

def send_chat_notification_internal(consultor, status):
    if CHAT_WEBHOOK_BASTAO and status == 'Bastão':
        message_template = "🎉 **BASTÃO GIRADO!** 🎉 \n\n- **Novo(a) Responsável:** {consultor}\n- **Acesse o Painel:** {app_url}"
        message_text = message_template.format(consultor=consultor, app_url=APP_URL_CLOUD) 
        chat_message = {"text": message_text}
        try:
            response = requests.post(CHAT_WEBHOOK_BASTAO, json=chat_message)
            response.raise_for_status()
            print(f"Notificação de bastão enviada para {consultor}")
            return True
        except requests.exceptions.RequestException as e:
            print(f"Erro ao enviar notificação de bastão: {e}")
            return False
    return False

def play_sound_html(): return f'<audio autoplay="true"><source src="{SOUND_URL}" type="audio/mpeg"></audio>'

# --- Efeito de Neve (CSS) ---
def render_snow_effect():
    snow_css = """
    <style>
    /* customizable snowflake styling */
    .snowflake {
      color: #fff;
      font-size: 1em;
      font-family: Arial;
      text-shadow: 0 0 1px #000;
    }

    @-webkit-keyframes snowflakes-fall{0%{top:-10%}100%{top:100%}}@-webkit-keyframes snowflakes-shake{0%{-webkit-transform:translateX(0px);transform:translateX(0px)}50%{-webkit-transform:translateX(80px);transform:translateX(80px)}100%{-webkit-transform:translateX(0px);transform:translateX(0px)}}@keyframes snowflakes-fall{0%{top:-10%}100%{top:100%}}@keyframes snowflakes-shake{0%{transform:translateX(0px)}50%{transform:translateX(80px)}100%{transform:translateX(0px)}}.snowflake{position:fixed;top:-10%;z-index:9999;-webkit-user-select:none;-moz-user-select:none;-ms-user-select:none;user-select:none;cursor:default;-webkit-animation-name:snowflakes-fall,snowflakes-shake;-webkit-animation-duration:10s,3s;-webkit-animation-timing-function:linear,ease-in-out;-webkit-animation-iteration-count:infinite,infinite;-webkit-animation-play-state:running,running;animation-name:snowflakes-fall,snowflakes-shake;animation-duration:10s,3s;animation-timing-function:linear,ease-in-out;animation-iteration-count:infinite,infinite;animation-play-state:running,running}.snowflake:nth-of-type(0){left:1%;-webkit-animation-delay:0s,0s;animation-delay:0s,0s}.snowflake:nth-of-type(1){left:10%;-webkit-animation-delay:1s,1s;animation-delay:1s,1s}.snowflake:nth-of-type(2){left:20%;-webkit-animation-delay:6s,.5s;animation-delay:6s,.5s}.snowflake:nth-of-type(3){left:30%;-webkit-animation-delay:4s,2s;animation-delay:4s,2s}.snowflake:nth-of-type(4){left:40%;-webkit-animation-delay:2s,2s;animation-delay:2s,2s}.snowflake:nth-of-type(5){left:50%;-webkit-animation-delay:8s,3s;animation-delay:8s,3s}.snowflake:nth-of-type(6){left:60%;-webkit-animation-delay:6s,2s;animation-delay:6s,2s}.snowflake:nth-of-type(7){left:70%;-webkit-animation-delay:2.5s,1s;animation-delay:2.5s,1s}.snowflake:nth-of-type(8){left:80%;-webkit-animation-delay:1s,0s;animation-delay:1s,0s}.snowflake:nth-of-type(9){left:90%;-webkit-animation-delay:3s,1.5s;animation-delay:3s,1.5s}
    </style>
    <div class="snowflakes" aria-hidden="true">
      <div class="snowflake">❅</div>
      <div class="snowflake">❅</div>
      <div class="snowflake">❆</div>
      <div class="snowflake">❄</div>
      <div class="snowflake">❅</div>
      <div class="snowflake">❆</div>
      <div class="snowflake">❄</div>
      <div class="snowflake">❅</div>
      <div class="snowflake">❆</div>
      <div class="snowflake">❄</div>
    </div>
    """
    st.markdown(snow_css, unsafe_allow_html=True)

# --- Função Geradora do HTML Personalizado (COM TEMA VERMELHO) ---
def gerar_html_checklist(consultor_nome, camara_nome, data_sessao_formatada):
    """Gera o código HTML do checklist com tema vermelho de Natal."""
    
    consultor_formatado = f"@{consultor_nome}" if not consultor_nome.startswith("@") else consultor_nome
    webhook_destino = GOOGLE_CHAT_WEBHOOK_CHECKLIST_HTML
    
    # Paleta de cores vermelha
    primary_red = "#8B0000" # Vermelho escuro para textos e bordas
    light_red_bg = "#FFEBEE" # Fundo vermelho bem claro
    accent_red = "#D42426" # Vermelho vibrante para destaques

    html_template = f"""
<!DOCTYPE html>
<html lang="pt-br">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>Acompanhamento de Sessão - {camara_nome}</title>
<style>
    body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; background-color: #f4f6f9; margin: 0; padding: 20px; color: #333; }}
    .container {{ max-width: 800px; margin: 0 auto; background: #fff; padding: 30px; border-radius: 8px; box-shadow: 0 2px 10px rgba(0,0,0,0.1); }}
    h1 {{ color: {primary_red}; font-size: 24px; border-bottom: 2px solid {primary_red}; padding-bottom: 10px; margin-bottom: 20px; }}
    .intro-box {{ background-color: {light_red_bg}; border-left: 5px solid {primary_red}; padding: 15px; margin-bottom: 25px; font-size: 14px; line-height: 1.5; }}
    
    .row-flex {{ display: flex; gap: 20px; margin-bottom: 20px; align-items: flex-end; }}
    .col-flex {{ flex: 1; }}
    
    .field-label {{ font-weight: bold; display: block; margin-bottom: 5px; color: #444; }}
    .static-value {{ background-color: #f9f9f9; padding: 10px; border: 1px solid #ddd; border-radius: 4px; color: #555; font-weight: 500; min-height: 20px; display: flex; align-items: center; }}
    select, input[type="text"] {{ width: 100%; padding: 10px; border: 1px solid #ccc; border-radius: 4px; font-size: 14px; box-sizing: border-box; }}
    
    .field-group {{ margin-bottom: 20px; }}

    .section-header {{ background-color: {primary_red}; color: white; padding: 10px 15px; border-radius: 4px; margin-top: 25px; margin-bottom: 15px; font-size: 15px; font-weight: bold; }}
    
    .checklist-title {{ font-size: 22px; font-weight: bold; color: #333; margin-top: 30px; margin-bottom: 5px; }}
    .checklist-desc {{ font-size: 14px; color: #666; font-style: italic; margin-bottom: 20px; }}
    
    .checkbox-item {{ margin-bottom: 15px; display: flex; align-items: flex-start; border-bottom: 1px solid #eee; padding-bottom: 10px; }}
    .checkbox-item:last-child {{ border-bottom: none; }}
    .checkbox-item input[type="checkbox"] {{ margin-right: 10px; margin-top: 3px; width: 18px; height: 18px; accent-color: {primary_red}; cursor: pointer; flex-shrink: 0; }}
    .checkbox-item label {{ cursor: pointer; line-height: 1.4; font-size: 14px; color: #444; }}
    .checkbox-item label strong {{ color: #000; }}
    
    .other-input {{ margin-top: 5px; width: 100%; display: none; margin-left: 28px; }}
    
    .btn-submit {{ background-color: #28a745; color: white; border: none; padding: 12px 24px; font-size: 16px; border-radius: 4px; cursor: pointer; display: block; width: 100%; margin-top: 30px; transition: background 0.3s; font-weight: bold; }}
    .btn-submit:hover {{ background-color: #218838; }}
    
    .hidden {{ display: none; }}
</style>
<script>
    function toggleSetor() {{
        const setor = document.getElementById("setor").value;
        const divCartorio = document.getElementById("checklist-cartorio-container");
        const divGabinete = document.getElementById("checklist-gabinete-container");
        
        if (setor === "Cartório") {{
            divCartorio.style.display = "block";
            divGabinete.style.display = "none";
        }} else {{
            divCartorio.style.display = "none";
            divGabinete.style.display = "block";
        }}
    }}

    function toggleOther(checkboxId, inputId) {{
        const checkboxEl = document.getElementById(checkboxId);
        const inputEl = document.getElementById(inputId);
        
        if (checkboxEl.checked) {{
            inputEl.style.display = "block";
            inputEl.focus();
        }} else {{
            inputEl.style.display = "none";
            inputEl.value = ""; 
        }}
    }}

    function enviarWebhook() {{
        const webhookUrl = '{webhook_destino}';
        
        const nomeUsuario = document.getElementById('nome_usuario').value;
        if (!nomeUsuario) {{
            alert("Por favor, preencha o nome do Responsável antes de enviar.");
            return;
        }}

        const setor = document.getElementById('setor').value;
        
        let containerAtivo;
        if (setor === "Cartório") {{
            containerAtivo = document.getElementById("checklist-cartorio-container");
        }} else {{
            containerAtivo = document.getElementById("checklist-gabinete-container");
        }}
        
        const checks = containerAtivo.querySelectorAll('input[type="checkbox"]:checked');
        let itensMarcados = [];
        
        checks.forEach((chk) => {{
            let val = "- " + chk.value;
            if (chk.id === "c_chk_outros_pre") {{
                const textoOutros = document.getElementById("c_input_outros_pre").value;
                if (textoOutros) val += ": " + textoOutros;
            }}
            if (chk.id === "c_chk_outros_pos") {{
                const textoOutros = document.getElementById("c_input_outros_pos").value;
                if (textoOutros) val += ": " + textoOutros;
            }}
            if (chk.id === "g_chk_outros_pre") {{
                const textoOutros = document.getElementById("g_input_outros_pre").value;
                if (textoOutros) val += ": " + textoOutros;
            }}
            if (chk.id === "g_chk_outros_pos") {{
                const textoOutros = document.getElementById("g_input_outros_pos").value;
                if (textoOutros) val += ": " + textoOutros;
            }}
            itensMarcados.push(val);
        }});
        
        if (itensMarcados.length === 0 && confirm("Nenhuma dúvida foi marcada. Deseja enviar mesmo assim como 'Sem dúvidas'?") === false) {{
            return;
        }}
        
        const dataSessaoStr = "{data_sessao_formatada}";
        const parts = dataSessaoStr.split('/');
        const dataSessaoObj = new Date(parts[2], parts[1] - 1, parts[0]);
        
        const hoje = new Date();
        hoje.setHours(0,0,0,0);
        
        let consultorResponsavel = "{consultor_formatado}";
        
        if (hoje > dataSessaoObj) {{
            consultorResponsavel = "Atendimento";
        }}
        
        const msgTexto = 
            "*📝 Retorno de Checklist de Sessão*\\n" +
            "*Câmara:* {camara_nome}\\n" +
            "*Data:* {data_sessao_formatada}\\n" +
            "*Responsável (Local):* " + nomeUsuario + "\\n" +
            "*Consultor(a) Técnico(a):* " + consultorResponsavel + "\\n" +
            "*Setor:* " + setor + "\\n\\n" +
            "*Dúvidas/Pontos de Atenção:*" + (itensMarcados.length > 0 ? "\\n" + itensMarcados.join("\\n") : "\\nNenhuma dúvida reportada (Checklist OK).");

        const payload = {{ text: msgTexto }};

        fetch(webhookUrl, {{
            method: 'POST',
            headers: {{ 'Content-Type': 'application/json' }},
            body: JSON.stringify(payload)
        }})
        .then(response => {{
            if (response.ok) {{
                alert('Formulário enviado com sucesso! O(A) consultor(a) já recebeu suas informações.');
            }} else {{
                alert('Falha ao enviar. Tente novamente.');
            }}
        }})
        .catch(error => {{
            console.error('Erro:', error);
            alert('Erro ao enviar (Verifique sua conexão).');
        }});
    }}
    
    window.onload = function() {{
        toggleSetor();
    }};
</script>
</head>
<body>

<div class="container">
    <h1>Acompanhamento de Sessão</h1>
    
    <div class="intro-box">
        <strong>Olá!</strong> Sou o(a) consultor(a) <strong>{consultor_nome}</strong> responsável pelo acompanhamento técnico da sua sessão.<br><br>
        Meu objetivo é garantir que todos os trâmites ocorram com fluidez na data agendada <strong>({data_sessao_formatada})</strong>. Abaixo, apresento um check-list dos procedimentos essenciais.<br><br>
        <strong>Caso tenha dúvida ou insegurança em alguma etapa, marque a caixa correspondente e envie o formulário.</strong> Isso me permitirá atuar preventivamente.
    </div>

    <div class="row-flex">
        <div class="col-flex">
            <label class="field-label">Câmara:</label>
            <div class="static-value">{camara_nome}</div>
        </div>
        <div class="col-flex">
            <label class="field-label">Responsável (Seu Nome):</label>
            <input type="text" id="nome_usuario" placeholder="Digite seu nome">
        </div>
    </div>

    <div class="field-group">
        <label class="field-label">Data da Sessão:</label>
        <div class="static-value">{data_sessao_formatada}</div>
    </div>

    <div class="field-group">
        <label class="field-label">Qual é o seu Setor?</label>
        <select id="setor" onchange="toggleSetor()">
            <option value="Cartório">Cartório (Secretaria)</option>
            <option value="Gabinete">Gabinete</option>
        </select>
    </div>
    
    <div id="checklist-cartorio-container">
        <div class="checklist-title">Check-list: Cartório (Secretaria)</div>
        <div class="checklist-desc">Fase Pré-Sessão: Inicia a partir do fechamento da pauta até a abertura da sessão.</div>
        
        <div class="section-header">I. Pré-Sessão</div>
        
        <div class="checkbox-item">
            <input type="checkbox" id="c_chk1" value="Cartório Pré: Verificar Manifestações Desembargadores">
            <label for="c_chk1"><strong>Verificar Manifestações:</strong> Certificar-se de que todos os desembargadores manifestaram: Pedidos de vista, Retirados de pauta, Acompanhamento de voto, Votos de declaração, Votos divergentes.</label>
        </div>
        <div class="checkbox-item">
            <input type="checkbox" id="c_chk2" value="Cartório Pré: Marcar Destaques Visualizados">
            <label for="c_chk2"><strong>Marcar Destaques Visualizados:</strong> Marcar os destaques dos votos como visualizados (garante que alterações posteriores sejam sinalizadas pelo sistema).</label>
        </div>
        <div class="checkbox-item">
            <input type="checkbox" id="c_chk3" value="Cartório Pré: Lançar Previsão de Resultado">
            <label for="c_chk3"><strong>Lançar Previsão de Resultado:</strong> Sinalizar a importância de “Lançar a previsão do resultado do julgamento”.</label>
        </div>
        <div class="checkbox-item">
            <input type="checkbox" id="c_chk4" value="Cartório Pré: Verificar Manter Voto (Retirados)">
            <label for="c_chk4"><strong>Verificar Manter Voto:</strong> Conferir se o gabinete marcou a opção de manter o voto para próxima sessão, em processos retirados de pauta.</label>
        </div>
        
        <div class="checkbox-item" style="flex-wrap: wrap;">
            <input type="checkbox" id="c_chk_outros_pre" value="Cartório Pré-Sessão: Outros" onclick="toggleOther('c_chk_outros_pre', 'c_input_outros_pre')">
            <label for="c_chk_outros_pre"><strong>Outros na Preparação:</strong> (Descreva abaixo)</label>
            <input type="text" id="c_input_outros_pre" class="other-input" placeholder="Detalhes da dúvida na Pré-Sessão...">
        </div>

        <div class="section-header">II. Durante e Pós-Sessão</div>

        <div class="checkbox-item">
            <input type="checkbox" id="c_chk5" value="Cartório Pós: Abrir a Sessão">
            <label for="c_chk5"><strong>Início da Sessão:</strong> Acompanhar o Cartório ao "Abrir a sessão".</label>
        </div>
        <div class="checkbox-item">
            <input type="checkbox" id="c_chk6" value="Cartório Pós: Julgamento dos Processos">
            <label for="c_chk6"><strong>Julgamento:</strong> Acompanhar os passos: Marcar item como em julgamento, Salvar resultado de julgamento, Desmarcar item em julgamento.</label>
        </div>
        <div class="checkbox-item">
            <input type="checkbox" id="c_chk7" value="Cartório Pós: Atualizar Resultados e Eventos">
            <label for="c_chk7"><strong>Atualizar Resultados:</strong> Rodar "Atualizar Resultados da Sessão de Julgamento" e Lançar os eventos de resultado.</label>
        </div>
        <div class="checkbox-item">
            <input type="checkbox" id="c_chk8" value="Cartório Pós: Encerrar e Gerar Ata">
            <label for="c_chk8"><strong>Finalização:</strong> "Encerrar da sessão" e "Gerar ata".</label>
        </div>

        <div class="checkbox-item">
            <input type="checkbox" id="c_chk_olhinho" value="Cartório Pós: Conferência da Sessão (Olhinho)">
            <label for="c_chk_olhinho"><strong>Conferência da Sessão:</strong> Após o lançamento dos resultados e encerramento, utilizar o ícone "Conferência da sessão de julgamento" (ícone do olhinho) para verificar o relatório de inconsistências/erros e realizar a correção.</label>
        </div>

        <div class="checkbox-item">
            <input type="checkbox" id="c_chk9" value="Cartório Pós: Minutas não Assinadas (Filtro)">
            <label for="c_chk9"><strong>Pós-Sessão:</strong> Orientar sobre a Aplicação do filtro – Minutas não assinadas e necessidade de contato com gabinetes para assinatura.</label>
        </div>
        <div class="checkbox-item">
            <input type="checkbox" id="c_chk10" value="Cartório Pós: Conferir Manter Voto (Retirados Pós)">
            <label for="c_chk10"><strong>Pós-Sessão:</strong> Verificar se há processos retirados de pauta e conferir a marcação do gabinete para manter o processo para próxima sessão.</label>
        </div>
        
        <div class="checkbox-item" style="flex-wrap: wrap;">
            <input type="checkbox" id="c_chk_outros_pos" value="Cartório Pós-Sessão: Outros" onclick="toggleOther('c_chk_outros_pos', 'c_input_outros_pos')">
            <label for="c_chk_outros_pos"><strong>Outros no Encerramento:</strong> (Descreva abaixo)</label>
            <input type="text" id="c_input_outros_pos" class="other-input" placeholder="Detalhes da dúvida na Pós-Sessão...">
        </div>
    </div>

    <div id="checklist-gabinete-container" class="hidden">
        <div class="checklist-title">Check-list: Gabinete</div>
        <div class="checklist-desc">Foco na análise processual, votos e disponibilização de documentos.</div>
        
        <div class="section-header">I. Pré-Sessão (Análise e Inclusão)</div>
        
        <div class="checkbox-item">
            <input type="checkbox" id="g_chk1" value="Gabinete Pré: Inclusão e Minutas">
            <label for="g_chk1"><strong>Inclusão/Minutas:</strong> Selecionar processos para inclusão na sessão e criar Relatório/Voto liberando visualização para Colegiado.</label>
        </div>
        <div class="checkbox-item">
            <input type="checkbox" id="g_chk2" value="Gabinete Pré: Destaques/Vistas">
            <label for="g_chk2"><strong>Destaques/Vistas:</strong> Analisar divergências/vistas e inserir destaques próprios.</label>
        </div>
        
        <div class="checkbox-item" style="flex-wrap: wrap;">
            <input type="checkbox" id="g_chk_outros_pre" value="Gabinete Pré-Sessão: Outros" onclick="toggleOther('g_chk_outros_pre', 'g_input_outros_pre')">
            <label for="g_chk_outros_pre"><strong>Outros na Preparação:</strong> (Descreva abaixo)</label>
            <input type="text" id="g_input_outros_pre" class="other-input" placeholder="Detalhes da dúvida na Pré-Sessão...">
        </div>

        <div class="section-header">II. Pós-Sessão (Formalização)</div>

        <div class="checkbox-item">
            <input type="checkbox" id="g_chk5" value="Gabinete Pós: Filtro minutas para assinar">
            <label for="g_chk5"><strong>Assinatura:</strong> Aplicar o "Filtro minutas para assinar" e realizar a assinatura do Relatório/Voto/Acórdão no status "Para Assinar".</label>
        </div>
        <div class="checkbox-item">
            <input type="checkbox" id="g_chk6" value="Gabinete Pós: Juntada e Evento Final">
            <label for="g_chk6"><strong>Movimentação Final:</strong> Juntada de relatório/voto/acórdão e Lançamento do Evento “Remetidos os votos com acórdão”.</label>
        </div>
        
        <div class="checkbox-item" style="flex-wrap: wrap;">
            <input type="checkbox" id="g_chk_outros_pos" value="Gabinete Pós-Sessão: Outros" onclick="toggleOther('g_chk_outros_pos', 'g_input_outros_pos')">
            <label for="g_chk_outros_pos"><strong>Outros na Formalização:</strong> (Descreva abaixo)</label>
            <input type="text" id="g_input_outros_pos" class="other-input" placeholder="Detalhes da dúvida na Pós-Sessão...">
        </div>
    </div>

    <button class="btn-submit" onclick="enviarWebhook()">Enviar Dúvidas ao(à) Consultor(a)</button>
</div>

</body>
</html>
    """
    return html_template

# --- Funções de Envio de Registro ---

def send_sessao_to_chat(consultor, texto_mensagem):
    if not GOOGLE_CHAT_WEBHOOK_SESSAO: return False
    if not consultor or consultor == 'Selecione um nome': return False
    if not texto_mensagem: return False 

    chat_message = {'text': texto_mensagem}
    try:
        response = requests.post(GOOGLE_CHAT_WEBHOOK_SESSAO, json=chat_message)
        response.raise_for_status()
        return True
    except requests.exceptions.RequestException as e:
        print(f"Erro ao enviar mensagem de Sessão: {e}")
        return False

def load_logs(): 
    return st.session_state.get('daily_logs', []).copy()

def save_logs(l): 
    st.session_state.daily_logs = l

def log_status_change(consultor, old_status, new_status, duration):
    """Registra uma mudança de status na lista de logs da sessão."""
    print(f'LOG: {consultor} de "{old_status or "-"}" para "{new_status or "-"}" após {duration}')
    if not isinstance(duration, timedelta): duration = timedelta(0)

    entry = {
        'timestamp': datetime.now(),
        'consultor': consultor,
        'old_status': old_status, 
        'new_status': new_status,
        'duration': duration,
        'duration_s': duration.total_seconds()
    }
    st.session_state.daily_logs.append(entry)
    
    if consultor not in st.session_state.current_status_starts:
        st.session_state.current_status_starts[consultor] = datetime.now()
    st.session_state.current_status_starts[consultor] = datetime.now()


def format_time_duration(duration):
    """Formata um objeto timedelta para H:M:S."""
    if not isinstance(duration, timedelta): return '--:--:--'
    s = int(duration.total_seconds()); h, s = divmod(s, 3600); m, s = divmod(s, 60)
    return f'{h:02}:{m:02}:{s:02}'

def send_daily_report(): 
    """Agrega os logs e contagens e envia o relatório diário."""
    print("Iniciando envio do relatório diário...")
    
    logs = load_logs() 
    bastao_counts = st.session_state.bastao_counts.copy()
    
    aggregated_data = {nome: {} for nome in CONSULTORES}
    
    for log in logs:
        try:
            consultor = log['consultor']
            status = log['old_status']
            duration = log.get('duration', timedelta(0))
            
            if not isinstance(duration, timedelta):
                try: duration = timedelta(seconds=float(duration))
                except: duration = timedelta(0)

            if status and consultor in aggregated_data:
                current_duration = aggregated_data[consultor].get(status, timedelta(0))
                aggregated_data[consultor][status] = current_duration + duration
        except Exception as e:
            print(f"Erro ao processar log: {e} - Log: {log}")

    today_str = datetime.now().strftime("%d/%m/%Y")
    report_text = f"📊 **Relatório Diário de Atividades - {today_str}** 📊\n\n"
    
    consultores_com_dados = []

    for nome in CONSULTORES:
        counts = bastao_counts.get(nome, 0)
        times = aggregated_data.get(nome, {})
        bastao_time = times.get('Bastão', timedelta(0))
        
        if counts > 0 or times:
            consultores_com_dados.append(nome)
            # AQUI: MUDANÇA PARA O EMOJI DE ÁRVORE NO RELATÓRIO
            report_text += f"**👤 {nome}**\n"
            report_text += f"- {BASTAO_EMOJI} Bastão Recebido: **{counts}** vez(es)\n"
            report_text += f"- ⏱️ Tempo com Bastão: **{format_time_duration(bastao_time)}**\n"
            
            other_statuses = []
            sorted_times = sorted(times.items(), key=itemgetter(0)) 
            
            for status, time in sorted_times:
                if status != 'Bastão' and status:
                    other_statuses.append(f"{status}: **{format_time_duration(time)}**")
            
            if other_statuses:
                report_text += f"- ⏳ Outros Tempos: {', '.join(other_statuses)}\n\n"
            else:
                report_text += "\n"

    if not consultores_com_dados:
        report_text = f"📊 **Relatório Diário - {today_str}** 📊\n\nNenhuma atividade registrada hoje."

    if not GOOGLE_CHAT_WEBHOOK_BACKUP: return 

    chat_message = {'text': report_text}
    try:
        response = requests.post(GOOGLE_CHAT_WEBHOOK_BACKUP, json=chat_message)
        response.raise_for_status() 
        print("Relatório diário enviado com sucesso.")
        
        st.session_state['report_last_run_date'] = datetime.now()
        st.session_state['daily_logs'] = []
        st.session_state['bastao_counts'] = {nome: 0 for nome in CONSULTORES}
        save_state() 

    except requests.exceptions.RequestException as e:
        print(f'Erro ao enviar relatório diário: {e}')

def init_session_state():
    """Inicializa/sincroniza o st.session_state com o estado GLOBAL do cache."""
    persisted_state = load_state()
    
    defaults = {
        'bastao_start_time': None, 
        'report_last_run_date': datetime.min, 
        'rotation_gif_start_time': None,
        'play_sound': False,
        'gif_warning': False,
        'lunch_warning_info': None,
        'last_reg_status': None, 
        'chamado_guide_step': 0, 
        'sessao_msg_preview': "", 
        'html_download_ready': False, 
        'html_content_cache': "", 
        'auxilio_ativo': False,
        'show_activity_menu': False,
        'show_sessao_dialog': False # NOVO ESTADO
    }

    for key, default in defaults.items():
        if key in ['play_sound', 'gif_warning', 'last_reg_status', 'chamado_guide_step', 'sessao_msg_preview', 'html_download_ready', 'html_content_cache', 'show_activity_menu', 'show_sessao_dialog']: 
            st.session_state.setdefault(key, default)
        else: 
            st.session_state[key] = persisted_state.get(key, default)

    st.session_state['bastao_queue'] = persisted_state.get('bastao_queue', []).copy()
    st.session_state['priority_return_queue'] = persisted_state.get('priority_return_queue', []).copy()
    st.session_state['bastao_counts'] = persisted_state.get('bastao_counts', {}).copy()
    st.session_state['skip_flags'] = persisted_state.get('skip_flags', {}).copy()
    st.session_state['status_texto'] = persisted_state.get('status_texto', {}).copy()
    st.session_state['current_status_starts'] = persisted_state.get('current_status_starts', {}).copy()
    st.session_state['daily_logs'] = persisted_state.get('daily_logs', []).copy() 
    
    st.session_state['auxilio_ativo'] = persisted_state.get('auxilio_ativo', False)

    for nome in CONSULTORES:
        st.session_state.bastao_counts.setdefault(nome, 0)
        st.session_state.skip_flags.setdefault(nome, False)
        
        current_status = st.session_state.status_texto.get(nome, 'Indisponível') 
        st.session_state.status_texto.setdefault(nome, current_status)
        
        is_available = (current_status == 'Bastão' or current_status == '') and nome not in st.session_state.priority_return_queue
        st.session_state[f'check_{nome}'] = is_available
        
        if nome not in st.session_state.current_status_starts:
                 st.session_state.current_status_starts[nome] = datetime.now()

    checked_on = {c for c in CONSULTORES if st.session_state.get(f'check_{c}')}
    if not st.session_state.bastao_queue and checked_on:
        st.session_state.bastao_queue = sorted(list(checked_on))

    check_and_assume_baton()

def find_next_holder_index(current_index, queue, skips):
    """Encontra o próximo consultor elegível na fila."""
    if not queue: return -1
    num_consultores = len(queue)
    if num_consultores == 0: return -1
    if current_index >= num_consultores or current_index < -1: current_index = -1

    next_idx = (current_index + 1) % num_consultores
    attempts = 0
    while attempts < num_consultores:
        consultor = queue[next_idx]
        if not skips.get(consultor, False) and st.session_state.get(f'check_{consultor}'):
            return next_idx
        next_idx = (next_idx + 1) % num_consultores
        attempts += 1
    return -1


def check_and_assume_baton():
    """Verifica o estado do bastão e o atribui/remove conforme necessário."""
    queue = st.session_state.bastao_queue
    skips = st.session_state.skip_flags
    current_holder_status = next((c for c, s in st.session_state.status_texto.items() if s == 'Bastão'), None)
    is_current_valid = (current_holder_status
                        and current_holder_status in queue
                        and st.session_state.get(f'check_{current_holder_status}'))

    first_eligible_index = find_next_holder_index(-1, queue, skips)
    first_eligible_holder = queue[first_eligible_index] if first_eligible_index != -1 else None

    should_have_baton = None
    if is_current_valid:
        should_have_baton = current_holder_status
    elif first_eligible_holder:
        should_have_baton = first_eligible_holder

    changed = False
    previous_holder = current_holder_status 

    for c in CONSULTORES:
        if c != should_have_baton and st.session_state.status_texto.get(c) == 'Bastão':
            duration = datetime.now() - st.session_state.current_status_starts.get(c, datetime.now())
            log_status_change(c, 'Bastão', 'Indisponível', duration)
            st.session_state.status_texto[c] = 'Indisponível'
            changed = True

    if should_have_baton and st.session_state.status_texto.get(should_have_baton) != 'Bastão':
        old_status = st.session_state.status_texto.get(should_have_baton, '')
        duration = datetime.now() - st.session_state.current_status_starts.get(should_have_baton, datetime.now())
        log_status_change(should_have_baton, old_status, 'Bastão', duration)
        st.session_state.status_texto[should_have_baton] = 'Bastão'
        st.session_state.bastao_start_time = datetime.now()
        if previous_holder != should_have_baton: 
            st.session_state.play_sound = True 
            send_chat_notification_internal(should_have_baton, 'Bastão') 
        if st.session_state.skip_flags.get(should_have_baton):
            st.session_state.skip_flags[should_have_baton] = False
        changed = True
    elif not should_have_baton:
        if current_holder_status:
            duration = datetime.now() - st.session_state.current_status_starts.get(current_holder_status, datetime.now())
            log_status_change(current_holder_status, 'Bastão', 'Indisponível', duration)
            st.session_state.status_texto[current_holder_status] = 'Indisponível' 
            changed = True
        if st.session_state.bastao_start_time is not None: changed = True
        st.session_state.bastao_start_time = None

    if changed: 
        save_state()
    return changed

# ============================================
# 3. FUNÇÕES DE CALLBACK GLOBAIS
# ============================================

def update_queue(consultor):
    st.session_state.gif_warning = False; st.session_state.rotation_gif_start_time = None
    st.session_state.lunch_warning_info = None 
    
    is_checked = st.session_state.get(f'check_{consultor}') 
    old_status_text = st.session_state.status_texto.get(consultor, '')
    was_holder_before = consultor == next((c for c, s in st.session_state.status_texto.items() if s == 'Bastão'), None)
    duration = datetime.now() - st.session_state.current_status_starts.get(consultor, datetime.now())

    if is_checked: 
        log_status_change(consultor, old_status_text or 'Indisponível', '', duration)
        st.session_state.status_texto[consultor] = '' 
        if consultor not in st.session_state.bastao_queue:
            st.session_state.bastao_queue.append(consultor) 
        st.session_state.skip_flags[consultor] = False 
        if consultor in st.session_state.priority_return_queue:
            st.session_state.priority_return_queue.remove(consultor)
            
    else: 
        if old_status_text not in STATUSES_DE_SAIDA and old_status_text != 'Bastão':
            log_old_status = old_status_text or ('Bastão' if was_holder_before else 'Disponível')
            log_status_change(consultor, log_old_status , 'Indisponível', duration)
            st.session_state.status_texto[consultor] = 'Indisponível' 
        
        if consultor in st.session_state.bastao_queue:
            st.session_state.bastao_queue.remove(consultor)
        st.session_state.skip_flags.pop(consultor, None) 
        
    baton_changed = check_and_assume_baton() 
    if not baton_changed:
        save_state()

def rotate_bastao(): 
    selected = st.session_state.consultor_selectbox
    st.session_state.gif_warning = False; st.session_state.rotation_gif_start_time = None
    st.session_state.lunch_warning_info = None 

    if not selected or selected == 'Selecione um nome': st.warning('Selecione um(a) consultor(a).'); return
    queue = st.session_state.bastao_queue
    skips = st.session_state.skip_flags
    current_holder = next((c for c, s in st.session_state.status_texto.items() if s == 'Bastão'), None)
    if selected != current_holder:
        st.session_state.gif_warning = True
        return 

    current_index = -1
    try: current_index = queue.index(current_holder)
    except ValueError:
        if check_and_assume_baton(): pass 
        return

    # Tenta achar o próximo com as regras atuais
    next_idx = find_next_holder_index(current_index, queue, skips)
    
    should_reset_flags = False

    # --- LÓGICA DE CORREÇÃO PARA "TODOS PULANDO" ---
    if (next_idx != -1 and queue[next_idx] == current_holder) and len(queue) > 1:
        should_reset_flags = True

    if next_idx != -1:
        next_holder = queue[next_idx]
        duration = datetime.now() - (st.session_state.bastao_start_time or datetime.now())
        
        log_status_change(current_holder, 'Bastão', '', duration)
        st.session_state.status_texto[current_holder] = '' 
        
        log_status_change(next_holder, st.session_state.status_texto.get(next_holder, ''), 'Bastão', timedelta(0))
        st.session_state.status_texto[next_holder] = 'Bastão'
        
        st.session_state.bastao_start_time = datetime.now()
        st.session_state.skip_flags[next_holder] = False 
        
        st.session_state.bastao_counts[current_holder] = st.session_state.bastao_counts.get(current_holder, 0) + 1
        
        st.session_state.play_sound = True 
        st.session_state.rotation_gif_start_time = datetime.now()
        
        # --- APLICA O RESET SE NECESSÁRIO ---
        if should_reset_flags:
            print("Ciclo bloqueado por pulos. Resetando flags de todos.")
            for c in queue:
                st.session_state.skip_flags[c] = False
            st.toast("Todos pularam! O bastão retornou para você e a fila foi reiniciada.", icon="🔄")
        
        save_state()
    else:
        st.warning('Não há próximo(a) consultor(a) elegível na fila no momento.')
        check_and_assume_baton() 

def toggle_skip(): 
    selected = st.session_state.consultor_selectbox
    st.session_state.gif_warning = False; st.session_state.rotation_gif_start_time = None
    st.session_state.lunch_warning_info = None 

    if not selected or selected == 'Selecione um nome': st.warning('Selecione um(a) consultor(a).'); return
    if not st.session_state.get(f'check_{selected}'): st.warning(f'{selected} não está disponível para marcar/desmarcar.'); return

    current_skip_status = st.session_state.skip_flags.get(selected, False)
    st.session_state.skip_flags[selected] = not current_skip_status

    current_holder = next((c for c, s in st.session_state.status_texto.items() if s == 'Bastão'), None)
    if selected == current_holder and st.session_state.skip_flags[selected]:
        save_state() 
        rotate_bastao() 
        return 

    save_state() 

def update_status(status_text, change_to_available): 
    selected = st.session_state.consultor_selectbox
    st.session_state.gif_warning = False; st.session_state.rotation_gif_start_time = None
    if not selected or selected == 'Selecione um nome': 
        st.warning('Selecione um(a) consultor(a).')
        return

    if status_text != 'Almoço':
        st.session_state.lunch_warning_info = None
    
    current_lunch_warning = st.session_state.get('lunch_warning_info')
    is_second_try = False
    if current_lunch_warning and current_lunch_warning.get('consultor') == selected:
        elapsed = (datetime.now() - current_lunch_warning.get('start_time', datetime.min)).total_seconds()
        if elapsed < 30:
            is_second_try = True 

    if status_text == 'Almoço' and not is_second_try:
        all_statuses = st.session_state.status_texto
        num_na_fila = sum(1 for s in all_statuses.values() if s == '' or s == 'Bastão')
        num_atividade = sum(1 for s in all_statuses.values() if s == 'Atendimento') 
        total_ativos = num_na_fila + num_atividade
        num_almoco = sum(1 for s in all_statuses.values() if s == 'Almoço')
        limite_almoco = total_ativos / 2.0
        
        if total_ativos > 0 and num_almoco >= limite_almoco:
            st.session_state.lunch_warning_info = {
                'consultor': selected,
                'start_time': datetime.now(),
                'message': f'Consultor(a) {selected} verificar horário. Metade dos consultores ativos já em almoço. Clique novamente em "Almoço" para confirmar.'
            }
            save_state() 
            return 
            
    st.session_state.lunch_warning_info = None

    st.session_state[f'check_{selected}'] = False 
    was_holder = next((True for c, s in st.session_state.status_texto.items() if s == 'Bastão' and c == selected), False)
    old_status = st.session_state.status_texto.get(selected, '') or ('Bastão' if was_holder else 'Disponível')
    duration = datetime.now() - st.session_state.current_status_starts.get(selected, datetime.now())
    
    log_status_change(selected, old_status, status_text, duration)
    st.session_state.status_texto[selected] = status_text 

    if selected in st.session_state.bastao_queue: st.session_state.bastao_queue.remove(selected)
    st.session_state.skip_flags.pop(selected, None)

    if status_text == 'Saída rápida':
        if selected not in st.session_state.priority_return_queue: st.session_state.priority_return_queue.append(selected)
    elif selected in st.session_state.priority_return_queue: st.session_state.priority_return_queue.remove(selected)

    baton_changed = False
    if was_holder: 
        baton_changed = check_and_assume_baton() 
    
    if not baton_changed: 
        save_state() 

def manual_rerun():
    st.session_state.gif_warning = False; st.session_state.rotation_gif_start_time = None
    st.session_state.lunch_warning_info = None 
    st.rerun() 
    
def on_auxilio_change():
    save_state()

def handle_sessao_submission():
    consultor = st.session_state.consultor_selectbox
    texto_final = st.session_state.get("sessao_msg_preview", "")
    
    camara = st.session_state.get('sessao_camara_select', 'Não informada')
    data_obj = st.session_state.get('sessao_data_input')
    data_formatada = data_obj.strftime("%d/%m/%Y") if data_obj else 'Não informada'
    data_nome_arquivo = data_obj.strftime("%d-%m-%Y") if data_obj else 'SemData'
    
    # Envia a mensagem de texto da sessão
    success = send_sessao_to_chat(consultor, texto_final)
    
    if success:
        st.session_state.last_reg_status = "success_sessao"
        st.session_state.sessao_msg_preview = ""
        
        # Gera HTML e prepara download
        html_content = gerar_html_checklist(consultor, camara, data_formatada)
        st.session_state.html_content_cache = html_content
        st.session_state.html_download_ready = True
        st.session_state.html_filename = f"Checklist_{data_nome_arquivo}.html"
        
        st.session_state.registro_tipo_selecao = None
    else:
        st.session_state.last_reg_status = "error_sessao"
        st.session_state.html_download_ready = False

def set_chamado_step(step_num):
    st.session_state.chamado_guide_step = step_num

# ============================================
# 4. EXECUÇÃO PRINCIPAL DO STREAMLIT APP
# ============================================

st.set_page_config(page_title="Controle Bastão Cesupe", layout="wide")
init_session_state()

st.components.v1.html("<script>window.scrollTo(0, 0);</script>", height=0)

# Renderiza o efeito de neve
render_snow_effect()

st.markdown(
    f"""
    <div style="display: flex; align-items: center; gap: 10px;">
        <h1 style="margin-bottom: 0;">Controle Bastão Cesupe {BASTAO_EMOJI}</h1>
        <img src="{PUGNOEL_URL}" alt="Pug Noel" style="width: 120px; height: auto;">
    </div>
    """,
    unsafe_allow_html=True
)

st.markdown("<hr style='border: 1px solid #D42426;'>", unsafe_allow_html=True) 

gif_start_time = st.session_state.get('rotation_gif_start_time')
lunch_warning_info = st.session_state.get('lunch_warning_info') 

show_gif = False
show_lunch_warning = False
refresh_interval = 40000 

if gif_start_time:
    try:
        elapsed = (datetime.now() - gif_start_time).total_seconds()
        if elapsed < 20: 
            show_gif = True
            refresh_interval = 2000 
        else: 
            st.session_state.rotation_gif_start_time = None
            save_state() 
    except: 
        st.session_state.rotation_gif_start_time = None
        
if lunch_warning_info and lunch_warning_info.get('start_time'):
    try:
        elapsed_lunch = (datetime.now() - lunch_warning_info['start_time']).total_seconds()
        if elapsed_lunch < 30: 
            show_lunch_warning = True
            refresh_interval = 2000 
        else:
            st.session_state.lunch_warning_info = None 
            save_state() 
    except Exception as e:
        print(f"Erro ao processar timer do aviso de almoço: {e}")
        st.session_state.lunch_warning_info = None
        
st_autorefresh(interval=refresh_interval, key='auto_rerun_key') 

if st.session_state.get('play_sound', False):
    st.components.v1.html(play_sound_html(), height=0, width=0)
    st.session_state.play_sound = False 

if show_gif: st.image(GIF_URL_ROTATION, width=200, caption='Bastão Passado!')

if show_lunch_warning:
    st.warning(f"🔔 **{lunch_warning_info['message']}**")
    st.image(GIF_URL_LUNCH_WARNING, width=200)

if st.session_state.get('gif_warning', False):
    st.error('🚫 Ação inválida! Verifique as regras.'); st.image(GIF_URL_WARNING, width=150)

# Layout
col_principal, col_disponibilidade = st.columns([1.5, 1])
queue = st.session_state.bastao_queue
skips = st.session_state.skip_flags
responsavel = next((c for c, s in st.session_state.status_texto.items() if s == 'Bastão'), None)
current_index = queue.index(responsavel) if responsavel in queue else -1
proximo_index = find_next_holder_index(current_index, queue, skips)
proximo = queue[proximo_index] if proximo_index != -1 else None
restante = []
if proximo_index != -1: 
    num_q = len(queue)
    start_check_idx = (proximo_index + 1) % num_q
    current_check_idx = start_check_idx
    checked_count = 0
    while checked_count < num_q:
        if current_check_idx == start_check_idx and checked_count > 0: break
        if 0 <= current_check_idx < num_q:
            consultor = queue[current_check_idx]
            if consultor != responsavel and consultor != proximo and \
                not skips.get(consultor, False) and \
                st.session_state.get(f'check_{consultor}'):
                restante.append(consultor)
        current_check_idx = (current_check_idx + 1) % num_q
        checked_count += 1

# --- Coluna Principal ---
with col_principal:
    st.header("Responsável pelo Bastão")
    
    # --- VISUAL DO RESPONSÁVEL COM TARJA E GIF (TEMA VERMELHO) ---
    if responsavel:
        bg_color = "#FFEBEE" # Vermelho claro
        border_color = "#D42426" # Vermelho vibrante
        text_color = "#8B0000" # Vermelho escuro
        
        st.markdown(f"""
        <div style="
            background-color: {bg_color}; 
            border-left: 10px solid {border_color}; 
            padding: 20px; 
            border-radius: 8px; 
            display: flex; 
            align-items: center; 
            box-shadow: 0 4px 6px rgba(0,0,0,0.1);
            margin-bottom: 20px;">
            <div style="flex-shrink: 0; margin-right: 20px;">
                <img src="{GIF_BASTAO_HOLDER}" style="width: 80px; height: 80px; border-radius: 50%; object-fit: cover;">
            </div>
            <div>
                <span style="font-size: 14px; color: #555; font-weight: bold; text-transform: uppercase; letter-spacing: 1px;">Atualmente com:</span><br>
                <span style="font-size: 42px; font-weight: 800; color: {text_color}; line-height: 1.1;">{responsavel}</span>
            </div>
        </div>
        """, unsafe_allow_html=True)
        
        duration = timedelta()
        if st.session_state.bastao_start_time:
             try: duration = datetime.now() - st.session_state.bastao_start_time
             except: pass
        st.caption(f"⏱️ Tempo com o bastão: **{format_time_duration(duration)}**")
        
    else: 
        st.markdown('<h2>(Ninguém com o bastão)</h2>', unsafe_allow_html=True)
    st.markdown("###")

    st.header("Próximos da Fila")
    if proximo:
        st.markdown(f'### 1º: **{proximo}**')
    if restante:
        st.markdown(f'#### 2º em diante: {", ".join(restante)}')
    if not proximo and not restante:
        if responsavel: st.markdown('*Apenas o responsável atual é elegível.*')
        elif queue and all(skips.get(c, False) or not st.session_state.get(f'check_{c}') for c in queue) : st.markdown('*Todos disponíveis estão marcados para pular...*')
        else: st.markdown('*Ninguém elegível na fila.*')
    elif not restante and proximo: st.markdown("&nbsp;")


    skipped_consultants = [c for c, is_skipped in skips.items() if is_skipped and st.session_state.get(f'check_{c}')]
    if skipped_consultants:
        skipped_text = ', '.join(sorted(skipped_consultants))
        num_skipped = len(skipped_consultants)
        titulo = '**Consultor(a) Pulou:**' if num_skipped == 1 else '**Consultores(as) Pularam:**'
        verbo_pular = 'pulou' if num_skipped == 1 else 'pularam'
        verbo_retornar = 'Irá retornar' if num_skipped == 1 else 'Irão retornar'
        st.markdown(f'''
        <div style="margin-top: 15px;">
            <span style="color: #FFC107; font-weight: bold;">{titulo}</span><br>
            <span style="color: black; font-weight: normal;">{skipped_text} {verbo_pular} o bastão!</span><br>
            <span style="color: black; font-weight: normal;">{verbo_retornar} no próximo ciclo!</span>
        </div>
        ''', unsafe_allow_html=True)

    st.markdown("###")
    st.header("**Consultor(a)**")
    st.selectbox('Selecione:', options=['Selecione um nome'] + CONSULTORES, key='consultor_selectbox', label_visibility='collapsed')
    st.markdown("#### "); st.markdown("**Ações:**")
    
    # --- MENUS DE AÇÃO (COLUNAS CORRIGIDAS) ---
    if 'show_activity_menu' not in st.session_state:
        st.session_state.show_activity_menu = False
    
    if 'show_sessao_dialog' not in st.session_state:
        st.session_state.show_sessao_dialog = False

    def open_activity_menu():
        st.session_state.show_activity_menu = True
        st.session_state.show_sessao_dialog = False
        
    def open_sessao_dialog():
        st.session_state.show_sessao_dialog = True
        st.session_state.show_activity_menu = False
    
    # 7 COLUNAS AGORA
    c1, c2, c3, c4, c5, c6, c7 = st.columns(7) 
    
    c1.button('🎯 Passar', on_click=rotate_bastao, use_container_width=True, help='Passa o bastão.')
    c2.button('⏭️ Pular', on_click=toggle_skip, use_container_width=True, help='Pular vez.')
    c3.button('📋 Atividades', on_click=open_activity_menu, use_container_width=True)
    c4.button('🍽️ Almoço', on_click=update_status, args=('Almoço', False,), use_container_width=True)
    c5.button('👤 Ausente', on_click=update_status, args=('Ausente', False,), use_container_width=True)
    c6.button('🎙️ Sessão', on_click=open_sessao_dialog, use_container_width=True)
    c7.button('🚶 Saída rápida', on_click=update_status, args=('Saída rápida', False,), use_container_width=True)
    
    # --- CONTAINER DO MENU DE ATIVIDADES ---
    if st.session_state.show_activity_menu:
        with st.container(border=True):
            st.markdown("### Selecione a Atividade")
            # MUDANÇA AQUI: MULTISELECT
            atividades_escolhidas = st.multiselect("Tipo:", OPCOES_ATIVIDADES_STATUS)
            
            texto_extra = ""
            if "Outros" in atividades_escolhidas:
                texto_extra = st.text_input("Descreva a atividade 'Outros':", placeholder="Ex: Ajuste técnico...")
            
            col_confirm_1, col_confirm_2 = st.columns(2)
            with col_confirm_1:
                if st.button("Confirmar Atividade", type="primary", use_container_width=True):
                    if atividades_escolhidas:
                        # Concatena as escolhas
                        str_atividades = ", ".join(atividades_escolhidas)
                        status_final = f"Atividade: {str_atividades}"
                        
                        if "Outros" in atividades_escolhidas and texto_extra:
                            status_final += f" - {texto_extra}"
                        
                        update_status(status_final, False)
                        st.session_state.show_activity_menu = False 
                        st.rerun()
                    else:
                        st.warning("Selecione pelo menos uma atividade.")
            
            with col_confirm_2:
                if st.button("Cancelar", use_container_width=True, key='cancel_act'):
                    st.session_state.show_activity_menu = False
                    st.rerun()

    # --- CONTAINER DO MENU DE SESSÃO (NOVO) ---
    if st.session_state.show_sessao_dialog:
        with st.container(border=True):
            st.markdown("### Informar Sessão")
            sessao_input = st.text_input("Qual sessão?", placeholder="Ex: 1ª Câmara Cível")
            
            col_sess_1, col_sess_2 = st.columns(2)
            with col_sess_1:
                if st.button("Confirmar Sessão", type="primary", use_container_width=True):
                    if sessao_input.strip():
                        status_final = f"Sessão: {sessao_input}"
                        update_status(status_final, False)
                        st.session_state.show_sessao_dialog = False
                        st.rerun()
                    else:
                        st.warning("Digite o nome da sessão.")
            
            with col_sess_2:
                if st.button("Cancelar", use_container_width=True, key='cancel_sess'):
                    st.session_state.show_sessao_dialog = False
                    st.rerun()
    
    st.markdown("####")
    st.button('🔄 Atualizar (Manual)', on_click=manual_rerun, use_container_width=True)
    
    # --- SEÇÃO "REGISTROS" REMOVIDA DAQUI ---
    
    # --- Bloco Padrão Abertura de Chamados (Mantido) ---
    st.markdown("---")
    st.header("Padrão abertura de chamados / jiras")

    guide_step = st.session_state.get('chamado_guide_step', 0)

    if guide_step == 0:
        st.button("Gerar prévia", on_click=set_chamado_step, args=(1,), use_container_width=True)
    else:
        with st.container(border=True):
            if guide_step == 1:
                st.subheader("📄 Resumo e Passo 1: Testes Iniciais")
                st.markdown("""
                O processo de abertura de chamados segue uma padronização dividida em três etapas principais:
                
                **PASSO 1: Testes Iniciais**
                
                Antes de abrir o chamado, o consultor(a) deve primeiro realizar os procedimentos de suporte e testes necessários para **verificar e confirmar o problema** que foi relatado pelo usuário.
                """)
                st.button("Próximo (Passo 2) ➡️", on_click=set_chamado_step, args=(2,))
            
            elif guide_step == 2:
                st.subheader("PASSO 2: Checklist de Abertura e Descrição")
                st.markdown("""
                Ao abrir o chamado, é obrigatório preencher um checklist com informações detalhadas para descrever a situação.
                
                **1. Dados do Usuário Envolvido**
                * Nome completo
                * Matrícula
                * Tipo/perfil do usuário
                * Número de telefone (celular ou ramal com prefixo)
                
                **2. Dados do Processo (Se aplicável)**
                * Número(s) completo(s) do(s) processo(s) afetados
                * Classe do(s) processo(s) afetados
                
                **3. Descrição do Erro**
                * Descrever o **passo a passo exato** que levou ao erro.
                * Indicar a data e o horário em que o erro ocorreu e qual a sua frequência (incidência).
                
                **4. Prints de Tela ou Vídeo**
                * Anexar imagens do erro apresentado nos sistemas (SIAP, THEMIS, JPE, EPROC).
                * Especificamente para o **THEMIS**, incluir um print da tela do **TOOLS** mostrando o log de erro.
                
                **5. Descrição dos Testes Realizados**
                * Descrever todos os testes que foram feitos (ex: teste em outra máquina, com outro usuário, em outro processo).
                * Informar se foi tentada alguma alternativa para contornar o erro e qual foi o resultado dessa tentativa.
                
                **6. Soluções de Contorno (Se houver)**
                * Descrever qual solução de contorno foi utilizada para resolver o problema temporariamente.
                
                **7. Identificação do(a) Consultor(a)**
                * Inserir a assinatura e identificação do(a) consultor(a).
                """)
                st.button("Próximo (Passo 3) ➡️", on_click=set_chamado_step, args=(3,))
                
            elif guide_step == 3:
                st.subheader("PASSO 3: Registrar e Informar o Usuário por E-mail")
                st.markdown("""
                Após a abertura do chamado, o consultor(a) deve enviar um e-mail ao usuário (serventuário) informando que:
                
                * A questão é de competência do setor de Informática do TJMG.
                * Um chamado ($n^{\circ}$ CH) foi aberto junto ao referido departamento.
                * O departamento de informática realizará as verificações e tomará as providências necessárias.
                * O usuário deve aguardar, e o consultor(a) entrará em contato assim que receber um feedback do departamento com as orientações.
                """)
                st.button("Próximo (Observações) ➡️", on_click=set_chamado_step, args=(4,))
                
            elif guide_step == 4:
                st.subheader("Observações Gerais Importantes")
                st.markdown("""
                * **Comunicação:** O envio de qualquer informação ou documento para setores ou usuários deve ser feito apenas para o **e-mail institucional oficial**.
                * **Atualização:** A atualização das informações sobre o andamento deve ser feita no **IN**.
                * **Controle:** Cada consultor(a) é **responsável por ter seu próprio controle** dos chamados que abriu, atualizá-los quando necessário e orientar o usuário.
                """)
                st.button("Entendi! Abrir campo de digitação ➡️", on_click=set_chamado_step, args=(5,))
                
            elif guide_step == 5:
                st.subheader("Campo de Digitação do Chamado")
                st.markdown("Utilize o campo abaixo para rascunhar seu chamado, seguindo o padrão lido. Você pode copiar e colar o texto daqui.")
                st.text_area(
                    "Rascunho do Chamado:", 
                    height=300, 
                    key="chamado_textarea", 
                    label_visibility="collapsed"
                )
                
                col_btn_1, col_btn_2 = st.columns(2)
                with col_btn_1:
                    st.button(
                        "Enviar Rascunho", 
                        on_click=handle_chamado_submission, 
                        use_container_width=True,
                        type="primary"
                    )
                with col_btn_2:
                    st.button(
                        "Cancelar", 
                        on_click=set_chamado_step, 
                        args=(0,), 
                        use_container_width=True
                    )


# --- Coluna Disponibilidade ---
with col_disponibilidade:
    st.markdown("###")
    
    st.toggle(
        "Auxílio HP/Emails/Whatsapp", 
        key='auxilio_ativo', 
        on_change=on_auxilio_change
    )
    
    if st.session_state.get('auxilio_ativo'):
        st.warning("HP/Emails/Whatsapp irão para bastão")
        st.image(GIF_URL_NEDRY, width=300)
    
    st.markdown("---")

    st.header('Status dos(as) Consultores(as)')
    st.markdown('Marque/Desmarque para entrar/sair.')
    
    # ----------------------------------------------------
    # LISTAS DO PAINEL DIREITO (ORGANIZADAS)
    # ----------------------------------------------------
    ui_lists = {'fila': [], 'almoco': [], 'saida': [], 'ausente': [], 'atividade_especifica': [], 'sessao_especifica': [], 'indisponivel': []} 
    
    for nome in CONSULTORES:
        is_checked = st.session_state.get(f'check_{nome}', False)
        status = st.session_state.status_texto.get(nome, 'Indisponível')
        
        if status == 'Bastão': ui_lists['fila'].insert(0, nome)
        elif status == '': ui_lists['fila'].append(nome)
        elif status == 'Almoço': ui_lists['almoco'].append(nome)
        elif status == 'Ausente': ui_lists['ausente'].append(nome)
        elif status == 'Saída rápida': ui_lists['saida'].append(nome)
        
        # SESSÃO
        elif status.startswith('Sessão'):
            # Remove "Sessão: " para exibir só o nome da câmara
            clean_status = status.replace('Sessão: ', '')
            ui_lists['sessao_especifica'].append((nome, clean_status))

        # ATIVIDADES (Demanda)
        elif status.startswith('Atividade') or status == 'Atendimento': 
            if status == 'Atendimento':
                ui_lists['atividade_especifica'].append((nome, "Atendimento"))
            else:
                clean_status = status.replace('Atividade: ', '')
                ui_lists['atividade_especifica'].append((nome, clean_status))
                
        elif status == 'Indisponível': ui_lists['indisponivel'].append(nome)
        else: ui_lists['indisponivel'].append(nome)

    st.subheader(f'✅ Na Fila ({len(ui_lists["fila"])})')
    render_order = [c for c in queue if c in ui_lists['fila']] + [c for c in ui_lists['fila'] if c not in queue]
    if not render_order: st.markdown('_Ninguém disponível._')
    else:
        for nome in render_order:
            col_nome, col_check = st.columns([0.8, 0.2])
            key = f'check_{nome}'
            
            col_check.checkbox(' ', key=key, on_change=update_queue, args=(nome,), label_visibility='collapsed')
            
            skip_flag = skips.get(nome, False)
            if nome == responsavel:
                # TAG VERMELHA PARA O RESPONSÁVEL
                display = f'<span style="background-color: #D42426; color: white; padding: 2px 6px; border-radius: 5px; font-weight: bold;">🔥 {nome}</span>'
            elif skip_flag:
                display = f'**{nome}** :orange-background[Pulando ⏭️]'
            else:
                # TAG VERMELHA PARA AGUARDANDO
                display = f'**{nome}** :red-background[Aguardando]'
            col_nome.markdown(display, unsafe_allow_html=True)
    st.markdown('---')

    def render_section(title, icon, names, tag_color):
        st.subheader(f'{icon} {title} ({len(names)})')
        if not names: st.markdown(f'_Ninguém em {title.lower()}._')
        else:
            for nome in sorted(names):
                col_nome, col_check = st.columns([0.8, 0.2])
                key = f'check_{nome}'
                col_check.checkbox(' ', key=key, value=False, on_change=update_queue, args=(nome,), label_visibility='collapsed')
                col_nome.markdown(f'**{nome}** :{tag_color}-background[{title}]', unsafe_allow_html=True)
        st.markdown('---')

    # 1. EM DEMANDA (Antigo Atividades/Atendimento)
    st.subheader(f'📋 Em Demanda ({len(ui_lists["atividade_especifica"])})')
    if not ui_lists['atividade_especifica']: 
        st.markdown('_Ninguém em demanda._')
    else:
        for nome, status_desc in sorted(ui_lists['atividade_especifica'], key=lambda x: x[0]):
            col_nome, col_check = st.columns([0.8, 0.2])
            col_check.checkbox(' ', key=f'check_{nome}', value=False, on_change=update_queue, args=(nome,), label_visibility='collapsed')
            col_nome.markdown(f'**{nome}** :orange-background[{status_desc}]', unsafe_allow_html=True)
    st.markdown('---')

    # 2. ALMOÇO - Agora com tag vermelha
    render_section('Almoço', '🍽️', ui_lists['almoco'], 'red')

    # 3. SESSÃO
    st.subheader(f'🎙️ Sessão ({len(ui_lists["sessao_especifica"])})')
    if not ui_lists['sessao_especifica']: 
        st.markdown('_Ninguém em sessão._')
    else:
        for nome, status_desc in sorted(ui_lists['sessao_especifica'], key=lambda x: x[0]):
            col_nome, col_check = st.columns([0.8, 0.2])
            col_check.checkbox(' ', key=f'check_{nome}', value=False, on_change=update_queue, args=(nome,), label_visibility='collapsed')
            col_nome.markdown(f'**{nome}** :green-background[{status_desc}]', unsafe_allow_html=True)
    st.markdown('---')

    # 4. SAÍDA RÁPIDA
    render_section('Saída rápida', '🚶', ui_lists['saida'], 'red')

    # 5. AUSENTES
    render_section('Ausente', '👤', ui_lists['ausente'], 'violet') 
    
    # 6. INDISPONÍVEL
    render_section('Indisponível', '❌', ui_lists['indisponivel'], 'grey')

# --- Lógica de Relatório Diário ---
now = datetime.now()
last_run_date = st.session_state.report_last_run_date.date() if isinstance(st.session_state.report_last_run_date, datetime) else datetime.min.date()

if now.hour >= 20 and now.date() > last_run_date:
    print(f"TRIGGER: Enviando relatório diário. Agora: {now}, Última Execução: {st.session_state.report_last_run_date}")
    send_daily_report()
