# ============================================
# 1. IMPORTS E DEFINIÇÕES GLOBAIS
# ============================================
import streamlit as st
import pandas as pd
import requests
import time
import json
import os
from datetime import datetime, timedelta
from operator import itemgetter
from streamlit_autorefresh import st_autorefresh

# --- Constantes ---
# --- ⬇️ MUDANÇA AQUI: Webhooks Reativados e Relatório Renomeado ---
# GOOGLE_CHAT_WEBHOOK_RELATORIO renomeado para GOOGLE_CHAT_WEBHOOK_BACKUP
GOOGLE_CHAT_WEBHOOK_BACKUP = "https://chat.googleapis.com/v1/spaces/AAQA0V8TAhs/messages?key=AIzaSyDdI0hCZtE6vySjMm-WEfRq3CPzqKqqsHI&token=Zl7KMv0PLrm5c7IMZZdaclfYoc-je9ilDDAlDfqDMAU"
CHAT_WEBHOOK_BASTAO = "https://chat.googleapis.com/v1/spaces/AAQAXbwpQHY/messages?key=AIzaSyDdI0hCZtE6vySjMm-WEfRq3CPzqKqqsHI&token=7AQaoGHiWIfv3eczQzVZ-fbQdBqSBOh1CyQ854o1f7k"
# --- ⬆️ FIM DA MUDANÇA ---
BASTAO_EMOJI = "🌸"
APP_URL_CLOUD = 'https://controle-bastao-cesupe.streamlit.app'
CONSULTORES = sorted([
    "Barbara", "Bruno", "Claudia", "Douglas", "Fábio", "Glayce", "Isac",
    "Isabela", "Ivana", "Leonardo", "Morôni", "Michael", "Pablo", "Ranyer",
    "Victoria"
])
LOG_FILE = 'status_log.json'
STATE_FILE = 'app_state.json'
STATUS_SAIDA_PRIORIDADE = ['Saída Temporária']
STATUSES_DE_SAIDA = ['Atividade', 'Almoço', 'Saída Temporária']
GIF_URL_WARNING = 'https://media0.giphy.com/media/v1.Y2lkPTc5MGI3NjExY2pjMDN0NGlvdXp1aHZ1ejJqMnY5MG1yZmN0d3NqcDl1bTU1dDJrciZlcD12MV9pbnRlcm5uYWxfZ2lmX2J5X2lkJmN0PWc/fXnRObM8Q0RkOmR5nf/giphy.gif'
GIF_URL_ROTATION = 'https://media0.giphy.com/media/v1.Y2lkPTc5MGI3NjExdmx4azVxbGt4Mnk1cjMzZm5sMmp1YThteGJsMzcyYmhsdmFoczV0aSZlcD12MV9pbnRlcm5uYWxfZ2lmX2J5X2lkJmN0PWc/JpkZEKWY0s9QI4DGvF/giphy.gif'
SOUND_URL = "https://github.com/matheusmg0550247-collab/controle-bastao-eproc2/raw/refs/heads/main/doorbell-223669.mp3"

# ============================================
# 2. FUNÇÕES AUXILIARES GLOBAIS
# ============================================

def date_serializer(obj):
    if isinstance(obj, datetime): return obj.isoformat()
    return str(obj)

def save_state():
    state_to_save = {
        'status_texto': st.session_state.status_texto,
        'bastao_queue': st.session_state.bastao_queue,
        'skip_flags': st.session_state.skip_flags,
        'bastao_start_time': st.session_state.bastao_start_time,
        'current_status_starts': st.session_state.current_status_starts,
        'report_last_run_date': st.session_state.report_last_run_date,
        'bastao_counts': st.session_state.bastao_counts,
        'priority_return_queue': st.session_state.priority_return_queue,
        'rotation_gif_start_time': st.session_state.get('rotation_gif_start_time'),
    }
    try:
        state_to_save['current_status_starts'] = {k: v.isoformat() if isinstance(v, datetime) else str(v) for k, v in state_to_save['current_status_starts'].items()}
        for key in ['bastao_start_time', 'report_last_run_date', 'rotation_gif_start_time']:
             if isinstance(state_to_save.get(key), datetime):
                  state_to_save[key] = state_to_save[key].isoformat()

        with open(STATE_FILE, 'w') as f: json.dump(state_to_save, f, indent=4)
        print(f'*** Estado Salvo ***')
    except Exception as e: print(f'Erro ao salvar estado: {e}')

def load_state():
    if not os.path.exists(STATE_FILE): return {}
    try:
        with open(STATE_FILE, 'r') as f: data = json.load(f)
        for key in ['bastao_start_time', 'report_last_run_date', 'rotation_gif_start_time']:
            if data.get(key) and isinstance(data[key], str):
                try: data[key] = datetime.fromisoformat(data[key])
                except (ValueError, TypeError): data[key] = None
        if 'current_status_starts' in data and isinstance(data['current_status_starts'], dict):
             temp_starts = {}
             for c, ts in data['current_status_starts'].items():
                 if c in CONSULTORES:
                     if ts and isinstance(ts, str):
                         try: temp_starts[c] = datetime.fromisoformat(ts)
                         except (ValueError, TypeError): temp_starts[c] = datetime.now()
                     elif isinstance(ts, datetime): temp_starts[c] = ts
                     else: temp_starts[c] = datetime.now()
             data['current_status_starts'] = temp_starts
        else: data['current_status_starts'] = {}
        data['bastao_queue'] = [c for c in data.get('bastao_queue', []) if c in CONSULTORES]
        data['skip_flags'] = {c: v for c, v in data.get('skip_flags', {}).items() if c in CONSULTORES}
        data['priority_return_queue'] = [c for c in data.get('priority_return_queue', []) if c in CONSULTORES]
        data['bastao_counts'] = {c: v for c, v in data.get('bastao_counts', {}).items() if c in CONSULTORES}
        data['status_texto'] = {c: v for c, v in data.get('status_texto', {}).items() if c in CONSULTORES}
        data.setdefault('bastao_counts', {})
        data.setdefault('priority_return_queue', [])
        data.setdefault('skip_flags', {})
        data.setdefault('status_texto', {})
        return data
    except Exception as e: print(f'Erro ao carregar estado: {e}. Resetando.'); return {}

def send_chat_notification_internal(consultor, status):
    # --- ⬇️ MUDANÇA AQUI: Usa CHAT_WEBHOOK_BASTAO ---
    if CHAT_WEBHOOK_BASTAO and status == 'Bastão':
        message_template = "🎉 **BASTÃO GIRADO!** 🎉 \\n\\n- **Novo Responsável:** {consultor}\\n- **Acesse o Painel:** {app_url}"
        message_text = message_template.format(consultor=consultor, app_url=APP_URL_CLOUD) # Usa a URL global
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
    # --- ⬆️ FIM DA MUDANÇA ---

def play_sound_html(): return f'<audio autoplay="true"><source src="{SOUND_URL}" type="audio/mpeg"></audio>'
def load_logs(): return [] # Implementação omitida
def save_logs(l): pass # Implementação omitida

def log_status_change(consultor, old_status, new_status, duration):
    print(f'LOG: {consultor} de "{old_status or '-'}" para "{new_status or '-'}" após {duration}')
    if not isinstance(duration, timedelta): duration = timedelta(0)
    st.session_state.current_status_starts[consultor] = datetime.now()

def format_time_duration(duration):
    if not isinstance(duration, timedelta): return '--:--:--'
    s = int(duration.total_seconds()); h, s = divmod(s, 3600); m, s = divmod(s, 60)
    return f'{h:02}:{m:02}:{s:02}'

def send_daily_report(): # Nome da função mantido, mas usa webhook renomeado
    # --- ⬇️ MUDANÇA AQUI: Usa GOOGLE_CHAT_WEBHOOK_BACKUP ---
    print("Tentando enviar backup diário...")
    logs = load_logs() # Carregaria os logs reais aqui
    today_str = datetime.now().date().isoformat()
    # Placeholder: Em um cenário real, você processaria os logs aqui
    report_data = [{'consultor': 'Exemplo', 'old_status': 'Bastão', 'duration_s': 3600}] # Dados de exemplo
    # report_data = [log for log in logs if log.get('start_time','').startswith(today_str)] # Filtragem real

    if not report_data or not GOOGLE_CHAT_WEBHOOK_BACKUP:
        print(f"Backup não enviado. Dados: {bool(report_data)}, Webhook: {bool(GOOGLE_CHAT_WEBHOOK_BACKUP)}")
        st.session_state['report_last_run_date'] = datetime.now()
        save_state()
        return

    # Placeholder: Construiria o report_text baseado nos report_data
    report_text = f"📊 **Backup Diário de Status - {today_str}**\n\n(Detalhes do processamento de logs omitidos)"

    chat_message = {'text': report_text}
    print(f"Enviando backup para: {GOOGLE_CHAT_WEBHOOK_BACKUP}")
    try:
        response = requests.post(GOOGLE_CHAT_WEBHOOK_BACKUP, json=chat_message)
        response.raise_for_status()
        st.session_state['report_last_run_date'] = datetime.now()
        print("Backup diário enviado com sucesso.")
        save_state()
    except requests.exceptions.RequestException as e:
        print(f'Erro ao enviar backup diário: {e}')
        if e.response is not None:
             print(f'Status: {e.response.status_code}, Resposta: {e.response.text}')
    # st.rerun() # Remover rerun daqui para evitar loop se chamado no render
    # --- ⬆️ FIM DA MUDANÇA ---


def init_session_state():
    persisted_state = load_state()
    defaults = {
        'status_texto': {nome: '' for nome in CONSULTORES}, 'bastao_queue': [],
        'skip_flags': {},
        'bastao_start_time': None, 'current_status_starts': {nome: datetime.now() for nome in CONSULTORES},
        'report_last_run_date': datetime.min, 'bastao_counts': {nome: 0 for nome in CONSULTORES},
        'priority_return_queue': [], 'rotation_gif_start_time': None,
    }
    for key, default in defaults.items():
        st.session_state.setdefault(key, persisted_state.get(key, default))
        if key == 'bastao_queue' and not isinstance(st.session_state.bastao_queue, list): st.session_state.bastao_queue = []
        if key == 'skip_flags' and not isinstance(st.session_state.skip_flags, dict): st.session_state.skip_flags = {}
        if key == 'priority_return_queue' and not isinstance(st.session_state.priority_return_queue, list): st.session_state.priority_return_queue = []
        if key == 'bastao_counts' and not isinstance(st.session_state.bastao_counts, dict): st.session_state.bastao_counts = {}
        if key == 'status_texto' and not isinstance(st.session_state.status_texto, dict): st.session_state.status_texto = {}
        if key == 'current_status_starts' and not isinstance(st.session_state.current_status_starts, dict): st.session_state.current_status_starts = {}

    loaded_starts = persisted_state.get('current_status_starts', {})
    loaded_counts = persisted_state.get('bastao_counts', {})
    loaded_skips = persisted_state.get('skip_flags', {})
    loaded_status = persisted_state.get('status_texto', {})

    for nome in CONSULTORES:
        st.session_state.current_status_starts.setdefault(nome, loaded_starts.get(nome, datetime.now()))
        st.session_state.bastao_counts.setdefault(nome, loaded_counts.get(nome, 0))
        st.session_state.skip_flags.setdefault(nome, loaded_skips.get(nome, False))
        st.session_state.status_texto.setdefault(nome, loaded_status.get(nome, ''))

    st.session_state.bastao_queue = [c for c in st.session_state.bastao_queue if c in CONSULTORES]
    st.session_state.priority_return_queue = [c for c in st.session_state.priority_return_queue if c in CONSULTORES]

    for nome in CONSULTORES:
        is_active = nome in st.session_state.bastao_queue or bool(st.session_state.status_texto.get(nome))
        st.session_state.setdefault(f'check_{nome}', is_active)

    checked_on = {c for c in CONSULTORES if st.session_state.get(f'check_{c}')}
    if not st.session_state.bastao_queue and checked_on:
        print('!!! Fila vazia na carga, reconstruindo !!!')
        master_order_from_state = persisted_state.get('master_order', [])
        master_order_from_state = [c for c in master_order_from_state if c in CONSULTORES]
        st.session_state.bastao_queue = [c for c in master_order_from_state if c in checked_on]
        for c in checked_on:
            if c not in st.session_state.bastao_queue:
                st.session_state.bastao_queue.append(c)

    print('--- Estado Inicializado ---')
    print(f' Fila: {st.session_state.bastao_queue}, Skip Flags: {st.session_state.skip_flags}')

def find_next_holder_index(current_index, queue, skips):
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
    print('--- VERIFICA E ASSUME BASTÃO ---')
    queue = st.session_state.bastao_queue
    skips = st.session_state.skip_flags
    current_holder_status = next((c for c, s in st.session_state.status_texto.items() if s == 'Bastão'), None)
    is_current_valid = (current_holder_status
                      and current_holder_status in queue
                      and st.session_state.get(f'check_{current_holder_status}'))

    first_eligible_index = find_next_holder_index(-1, queue, skips)
    first_eligible_holder = queue[first_eligible_index] if first_eligible_index != -1 else None

    print(f'Fila: {queue}, Skips: {skips}, Próximo Elegível: {first_eligible_holder}, Portador Atual (Status): {current_holder_status}, Atual é Válido?: {is_current_valid}')

    should_have_baton = None
    if is_current_valid:
        should_have_baton = current_holder_status
    elif first_eligible_holder:
        should_have_baton = first_eligible_holder

    changed = False
    for c in CONSULTORES:
        if c != should_have_baton and st.session_state.status_texto.get(c) == 'Bastão':
            print(f'Limpando bastão de {c} (não deveria ter)')
            duration = datetime.now() - st.session_state.current_status_starts.get(c, datetime.now())
            log_status_change(c, 'Bastão', '', duration)
            st.session_state.status_texto[c] = ''
            changed = True

    if should_have_baton and st.session_state.status_texto.get(should_have_baton) != 'Bastão':
        print(f'Atribuindo bastão para {should_have_baton}')
        old_status = st.session_state.status_texto.get(should_have_baton, '')
        duration = datetime.now() - st.session_state.current_status_starts.get(should_have_baton, datetime.now())
        log_status_change(should_have_baton, old_status, 'Bastão', duration)
        st.session_state.status_texto[should_have_baton] = 'Bastão'
        st.session_state.bastao_start_time = datetime.now()
        if current_holder_status != should_have_baton: st.session_state.play_sound = True; send_chat_notification_internal(should_have_baton, 'Bastão') # Notifica
        if st.session_state.skip_flags.get(should_have_baton):
             print(f' Consumindo skip flag de {should_have_baton} ao assumir.')
             st.session_state.skip_flags[should_have_baton] = False
        changed = True
    elif not should_have_baton:
         if current_holder_status:
              print(f'Ninguém elegível, limpando bastão de {current_holder_status}')
              duration = datetime.now() - st.session_state.current_status_starts.get(current_holder_status, datetime.now())
              log_status_change(current_holder_status, 'Bastão', '', duration)
              st.session_state.status_texto[current_holder_status] = ''
              changed = True
         if st.session_state.bastao_start_time is not None: changed = True
         st.session_state.bastao_start_time = None

    if changed: print('Estado do bastão mudou.'); save_state()
    return changed

# ============================================
# 3. FUNÇÕES DE CALLBACK GLOBAIS
# ============================================

def update_queue(consultor):
    print(f'CALLBACK UPDATE QUEUE: {consultor}')
    st.session_state.gif_warning = False; st.session_state.rotation_gif_start_time = None
    is_checked = st.session_state.get(f'check_{consultor}') # New state
    old_status_text = st.session_state.status_texto.get(consultor, '')
    was_holder_before = consultor == next((c for c, s in st.session_state.status_texto.items() if s == 'Bastão'), None)
    duration = datetime.now() - st.session_state.current_status_starts.get(consultor, datetime.now())

    if is_checked: # Becoming available
        log_status_change(consultor, old_status_text or 'Indisponível', '', duration)
        st.session_state.status_texto[consultor] = ''
        if consultor not in st.session_state.bastao_queue:
            st.session_state.bastao_queue.append(consultor) # Add to end
            print(f'Adicionado {consultor} ao fim da fila.')
        st.session_state.skip_flags[consultor] = False # Ensure not skipped
    else: # Becoming unavailable
        log_old_status = old_status_text or ('Bastão' if was_holder_before else 'Disponível')
        log_status_change(consultor, log_old_status , 'Indisponível', duration)
        st.session_state.status_texto[consultor] = ''
        if consultor in st.session_state.bastao_queue:
            st.session_state.bastao_queue.remove(consultor)
            print(f'Removido {consultor} da fila.')
        st.session_state.skip_flags.pop(consultor, None) # Remove flag


    print(f'... Fila: {st.session_state.bastao_queue}, Skips: {st.session_state.skip_flags}')
    baton_changed = check_and_assume_baton()
    # Save state if baton logic didn't already (e.g., just queue changed)
    # Check_and_assume now saves state if changed, so save here ONLY if no baton change occurred.
    if not baton_changed:
        save_state()
    st.rerun()


def rotate_bastao(): # Action 'Passar'
    print('CALLBACK ROTATE BASTAO (PASSAR)')
    selected = st.session_state.consultor_selectbox
    st.session_state.gif_warning = False; st.session_state.rotation_gif_start_time = None
    if not selected or selected == 'Selecione um nome': st.warning('Selecione um consultor.'); return
    queue = st.session_state.bastao_queue
    skips = st.session_state.skip_flags
    current_holder = next((c for c, s in st.session_state.status_texto.items() if s == 'Bastão'), None)
    # Allow rotate only if selected IS the current holder
    if selected != current_holder:
        st.session_state.gif_warning = True
        print(f'Aviso: {selected} tentou passar, mas {current_holder} tem o bastão.')
        st.rerun()
        return

    current_index = -1
    try: current_index = queue.index(current_holder)
    except ValueError:
        print(f'ERRO: Portador atual {current_holder} não encontrado na fila {queue}. Tentando recuperar.')
        st.warning(f'Erro interno: Portador {current_holder} não está na fila.')
        if check_and_assume_baton(): st.rerun()
        return

    # --- LÓGICA DE RESET ---
    reset_triggered = False
    first_eligible_index_overall = find_next_holder_index(-1, queue, skips)

    if first_eligible_index_overall != -1:
        first_eligible_holder_overall = queue[first_eligible_index_overall]
        potential_next_index_no_reset = find_next_holder_index(current_index, queue, skips)

        # Reset condition: next *would be* the first overall AND it's not the current holder
        if potential_next_index_no_reset != -1 and \
           queue[potential_next_index_no_reset] == first_eligible_holder_overall and \
           current_holder != first_eligible_holder_overall :
            print("--- RESETANDO CICLO (Detectado ao passar para o primeiro elegível) ---")
            new_skips = {}
            for c in queue: # Iterate over the current queue order
                if st.session_state.get(f'check_{c}'):
                    new_skips[c] = False # Reset flag for available
                elif c in skips: # Keep flag if unavailable? Let's clear for simplicity.
                    new_skips[c] = False
            st.session_state.skip_flags = new_skips
            skips = st.session_state.skip_flags # Atualiza a variável local
            reset_triggered = True
            # After reset, the next MUST be the first eligible overall
            next_index = first_eligible_index_overall
            print(f'Flags limpas. Próximo índice recalculado para: {next_index} ({queue[next_index] if next_index != -1 else "Nenhum"})')
        else:
             # No reset, use the normally calculated next index
             next_index = potential_next_index_no_reset
             print(f'Sem reset. Próximo índice: {next_index} ({queue[next_index] if next_index != -1 else "Nenhum"})')
    else:
        # No one eligible in the entire queue
        print('Ninguém elegível na fila inteira.')
        next_index = -1
    # --- FIM LÓGICA DE RESET ---


    if next_index != -1:
        next_holder = queue[next_index]
        print(f'Passando bastão de {current_holder} para {next_holder} (Reset Triggered: {reset_triggered})')
        duration = datetime.now() - (st.session_state.bastao_start_time or datetime.now())
        log_status_change(current_holder, 'Bastão', '', duration)
        st.session_state.status_texto[current_holder] = ''
        log_status_change(next_holder, st.session_state.status_texto.get(next_holder, ''), 'Bastão', timedelta(0))
        st.session_state.status_texto[next_holder] = 'Bastão'
        st.session_state.bastao_start_time = datetime.now()
        # Consume flag (safe even if reset already cleared)
        st.session_state.skip_flags[next_holder] = False
        st.session_state.bastao_counts[current_holder] = st.session_state.bastao_counts.get(current_holder, 0) + 1
        st.session_state.play_sound = True
        st.session_state.rotation_gif_start_time = datetime.now()
        save_state()
    else:
        print('Não foi encontrado próximo elegível após verificação. Bastão permanece com {current_holder} (ou ninguém).')
        st.warning('Não há próximo consultor elegível na fila no momento.')
        # Don't save state if nothing changed effectively

    st.rerun()


def toggle_skip(): # Action 'Pular'
    print('CALLBACK TOGGLE SKIP')
    selected = st.session_state.consultor_selectbox
    st.session_state.gif_warning = False; st.session_state.rotation_gif_start_time = None
    if not selected or selected == 'Selecione um nome': st.warning('Selecione um consultor.'); return
    # Allow marking anyone currently available (checkbox ON)
    if not st.session_state.get(f'check_{selected}'): st.warning(f'{selected} não está disponível para marcar/desmarcar.'); return

    current_skip_status = st.session_state.skip_flags.get(selected, False)
    st.session_state.skip_flags[selected] = not current_skip_status
    new_status_str = 'MARCADO para pular' if not current_skip_status else 'DESMARCADO para pular'
    print(f'{selected} foi {new_status_str}')

    current_holder = next((c for c, s in st.session_state.status_texto.items() if s == 'Bastão'), None)
    # If the current holder marks themselves to skip, immediately try to pass the baton
    if selected == current_holder and st.session_state.skip_flags[selected]:
        print(f'Portador {selected} se marcou para pular. Tentando passar o bastão...')
        save_state() # Save the flag change before calling rotate
        rotate_bastao() # Rotate handles rerun and saving state changes from rotation
        return # Avoid double save/rerun

    save_state() # Save the changed flag otherwise
    st.rerun()


def update_status(status_text, change_to_available): # Unavailable + Status
    print(f'CALLBACK UPDATE STATUS: {status_text}')
    selected = st.session_state.consultor_selectbox
    st.session_state.gif_warning = False; st.session_state.rotation_gif_start_time = None
    if not selected or selected == 'Selecione um nome': st.warning('Selecione um consultor.'); return

    st.session_state[f'check_{selected}'] = False # Mark unavailable
    was_holder = next((True for c, s in st.session_state.status_texto.items() if s == 'Bastão' and c == selected), False)
    old_status = st.session_state.status_texto.get(selected, '') or ('Bastão' if was_holder else 'Disponível')
    duration = datetime.now() - st.session_state.current_status_starts.get(selected, datetime.now())
    log_status_change(selected, old_status, status_text, duration)
    st.session_state.status_texto[selected] = status_text # Set the specific status

    # Remove from queue and clear skip flag if they leave
    if selected in st.session_state.bastao_queue: st.session_state.bastao_queue.remove(selected)
    st.session_state.skip_flags.pop(selected, None)

    if status_text == 'Saída Temporária':
        if selected not in st.session_state.priority_return_queue: st.session_state.priority_return_queue.append(selected)
    elif selected in st.session_state.priority_return_queue: st.session_state.priority_return_queue.remove(selected)

    print(f'... Fila: {st.session_state.bastao_queue}, Skips: {st.session_state.skip_flags}')
    baton_changed = False
    if was_holder: # If holder left, must find next
        baton_changed = check_and_assume_baton()
    # Save state if check_assume didn't (e.g., someone left but wasn't holder)
    if not baton_changed: save_state()
    st.rerun()


def manual_rerun():
    print('CALLBACK MANUAL RERUN')
    st.session_state.gif_warning = False; st.session_state.rotation_gif_start_time = None
    st.rerun()

# ============================================
# 4. EXECUÇÃO PRINCIPAL DO STREAMLIT APP
# ============================================

st.set_page_config(page_title="Controle Bastão Cesupe", layout="wide")
st.markdown('<style>div.stAlert { display: none !important; }</style>', unsafe_allow_html=True)
init_session_state()

# --- Scroll to Top ---
st.components.v1.html("<script>window.scrollTo(0, 0);</script>", height=0)
# --- Fim Scroll to Top ---

st.title(f'Controle Bastão Cesupe {BASTAO_EMOJI}')
st.markdown("<hr style='border: 1px solid #E75480;'>", unsafe_allow_html=True)

# Auto Refresh & Timed Elements
gif_start_time = st.session_state.get('rotation_gif_start_time')
show_gif = False; refresh_interval = 30000
if gif_start_time:
    try:
        elapsed = (datetime.now() - gif_start_time).total_seconds()
        if elapsed < 20: show_gif = True; refresh_interval = 5000
        else: st.session_state.rotation_gif_start_time = None
    except: st.session_state.rotation_gif_start_time = None
st_autorefresh(interval=refresh_interval, key='auto_rerun_key')
if st.session_state.get('play_sound', False):
    st.components.v1.html(play_sound_html(), height=0, width=0); st.session_state.play_sound = False
if show_gif: st.image(GIF_URL_ROTATION, width=200, caption='Bastão Passado!')
if st.session_state.get('gif_warning', False):
    st.error('🚫 Ação inválida! Verifique as regras.'); st.image(GIF_URL_WARNING, width=150)

# Garantir Assunção Inicial
holder_exists = any(s == 'Bastão' for s in st.session_state.status_texto.values())
eligible_exists = any(not st.session_state.skip_flags.get(c, False) for c in st.session_state.bastao_queue if st.session_state.get(f'check_{c}'))
rerun_needed = False
if not holder_exists and st.session_state.bastao_queue and eligible_exists:
    print('!!! FORÇANDO CHECK ASSUME BASTÃO NO RENDER !!!')
    if not st.session_state.get('_assign_attempt', False):
        st.session_state._assign_attempt = True
        if check_and_assume_baton():
            print('--> Bastão reassumido no render, marcando para rerun...')
            rerun_needed = True
    else:
        print('AVISO: Segunda tentativa de assumir bastão no render evitada.')
if '_assign_attempt' in st.session_state: del st.session_state['_assign_attempt']


# Layout
col_principal, col_disponibilidade = st.columns([1.5, 1])
queue = st.session_state.bastao_queue
skips = st.session_state.skip_flags
responsavel = next((c for c, s in st.session_state.status_texto.items() if s == 'Bastão'), None)
current_index = queue.index(responsavel) if responsavel in queue else -1
proximo_index = find_next_holder_index(current_index, queue, skips)
proximo = queue[proximo_index] if proximo_index != -1 else None
restante = []
if proximo_index != -1: # If there is a 'next' person
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
        # --- Alteração: Tamanho 2em ---
        st.markdown(f'<span style="font-size: 2em; font-weight: bold;">{responsavel}</span>', unsafe_allow_html=True)
    else: st.markdown('<h2>(Ninguém com o bastão)</h2>', unsafe_allow_html=True)
    st.markdown("###")

    st.header("Próximos da Fila")
    if proximo:
        # --- Alteração: Tamanho padrão (H3) ---
        st.markdown(f'### 1º: **{proximo}**')
    if restante:
        st.markdown(f'#### 2º em diante: {", ".join(restante)}')
    if not proximo and not restante:
         if responsavel: st.markdown('*Apenas o responsável atual é elegível.*')
         elif queue and all(skips.get(c, False) or not st.session_state.get(f'check_{c}') for c in queue) : st.markdown('*Todos disponíveis estão marcados para pular...*')
         else: st.markdown('*Ninguém elegível na fila.*')
    elif not restante and proximo: st.markdown("&nbsp;")


    # --- Seção Pular (Estilo Ajustado) ---
    skipped_consultants = [c for c, is_skipped in skips.items() if is_skipped and st.session_state.get(f'check_{c}')]
    if skipped_consultants:
         skipped_text = ', '.join(sorted(skipped_consultants))
         num_skipped = len(skipped_consultants)
         # --- Alteração: Título amarelo/negrito, resto preto/normal ---
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
    # --- Fim Seção Pular ---

    st.markdown("###")
    st.header("**Consultor**")
    st.selectbox('Selecione:', options=['Selecione um nome'] + CONSULTORES, key='consultor_selectbox', label_visibility='collapsed')
    st.markdown("#### "); st.markdown("**Ações:**")
    c1, c2, c3, c4, c5 = st.columns(5)
    c1.button('🎯 Passar', on_click=rotate_bastao, use_container_width=True, help='Passa o bastão para o próximo elegível. Apenas o responsável atual.')
    c2.button('⏭️ Pular', on_click=toggle_skip, use_container_width=True, help='Marca/Desmarca o consultor selecionado para ser pulado na próxima rotação.')
    c3.button('✏️ Atividade', on_click=update_status, args=('Atividade', False,), use_container_width=True)
    c4.button('🍽️ Almoço', on_click=update_status, args=('Almoço', False,), use_container_width=True)
    c5.button('🚶 Saída', on_click=update_status, args=('Saída Temporária', False,), use_container_width=True)
    st.markdown("####")
    st.button('🔄 Atualizar (Manual)', on_click=manual_rerun, use_container_width=True)
    st.markdown("---")

# --- Coluna Disponibilidade ---
with col_disponibilidade:
    st.header('Status dos Consultores')
    st.markdown('Marque/Desmarque para entrar/sair.')
    ui_lists = {'fila': [], 'atividade': [], 'almoco': [], 'saida': [], 'indisponivel': []}
    for nome in CONSULTORES:
        is_checked = st.session_state.get(f'check_{nome}', False)
        status = st.session_state.status_texto.get(nome, '')
        if is_checked: ui_lists['fila'].append(nome)
        elif status == 'Atividade': ui_lists['atividade'].append(nome)
        elif status == 'Almoço': ui_lists['almoco'].append(nome)
        elif status == 'Saída Temporária': ui_lists['saida'].append(nome)
        else: ui_lists['indisponivel'].append(nome)

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
                display = f'<span style="background-color: #E75480; color: white; padding: 2px 6px; border-radius: 5px; font-weight: bold;">🔥 {nome}</span>'
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
                col_check.checkbox(' ', key=key, on_change=update_queue, args=(nome,), label_visibility='collapsed')
                col_nome.markdown(f'**{nome}** :{tag_color}-background[{title}]', unsafe_allow_html=True)
        st.markdown('---')

    render_section('Atividade', '✏️', ui_lists['atividade'], 'yellow')
    render_section('Almoço', '🍽️', ui_lists['almoco'], 'blue')
    render_section('Saída', '🚶', ui_lists['saida'], 'red')
    render_section('Indisponível', '❌', ui_lists['indisponivel'], 'grey')

    if datetime.now().hour >= 20 and datetime.now().date() > (st.session_state.report_last_run_date.date() if isinstance(st.session_state.report_last_run_date, datetime) else datetime.min.date()):
        send_daily_report()

print('--- FIM DO RENDER ---')

if rerun_needed:
    st.rerun()
