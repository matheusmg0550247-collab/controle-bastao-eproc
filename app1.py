# ============================================
# 1. IMPORTS E DEFINIÇÕES GLOBAIS
# ============================================
import streamlit as st
import pandas as pd
import requests
from datetime import datetime, timedelta, date, time
from operator import itemgetter
from streamlit_autorefresh import st_autorefresh
import json # Usado para serialização de logs

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
        'daily_logs': [] # Log persistente para o relatório
    }

# --- Constantes ---
GOOGLE_CHAT_WEBHOOK_BACKUP = "https://chat.googleapis.com/v1/spaces/AAQA0V8TAhs/messages?key=AIzaSyDdI0hCZtE6vySjMm-WEfRq3CPzqKqqsHI&token=Zl7KMv0PLrm5c7IMZZdaclfYoc-je9ilDDAlDfqDMAU"
CHAT_WEBHOOK_BASTAO = "" 

# -- Constantes de Registro de Atividade --
GOOGLE_CHAT_WEBHOOK_REGISTRO = "https://chat.googleapis.com/v1/spaces/AAQAVvsU4Lg/messages?key=AIzaSyDdI0hCZtE6vySjMm-WEfRq3CPzqKqqsHI&token=hSghjEZq8-1EmlfHdSoPRq_nTSpYc0usCs23RJOD-yk"

# Webhook para Rascunho de Chamados
GOOGLE_CHAT_WEBHOOK_CHAMADO = "https://chat.googleapis.com/v1/spaces/AAQAPPWlpW8/messages?key=AIzaSyDdI0hCZtE6vySjMm-WEfRq3CPzqKqqsHI&token=jMg2PkqtpIe3JbG_SZG_ZhcfuQQII9RXM0rZQienUZk"

# Formulário "Atividade"
REG_USUARIO_OPCOES = ["Cartório", "Externo", "Gabinete", "Interno"]
REG_SISTEMA_OPCOES = ["Conveniados/Outros", "Eproc", "Themis", "JIPE", "SIAP"]
REG_CANAL_OPCOES = ["Email", "Telefone", "Whatsapp"]
REG_DESFECHO_OPCOES = ["Escalonado", "Resolvido - Cesupe"]
# Formulário "Presencial"
REG_PRESENCIAL_ATIVIDADE_OPCOES = ["Sessão", "Homologação", "Treinamento", "Chamado/Jira", "Atendimento", "Outros"]

BASTAO_EMOJI = "💙" 
APP_URL_CLOUD = 'https://controle-bastao-cesupe.streamlit.app'
STATUS_SAIDA_PRIORIDADE = ['Saída Temporária']
STATUSES_DE_SAIDA = ['Atendimento', 'Almoço', 'Saída Temporária', 'Ausente', 'Sessão'] # MODIFICADO: 'Atividade' para 'Atendimento'
GIF_URL_WARNING = 'https://media0.giphy.com/media/v1.Y2lkPTc5MGI3NjExY2pjMDN0NGlvdXp1aHZ1ejJqMnY5MG1yZmN0d3NqcDl1bTU1dDJrciZlcD12MV9pbnRlcm5uYWxfZ2lmX2J5X2lkJmN0PWc/fXnRObM8Q0RkOmR5nf/giphy.gif'
GIF_URL_ROTATION = 'https://media0.giphy.com/media/v1.Y2lkPTc5MGI3NjExdmx4azVxbGt4Mnk1cjMzZm5sMmp1YThteGJsMzcyYmhsdmFoczV0aSZlcD12MV9pbnRlcm5uYWxfZ2lmX2J5X2lkJmN0PWc/JpkZEKWY0s9QI4DGvF/giphy.gif'
GIF_URL_LUNCH_WARNING = 'https://media3.giphy.com/media/v1.Y2lkPTc5MGI3NjExMGZlbHN1azB3b2drdTI1eG10cDEzeWpmcmtwenZxNTV0bnc2OWgzZSYlcD12MV9pbnRlcm5uYWxfZ2lmX2J5X2lkJmN0PWc/bNlqpmBJRDMpxulfFB/giphy.gif'
SOUND_URL = "https://github.com/matheusmg0550247-collab/controle-bastao-eproc2/raw/main/doorbell-223669.mp3"
# URL da Imagem Novembro Azul
NOVEMBRO_AZUL_URL = "https://github.com/matheusmg0550247-collab/controle-bastao-eproc2/raw/main/novembro-azul.png"

# ============================================
# 2. FUNÇÕES AUXILIARES GLOBAIS
# ============================================

def date_serializer(obj):
    """Serializador para objetos datetime (usado em logs)."""
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
        
        global_data['daily_logs'] = json.loads(json.dumps(st.session_state.daily_logs, default=date_serializer))
        
        print(f'*** Estado GLOBAL Salvo (Cache de Recurso) ***')
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
    """Envia notificação de giro do bastão (não o relatório)."""
    if CHAT_WEBHOOK_BASTAO and status == 'Bastão':
        message_template = "🎉 **BASTÃO GIRADO!** 🎉 \n\n- **Novo Responsável:** {consultor}\n- **Acesse o Painel:** {app_url}"
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

# --- Funções de Envio de Registro ---

def send_atividade_to_chat(consultor, tipo_atendimento, form_data): # MODIFICADO: Nome da função de Atividade para Atendimento
    """Envia o registro de 'Atendimento' para o webhook do Google Chat."""
    if not GOOGLE_CHAT_WEBHOOK_REGISTRO:
        print("Webhook de registro não configurado.")
        return False

    if not consultor or consultor == 'Selecione um nome':
        print("Erro de registro: Consultor não selecionado.")
        return False

    message_text = (
        f"**📋 Novo Registro de Atendimento**\n\n"
        f"**Consultor:** {consultor}\n"
        f"**Tipo:** {tipo_atendimento}\n"
        f"**Usuário:** {form_data['usuario']}\n"
        f"**Nome/Setor:** {form_data['nome_setor']}\n"
        f"**Sistema:** {form_data['sistema']}\n"
        f"**Canal:** {form_data['canal']}\n"
        f"**Desfecho:** {form_data['desfecho']}\n"
        f"**Descrição:** {form_data['descricao']}\n"
    )
    
    chat_message = {'text': message_text}
    try:
        response = requests.post(GOOGLE_CHAT_WEBHOOK_REGISTRO, json=chat_message)
        response.raise_for_status()
        print("Registro de 'Atendimento' enviado com sucesso.")
        return True
    except requests.exceptions.RequestException as e:
        print(f"Erro ao enviar registro de 'Atendimento': {e}")
        return False

def send_presencial_to_chat(consultor, form_data): # MODIFICADO: Nome da função de Presencial para Atividade
    """Envia o registro de 'Atividade' para o webhook do Google Chat."""
    if not GOOGLE_CHAT_WEBHOOK_REGISTRO:
        print("Webhook de registro não configurado.")
        return False

    if not consultor or consultor == 'Selecione um nome':
        print("Erro de registro: Consultor não selecionado.")
        return False

    # Formata a data e horas
    data_str = form_data['data'].strftime("%d/%m/%Y")
    inicio_str = form_data['inicio'].strftime("%H:%M")
    fim_str = form_data['fim'].strftime("%H:%M")

    message_text = (
        f"**📅 Novo Registro de Atividade**\n\n" # MODIFICADO: 'Presencial' para 'Atividade'
        f"**Consultor:** {consultor}\n"
        f"**Atividade:** {form_data['atividade']}\n"
        f"**Data:** {data_str}\n"
        f"**Início:** {inicio_str}\n"
        f"**Fim:** {fim_str}\n"
        f"**Descrição:** {form_data['descricao']}\n"
        f"**Participantes Cesupe:** {form_data['particip_cesupe']}\n"
        f"**Participantes Externos:** {form_data['particip_externos']}\n"
    )
    
    chat_message = {'text': message_text}
    try:
        response = requests.post(GOOGLE_CHAT_WEBHOOK_REGISTRO, json=chat_message)
        response.raise_for_status()
        print("Registro de 'Atividade' enviado com sucesso.") # MODIFICADO: 'Presencial' para 'Atividade'
        return True
    except requests.exceptions.RequestException as e:
        print(f"Erro ao enviar registro de 'Atividade': {e}") # MODIFICADO: 'Presencial' para 'Atividade'
        return False

def send_chamado_to_chat(consultor, texto_chamado):
    """Envia o rascunho do chamado para o webhook específico."""
    if not GOOGLE_CHAT_WEBHOOK_CHAMADO:
        print("Webhook de chamado não configurado.")
        return False

    if not consultor or consultor == 'Selecione um nome':
        print("Erro de registro de chamado: Consultor não selecionado.")
        return False
        
    if not texto_chamado:
        print("Erro de registro de chamado: Texto do chamado está vazio.")
        return False # Não envia rascunho vazio

    message_text = (
        f"**🔔 Novo Rascunho de Chamado/Jira**\n\n"
        f"**Consultor:** {consultor}\n"
        f"--- (Início do Rascunho) ---\n"
        f"{texto_chamado}\n"
        f"--- (Fim do Rascunho) ---"
    )
    
    chat_message = {'text': message_text}
    try:
        response = requests.post(GOOGLE_CHAT_WEBHOOK_CHAMADO, json=chat_message)
        response.raise_for_status()
        print("Rascunho de chamado enviado com sucesso.")
        return True
    except requests.exceptions.RequestException as e:
        print(f"Erro ao enviar rascunho de chamado: {e}")
        return False


def load_logs(): 
    """Carrega logs do st.session_state local."""
    return st.session_state.get('daily_logs', []).copy()

def save_logs(l): 
    """Salva logs no st.session_state local."""
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
            report_text += f"**👤 {nome}**\n"
            report_text += f"- 💙 Bastão Recebido: **{counts}** vez(es)\n"
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
        print("Relatório diário não enviado: Sem dados de atividade hoje.")
        report_text = f"📊 **Relatório Diário - {today_str}** 📊\n\nNenhuma atividade registrada hoje."

    if not GOOGLE_CHAT_WEBHOOK_BACKUP:
        print("Webhook de backup não configurado. Relatório não enviado.")
        return 

    chat_message = {'text': report_text}
    print(f"Enviando relatório diário para o webhook...")
    
    try:
        response = requests.post(GOOGLE_CHAT_WEBHOOK_BACKUP, json=chat_message)
        response.raise_for_status() 
        
        print("Relatório diário enviado com sucesso.")
        
        st.session_state['report_last_run_date'] = datetime.now()
        st.session_state['daily_logs'] = []
        st.session_state['bastao_counts'] = {nome: 0 for nome in CONSULTORES}
        
        print("Logs diários e contagens de bastão foram resetados.")
        save_state() 

    except requests.exceptions.RequestException as e:
        print(f'Erro ao enviar relatório diário: {e}')
        if e.response is not None:
            print(f'Status: {e.response.status_code}, Resposta: {e.response.text}')

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
        'last_reg_status': None, # Flag para status de registro
        'chamado_guide_step': 0 # Etapa do guia de chamados
    }

    for key, default in defaults.items():
        if key in ['play_sound', 'gif_warning', 'last_reg_status', 'chamado_guide_step']: 
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
        print('!!! Fila vazia na carga, reconstruindo !!!')
        st.session_state.bastao_queue = sorted(list(checked_on))

    check_and_assume_baton()
    print('--- Estado Sincronizado (GLOBAL -> LOCAL) ---')

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
    print("AVISO: find_next_holder_index não encontrou ninguém elegível.")
    return -1


def check_and_assume_baton():
    """Verifica o estado do bastão e o atribui/remove conforme necessário."""
    print('--- VERIFICA E ASSUME BASTÃO ---')
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
            print(f'Limpando bastão de {c} (não deveria ter)')
            duration = datetime.now() - st.session_state.current_status_starts.get(c, datetime.now())
            log_status_change(c, 'Bastão', 'Indisponível', duration)
            st.session_state.status_texto[c] = 'Indisponível'
            changed = True

    if should_have_baton and st.session_state.status_texto.get(should_have_baton) != 'Bastão':
        print(f'Atribuindo bastão para {should_have_baton}')
        old_status = st.session_state.status_texto.get(should_have_baton, '')
        duration = datetime.now() - st.session_state.current_status_starts.get(should_have_baton, datetime.now())
        log_status_change(should_have_baton, old_status, 'Bastão', duration)
        st.session_state.status_texto[should_have_baton] = 'Bastão'
        st.session_state.bastao_start_time = datetime.now()
        if previous_holder != should_have_baton: 
            st.session_state.play_sound = True 
            print("SOUND TRIGGER: check_and_assume_baton assigned baton.")
            send_chat_notification_internal(should_have_baton, 'Bastão') 
        if st.session_state.skip_flags.get(should_have_baton):
            print(f' Consumindo skip flag de {should_have_baton} ao assumir.')
            st.session_state.skip_flags[should_have_baton] = False
        changed = True
    elif not should_have_baton:
        if current_holder_status:
            print(f'Ninguém elegível, limpando bastão de {current_holder_status}')
            duration = datetime.now() - st.session_state.current_status_starts.get(current_holder_status, datetime.now())
            log_status_change(current_holder_status, 'Bastão', 'Indisponível', duration)
            st.session_state.status_texto[current_holder_status] = 'Indisponível' 
            changed = True
        if st.session_state.bastao_start_time is not None: changed = True
        st.session_state.bastao_start_time = None

    if changed: 
        print('Estado do bastão mudou. Salvando GLOBAL.')
        save_state()
    return changed

# ============================================
# 3. FUNÇÕES DE CALLBACK GLOBAIS
# ============================================

def update_queue(consultor):
    """Callback: Checkbox de disponibilidade (entrar/sair da fila)."""
    print(f'CALLBACK UPDATE QUEUE: {consultor}')
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
            print(f'Adicionado {consultor} ao fim da fila.')
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
            print(f'Removido {consultor} da fila.')
        st.session_state.skip_flags.pop(consultor, None) 
        
    baton_changed = check_and_assume_baton() 
    if not baton_changed:
        save_state()

def rotate_bastao(): 
    """Callback: Botão 'Passar'."""
    print('CALLBACK ROTATE BASTAO (PASSAR)')
    selected = st.session_state.consultor_selectbox
    st.session_state.gif_warning = False; st.session_state.rotation_gif_start_time = None
    st.session_state.lunch_warning_info = None 

    if not selected or selected == 'Selecione um nome': st.warning('Selecione um consultor.'); return
    queue = st.session_state.bastao_queue
    skips = st.session_state.skip_flags
    current_holder = next((c for c, s in st.session_state.status_texto.items() if s == 'Bastão'), None)
    if selected != current_holder:
        st.session_state.gif_warning = True
        return 

    current_index = -1
    try: current_index = queue.index(current_holder)
    except ValueError:
        st.warning(f'Erro interno: Portador {current_holder} não encontrado na fila. Tentando corrigir.')
        if check_and_assume_baton(): pass 
        return

    reset_triggered = False
    first_eligible_index_overall = find_next_holder_index(-1, queue, skips) 
    potential_next_index = find_next_holder_index(current_index, queue, skips)

    if potential_next_index != -1 and first_eligible_index_overall != -1:
        first_eligible_holder_overall = queue[first_eligible_index_overall]
        potential_next_holder = queue[potential_next_index]

        if potential_next_holder == first_eligible_holder_overall and current_holder != first_eligible_holder_overall:
            print("--- RESETANDO CICLO (Detectado ao passar para o primeiro elegível) ---")
            st.session_state.skip_flags = {c: False for c in CONSULTORES if st.session_state.get(f'check_{c}')}
            skips = st.session_state.skip_flags 
            reset_triggered = True
            next_index = first_eligible_index_overall 
        else:
            next_index = potential_next_index
    else:
        next_index = -1

    if next_index != -1:
        next_holder = queue[next_index]
        print(f'Passando bastão de {current_holder} para {next_holder} (Reset Triggered: {reset_triggered})')
        duration = datetime.now() - (st.session_state.bastao_start_time or datetime.now())
        
        log_status_change(current_holder, 'Bastão', '', duration)
        st.session_state.status_texto[current_holder] = '' 
        
        log_status_change(next_holder, st.session_state.status_texto.get(next_holder, ''), 'Bastão', timedelta(0))
        st.session_state.status_texto[next_holder] = 'Bastão'
        
        st.session_state.bastao_start_time = datetime.now()
        st.session_state.skip_flags[next_holder] = False 
        
        st.session_state.bastao_counts[current_holder] = st.session_state.bastao_counts.get(current_holder, 0) + 1
        
        st.session_state.play_sound = True 
        print("SOUND TRIGGER: rotate_bastao successful.")
        st.session_state.rotation_gif_start_time = datetime.now()
        
        save_state()
    else:
        print('Ninguém elegível. Forçando re-check e mantendo estado atual.')
        st.warning('Não há próximo consultor elegível na fila no momento.')
        check_and_assume_baton() 

def toggle_skip(): 
    """Callback: Botão 'Pular'."""
    print('CALLBACK TOGGLE SKIP')
    selected = st.session_state.consultor_selectbox
    st.session_state.gif_warning = False; st.session_state.rotation_gif_start_time = None
    st.session_state.lunch_warning_info = None 

    if not selected or selected == 'Selecione um nome': st.warning('Selecione um consultor.'); return
    if not st.session_state.get(f'check_{selected}'): st.warning(f'{selected} não está disponível para marcar/desmarcar.'); return

    current_skip_status = st.session_state.skip_flags.get(selected, False)
    st.session_state.skip_flags[selected] = not current_skip_status
    new_status_str = 'MARCADO para pular' if not current_skip_status else 'DESMARCADO para pular'
    print(f'{selected} foi {new_status_str}')

    current_holder = next((c for c, s in st.session_state.status_texto.items() if s == 'Bastão'), None)
    if selected == current_holder and st.session_state.skip_flags[selected]:
        print(f'Portador {selected} se marcou para pular. Tentando passar o bastão...')
        save_state() 
        rotate_bastao() 
        return 

    save_state() 

def update_status(status_text, change_to_available): 
    """Callback: Botões de Ação (Atendimento, Almoço, etc.).""" # MODIFICADO: 'Atividade' para 'Atendimento'
    print(f'CALLBACK UPDATE STATUS: {status_text}')
    selected = st.session_state.consultor_selectbox
    st.session_state.gif_warning = False; st.session_state.rotation_gif_start_time = None
    if not selected or selected == 'Selecione um nome': 
        st.warning('Selecione um consultor.')
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
        num_atividade = sum(1 for s in all_statuses.values() if s == 'Atendimento') # MODIFICADO: 'Atividade' para 'Atendimento'
        total_ativos = num_na_fila + num_atividade
        num_almoco = sum(1 for s in all_statuses.values() if s == 'Almoço')
        limite_almoco = total_ativos / 2.0
        
        print(f"Check Almoço: Ativos={total_ativos}, EmAlmoço={num_almoco}, Limite={limite_almoco}")
        
        if total_ativos > 0 and num_almoco >= limite_almoco:
            print(f"AVISO ALMOÇO (Global): {selected}.")
            st.session_state.lunch_warning_info = {
                'consultor': selected,
                'start_time': datetime.now(),
                'message': f'Consultor {selected} verificar horário. Metade dos consultores ativos já em almoço. Clique novamente em "Almoço" para confirmar.'
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

    if status_text == 'Saída Temporária':
        if selected not in st.session_state.priority_return_queue: st.session_state.priority_return_queue.append(selected)
    elif selected in st.session_state.priority_return_queue: st.session_state.priority_return_queue.remove(selected)

    print(f'... Fila: {st.session_state.bastao_queue}, Skips: {st.session_state.skip_flags}')
    baton_changed = False
    if was_holder: 
        baton_changed = check_and_assume_baton() 
    
    if not baton_changed: 
        save_state() 

def manual_rerun():
    """Callback: Botão 'Atualizar (Manual)'."""
    print('CALLBACK MANUAL RERUN')
    st.session_state.gif_warning = False; st.session_state.rotation_gif_start_time = None
    st.session_state.lunch_warning_info = None 
    st.rerun() 

# --- Callbacks de Formulário de Registro ---

def handle_atividade_submission(): # MODIFICADO: Nome da função de Atividade para Atendimento
    """Callback: Envio do formulário 'Atendimento'."""
    print("CALLBACK: handle_atividade_submission")
    
    consultor_selecionado = st.session_state.consultor_selectbox
    tipo_atendimento = st.session_state.registro_tipo_selecao
    
    form_data = {
        "usuario": st.session_state.get('reg_usuario') or "N/A",
        "nome_setor": st.session_state.get('reg_nome_setor') or "N/A",
        "sistema": st.session_state.get('reg_sistema') or "N/A",
        "descricao": st.session_state.get('reg_descricao') or "N/A",
        "canal": st.session_state.get('reg_canal') or "N/A",
        "desfecho": st.session_state.get('reg_desfecho') or "N/A"
    }
    
    success = send_atividade_to_chat(consultor_selecionado, tipo_atendimento, form_data) # MODIFICADO: Nome da função
    
    if success:
        st.session_state.last_reg_status = "success"
        st.session_state.registro_tipo_selecao = None # Fecha o formulário
        # Limpa os campos do formulário
        st.session_state.reg_usuario = None
        st.session_state.reg_nome_setor = ""
        st.session_state.reg_sistema = None
        st.session_state.reg_descricao = ""
        st.session_state.reg_canal = None
        st.session_state.reg_desfecho = None
    else:
        st.session_state.last_reg_status = "error"

def handle_presencial_submission(): # MODIFICADO: Nome da função de Presencial para Atividade
    """Callback: Envio do formulário 'Atividade'."""
    print("CALLBACK: handle_presencial_submission")
    
    consultor_selecionado = st.session_state.consultor_selectbox
    
    # Lógica de 'Outros'
    atividade = st.session_state.get('reg_pres_atividade')
    if atividade == "Outros":
        atividade_final = st.session_state.get('reg_pres_atividade_outro') or "Outros (não especificado)"
    else:
        atividade_final = atividade or "N/A"

    # Ler horas e minutos e criar objetos 'time'
    inicio_h = st.session_state.get('reg_pres_inicio_h', 0)
    inicio_m = st.session_state.get('reg_pres_inicio_m', 0)
    fim_h = st.session_state.get('reg_pres_fim_h', 0)
    fim_m = st.session_state.get('reg_pres_fim_m', 0)
    
    try:
        inicio_time = time(int(inicio_h), int(inicio_m))
        fim_time = time(int(fim_h), int(fim_m))
    except ValueError as e:
        print(f"Erro ao criar objeto time: {e} (h:{inicio_h}, m:{inicio_m})")
        st.session_state.last_reg_status = "error_time" # Erro específico
        return

    form_data = {
        "atividade": atividade_final,
        "descricao": st.session_state.get('reg_pres_descricao') or "N/A",
        "particip_cesupe": st.session_state.get('reg_pres_particip_cesupe') or "N/A",
        "particip_externos": st.session_state.get('reg_pres_particip_externos') or "N/A",
        "data": st.session_state.get('reg_pres_data') or date.today(),
        "inicio": inicio_time, # Passa o objeto time
        "fim": fim_time        # Passa o objeto time
    }
    
    success = send_presencial_to_chat(consultor_selecionado, form_data) # MODIFICADO: Nome da função
    
    if success:
        st.session_state.last_reg_status = "success"
        st.session_state.registro_tipo_selecao = None # Fecha o formulário
        # Limpa os campos do formulário
        st.session_state.reg_pres_atividade = None
        st.session_state.reg_pres_atividade_outro = ""
        st.session_state.reg_pres_descricao = ""
        st.session_state.reg_pres_particip_cesupe = ""
        st.session_state.reg_pres_particip_externos = ""
        # Limpa os campos de hora/minuto
        st.session_state.reg_pres_inicio_h = 0
        st.session_state.reg_pres_inicio_m = 0
        st.session_state.reg_pres_fim_h = 0
        st.session_state.reg_pres_fim_m = 0
    else:
        st.session_state.last_reg_status = "error"

# Callbacks para o guia de chamados
def set_chamado_step(step_num):
    """Callback para ATUALIZAR a etapa do guia de chamados."""
    st.session_state.chamado_guide_step = step_num

def handle_chamado_submission():
    """Callback: Envio do rascunho do chamado."""
    print("CALLBACK: handle_chamado_submission")
    
    consultor = st.session_state.consultor_selectbox
    texto_chamado = st.session_state.get("chamado_textarea", "")
    
    success = send_chamado_to_chat(consultor, texto_chamado)
    
    if success:
        # Mensagem de sucesso específica!
        st.session_state.last_reg_status = "success_chamado" 
        st.session_state.chamado_guide_step = 0 # Fecha o guia
        st.session_state.chamado_textarea = "" # Limpa o rascunho
    else:
        # Erro (Consultor não selecionado ou texto vazio)
        st.session_state.last_reg_status = "error_chamado"


# ============================================
# 4. EXECUÇÃO PRINCIPAL DO STREAMLIT APP
# ============================================

st.set_page_config(page_title="Controle Bastão Cesupe", layout="wide")
init_session_state()

st.components.v1.html("<script>window.scrollTo(0, 0);</script>", height=0)

# <-- MODIFICADO: Título com Imagem (width ajustado para 120px) -->
st.markdown(
    f"""
    <div style="display: flex; align-items: center; gap: 10px;">
        <h1 style="margin-bottom: 0;">Controle Bastão Cesupe {BASTAO_EMOJI}</h1>
        <img src="{NOVEMBRO_AZUL_URL}" alt="Novembro Azul" style="width: 120px; height: auto;">
    </div>
    """,
    unsafe_allow_html=True
)
# <-- FIM DA MODIFICAÇÃO -->

st.markdown("<hr style='border: 1px solid #4A90E2;'>", unsafe_allow_html=True) 

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
    _, col_time = st.columns([0.25, 0.75])
    duration = timedelta()
    if responsavel and st.session_state.bastao_start_time:
        try: duration = datetime.now() - st.session_state.bastao_start_time
        except: pass
    col_time.markdown(f'#### 🕒 Tempo: **{format_time_duration(duration)}**')
    if responsavel:
        st.markdown(f'<span style="font-size: 2em; font-weight: bold;">{responsavel}</span>', unsafe_allow_html=True)
    else: st.markdown('<h2>(Ninguém com o bastão)</h2>', unsafe_allow_html=True)
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
        titulo = '**Consultor Pulou:**' if num_skipped == 1 else '**Consultores Pularam:**'
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
    st.header("**Consultor**")
    st.selectbox('Selecione:', options=['Selecione um nome'] + CONSULTORES, key='consultor_selectbox', label_visibility='collapsed')
    st.markdown("#### "); st.markdown("**Ações:**")
    
    c1, c2, c3, c4, c5, c6, c7 = st.columns(7) 
    
    c1.button('🎯 Passar', on_click=rotate_bastao, use_container_width=True, help='Passa o bastão para o próximo elegível. Apenas o responsável atual.')
    c2.button('⏭️ Pular', on_click=toggle_skip, use_container_width=True, help='Marca/Desmarca o consultor selecionado para ser pulado na próxima rotação.')
    c3.button('✏️ Atendimento', on_click=update_status, args=('Atendimento', False,), use_container_width=True) # MODIFICADO: 'Atividade' para 'Atendimento'
    c4.button('🍽️ Almoço', on_click=update_status, args=('Almoço', False,), use_container_width=True)
    c5.button('👤 Ausente', on_click=update_status, args=('Ausente', False,), use_container_width=True)
    c6.button('🎙️ Sessão', on_click=update_status, args=('Sessão', False,), use_container_width=True)
    c7.button('🚶 Saída', on_click=update_status, args=('Saída Temporária', False,), use_container_width=True)
    
    st.markdown("####")
    st.button('🔄 Atualizar (Manual)', on_click=manual_rerun, use_container_width=True)
    
    # --- Bloco de Registro de Atividade ---
    st.markdown("---")
    
    if st.session_state.last_reg_status == "success":
        st.success("Registro enviado com sucesso!")
        st.session_state.last_reg_status = None 
    elif st.session_state.last_reg_status == "success_chamado":
        st.success("Chamado enviado! A resposta será enviada no seu email institucional.")
        st.session_state.last_reg_status = None
    elif st.session_state.last_reg_status == "error":
        st.error("Erro ao enviar registro. Verifique se seu nome está selecionado no menu 'Consultor' acima.")
        st.session_state.last_reg_status = None
    elif st.session_state.last_reg_status == "error_chamado":
        st.error("Erro ao enviar chamado. Verifique se seu nome está selecionado e se o campo de rascunho não está vazio.")
        st.session_state.last_reg_status = None
    elif st.session_state.last_reg_status == "error_time":
        st.error("Erro ao enviar registro. Hora ou minuto inválido.")
        st.session_state.last_reg_status = None
    
    st.header("Registrar Atendimento") # MODIFICADO: 'Atividade' para 'Atendimento'

    st.radio(
        "Tipo de Atendimento:",
        ["Atendimento", "Atividade"], # MODIFICADO: 'Atividade' para 'Atendimento' e 'Presencial' para 'Atividade'
        index=None,
        key='registro_tipo_selecao', 
        horizontal=True
    )

    # --- Formulário "Atendimento" --- # MODIFICADO: 'Atividade' para 'Atendimento'
    if st.session_state.registro_tipo_selecao == "Atendimento": # MODIFICADO: 'Atividade' para 'Atendimento'
        with st.form(key="form_atividade"):
            st.subheader(f"Registro de: **Atendimento**") # MODIFICADO: 'Atividade' para 'Atendimento'
            
            st.selectbox("Usuário:", REG_USUARIO_OPCOES, index=None, placeholder="Selecione o tipo de usuário", key='reg_usuario')
            st.text_input("Nome-usuário - Setor:", key='reg_nome_setor')
            st.selectbox("Sistema:", REG_SISTEMA_OPCOES, index=None, placeholder="Selecione o sistema", key='reg_sistema')
            st.text_input("Descrição do atendimento (até 7 palavras):", key='reg_descricao')
            st.selectbox("Canal de atendimento:", REG_CANAL_OPCOES, index=None, placeholder="Selecione o canal", key='reg_canal')
            st.selectbox("Desfecho:", REG_DESFECHO_OPCOES, index=None, placeholder="Selecione o desfecho", key='reg_desfecho')
            
            st.form_submit_button(
                "Enviar Registro",
                on_click=handle_atividade_submission # MODIFICADO: Nome da função
            )
            
    # --- Formulário "Atividade" --- # MODIFICADO: 'Presencial' para 'Atividade'
    elif st.session_state.registro_tipo_selecao == "Atividade": # MODIFICADO: 'Presencial' para 'Atividade'
        
        st.selectbox(
            "Atividade:", 
            REG_PRESENCIAL_ATIVIDADE_OPCOES, 
            index=None, 
            placeholder="Selecione a atividade", 
            key='reg_pres_atividade'
        )

        if st.session_state.get('reg_pres_atividade'):
            with st.form(key="form_presencial"):
                st.subheader(f"Registro de: **Atividade** ({st.session_state.get('reg_pres_atividade')})") # MODIFICADO: 'Presencial' para 'Atividade'
                
                if st.session_state.get('reg_pres_atividade') == "Outros":
                    st.text_input("Especifique a atividade:", key='reg_pres_atividade_outro')

                st.text_input("Descrição:", key='reg_pres_descricao')
                st.text_input(
                    "Participantes Cesupe:", 
                    help="(Preencher se o registro for para mais de um consultor)", 
                    key='reg_pres_particip_cesupe'
                )
                st.text_input("Participantes Externos:", key='reg_pres_particip_externos')
                
                st.date_input("Data:", key='reg_pres_data', format="DD/MM/YYYY")
                
                st.markdown("**Início:**")
                col_ini_1, col_ini_2 = st.columns(2)
                with col_ini_1:
                    st.number_input("Hora", min_value=0, max_value=23, step=1, key='reg_pres_inicio_h', format="%02d", label_visibility="collapsed")
                with col_ini_2:
                    st.number_input("Minuto", min_value=0, max_value=59, step=1, key='reg_pres_inicio_m', format="%02d", label_visibility="collapsed")

                st.markdown("**Fim:**")
                col_fim_1, col_fim_2 = st.columns(2)
                with col_fim_1:
                    st.number_input("Hora ", min_value=0, max_value=23, step=1, key='reg_pres_fim_h', format="%02d", label_visibility="collapsed")
                with col_fim_2:
                    st.number_input("Minuto ", min_value=0, max_value=59, step=1, key='reg_pres_fim_m', format="%02d", label_visibility="collapsed")

                st.form_submit_button(
                    "Enviar Registro",
                    on_click=handle_presencial_submission # MODIFICADO: Nome da função
                )
                
    # --- Bloco Padrão Abertura de Chamados ---
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
                
                Antes de abrir o chamado, o consultor deve primeiro realizar os procedimentos de suporte e testes necessários para **verificar e confirmar o problema** que foi relatado pelo usuário.
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
                
                **7. Identificação do Consultor**
                * Inserir a assinatura e identificação do consultor.
                
                > **Observação para a Abertura:**
                > Ao abrir chamados na aba específica "CONSULTORES CESUPE - ERRO", deve-se verificar se o campo "Título Extra" está preenchido com o nome do setor responsável pela abertura (CESUPE).
                """)
                st.button("Próximo (Passo 3) ➡️", on_click=set_chamado_step, args=(3,))
                
            elif guide_step == 3:
                st.subheader("PASSO 3: Registrar e Informar o Usuário por E-mail")
                st.markdown("""
                Após a abertura do chamado, o consultor deve enviar um e-mail ao usuário (serventuário) informando que:
                
                * A questão é de competência do setor de Informática do TJMG.
                * Um chamado ($n^{\circ}$ CH) foi aberto junto ao referido departamento.
                * O departamento de informática realizará as verificações e tomará as providências necessárias.
                * O usuário deve aguardar, e o consultor entrará em contato assim que receber um feedback do departamento com as orientações.
                """)
                st.button("Próximo (Observações) ➡️", on_click=set_chamado_step, args=(4,))
                
            elif guide_step == 4:
                st.subheader("Observações Gerais Importantes")
                st.markdown("""
                * **Comunicação:** O envio de qualquer informação ou documento para setores ou usuários deve ser feito apenas para o **e-mail institucional oficial**.
                * **Atualização:** A atualização das informações sobre o andamento deve ser feita no **IN**.
                * **Controle:** Cada consultor é **responsável por ter seu próprio controle** dos chamados que abriu, atualizá-los quando necessário e orientar o usuário.
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
    st.header('Status dos Consultores')
    st.markdown('Marque/Desmarque para entrar/sair.')
    ui_lists = {'fila': [], 'atendimento': [], 'almoco': [], 'saida': [], 'ausente': [], 'sessao': [], 'indisponivel': []} # MODIFICADO: 'atividade' para 'atendimento'
    
    for nome in CONSULTORES:
        is_checked = st.session_state.get(f'check_{nome}', False)
        status = st.session_state.status_texto.get(nome, 'Indisponível')
        
        if status == 'Bastão': 
            ui_lists['fila'].insert(0, nome)
        elif status == '': 
            ui_lists['fila'].append(nome) 
        elif status == 'Atendimento': # MODIFICADO: 'Atividade' para 'Atendimento'
            ui_lists['atendimento'].append(nome) # MODIFICADO: 'atividade' para 'atendimento'
        elif status == 'Almoço': 
            ui_lists['almoco'].append(nome)
        elif status == 'Ausente':
            ui_lists['ausente'].append(nome)
        elif status == 'Sessão':
            ui_lists['sessao'].append(nome)
        elif status == 'Saída Temporária': 
            ui_lists['saida'].append(nome)
        elif status == 'Indisponível': 
            ui_lists['indisponivel'].append(nome)

    st.subheader(f'✅ Na Fila ({len(ui_lists['fila'])})')
    render_order = [c for c in queue if c in ui_lists['fila']] + [c for c in ui_lists['fila'] if c not in queue]
    if not render_order: st.markdown('_Ninguém disponível._')
    else:
        for nome in render_order:
            col_nome, col_check = st.columns([0.8, 0.2])
            key = f'check_{nome}'
            
            col_check.checkbox(' ', key=key, on_change=update_queue, args=(nome,), label_visibility='collapsed')
            
            skip_flag = skips.get(nome, False)
            if nome == responsavel:
                display = f'<span style="background-color: #007BFF; color: white; padding: 2px 6px; border-radius: 5px; font-weight: bold;">🔥 {nome}</span>'
            elif skip_flag:
                display = f'**{nome}** :orange-background[Pulando ⏭️]'
            else:
                display = f'**{nome}** :blue-background[Aguardando]'
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

    render_section('Atendimento', '✏️', ui_lists['atendimento'], 'yellow') # MODIFICADO: 'Atividade' para 'Atendimento' e ui_lists
    render_section('Almoço', '🍽️', ui_lists['almoco'], 'blue')
    render_section('Ausente', '👤', ui_lists['ausente'], 'violet') 
    render_section('Sessão', '🎙️', ui_lists['sessao'], 'green')
    render_section('Saída', '🚶', ui_lists['saida'], 'red')
    render_section('Indisponível', '❌', ui_lists['indisponivel'], 'grey')

# --- Lógica de Relatório Diário ---
now = datetime.now()
last_run_date = st.session_state.report_last_run_date.date() if isinstance(st.session_state.report_last_run_date, datetime) else datetime.min.date()

# Rodar o relatório uma vez por dia, a partir das 20h
if now.hour >= 20 and now.date() > last_run_date:
    print(f"TRIGGER: Enviando relatório diário. Agora: {now}, Última Execução: {st.session_state.report_last_run_date}")
    send_daily_report()
