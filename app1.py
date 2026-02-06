# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd
import requests
import time
import gc
from datetime import datetime, timedelta, date
from operator import itemgetter
import json
import re
import base64
import io
import altair as alt
from supabase import create_client
from docx import Document
from docx.shared import Pt, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH

# Importação condicional
try:
    from streamlit_javascript import st_javascript
except ImportError:
    st_javascript = None

# Importações de utilitários
from utils import (get_brazil_time, get_secret, send_to_chat)

# ============================================
# 1. CONFIGURAÇÕES E CONSTANTES (EQUIPE ID 1)
# ============================================
DB_APP_ID = 1        # ID da Fila desta equipe
LOGMEIN_DB_ID = 1    # ID do LogMeIn (COMPARTILHADO - SEMPRE 1)

CONSULTORES = sorted([
    "Alex Paulo", "Dirceu Gonçalves", "Douglas De Souza", "Farley Leandro", "Gleis Da Silva", 
    "Hugo Leonardo", "Igor Dayrell", "Jerry Marcos", "Jonatas Gomes", "Leandro Victor", 
    "Luiz Henrique", "Marcelo Dos Santos", "Marina Silva", "Marina Torres", "Vanessa Ligiane"
])

# Listas de Opções
REG_USUARIO_OPCOES = ["Cartório", "Gabinete", "Externo"]
REG_SISTEMA_OPCOES = ["Conveniados", "Outros", "Eproc", "Themis", "JPE", "SIAP"]
REG_CANAL_OPCOES = ["Presencial", "Telefone", "Email", "Whatsapp", "Outros"]
REG_DESFECHO_OPCOES = ["Resolvido - Cesupe", "Escalonado"]

OPCOES_ATIVIDADES_STATUS = ["HP", "E-mail", "WhatsApp Plantão", "Homologação", "Redação Documentos", "Outros"]

# URLs e Visuais
GIF_BASTAO_HOLDER = "https://media2.giphy.com/media/v1.Y2lkPTc5MGI3NjExa3Uwazd5cnNra2oxdDkydjZkcHdqcWN2cng0Y2N0cmNmN21vYXVzMiZlcD12MV9pbnRlcm5uYWxfZ2lmX2J5X2lkJmN0PWc/3rXs5J0hZkXwTZjuvM/giphy.gif"
GIF_LOGMEIN_TARGET = "https://media1.giphy.com/media/v1.Y2lkPTc5MGI3NjExZjFvczlzd3ExMWc2cWJrZ3EwNmplM285OGFqOHE1MXlzdnd4cndibiZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/mcsPU3SkKrYDdW3aAU/giphy.gif"
BASTAO_EMOJI = "🎭" 
PUG2026_FILENAME = "Carnaval.gif" 
APP_URL_CLOUD = 'https://controle-bastao-equipe1.streamlit.app'

# Secrets
CHAT_WEBHOOK_BASTAO = get_secret("chat", "bastao")
WEBHOOK_STATE_DUMP = get_secret("webhook", "test_state")

# ============================================
# 2. OTIMIZAÇÃO E CONEXÃO (BLINDADA)
# ============================================

# TTL DE 1 HORA NA CONEXÃO
@st.cache_resource(ttl=3600)
def get_supabase():
    try: 
        return create_client(st.secrets["supabase"]["url"], st.secrets["supabase"]["key"])
    except Exception as e:
        st.cache_resource.clear()
        return None

@st.cache_data(ttl=86400, show_spinner=False)
def carregar_dados_grafico():
    sb = get_supabase()
    if not sb: return None, None
    try:
        res = sb.table("atendimentos_resumo").select("data").eq("id", DB_APP_ID).execute()
        if res.data:
            json_data = res.data[0]['data']
            if 'totais_por_relatorio' in json_data:
                df = pd.DataFrame(json_data['totais_por_relatorio'])
                return df, json_data.get('gerado_em', '-')
    except Exception: return None, None

@st.cache_data
def get_img_as_base64_cached(file_path):
    try:
        with open(file_path, "rb") as f:
            data = f.read()
        return base64.b64encode(data).decode()
    except: return None

# ============================================
# 3. REPOSITÓRIO (CACHE CURTO DE 2s)
# ============================================

def clean_data_for_db(obj):
    if isinstance(obj, dict):
        return {k: clean_data_for_db(v) for k, v in obj.items()}
    elif isinstance(obj, list):
        return [clean_data_for_db(i) for i in obj]
    elif isinstance(obj, (datetime, date)):
        return obj.isoformat()
    elif isinstance(obj, timedelta):
        return obj.total_seconds()
    else:
        return obj

# CACHE DE 2 SEGUNDOS: Protege o banco do "Efeito Manada" dos fragmentos
@st.cache_data(ttl=2, show_spinner=False)
def load_state_from_db():
    sb = get_supabase()
    if not sb: return {}
    try:
        response = sb.table("app_state").select("data").eq("id", DB_APP_ID).execute()
        if response.data and len(response.data) > 0:
            return response.data[0].get("data", {})
        return {}
    except: return {}

def save_state_to_db(state_data):
    sb = get_supabase()
    if not sb: return
    try:
        sanitized_data = clean_data_for_db(state_data)
        sb.table("app_state").upsert({"id": DB_APP_ID, "data": sanitized_data}).execute()
    except Exception as e: st.error(f"Erro DB: {e}")

# --- LOGMEIN DB ---
def get_logmein_status():
    sb = get_supabase()
    if not sb: return None, False
    try:
        res = sb.table("controle_logmein").select("*").eq("id", LOGMEIN_DB_ID).execute()
        if res.data:
            return res.data[0].get('consultor_atual'), res.data[0].get('em_uso', False)
    except: pass
    return None, False

def set_logmein_status(consultor, em_uso):
    sb = get_supabase()
    if not sb: return
    try:
        dados = {
            "consultor_atual": consultor if em_uso else None,
            "em_uso": em_uso,
            "data_inicio": datetime.now().isoformat()
        }
        sb.table("controle_logmein").update(dados).eq("id", LOGMEIN_DB_ID).execute()
    except: pass

# ============================================
# 4. FUNÇÕES DE UTILIDADE E IP
# ============================================
def get_browser_id():
    if st_javascript is None: return "no_js_lib"
    js_code = """(function() {
        let id = localStorage.getItem("device_id");
        if (!id) {
            id = "id_" + Math.random().toString(36).substr(2, 9);
            localStorage.setItem("device_id", id);
        }
        return id;
    })();"""
    try:
        return st_javascript(js_code, key="browser_id_tag")
    except: return "unknown_device"

def get_remote_ip():
    try:
        from streamlit.web.server.websocket_headers import ClientWebSocketRequest
        ctx = st.runtime.scriptrunner.get_script_run_ctx()
        if ctx and ctx.session_id:
            session_info = st.runtime.get_instance().get_client(ctx.session_id)
            if session_info:
                request = session_info.request
                if isinstance(request, ClientWebSocketRequest):
                    if 'X-Forwarded-For' in request.headers:
                        return request.headers['X-Forwarded-For'].split(',')[0]
                    return request.remote_ip
    except: return "Unknown"
    return "Unknown"

# --- LIMPEZA DE MEMÓRIA ---
def memory_sweeper():
    if 'last_cleanup' not in st.session_state:
        st.session_state.last_cleanup = time.time()
        return
    if time.time() - st.session_state.last_cleanup > 300:
        st.session_state.word_buffer = None 
        gc.collect()
        st.session_state.last_cleanup = time.time()
    
    if 'last_hard_cleanup' not in st.session_state:
        st.session_state.last_hard_cleanup = time.time()
        
    if time.time() - st.session_state.last_hard_cleanup > 14400: # 4h
        st.cache_data.clear()
        gc.collect()
        st.session_state.last_hard_cleanup = time.time()

# --- LÓGICA DE FILA VISUAL ---
def get_ordered_visual_queue(queue, status_dict):
    if not queue: return []
    current_holder = next((c for c, s in status_dict.items() if 'Bastão' in (s or '')), None)
    if not current_holder or current_holder not in queue: return list(queue)
    try:
        idx = queue.index(current_holder)
        return queue[idx:] + queue[:idx]
    except ValueError: return list(queue)

# ============================================
# 5. LOGICA DO SISTEMA
# ============================================
# (Funções de banco e Word mantidas simplificadas para caber, lógica é a mesma)
def verificar_duplicidade_certidao(tipo, processo=None, data=None):
    sb = get_supabase()
    if not sb: return False
    try:
        query = sb.table("certidoes_registro").select("*")
        if tipo in ['Físico', 'Eletrônico', 'Física', 'Eletrônica'] and processo:
            proc_limpo = str(processo).strip()
            if not proc_limpo: return False
            response = query.eq("processo", proc_limpo).execute()
            return len(response.data) > 0
        return False
    except: return False

def salvar_certidao_db(dados):
    sb = get_supabase()
    if not sb: return False
    try:
        if isinstance(dados.get('data'), (date, datetime)): dados['data'] = dados['data'].isoformat()
        if 'hora_periodo' in dados: del dados['hora_periodo']
        if 'n_processo' in dados: dados['processo'] = dados.pop('n_processo')
        if 'n_chamado' in dados: dados['incidente'] = dados.pop('n_chamado')
        if 'data_evento' in dados: dados['data'] = dados.pop('data_evento')
        sb.table("certidoes_registro").insert(dados).execute()
        return True
    except: return False

def gerar_docx_certidao_internal(tipo, numero, data, consultor, motivo, chamado="", hora="", nome_parte=""):
    try:
        doc = Document()
        section = doc.sections[0]
        section.top_margin = Cm(2.5); section.bottom_margin = Cm(2.0)
        section.left_margin = Cm(3.0); section.right_margin = Cm(3.0)
        style = doc.styles['Normal']; style.font.name = 'Arial'; style.font.size = Pt(11)
        head_p = doc.add_paragraph(); head_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        runner = head_p.add_run("TRIBUNAL DE JUSTIÇA DO ESTADO DE MINAS GERAIS\n")
        runner.bold = True
        head_p.add_run("Rua Ouro Preto, N° 1564 - Bairro Santo Agostinho - CEP 30170-041 - Belo Horizonte - MG\nwww.tjmg.jus.br - Andar: 3º e 4º PV\n")
        
        doc.add_paragraph(f"Parecer Técnico GEJUD/DIRTEC/TJMG nº ____/2026.")
        doc.add_paragraph(f"Belo Horizonte, {data}")
        doc.add_paragraph(f"Exmo(a). Senhor(a) Relator(a),")
        
        corpo = doc.add_paragraph(); corpo.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        corpo.add_run(f"Informamos que houve indisponibilidade do sistema para o processo {numero}. Motivo: {motivo}. Chamado: {chamado}.")
        
        doc.add_paragraph("\nRespeitosamente,\nWaner Andrade Silva")
        buffer = io.BytesIO(); doc.save(buffer); buffer.seek(0)
        return buffer
    except: return None

# Webhooks simplificados
def send_chat_notification_internal(consultor, status):
    if CHAT_WEBHOOK_BASTAO and status == 'Bastão':
        try: send_to_chat("bastao", f"🎉 **BASTÃO GIRADO!** 🎉 \n\n- **Novo(a):** {consultor}\n- **Painel:** {APP_URL_CLOUD}"); return True
        except: return False
    return False

def send_state_dump_webhook(state_data):
    if not WEBHOOK_STATE_DUMP: return False
    try:
        sanitized_data = clean_data_for_db(state_data)
        requests.post(WEBHOOK_STATE_DUMP, data=json.dumps(sanitized_data), headers={'Content-Type': 'application/json'}, timeout=5)
        return True
    except: return False

def send_horas_extras_to_chat(consultor, data, inicio, tempo, motivo):
    try: send_to_chat("extras", f"⏰ **Extra**\n👤 {consultor}\n📅 {data}\n🕐 {inicio}\n⏱️ {tempo}\n📝 {motivo}"); return True
    except: return False

def send_atendimento_to_chat(consultor, data, usuario, nome_setor, sistema, descricao, canal, desfecho, jira=""):
    try: send_to_chat("registro", f"📋 **Atendimento**\n👤 {consultor}\n📝 {descricao}\n✅ {desfecho}"); return True
    except: return False

def send_chamado_to_chat(consultor, texto):
    try: send_to_chat('chamado', f"🆘 **Chamado**\n👤 {consultor}\n📝 {texto}"); return True
    except: return False

def handle_erro_novidade_submission(consultor, titulo, obj, rel, res):
    try: send_to_chat("erro", f"🐛 **Erro/Novidade**\n👤 {consultor}\n📌 {titulo}"); return True
    except: return False

def handle_sugestao_submission(consultor, texto):
    try: send_to_chat("extras", f"💡 **Sugestão**\n👤 {consultor}\n📝 {texto}"); return True
    except: return False

# ============================================
# 7. GESTÃO DE ESTADO
# ============================================
def save_state():
    try:
        last_run = st.session_state.report_last_run_date
        visual_queue_calculated = get_ordered_visual_queue(st.session_state.bastao_queue, st.session_state.status_texto)
        state_to_save = {
            'status_texto': st.session_state.status_texto, 'bastao_queue': st.session_state.bastao_queue,
            'visual_queue': visual_queue_calculated, 'skip_flags': st.session_state.skip_flags, 
            'current_status_starts': st.session_state.current_status_starts,
            'bastao_counts': st.session_state.bastao_counts, 'priority_return_queue': st.session_state.priority_return_queue,
            'bastao_start_time': st.session_state.bastao_start_time, 
            'report_last_run_date': last_run, 
            'rotation_gif_start_time': st.session_state.get('rotation_gif_start_time'), 
            'auxilio_ativo': st.session_state.get('auxilio_ativo', False), 
            'daily_logs': st.session_state.daily_logs, 
            'simon_ranking': st.session_state.get('simon_ranking', []),
            'previous_states': st.session_state.get('previous_states', {})
        }
        save_state_to_db(state_to_save)
        # Importante: Limpa cache para todos verem a mudança
        load_state_from_db.clear()
    except Exception as e: print(f"Erro save: {e}")

def sync_state_from_db():
    try:
        db_data = load_state_from_db()
        if not db_data: return
        keys = ['status_texto', 'bastao_queue', 'skip_flags', 'bastao_counts', 'priority_return_queue', 'daily_logs', 'simon_ranking', 'previous_states']
        for k in keys:
            if k in db_data: 
                if k == 'daily_logs' and isinstance(db_data[k], list) and len(db_data[k]) > 150:
                    st.session_state[k] = db_data[k][-150:] 
                else:
                    st.session_state[k] = db_data[k]
        if 'bastao_start_time' in db_data:
            try: st.session_state['bastao_start_time'] = datetime.fromisoformat(db_data['bastao_start_time']) if isinstance(db_data['bastao_start_time'], str) else db_data['bastao_start_time']
            except: pass
        if 'current_status_starts' in db_data:
            for nome, val in db_data['current_status_starts'].items():
                try: st.session_state.current_status_starts[nome] = datetime.fromisoformat(val) if isinstance(val, str) else val
                except: pass
    except Exception as e: print(f"Erro sync: {e}")

def log_status_change(consultor, old_status, new_status, duration):
    if not isinstance(duration, timedelta): duration = timedelta(0)
    now_br = get_brazil_time()
    st.session_state.daily_logs.append({
        'timestamp': now_br, 'consultor': consultor, 
        'old_status': old_status or 'Fila', 'new_status': new_status or 'Fila', 
        'duration': duration, 'ip': st.session_state.get('device_id_val', 'unknown')
    })
    if len(st.session_state.daily_logs) > 150: st.session_state.daily_logs = st.session_state.daily_logs[-150:]
    st.session_state.current_status_starts[consultor] = now_br

# --- LOGICA DE STATUS ---
def update_status(novo_status: str, marcar_indisponivel: bool = False, manter_fila_atual: bool = False):
    selected = st.session_state.get('consultor_selectbox')
    if not selected or selected == 'Selecione um nome': return
    ensure_daily_reset()
    now_br = get_brazil_time()
    current = st.session_state.status_texto.get(selected, '')
    forced_successor = None
    current_holder = next((c for c, s in st.session_state.status_texto.items() if 'Bastão' in (s or '')), None)
    
    if novo_status == 'Almoço':
        st.session_state.previous_states[selected] = {'status': current, 'in_queue': selected in st.session_state.bastao_queue}
    
    if marcar_indisponivel and selected in st.session_state.bastao_queue:
        if selected == current_holder:
            idx = st.session_state.bastao_queue.index(selected)
            nxt = find_next_holder_index(idx, st.session_state.bastao_queue, st.session_state.skip_flags)
            if nxt != -1: forced_successor = st.session_state.bastao_queue[nxt]
        st.session_state.bastao_queue.remove(selected)
        st.session_state[f'check_{selected}'] = False
        st.session_state.skip_flags[selected] = True
        if selected not in st.session_state.priority_return_queue: st.session_state.priority_return_queue.append(selected)
    elif not manter_fila_atual:
        if selected not in st.session_state.bastao_queue: st.session_state.bastao_queue.append(selected)
        st.session_state[f'check_{selected}'] = True
        st.session_state.skip_flags[selected] = False
    
    final_status = (novo_status or '').strip()
    if selected == current_holder and selected in st.session_state.bastao_queue:
          final_status = ('Bastão | ' + final_status).strip(' |')
    if not final_status and (selected not in st.session_state.bastao_queue): final_status = 'Indisponível'
    
    log_status_change(selected, current, final_status, now_br - st.session_state.current_status_starts.get(selected, now_br))
    st.session_state.status_texto[selected] = final_status
    check_and_assume_baton(forced_successor)
    save_state()

def auto_manage_time():
    now = get_brazil_time()
    if now.date() > st.session_state.report_last_run_date.date(): reset_day_state(); save_state()

def find_next_holder_index(current_index, queue, skips):
    if not queue: return -1
    n = len(queue); start_index = (current_index + 1) % n
    for i in range(n):
        idx = (start_index + i) % n
        if not skips.get(queue[idx], False): return idx
    if n > 1:
        proximo = (current_index + 1) % n
        st.session_state.skip_flags[queue[proximo]] = False
        return proximo
    return -1

def check_and_assume_baton(forced_successor=None):
    queue, skips = st.session_state.bastao_queue, st.session_state.skip_flags
    current_holder = next((c for c, s in st.session_state.status_texto.items() if 'Bastão' in s), None)
    target = forced_successor
    
    if not target:
        curr_idx = queue.index(current_holder) if (current_holder and current_holder in queue) else -1
        idx = find_next_holder_index(curr_idx, queue, skips)
        target = queue[idx] if idx != -1 else None
        
    changed = False; now = get_brazil_time()
    
    if target:
        curr_s = st.session_state.status_texto.get(target, '')
        if 'Bastão' not in curr_s:
            st.session_state.status_texto[target] = f"Bastão | {curr_s}" if curr_s and curr_s != "Indisponível" else "Bastão"
            st.session_state.bastao_start_time = now
            if current_holder != target: st.session_state.play_sound = True; send_chat_notification_internal(target, 'Bastão')
            st.session_state.skip_flags[target] = False
            changed = True
            
            # Remove bastão do anterior
            if current_holder and current_holder != target:
                 st.session_state.status_texto[current_holder] = 'Indisponível'
                 
    elif not target and current_holder:
        st.session_state.status_texto[current_holder] = 'Indisponível'; changed = True
            
    if changed: save_state()

def init_session_state():
    dev_id = get_browser_id(); 
    if dev_id: st.session_state['device_id_val'] = dev_id
    if 'db_loaded' not in st.session_state:
        st.session_state.update(load_state_from_db())
        st.session_state['db_loaded'] = True
    
    defaults = {
        'bastao_start_time': None, 'report_last_run_date': datetime.min, 'rotation_gif_start_time': None,
        'play_sound': False, 'gif_warning': False, 'lunch_warning_info': None,
        'chamado_guide_step': 0, 'auxilio_ativo': False, 'active_view': None,
        'consultor_selectbox': "Selecione um nome", 'status_texto': {nome: 'Indisponível' for nome in CONSULTORES},
        'bastao_queue': [], 'skip_flags': {}, 'current_status_starts': {nome: get_brazil_time() for nome in CONSULTORES},
        'bastao_counts': {nome: 0 for nome in CONSULTORES}, 'priority_return_queue': [], 'daily_logs': [], 'simon_ranking': [],
        'word_buffer': None, 'aviso_duplicidade': False, 'previous_states': {}, 'view_logmein_ui': False,
        'last_cleanup': time.time(), 'last_hard_cleanup': time.time()
    }
    for key, default in defaults.items():
        if key not in st.session_state: st.session_state[key] = default
        
    for nome in CONSULTORES:
        st.session_state.skip_flags.setdefault(nome, False)
        st.session_state[f'check_{nome}'] = nome in st.session_state.bastao_queue

def reset_day_state():
    st.session_state.bastao_queue = []
    st.session_state.status_texto = {n: 'Indisponível' for n in CONSULTORES}
    st.session_state.daily_logs = []
    st.session_state.report_last_run_date = get_brazil_time()

def ensure_daily_reset():
    now_br = get_brazil_time()
    if now_br.date() > st.session_state.report_last_run_date.date():
        if st.session_state.daily_logs: send_daily_report_to_webhook()
        reset_day_state(); save_state()

def toggle_queue(consultor):
    ensure_daily_reset()
    if consultor in st.session_state.bastao_queue:
        current_holder = next((c for c, s in st.session_state.status_texto.items() if 'Bastão' in s), None)
        forced_successor = None
        if consultor == current_holder:
            idx = st.session_state.bastao_queue.index(consultor)
            nxt = find_next_holder_index(idx, st.session_state.bastao_queue, st.session_state.skip_flags)
            if nxt != -1: forced_successor = st.session_state.bastao_queue[nxt]
        st.session_state.bastao_queue.remove(consultor)
        st.session_state.status_texto[consultor] = 'Indisponível'
        check_and_assume_baton(forced_successor)
    else:
        st.session_state.bastao_queue.append(consultor)
        st.session_state.skip_flags[consultor] = False
        if consultor in st.session_state.priority_return_queue: st.session_state.priority_return_queue.remove(consultor)
        st.session_state.status_texto[consultor] = ''
        check_and_assume_baton()
    save_state()

def rotate_bastao():
    ensure_daily_reset(); selected = st.session_state.consultor_selectbox
    if not selected or selected == 'Selecione um nome': st.warning('Selecione um(a) consultor(a).'); return
    
    queue = st.session_state.bastao_queue
    current_holder = next((c for c, s in st.session_state.status_texto.items() if 'Bastão' in s), None)
    
    if selected != current_holder: st.error(f"Apenas {current_holder} pode passar!"); return
        
    current_index = queue.index(current_holder) if current_holder in queue else -1
    next_idx = find_next_holder_index(current_index, queue, st.session_state.skip_flags)
    
    if next_idx != -1:
        next_holder = queue[next_idx]
        st.session_state.skip_flags[next_holder] = False
        st.session_state.status_texto[current_holder] = st.session_state.status_texto[current_holder].replace('Bastão', '').strip()
        st.session_state.status_texto[next_holder] = "Bastão"
        st.session_state.bastao_start_time = get_brazil_time()
        send_chat_notification_internal(next_holder, 'Bastão')
        save_state()
    else: st.warning('Ninguém elegível.'); check_and_assume_baton()

def toggle_skip():
    selected = st.session_state.consultor_selectbox
    if selected not in st.session_state.bastao_queue: return
    st.session_state.skip_flags[selected] = not st.session_state.skip_flags.get(selected, False)
    save_state()

def toggle_presence_btn():
    selected = st.session_state.consultor_selectbox
    if selected and selected != 'Selecione um nome': toggle_queue(selected)

# ============================================
# 8. INTERFACE (FRAGMENTADA)
# ============================================
st.set_page_config(page_title="Controle Bastão Cesupe", layout="wide", page_icon="🎭")
st.markdown("""<style>div.stButton > button {width: 100%; height: 3rem;}</style>""", unsafe_allow_html=True)

init_session_state(); memory_sweeper(); auto_manage_time()

# ----------------------------------------------------
# FRAGMENTO PRINCIPAL (ATUALIZA A CADA 10 SEGUNDOS)
# ----------------------------------------------------
@st.fragment(run_every=10)
def painel_principal():
    # 1. Sincroniza estado (Rápido devido ao cache de 2s)
    sync_state_from_db()
    
    # 2. Topo
    c_topo_esq, c_topo_dir = st.columns([2, 1], vertical_alignment="bottom")
    with c_topo_esq:
        img = get_img_as_base64_cached(PUG2026_FILENAME); src = f"data:image/png;base64,{img}" if img else GIF_BASTAO_HOLDER
        st.markdown(f"""<div style="display: flex; align-items: center; gap: 15px;"><h1 style="color: #FF8C00;">Controle Bastão {BASTAO_EMOJI}</h1><img src="{src}" style="width: 80px; height: 80px; border-radius: 10px;"></div>""", unsafe_allow_html=True)
    with c_topo_dir:
        # Ações rápidas dentro do fragmento funcionam e atualizam o estado
        c_sub1, c_sub2 = st.columns([2, 1], vertical_alignment="bottom")
        novo_responsavel = c_sub1.selectbox("Assumir (Rápido)", ["Selecione"] + CONSULTORES, label_visibility="collapsed")
        if c_sub2.button("🚀 Entrar"):
            if novo_responsavel != "Selecione": toggle_queue(novo_responsavel); st.rerun()

    st.markdown("<hr style='border: 1px solid #FF8C00; margin: 10px 0;'>", unsafe_allow_html=True)

    # 3. Corpo Principal
    col_principal, col_disponibilidade = st.columns([1.5, 1])
    queue = st.session_state.bastao_queue
    responsavel = next((c for c, s in st.session_state.status_texto.items() if 'Bastão' in s), None)
    
    with col_principal:
        st.subheader("Responsável pelo Bastão")
        if responsavel:
            st.markdown(f"""<div style="background: #FFF3E0; border: 3px solid #FF8C00; padding: 20px; border-radius: 15px; display: flex; align-items: center;"><img src="{GIF_BASTAO_HOLDER}" style="width: 80px; height: 80px; border-radius: 50%; margin-right: 20px;"><div><span style="font-size: 36px; font-weight: 800; color: #FF4500;">{responsavel}</span></div></div>""", unsafe_allow_html=True)
        else: st.markdown('**(Ninguém com o bastão)**')
        
        # Grid de Ações (Inputs mantêm estado dentro do fragmento)
        st.markdown("### Ações")
        c_nome, c_act1, c_act2, c_act3 = st.columns([2, 1, 1, 1], vertical_alignment="bottom")
        st.session_state.consultor_selectbox = c_nome.selectbox('Selecione:', ['Selecione um nome'] + CONSULTORES, key='main_select')
        
        if c_act1.button("🎭 Fila"): toggle_presence_btn(); st.rerun()
        if c_act2.button('🎯 Passar'): rotate_bastao(); st.rerun()
        if c_act3.button('⏭️ Pular'): toggle_skip(); st.rerun()
        
        r2c1, r2c2, r2c3, r2c4, r2c5 = st.columns(5)
        if r2c1.button('📋 Ativ.'): update_status("Atividade", True, True); st.rerun() # Simplificado para teste
        if r2c2.button('🍽️ Almoço'): update_status('Almoço', True); st.rerun()
        if r2c3.button('🏃 Sair'): update_status('Indisponível', True); st.rerun()
        if r2c4.button('🔄 Refresh'): st.rerun()
        
        # LogMeIn simplificado no fragmento
        if st.button('🔑 LogMeIn'): 
            l_user, l_in_use = get_logmein_status()
            if l_in_use: st.error(f"Em uso por: {l_user}")
            else: 
                meu_nome = st.session_state.consultor_selectbox
                if meu_nome != 'Selecione um nome': set_logmein_status(meu_nome, True); st.rerun()
                else: st.warning("Selecione nome")

    with col_disponibilidade:
        st.subheader(f'✅ Na Fila ({len(queue)})')
        for i, nome in enumerate(get_ordered_visual_queue(queue, st.session_state.status_texto)):
            extra = '⏭️' if st.session_state.skip_flags.get(nome) else ''
            st.markdown(f"**{i+1}. {nome}** {extra}")
            
        st.markdown("---")
        st.subheader("Ausentes/Ocupados")
        for nome, status in st.session_state.status_texto.items():
            if nome not in queue and status and status != 'Indisponível':
                st.write(f"**{nome}**: {status}")

# Executa o fragmento principal
painel_principal()

# Ferramentas extras fora do fragmento (carregam sob demanda)
with st.expander("🛠️ Ferramentas (Clique para abrir)"):
    tab1, tab2, tab3 = st.tabs(["Chamados", "Certidão", "Gráfico"])
    with tab1:
        txt = st.text_area("Texto Chamado")
        if st.button("Enviar Chamado"): handle_chamado_submission(); st.success("Enviado")
    with tab2:
        st.write("Certidão aqui...")
    with tab3:
        df, _ = carregar_dados_grafico()
        if df is not None: st.dataframe(df)
