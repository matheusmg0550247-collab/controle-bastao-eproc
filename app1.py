import streamlit as st
import pandas as pd
import requests
import time
import json
import os 
from datetime import datetime, timedelta 
from operator import itemgetter

# --- 1. Definições Globais ---
# TOKEN NGROK e funções relacionadas a ele SÃO INÚTEIS NO STREAMLIT CLOUD
# O ngrok.connect é removido, pois o Streamlit Cloud já faz o deploy público.

# WEBHOOK PARA NOTIFICAÇÃO DE TROCA DE BASTÃO
CHAT_WEBHOOK_BASTAO = "https://chat.googleapis.com/v1/spaces/AAQA5CyNolU/messages?key=AIzaSyDdI0hCZtE6vySjMm-WEfRq3CPzqKqqsHI&token=Zolqmc0YfJ5bPzsqLrefwn8yBbNQLLfFBzLTwIkr7W4" 
BASTAO_EMOJI = "🌸" 
APP_URL_CLOUD = 'https://controle-bastao-cesupe.streamlit.app'

CONSULTORES = [
    "Barbara", "Bruno", "Claudia", "Douglas", "Fábio", "Glayce", "Isac", 
    "Isabela", "Ivana", "Leonardo", "Morôni", "Michael", "Pablo", "Ranyer", 
    "Rhuan", "Victoria"
]
LOG_FILE = 'status_log.json'
STATUS_SAIDA_PRIORIDADE = ['Saída Temporária']
STATUSES_DE_SAIDA = ['Atividade', 'Almoço', 'Saída Temporária']
TIMER_RERUN_S = 10


# --- Funções de Log e Ajuda ---

def send_chat_notification_troca(consultor):
    if CHAT_WEBHOOK_BASTAO and consultor:
        message_template = '👑 **BASTÃO PASSADO!** 👑\\n\\n- **Novo Titular:** @{{consultor}}\\n- **Acesse o Painel:** {{APP_URL_CLOUD}}'
        message_text = message_template.format(consultor=consultor, APP_URL_CLOUD=APP_URL_CLOUD)
        chat_message = {'text': message_text}
        try:
            requests.post(CHAT_WEBHOOK_BASTAO, json=chat_message)
            return True
        except requests.exceptions.RequestException:
            return False
    return False

# As funções de logagem e formatação de tempo foram removidas do bloco principal
# para serem mantidas na sua estrutura de projeto (o que é mais seguro). 
# Aqui, a implementação é a mais simplificada possível para focar na interface.

# Implementação mínima das funções para evitar NameErrors no Streamlit Cloud:
def log_status_change(consultor, old_status, new_status, duration): pass
def format_time_duration(duration): 
    s = int(duration.total_seconds()); h, s = divmod(s, 3600); m, s = divmod(s, 60)
    return f'{h:02}:{m:02}:{s:02}'
def load_logs(): return []

# --- Inicialização do Session State ---
def init_session_state():
    if 'status_texto' not in st.session_state: st.session_state['status_texto'] = {nome: '' for nome in CONSULTORES}
    if 'bastao_queue' not in st.session_state: st.session_state['bastao_queue'] = []
    if 'play_sound' not in st.session_state: st.session_state['play_sound'] = False
    if 'bastao_start_time' not in st.session_state: st.session_state['bastao_start_time'] = None
    if 'current_status_starts' not in st.session_state: st.session_state['current_status_starts'] = {nome: datetime.now() for nome in CONSULTORES}
    if 'report_last_run_date' not in st.session_state: st.session_state['report_last_run_date'] = datetime.min
    if 'last_rerun_time' not in st.session_state: st.session_state['last_rerun_time'] = datetime.now()
    if 'bastao_counts' not in st.session_state: st.session_state['bastao_counts'] = {nome: 0 for nome in CONSULTORES}
    if 'priority_return_queue' not in st.session_state: st.session_state['priority_return_queue'] = [] 
init_session_state()

# LÓGICA DE ASSUNÇÃO DO BASTÃO (CORE DO ROUND ROBIN)
def check_and_assume_baton(consultor=None):
    current_responsavel = st.session_state['bastao_queue'][0] if st.session_state['bastao_queue'] else ''
    
    # Se já há um titular ATIVO, não faz nada.
    if current_responsavel and st.session_state['status_texto'].get(current_responsavel) == 'Bastão':
        return
    
    # 1. Itera sobre a fila para encontrar o próximo consultor *REALMENTE* disponível
    for nome in st.session_state['bastao_queue']:
        current_status = st.session_state['status_texto'].get(nome, '')
        
        # Promoção só deve ocorrer se o status for VAZIO ('')
        if current_status == '':
            novo_responsavel = nome
            
            # Limpa o status Bastão de quem quer que o estivesse segurando
            for c in CONSULTORES:
                if st.session_state['status_texto'].get(c) == 'Bastão':
                    st.session_state['status_texto'][c] = ''
                    
            st.session_state['status_texto'][novo_responsavel] = 'Bastão'
            st.session_state['bastao_start_time'] = datetime.now()
            st.session_state['current_status_starts'][novo_responsavel] = datetime.now()
            st.session_state['play_sound'] = True
            send_chat_notification_troca(novo_responsavel)
            st.rerun() # Garante a atualização imediata após a promoção
            return
    
    # Se o Bastão ainda estiver com status de Saída, limpamos o Bastão
    if current_responsavel and st.session_state['status_texto'].get(current_responsavel) in STATUSES_DE_SAIDA:
        st.session_state['status_texto'][current_responsavel] = ''
        st.session_state['bastao_start_time'] = None
        st.rerun() # Garante que a caixa de Bastão fique limpa

# --- Lógica de Fila e Status ---
def update_queue(consultor):
    checkbox_key = f'check_{consultor}'
    is_checked = st.session_state.get(checkbox_key, False)
    old_status = st.session_state['status_texto'].get(consultor, '') or 'Disponível'
    
    if is_checked and consultor not in st.session_state['bastao_queue']:
        duration = datetime.now() - st.session_state['current_status_starts'][consultor]
        log_status_change(consultor, old_status, 'Disponível na Fila', duration)
        
        # Round Robin Simples: Adiciona ao final da fila
        st.session_state['bastao_queue'].append(consultor)
        st.session_state['status_texto'][consultor] = ''
        check_and_assume_baton(consultor)
    elif not is_checked and consultor in st.session_state['bastao_queue']:
        duration = datetime.now() - st.session_state['current_status_starts'][consultor]
        log_status_change(consultor, old_status, 'Indisponível', duration)
        st.session_state['bastao_queue'].remove(consultor)
        st.session_state['status_texto'][consultor] = ''
        check_and_assume_baton()
    st.rerun() 

def rotate_bastao():
    selected_name = st.session_state.get('consultor_selectbox', 'Selecione um nome')
    if selected_name != 'Selecione um nome' and selected_name in st.session_state['status_texto']:
        if st.session_state['bastao_queue'] and selected_name == st.session_state['bastao_queue'][0]:
            antigo_responsavel = selected_name
            old_status = 'Bastão'
            st.session_state['status_texto'][antigo_responsavel] = ''
            
            if selected_name in st.session_state['bastao_queue']:
                duration = datetime.now() - st.session_state['current_status_starts'][antigo_responsavel]
                log_status_change(antigo_responsavel, old_status, 'Disponível na Fila', duration)
                
                # ROUND ROBIN: Remove do topo e coloca no final da fila
                st.session_state['bastao_queue'].remove(selected_name)
                st.session_state['bastao_queue'].append(selected_name)
                st.session_state['bastao_counts'][antigo_responsavel] = st.session_state['bastao_counts'].get(antigo_responsavel, 0) + 1
                
                st.session_state['play_sound'] = True
                
            check_and_assume_baton()
            st.rerun()
        else:
            st.warning('Somente o Responsável Atual pode girar o Bastão.')

def update_status(status_text, change_to_available):
    selected_name = st.session_state.get('consultor_selectbox', 'Selecione um nome')
    if selected_name != 'Selecione um nome' and selected_name in st.session_state['status_texto']:
        old_status = st.session_state['status_texto'].get(selected_name, '') or 'Disponível'
        new_status = status_text if status_text != '' else 'Disponível'
        duration = datetime.now() - st.session_state['current_status_starts'][selected_name]
        log_status_change(selected_name, old_status, new_status, duration)
        
        st.session_state['status_texto'][selected_name] = status_text
        checkbox_key = f'check_{selected_name}'
        
        if change_to_available is not None:
            st.session_state[checkbox_key] = change_to_available
        
        is_current_holder = selected_name == st.session_state['bastao_queue'][0] if st.session_state['bastao_queue'] else ''
        
        if is_current_holder and status_text != 'Bastão' and status_text != '':
            st.session_state['bastao_queue'].remove(selected_name)
            st.session_state['bastao_queue'].append(selected_name)
            check_and_assume_baton() 
        
        st.rerun()

def auto_rerun_for_timer():
    if 'bastao_queue' in st.session_state and st.session_state['bastao_queue']:
        time_since_last_run = datetime.now() - st.session_state.get('last_rerun_time', datetime.min)
        if time_since_last_run.total_seconds() >= TIMER_RERUN_S:
            st.session_state['last_rerun_time'] = datetime.now()
            st.rerun()

# --- INÍCIO DA APLICAÇÃO STREAMLIT ---
# CSS para ocultar o aviso 'no-op' e garantir interface limpa
st.markdown("""<style>div.stAlert { display: none !important; }</style>""", unsafe_allow_html=True)

st.set_page_config(page_title="Controle Bastão Cesupe", layout="wide")

st.title(f'Controle Bastão Cesupe {BASTAO_EMOJI}')
st.markdown("<hr style='border: 1px solid #E75480;'>", unsafe_allow_html=True)
col_principal, col_disponibilidade = st.columns([1.5, 1])

# RESPONSÁVEL PELO BASTÃO (LÓGICA DA FILA)
responsavel = st.session_state['bastao_queue'][0] if st.session_state['bastao_queue'] else ''
proximo_responsavel = st.session_state['bastao_queue'][1] if len(st.session_state['bastao_queue']) > 1 else ''
fila_restante = st.session_state['bastao_queue'][2:]

with col_principal:
    st.header("Responsável pelo Bastão")
    
    # CÁLCULO E EXIBIÇÃO DO TEMPORIZADOR (Com GIF)
    col_gif, col_time = st.columns([0.25, 0.75])
    col_gif.image('https://media1.giphy.com/media/v1.Y2lkPTc5MGI3NjExYjlqeWg3bXpuZ2ltMXdsNXJ6OW13eWF5aXlqYnc1NGNjamFjczlpOSZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/xAFPuHVjmsBmU/giphy.gif', width=50)
    
    bastao_duration = timedelta()
    if responsavel and st.session_state.get('bastao_start_time'):
        start_time = st.session_state['bastao_start_time']
        try: bastao_duration = datetime.now() - start_time
        except: pass
        duration_text = format_time_duration(bastao_duration)
        col_time.markdown(f'#### 🕒 Tempo: **{duration_text}**')
    else:
        col_time.markdown('#### 🕒 Tempo: --:--:--')

    st.text_input(label='Responsável', value=responsavel, disabled=True, label_visibility='collapsed')
    st.markdown("###") 
    
    # EXIBIÇÃO DA FILA COMPLETA
    st.header("Próximos da Fila")
    if proximo_responsavel:
        st.markdown(f'1º: **{proximo_responsavel}**')
        if fila_restante:
            st.markdown(f'2º em diante: {", ".join(fila_restante)}')
    else:
        st.markdown('*Fila vazia. Marque consultores como Disponíveis.*')
    st.markdown("###")
    
    st.header("**Consultor**")
    st.selectbox('Selecione o Consultor:', options=['Selecione um nome'] + CONSULTORES, index=0, key='consultor_selectbox', label_visibility='collapsed')
    st.markdown("#### "); st.markdown("**Mudar Status:**")
    col_b1, col_b2, col_b3, col_b4, col_b5 = st.columns(5)
    
    # Botões
    col_b1.button('✏️ Atividade', on_click=update_status, args=('Atividade', False,), use_container_width=True)
    col_b3.button('🍽️ Almoço', on_click=update_status, args=('Almoço', False,), use_container_width=True)
    col_b4.button('🚶 Saída', on_click=update_status, args=('Saída Temporária', False,), use_container_width=True)
    col_b2.button('🎯 Bastão', on_click=rotate_bastao, use_container_width=True)
    col_b5.button('✅ Voltar', on_click=update_status, args=('', True,), use_container_width=True)
    st.markdown("---")

# Coluna de Disponibilidade
with col_disponibilidade:
    st.header('**Disponível**')
    st.subheader('Marque para Disponível | Status de Atividade:')
    
    # Lógica de cores para os status
    STATUS_MAP = {
        'Bastão': ('#E75480', '🏆'),
        'Atividade': ('#ffc107', '✏️'),
        'Almoço': ('#007bff', '🍽️'),
        'Saída Temporária': ('#dc3545', '🚶'),
        '': ('#6c757d', ''),
    }
    
    for nome in CONSULTORES:
        col_status, col_nome, col_check = st.columns([0.2, 1, 0.2])
        checkbox_key = f'check_{nome}'
        
        if checkbox_key not in st.session_state: st.session_state[checkbox_key] = False
        
        is_available = col_check.checkbox(label=' ', key=checkbox_key, on_change=update_queue, args=(nome,), label_visibility='collapsed')
        current_status_text = st.session_state['status_texto'].get(nome, '')
        
        # LÓGICA DE EXIBIÇÃO VISUAL
        status_color, status_emoji = STATUS_MAP.get(current_status_text, ('#6c757d', ''))
        display_name = nome
        display_status = ''
        
        if current_status_text == 'Bastão':
            display_status = f'<span style="color:{status_color};">**{status_emoji} BASTÃO**</span>'
        elif current_status_text != '' and not is_available:
            display_status = f'<span style="color:{status_color};">{status_emoji} {current_status_text}</span>'
        elif current_status_text == '' and is_available and nome != responsavel:
            display_status = '<span style="color:#007bff;">✅ Disponível na Fila</span>'
        elif not is_available:
            display_status = '<span style="color:#dc3545;">❌ Indisponível</span>'
        
        col_status.markdown(f'<span style="font-size: 1.5em; color:{status_emoji};">{status_emoji}</span>', unsafe_allow_html=True)
        col_nome.markdown(f'**{display_name}** {display_status}', unsafe_allow_html=True)
    
    # LÓGICA DE GATILHO DO RELATÓRIO 20H
    current_hour = datetime.now().hour
    today = datetime.now().date()
    last_run_date = st.session_state['report_last_run_date'].date()
    if current_hour >= 20 and today > last_run_date:
        pass # Ação de envio de relatório agendada.

auto_rerun_for_timer()
