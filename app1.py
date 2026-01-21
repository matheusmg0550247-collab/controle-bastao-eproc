# -*- coding: utf-8 -*-
import streamlit as st
import pandas as pd
import requests
import time
from datetime import datetime, timedelta
from operator import itemgetter
from streamlit_autorefresh import st_autorefresh
import json
import re
import base64
import io
import altair as alt
from supabase import create_client
from docx import Document
from docx.shared import Pt, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH

# Importações locais (Certifique-se que repository.py e utils.py estão na mesma pasta)
from repository import load_state_from_db, save_state_to_db
from utils import (get_brazil_time, get_secret, send_to_chat, get_img_as_base64)

# ============================================
# 1. CONFIGURAÇÕES E CONSTANTES
# ============================================
CONSULTORES = sorted([
    "Alex Paulo", "Dirceu Gonçalves", "Douglas De Souza", "Farley Leandro", "Gleis Da Silva", 
    "Hugo Leonardo", "Igor Dayrell", "Jerry Marcos", "Jonatas Gomes", "Leandro Victor", 
    "Luiz Henrique", "Marcelo Dos Santos", "Marina Silva", "Marina Torres", "Vanessa Ligiane"
])

# --- LISTAS DE OPÇÕES (ESSENCIAIS PARA O MENU DE ATENDIMENTO) ---
REG_USUARIO_OPCOES = ["Cartório", "Gabinete", "Externo"]
REG_SISTEMA_OPCOES = ["Conveniados", "Outros", "Eproc", "Themis", "JPE", "SIAP"]
REG_CANAL_OPCOES = ["Presencial", "Telefone", "Email", "Whatsapp", "Outros"]
REG_DESFECHO_OPCOES = ["Resolvido - Cesupe", "Escalonado"]

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
OPCOES_ATIVIDADES_STATUS = ["HP", "E-mail", "WhatsApp Plantão", "Homologação", "Redação Documentos", "Outros"]
OPCOES_PROJETOS = ["Soma", "Treinamentos Eproc", "Manuais Eproc", "Cartilhas Gabinetes", "Notebook Lm", "Inteligência artifical cartórios"]

GIF_BASTAO_HOLDER = "https://media2.giphy.com/media/v1.Y2lkPTc5MGI3NjExa3Uwazd5cnNra2oxdDkydjZkcHdqcWN2cng0Y2N0cmNmN21vYXVzMiZlcD12MV9pbnRlcm5uYWxfZ2lmX2J5X2lkJmN0PWc/3rXs5J0hZkXwTZjuvM/giphy.gif"
BASTAO_EMOJI = "🥂" 
PUG2026_FILENAME = "pug2026.png"
APP_URL_CLOUD = 'https://controle-bastao-cesupe.streamlit.app'

# Webhooks (Secrets)
CHAT_WEBHOOK_BASTAO = get_secret("chat", "bastao")

def get_supabase():
    try: return create_client(st.secrets["supabase"]["url"], st.secrets["supabase"]["key"])
    except: return None

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
# 2. LÓGICA DE BANCO / CERTIDÃO
# ============================================
def verificar_duplicidade_certidao(tipo, n_processo=None, data_evento=None, hora_periodo=None):
    sb = get_supabase()
    if not sb: return False
    try:
        query = sb.table("certidoes_registro").select("*").eq("tipo", tipo)
        if tipo in ['Física', 'Eletrônica'] and n_processo:
            proc_limpo = str(n_processo).strip().rstrip('.')
            if not proc_limpo: return False
            response = query.ilike("n_processo", f"%{proc_limpo}%").execute()
            return len(response.data) > 0
        elif tipo == 'Geral' and data_evento:
            data_str = data_evento.isoformat() if hasattr(data_evento, 'isoformat') else str(data_evento)
            query = query.eq("data_evento", data_str)
            if hora_periodo: query = query.eq("hora_periodo", hora_periodo)
            response = query.execute()
            return len(response.data) > 0
    except: return False
    return False

def salvar_certidao_db(dados):
    sb = get_supabase()
    if not sb: return False
    try:
        sb.table("certidoes_registro").insert(dados).execute()
        return True
    except: return False

def gerar_docx_certidao_internal(tipo, numero, data, consultor, motivo, chamado="", hora=""):
    try:
        doc = Document()
        section = doc.sections[0]
        section.top_margin = Cm(2.5); section.bottom_margin = Cm(2.0)
        section.left_margin = Cm(3.0); section.right_margin = Cm(3.0)
        style = doc.styles['Normal']; style.font.name = 'Arial'; style.font.size = Pt(11)
        head_p = doc.add_paragraph(); head_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        runner = head_p.add_run("TRIBUNAL DE JUSTIÇA DO ESTADO DE MINAS GERAIS\n")
        runner.bold = True
        head_p.add_run("Rua Ouro Preto, N° 1564 - Bairro Santo Agostinho - CEP 30170-041 - Belo Horizonte - MG\nwww.tjmg.jus.br - Andar: 3º e 4º PV")
        doc.add_paragraph("\n")
        p_num = doc.add_paragraph(f"Parecer Técnico GEJUD/DIRTEC/TJMG nº ____/2025.")
        p_num.runs[0].bold = True
        doc.add_paragraph("Assunto: Notifica erro no \"JPe - 2ª Instância\" ao peticionar.")
        data_atual = datetime.now().strftime("%d de %B de %Y")
        doc.add_paragraph(f"\nExmo(a). Senhor(a) Relator(a),\n\nBelo Horizonte, {data_atual}")
        corpo = doc.add_paragraph(); corpo.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        if tipo == 'Geral':
            txt = (f"Para fins de cumprimento dos artigos 13 e 14 da Resolução nº 780/2014 do Tribunal de Justiça do Estado de Minas Gerais, "
                   f"informamos que em {data} houve indisponibilidade do portal JPe, superior a uma hora, {hora}, que impossibilitou o peticionamento eletrônico de recursos em processos que já tramitavam no sistema.")
            corpo.add_run(txt)
        else:
            corpo.add_run(f"Informamos que no dia {data}, houve indisponibilidade específica do sistema para o peticionamento do processo nº {numero}.\n\n")
            corpo.add_run(f"O Chamado de número {chamado if chamado else '_____'}, foi aberto e encaminhado à DIRTEC (Diretoria Executiva de Tecnologia da Informação e Comunicação).\n\n")
            if tipo == 'Física': corpo.add_run("Diante da indisponibilidade específica, não havendo um prazo para solução do problema, a Primeira Vice-Presidência recomenda o ingresso dos autos físicos, nos termos do § 2º, do artigo 14º, da Resolução nº 780/2014, do Tribunal de Justiça do Estado de Minas Gerais.\n\n")
            else: corpo.add_run("Informamos a indisponibilidade para fins de restituição de prazo ou providências que V.Exa julgar necessárias, nos termos da legislação vigente.\n\n")
        corpo.add_run("\nColocamo-nos à disposição para outras informações que se fizerem necessárias.")
        doc.add_paragraph("\nRespeitosamente,")
        doc.add_paragraph("\n\n___________________________________\nWaner Andrade Silva\n0-009020-9\nCoordenação de Análise e Integração de Sistemas Judiciais Informatizados - COJIN\nGerência de Sistemas Judiciais - GEJUD\nDiretoria Executiva de Tecnologia da Informação e Comunicação - DIRTEC")
        buffer = io.BytesIO(); doc.save(buffer); buffer.seek(0)
        return buffer
    except: return None

# ============================================
# 3. NOTIFICAÇÕES (ATIVAS)
# ============================================
def send_chat_notification_internal(consultor, status):
    if CHAT_WEBHOOK_BASTAO and status == 'Bastão':
        msg = f"🎉 **BASTÃO GIRADO!** 🎉 \n\n- **Novo(a) Responsável:** {consultor}\n- **Acesse o Painel:** {APP_URL_CLOUD}"
        try: send_to_chat("bastao", msg); return True
        except: return False
    return False

def send_horas_extras_to_chat(consultor, data, inicio, tempo, motivo):
    msg = f"⏰ **Registro de Horas Extras**\n\n👤 **Consultor:** {consultor}\n📅 **Data:** {data.strftime('%d/%m/%Y')}\n🕐 **Início:** {inicio.strftime('%H:%M')}\n⏱️ **Tempo Total:** {tempo}\n📝 **Motivo:** {motivo}"
    try: send_to_chat("extras", msg); return True
    except: return False

def send_atendimento_to_chat(consultor, data, usuario, nome_setor, sistema, descricao, canal, desfecho, jira_opcional=""):
    jira_str = f"\n🔢 **Jira:** CESUPE-{jira_opcional}" if jira_opcional else ""
    msg = f"📋 **Novo Registro de Atendimento**\n\n👤 **Consultor:** {consultor}\n📅 **Data:** {data.strftime('%d/%m/%Y')}\n👥 **Usuário:** {usuario}\n🏢 **Nome/Setor:** {nome_setor}\n💻 **Sistema:** {sistema}\n📝 **Descrição:** {descricao}\n📞 **Canal:** {canal}\n✅ **Desfecho:** {desfecho}{jira_str}"
    try: send_to_chat("registro", msg); return True
    except: return False

def send_chamado_to_chat(consultor, texto):
    if not consultor or consultor == 'Selecione um nome' or not texto.strip(): return False
    data_envio = get_brazil_time().strftime('%d/%m/%Y %H:%M')
    msg = f"🆘 **Rascunho de Chamado/Jira**\n📅 **Data:** {data_envio}\n\n👤 **Autor:** {consultor}\n\n📝 **Texto:**\n{texto}"
    try: send_to_chat('chamado', msg); return True
    except:
        try: send_to_chat('registro', msg); return True
        except: return False

def handle_erro_novidade_submission(consultor, titulo, objetivo, relato, resultado):
    data_envio = get_brazil_time().strftime("%d/%m/%Y %H:%M")
    msg = f"🐛 **Novo Relato de Erro/Novidade**\n📅 **Data:** {data_envio}\n\n👤 **Autor:** {consultor}\n📌 **Título:** {titulo}\n\n🎯 **Objetivo:**\n{objetivo}\n\n🧪 **Relato:**\n{relato}\n\n🏁 **Resultado:**\n{resultado}"
    try: send_to_chat("erro", msg); return True
    except: return False

def send_sessao_to_chat_fn(consultor, texto_mensagem):
    if not consultor or consultor == 'Selecione um nome': return False
    try: send_to_chat("sessao", texto_mensagem); return True
    except: return False

# ============================================
# 4. GESTÃO DE ESTADO
# ============================================
def save_state():
    try:
        last_run = st.session_state.report_last_run_date
        last_run_iso = last_run.isoformat() if isinstance(last_run, datetime) else datetime.min.isoformat()
        visual_queue_calculated = get_ordered_visual_queue(st.session_state.bastao_queue, st.session_state.status_texto)
        
        state_to_save = {
            'status_texto': st.session_state.status_texto, 'bastao_queue': st.session_state.bastao_queue,
            'visual_queue': visual_queue_calculated, 'skip_flags': st.session_state.skip_flags, 
            'current_status_starts': st.session_state.current_status_starts,
            'bastao_counts': st.session_state.bastao_counts, 'priority_return_queue': st.session_state.priority_return_queue,
            'bastao_start_time': st.session_state.bastao_start_time, 'report_last_run_date': last_run_iso, 
            'rotation_gif_start_time': st.session_state.get('rotation_gif_start_time'), 'auxilio_ativo': st.session_state.get('auxilio_ativo', False), 
            'daily_logs': st.session_state.daily_logs, 'simon_ranking': st.session_state.get('simon_ranking', [])
        }
        save_state_to_db(state_to_save)
    except Exception as e: print(f"Erro save: {e}")

def format_time_duration(duration):
    if not isinstance(duration, timedelta): return '--:--:--'
    s = int(duration.total_seconds()); h, s = divmod(s, 3600); m, s = divmod(s, 60)
    return f'{h:02}:{m:02}:{s:02}'

def sync_state_from_db():
    try:
        db_data = load_state_from_db()
        if not db_data: return
        keys = ['status_texto', 'bastao_queue', 'skip_flags', 'bastao_counts', 'priority_return_queue', 'daily_logs', 'simon_ranking']
        for k in keys:
            if k in db_data: st.session_state[k] = db_data[k]
        if 'bastao_start_time' in db_data and db_data['bastao_start_time']:
            try:
                if isinstance(db_data['bastao_start_time'], str): st.session_state['bastao_start_time'] = datetime.fromisoformat(db_data['bastao_start_time'])
                else: st.session_state['bastao_start_time'] = db_data['bastao_start_time']
            except: pass
        if 'current_status_starts' in db_data:
            starts = db_data['current_status_starts']
            for nome, val in starts.items():
                if isinstance(val, str):
                    try: st.session_state.current_status_starts[nome] = datetime.fromisoformat(val)
                    except: pass
                else: st.session_state.current_status_starts[nome] = val
    except Exception as e: print(f"Erro sync: {e}")

def log_status_change(consultor, old_status, new_status, duration):
    if not isinstance(duration, timedelta): duration = timedelta(0)
    now_br = get_brazil_time()
    old_lbl = old_status if old_status else 'Fila Bastão'
    new_lbl = new_status if new_status else 'Fila Bastão'
    if consultor in st.session_state.bastao_queue:
        if 'Bastão' not in new_lbl and new_lbl != 'Fila Bastão': new_lbl = f"Fila | {new_lbl}"
    st.session_state.daily_logs.append({'timestamp': now_br, 'consultor': consultor, 'old_status': old_lbl, 'new_status': new_lbl, 'duration': duration})
    st.session_state.current_status_starts[consultor] = now_br

def update_status(novo_status: str, marcar_indisponivel: bool = False):
    selected = st.session_state.get('consultor_selectbox')
    if not selected or selected == 'Selecione um nome': st.warning('Selecione um(a) consultor(a).'); return
    ensure_daily_reset(); now_br = get_brazil_time(); current = st.session_state.status_texto.get(selected, '')
    forced_successor = None
    current_holder = next((c for c, s in st.session_state.status_texto.items() if 'Bastão' in (s or '')), None)
    if marcar_indisponivel and selected == current_holder and selected in st.session_state.bastao_queue:
        try:
            idx = st.session_state.bastao_queue.index(selected)
            nxt = find_next_holder_index(idx, st.session_state.bastao_queue, st.session_state.skip_flags)
            if nxt != -1: forced_successor = st.session_state.bastao_queue[nxt]
        except: forced_successor = None
    if marcar_indisponivel:
        st.session_state[f'check_{selected}'] = False; st.session_state.skip_flags[selected] = True
        if selected in st.session_state.bastao_queue:
            st.session_state.bastao_queue.remove(selected)
            if selected not in st.session_state.priority_return_queue: st.session_state.priority_return_queue.append(selected)
    else: st.session_state[f'check_{selected}'] = True; st.session_state.skip_flags[selected] = False
    clean_new = (novo_status or '').strip()
    if clean_new == 'Fila Bastão': clean_new = ''
    if (not marcar_indisponivel) and selected == current_holder: final_status = ('Bastão | ' + clean_new).strip(' |') if clean_new else 'Bastão'
    else: final_status = clean_new
    if not final_status and (selected in st.session_state.bastao_queue): final_status = ''
    if not final_status and (selected not in st.session_state.bastao_queue): final_status = 'Indisponível'
    try:
        started = st.session_state.current_status_starts.get(selected, now_br)
        log_status_change(selected, current, final_status, now_br - started)
    except: pass
    st.session_state.status_texto[selected] = final_status
    try: check_and_assume_baton(forced_successor=forced_successor)
    except: pass
    save_state()

def auto_manage_time():
    now = get_brazil_time(); last_run = st.session_state.report_last_run_date
    if now.hour >= 23 and now.date() == last_run.date(): reset_day_state(); save_state()
    elif now.date() > last_run.date(): reset_day_state(); save_state()

def find_next_holder_index(current_index, queue, skips):
    if not queue: return -1
    n = len(queue); start_index = (current_index + 1) % n
    for i in range(n):
        idx = (start_index + i) % n
        consultor = queue[idx]
        if consultor == queue[current_index] and n > 1: continue
        if not skips.get(consultor, False): return idx
    if n > 1:
        proximo_imediato_idx = (current_index + 1) % n
        nome_escolhido = queue[proximo_imediato_idx]; st.session_state.skip_flags[nome_escolhido] = False 
        return proximo_imediato_idx
    return -1

def check_and_assume_baton(forced_successor=None, immune_consultant=None):
    queue, skips = st.session_state.bastao_queue, st.session_state.skip_flags
    current_holder = next((c for c, s in st.session_state.status_texto.items() if 'Bastão' in s), None)
    is_valid = (current_holder and current_holder in queue)
    target = forced_successor if forced_successor else (current_holder if is_valid else None)
    if not target:
        curr_idx = queue.index(current_holder) if (current_holder and current_holder in queue) else -1
        idx = find_next_holder_index(curr_idx, queue, skips)
        target = queue[idx] if idx != -1 else None
    changed = False; now = get_brazil_time()
    for c in CONSULTORES:
        if c != immune_consultant: 
            if c != target and 'Bastão' in st.session_state.status_texto.get(c, ''):
                log_status_change(c, 'Bastão', 'Indisponível', now - st.session_state.current_status_starts.get(c, now))
                st.session_state.status_texto[c] = 'Indisponível'; changed = True
    if target:
        curr_s = st.session_state.status_texto.get(target, '')
        if 'Bastão' not in curr_s:
            old_s = curr_s; new_s = f"Bastão | {old_s}" if old_s and old_s != "Indisponível" else "Bastão"
            log_status_change(target, old_s, new_s, now - st.session_state.current_status_starts.get(target, now))
            st.session_state.status_texto[target] = new_s; st.session_state.bastao_start_time = now
            if current_holder != target: st.session_state.play_sound = True; send_chat_notification_internal(target, 'Bastão')
            st.session_state.skip_flags[target] = False
            changed = True
    elif not target and current_holder:
        if current_holder != immune_consultant:
            log_status_change(current_holder, 'Bastão', 'Indisponível', now - st.session_state.current_status_starts.get(current_holder, now))
            st.session_state.status_texto[current_holder] = 'Indisponível'; changed = True
    if changed: save_state()
    return changed

def init_session_state():
    if 'db_loaded' not in st.session_state:
        try:
            db_data = load_state_from_db()
            if db_data:
                for key, value in db_data.items(): st.session_state[key] = value
        except: pass
        st.session_state['db_loaded'] = True
    if 'report_last_run_date' in st.session_state and isinstance(st.session_state['report_last_run_date'], str):
        try: st.session_state['report_last_run_date'] = datetime.fromisoformat(st.session_state['report_last_run_date'])
        except: st.session_state['report_last_run_date'] = datetime.min
    now = get_brazil_time()
    defaults = {
        'bastao_start_time': None, 'report_last_run_date': datetime.min, 'rotation_gif_start_time': None,
        'play_sound': False, 'gif_warning': False, 'lunch_warning_info': None, 'last_reg_status': None,
        'chamado_guide_step': 0, 'auxilio_ativo': False, 'active_view': None, 'last_jira_number': "",
        'consultor_selectbox': "Selecione um nome", 'status_texto': {nome: 'Indisponível' for nome in CONSULTORES},
        'bastao_queue': [], 'skip_flags': {}, 'current_status_starts': {nome: now for nome in CONSULTORES},
        'bastao_counts': {nome: 0 for nome in CONSULTORES}, 'priority_return_queue': [], 'daily_logs': [], 'simon_ranking': [],
        'word_buffer': None, 'aviso_duplicidade': False
    }
    for key, default in defaults.items():
        if key not in st.session_state: st.session_state[key] = default
    for nome in CONSULTORES:
        st.session_state.bastao_counts.setdefault(nome, 0); st.session_state.skip_flags.setdefault(nome, False)
        current_status = st.session_state.status_texto.get(nome, 'Indisponível')
        if current_status is None: current_status = 'Indisponível'
        st.session_state.status_texto[nome] = current_status
        blocking = ['Almoço', 'Ausente', 'Saída rápida', 'Sessão', 'Reunião', 'Treinamento', 'Atendimento Presencial']
        is_hard_blocked = any(kw in current_status for kw in blocking)
        if is_hard_blocked: is_available = False
        elif nome in st.session_state.priority_return_queue: is_available = False
        elif nome in st.session_state.bastao_queue: is_available = True
        else: is_available = 'Indisponível' not in current_status
        st.session_state[f'check_{nome}'] = is_available
        if nome not in st.session_state.current_status_starts: st.session_state.current_status_starts[nome] = now
    check_and_assume_baton()

def reset_day_state():
    now = get_brazil_time()
    st.session_state.bastao_queue = []; st.session_state.status_texto = {n: 'Indisponível' for n in CONSULTORES}
    st.session_state.bastao_counts = {n: 0 for n in CONSULTORES}; st.session_state.skip_flags = {}
    st.session_state.daily_logs = []; st.session_state.current_status_starts = {n: now for n in CONSULTORES}
    st.session_state.report_last_run_date = now
    for n in CONSULTORES: st.session_state[f'check_{n}'] = False

def ensure_daily_reset():
    now_br = get_brazil_time(); last_run = st.session_state.report_last_run_date
    if now_br.date() > last_run.date(): reset_day_state(); st.toast("☀️ Novo dia detectado! Fila limpa.", icon="🧹"); save_state()

def toggle_queue(consultor):
    ensure_daily_reset(); st.session_state.gif_warning = False; now_br = get_brazil_time()
    if consultor in st.session_state.bastao_queue:
        current_holder = next((c for c, s in st.session_state.status_texto.items() if 'Bastão' in s), None)
        forced_successor = None
        if consultor == current_holder:
            idx = st.session_state.bastao_queue.index(consultor)
            nxt = find_next_holder_index(idx, st.session_state.bastao_queue, st.session_state.skip_flags)
            if nxt != -1: forced_successor = st.session_state.bastao_queue[nxt]
        st.session_state.bastao_queue.remove(consultor)
        st.session_state[f'check_{consultor}'] = False
        current_s = st.session_state.status_texto.get(consultor, '')
        if current_s == '' or current_s == 'Bastão':
            log_status_change(consultor, current_s, 'Indisponível', now_br - st.session_state.current_status_starts.get(consultor, now_br))
            st.session_state.status_texto[consultor] = 'Indisponível'
        check_and_assume_baton(forced_successor)
    else:
        st.session_state.bastao_queue.append(consultor)
        st.session_state[f'check_{consultor}'] = True
        st.session_state.skip_flags[consultor] = False
        if consultor in st.session_state.priority_return_queue: st.session_state.priority_return_queue.remove(consultor)
        current_s = st.session_state.status_texto.get(consultor, 'Indisponível')
        if 'Indisponível' in current_s:
            log_status_change(consultor, current_s, '', now_br - st.session_state.current_status_starts.get(consultor, now_br))
            st.session_state.status_texto[consultor] = ''
        check_and_assume_baton()
    save_state()

def leave_specific_status(consultor, status_type_to_remove):
    ensure_daily_reset(); st.session_state.gif_warning = False
    if status_type_to_remove in ['Almoço', 'Treinamento', 'Sessão', 'Reunião', 'Saída rápida', 'Ausente', 'Atendimento Presencial']:
        if consultor not in st.session_state.bastao_queue: st.session_state.bastao_queue.append(consultor)
        st.session_state[f'check_{consultor}'] = True; st.session_state.skip_flags[consultor] = False
    old_status = st.session_state.status_texto.get(consultor, '')
    now_br = get_brazil_time(); duration = now_br - st.session_state.current_status_starts.get(consultor, now_br)
    parts = [p.strip() for p in old_status.split('|')]
    new_parts = [p for p in parts if status_type_to_remove not in p and p]
    new_status = " | ".join(new_parts)
    if not new_status and consultor in st.session_state.bastao_queue: new_status = '' 
    elif not new_status: new_status = 'Indisponível'
    log_status_change(consultor, old_status, new_status, duration)
    st.session_state.status_texto[consultor] = new_status
    check_and_assume_baton(); save_state()

def enter_from_indisponivel(consultor):
    ensure_daily_reset(); st.session_state.gif_warning = False
    if consultor not in st.session_state.bastao_queue: st.session_state.bastao_queue.append(consultor)
    st.session_state[f'check_{consultor}'] = True; st.session_state.skip_flags[consultor] = False
    old_status = st.session_state.status_texto.get(consultor, 'Indisponível')
    duration = get_brazil_time() - st.session_state.current_status_starts.get(consultor, get_brazil_time())
    log_status_change(consultor, old_status, '', duration)
    st.session_state.status_texto[consultor] = ''
    check_and_assume_baton(); save_state()

def rotate_bastao():
    ensure_daily_reset(); selected = st.session_state.consultor_selectbox
    if not selected or selected == 'Selecione um nome': st.warning('Selecione um(a) consultor(a).'); return
    queue = st.session_state.bastao_queue; skips = st.session_state.skip_flags
    current_holder = next((c for c, s in st.session_state.status_texto.items() if 'Bastão' in s), None)
    if selected != current_holder: st.session_state.gif_warning = True; return
    current_index = queue.index(current_holder) if current_holder in queue else -1
    if current_index == -1: check_and_assume_baton(); return
    next_idx = find_next_holder_index(current_index, queue, skips)
    if next_idx == -1 and len(queue) > 1: next_idx = (current_index + 1) % len(queue)
    if next_idx != -1:
        n_queue = len(queue); tmp_idx = (current_index + 1) % n_queue
        while tmp_idx != next_idx:
            skipped_name = queue[tmp_idx]
            if st.session_state.skip_flags.get(skipped_name, False): st.session_state.skip_flags[skipped_name] = False
            tmp_idx = (tmp_idx + 1) % n_queue
        next_holder = queue[next_idx]; st.session_state.skip_flags[next_holder] = False; now_br = get_brazil_time()
        old_h_status = st.session_state.status_texto[current_holder]
        new_h_status = old_h_status.replace('Bastão | ', '').replace('Bastão', '').strip()
        log_status_change(current_holder, old_h_status, new_h_status, now_br - (st.session_state.bastao_start_time or now_br))
        st.session_state.status_texto[current_holder] = new_h_status
        old_n_status = st.session_state.status_texto.get(next_holder, '')
        new_n_status = f"Bastão | {old_n_status}" if old_n_status else "Bastão"
        log_status_change(next_holder, old_n_status, new_n_status, timedelta(0))
        st.session_state.status_texto[next_holder] = new_n_status
        st.session_state.bastao_start_time = now_br
        st.session_state.bastao_counts[current_holder] = st.session_state.bastao_counts.get(current_holder, 0) + 1
        st.session_state.play_sound = True; send_chat_notification_internal(next_holder, 'Bastão')
        save_state()
    else: st.warning('Ninguém elegível.'); check_and_assume_baton()

def manual_rerun(): st.session_state.gif_warning = False; st.rerun()
def toggle_view(v):
    if st.session_state.active_view == v: st.session_state.active_view = None; return
    st.session_state.active_view = v
    if v == 'chamados': st.session_state.chamado_guide_step = 1

def toggle_skip():
    selected = st.session_state.consultor_selectbox
    if not selected or selected == 'Selecione um nome': st.warning('Selecione um(a) consultor(a).'); return
    if selected not in st.session_state.bastao_queue: st.warning(f'{selected} não está na fila do bastão.'); return
    novo = not st.session_state.skip_flags.get(selected, False)
    st.session_state.skip_flags[selected] = novo
    save_state()

# --- HANDLER PARA CHAMADOS ---
def handle_chamado_submission():
    consultor = st.session_state.get('consultor_selectbox')
    texto = st.session_state.get('chamado_textarea', '')
    ok = send_chamado_to_chat(consultor, texto)
    if ok: st.session_state.chamado_textarea = ''; st.session_state.chamado_guide_step = 1
    return ok

def set_chamado_step(step): st.session_state.chamado_guide_step = int(step)

# ============================================
# 5. INTERFACE
# ============================================
st.set_page_config(page_title="Controle Bastão Cesupe 2026", layout="wide", page_icon="🥂")
st.markdown("""<style>div.stButton > button {width: 100%; white-space: nowrap; height: 3rem;} [data-testid='stHorizontalBlock'] div.stButton > button {white-space: nowrap; height: 3rem;}</style>""", unsafe_allow_html=True)
init_session_state(); auto_manage_time()
st.components.v1.html("<script>window.scrollTo(0, 0);</script>", height=0)

c_topo_esq, c_topo_dir = st.columns([2, 1], vertical_alignment="bottom")
with c_topo_esq:
    img = get_img_as_base64(PUG2026_FILENAME); src = f"data:image/png;base64,{img}" if img else GIF_BASTAO_HOLDER
    st.markdown(f"""<div style="display: flex; align-items: center; gap: 15px;"><h1 style="margin: 0; padding: 0; font-size: 2.2rem; color: #FFD700; text-shadow: 1px 1px 2px #B8860B;">Controle Bastão Cesupe 2026 {BASTAO_EMOJI}</h1><img src="{src}" style="width: 120px; height: 120px; border-radius: 50%; border: 3px solid #FFD700; object-fit: cover;"></div>""", unsafe_allow_html=True)
with c_topo_dir:
    c_sub1, c_sub2 = st.columns([2, 1], vertical_alignment="bottom")
    with c_sub1: novo_responsavel = st.selectbox("Assumir Bastão (Rápido)", options=["Selecione"] + CONSULTORES, label_visibility="collapsed", key="quick_enter")
    with c_sub2:
        if st.button("🚀 Entrar", use_container_width=True):
            if novo_responsavel != "Selecione": toggle_queue(novo_responsavel); st.rerun()
st.markdown("<hr style='border: 1px solid #FFD700; margin-top: 5px; margin-bottom: 20px;'>", unsafe_allow_html=True)

if st.session_state.active_view is None: st_autorefresh(interval=20000, key='auto_rerun'); sync_state_from_db() 
else: st.caption("⏸️ Atualização automática pausada durante o registro.")

col_principal, col_disponibilidade = st.columns([1.5, 1])
queue, skips = st.session_state.bastao_queue, st.session_state.skip_flags
responsavel = next((c for c, s in st.session_state.status_texto.items() if 'Bastão' in s), None)
curr_idx = queue.index(responsavel) if responsavel in queue else -1
prox_idx = find_next_holder_index(curr_idx, queue, skips)
proximo = queue[prox_idx] if prox_idx != -1 else None

with col_principal:
    st.header("Responsável pelo Bastão")
    if responsavel:
        st.markdown(f"""<div style="background: linear-gradient(135deg, #FFF8DC 0%, #FFFFFF 100%); border: 3px solid #FFD700; padding: 25px; border-radius: 15px; display: flex; align-items: center; box-shadow: 0 4px 15px rgba(255, 215, 0, 0.3); margin-bottom: 20px;"><div style="flex-shrink: 0; margin-right: 25px;"><img src="{GIF_BASTAO_HOLDER}" style="width: 90px; height: 90px; border-radius: 50%; object-fit: cover; border: 2px solid #FFD700;"></div><div><span style="font-size: 14px; color: #555; font-weight: bold; text-transform: uppercase; letter-spacing: 1.5px;">Atualmente com:</span><br><span style="font-size: 42px; font-weight: 800; color: #000080; line-height: 1.1;">{responsavel}</span></div></div>""", unsafe_allow_html=True)
        dur = get_brazil_time() - (st.session_state.bastao_start_time or get_brazil_time())
        st.caption(f"⏱️ Tempo com o bastão: **{format_time_duration(dur)}**")
    else: st.markdown('<h2>(Ninguém com o bastão)</h2>', unsafe_allow_html=True)
    st.markdown("###"); st.header("Próximos da Fila")
    
    if responsavel and responsavel in queue:
        c_idx = queue.index(responsavel)
        raw_ordered = queue[c_idx+1:] + queue[:c_idx]
    else: raw_ordered = list(queue)

    lista_pularam = [n for n in queue if skips.get(n, False) and n != responsavel]
    demais_na_fila = [n for n in raw_ordered if n != proximo and not skips.get(n, False)]

    if proximo: st.markdown(f"**Próximo Bastão:** {proximo}")
    else: st.markdown("**Próximo Bastão:** _Ninguém elegível_")
    if demais_na_fila: st.markdown(f"**Demais na fila:** {', '.join(demais_na_fila)}")
    else: st.markdown("**Demais na fila:** _Vazio_")
    if lista_pularam: st.markdown(f"**Consultor(es) pulou(pularam) o bastão:** {', '.join(lista_pularam)}")

    st.markdown("###"); st.header("**Consultor(a)**")
    st.selectbox('Selecione:', ['Selecione um nome'] + CONSULTORES, key='consultor_selectbox', label_visibility='collapsed')
    r1c1, r1c2, r1c3, r1c4 = st.columns(4); r2c1, r2c2, r2c3, r2c4, r2c5, r2c6 = st.columns(6)
    r1c1.button('🎯 Passar', on_click=rotate_bastao, use_container_width=True)
    r1c2.button('⏭️ Pular', on_click=toggle_skip, use_container_width=True)
    r1c3.button('📋 Atividades', on_click=toggle_view, args=('menu_atividades',), use_container_width=True)
    r1c4.button('🏗️ Projeto', on_click=toggle_view, args=('menu_projetos',), use_container_width=True)
    r2c1.button('🎓 Treinamento', on_click=toggle_view, args=('menu_treinamento',), use_container_width=True)
    r2c2.button('📅 Reunião', on_click=toggle_view, args=('menu_reuniao',), use_container_width=True)
    r2c3.button('🍽️ Almoço', on_click=update_status, args=('Almoço', True), use_container_width=True)
    r2c4.button('🎙️ Sessão', on_click=toggle_view, args=('menu_sessao',), use_container_width=True)
    r2c5.button('🚶 Saída', on_click=update_status, args=('Saída rápida', True), use_container_width=True)
    r2c6.button('👤 Ausente', on_click=update_status, args=('Ausente', True), use_container_width=True)
    if st.button("🤝 Atend. Presencial", use_container_width=True): toggle_view('menu_presencial')

    if st.session_state.active_view == 'menu_atividades':
        with st.container(border=True):
            at_t = st.multiselect("Tipo:", OPCOES_ATIVIDADES_STATUS); at_e = st.text_input("Detalhe:")
            if st.button("Confirmar Atividade"): st.session_state.active_view = None; update_status(f"Atividade: {', '.join(at_t)} - {at_e}")
            if st.button("❌ Cancelar Registro"): st.session_state.active_view = None; st.rerun()
    if st.session_state.active_view == 'menu_presencial':
        with st.container(border=True):
            st.subheader('🤝 Registrar Atendimento Presencial'); local_presencial = st.text_input('Local:', key='pres_local'); objetivo_presencial = st.text_input('Objetivo:', key='pres_obj')
            c_ok, c_cancel = st.columns(2)
            with c_ok:
                if st.button('✅ Confirmar', type='primary', use_container_width=True):
                    if not local_presencial.strip() or not objetivo_presencial.strip(): st.warning('Preencha Local e Objetivo.')
                    else: st.session_state.active_view = None; update_status(f"Atendimento Presencial: {local_presencial.strip()} - {objetivo_presencial.strip()}", True)
            with c_cancel:
                if st.button('❌ Cancelar', use_container_width=True): st.session_state.active_view = None; st.rerun()
    if st.session_state.active_view == 'menu_projetos':
        with st.container(border=True):
            st.subheader('🏗️ Registrar Projeto'); proj = st.selectbox('Projeto:', ['Selecione'] + OPCOES_PROJETOS); det = st.text_input('Detalhe (opcional):')
            c_ok, c_cancel = st.columns(2)
            with c_ok:
                if st.button('✅ Confirmar', type='primary', use_container_width=True):
                    if proj == 'Selecione': st.warning('Selecione um projeto.')
                    else: st.session_state.active_view = None; update_status(f"Projeto: {proj}" + (f" - {det.strip()}" if det.strip() else ""), False)
            with c_cancel:
                if st.button('❌ Cancelar', use_container_width=True): st.session_state.active_view = None; st.rerun()
    if st.session_state.active_view == 'menu_treinamento':
        with st.container(border=True):
            st.subheader('🎓 Registrar Treinamento'); tema = st.text_input('Tema/Conteúdo:'); obs = st.text_input('Observação (opcional):')
            c_ok, c_cancel = st.columns(2)
            with c_ok:
                if st.button('✅ Confirmar', type='primary', use_container_width=True):
                    if not tema.strip(): st.warning('Informe o tema.')
                    else: st.session_state.active_view = None; update_status(f"Treinamento: {tema.strip()}" + (f" - {obs.strip()}" if obs.strip() else ""), True)
            with c_cancel:
                if st.button('❌ Cancelar', use_container_width=True): st.session_state.active_view = None; st.rerun()
    if st.session_state.active_view == 'menu_reuniao':
        with st.container(border=True):
            st.subheader('📅 Registrar Reunião'); assunto = st.text_input('Assunto:'); obs = st.text_input('Observação (opcional):')
            c_ok, c_cancel = st.columns(2)
            with c_ok:
                if st.button('✅ Confirmar', type='primary', use_container_width=True):
                    if not assunto.strip(): st.warning('Informe o assunto.')
                    else: st.session_state.active_view = None; update_status(f"Reunião: {assunto.strip()}" + (f" - {obs.strip()}" if obs.strip() else ""), True)
            with c_cancel:
                if st.button('❌ Cancelar', use_container_width=True): st.session_state.active_view = None; st.rerun()
    if st.session_state.active_view == 'menu_sessao':
        with st.container(border=True):
            st.subheader('🎙️ Registrar Sessão'); cam = st.selectbox('Câmara:', ['Selecione'] + CAMARAS_OPCOES); obs = st.text_input('Observação (opcional):')
            enviar_chat = st.checkbox('Enviar aviso no chat', value=True)
            c_ok, c_cancel = st.columns(2)
            with c_ok:
                if st.button('✅ Confirmar', type='primary', use_container_width=True):
                    consultor = st.session_state.get('consultor_selectbox')
                    if not consultor or consultor == 'Selecione um nome': st.error('Selecione um consultor.')
                    elif cam == 'Selecione': st.warning('Selecione uma câmara.')
                    else:
                        if enviar_chat:
                            msg = f"🎙️ **Sessão registrada**\n👤 **Consultor:** {consultor}\n🏛️ **Câmara:** {cam}\n📝 **Obs:** {obs}"
                            send_sessao_to_chat_fn(consultor, msg)
                        st.session_state.active_view = None; update_status(f"Sessão: {cam}" + (f" - {obs.strip()}" if obs.strip() else ""), True)
            with c_cancel:
                if st.button('❌ Cancelar', use_container_width=True): st.session_state.active_view = None; st.rerun()

    st.markdown("####"); st.button('🔄 Atualizar (Manual)', on_click=manual_rerun, use_container_width=True); st.markdown("---")
    
    # --- MENUS RESTAURADOS (FERRAMENTAS) ---
    c_tool1, c_tool2, c_tool3, c_tool4, c_tool5, c_tool6 = st.columns(6)
    c_tool1.button("📑 Checklist", use_container_width=True, on_click=toggle_view, args=("checklist",))
    c_tool2.button("🆘 Chamados", use_container_width=True, on_click=toggle_view, args=("chamados",))
    c_tool3.button("📝 Atendimentos", use_container_width=True, on_click=toggle_view, args=("atendimentos",))
    c_tool4.button("⏰ H. Extras", use_container_width=True, on_click=toggle_view, args=("hextras",))
    c_tool5.button("🐛 Erro/Novidade", use_container_width=True, on_click=toggle_view, args=("erro_novidade",))
    c_tool6.button("🖨️ Certidão", use_container_width=True, on_click=toggle_view, args=("certidao",))

    if st.session_state.active_view == "checklist":
        with st.container(border=True):
            st.header("Gerador de Checklist"); data_eproc = st.date_input("Data:", value=get_brazil_time().date()); camara_eproc = st.selectbox("Câmara:", CAMARAS_OPCOES)
            if st.button("Gerar HTML"): send_to_chat("sessao", f"Consultor {st.session_state.consultor_selectbox} acompanhando sessão {camara_eproc}"); st.success("Registrado no chat!")
            if st.button("❌ Cancelar"): st.session_state.active_view = None; st.rerun()

    if st.session_state.active_view == "chamados":
        with st.container(border=True):
            st.header('🆘 Chamados (Padrão / Jira)')
            guide_step = st.session_state.get('chamado_guide_step', 1)
            if guide_step == 1:
                st.subheader('Passo 1: Testes'); st.markdown('Testes de suporte e evidências.'); st.button('Próximo ➡️', on_click=set_chamado_step, args=(2,), use_container_width=True)
            elif guide_step == 2:
                st.subheader('Passo 2: Checklist'); st.markdown('- Dados usuário/processo\n- Prints'); st.button('Próximo ➡️', on_click=set_chamado_step, args=(3,), use_container_width=True)
            elif guide_step == 3:
                st.subheader('Passo 3: Registrar'); st.markdown('Informe número ao usuário.'); st.button('Próximo ➡️', on_click=set_chamado_step, args=(4,), use_container_width=True)
            elif guide_step == 4:
                st.subheader('Observações'); st.markdown('Email institucional.'); st.button('Abrir campo ➡️', on_click=set_chamado_step, args=(5,), use_container_width=True)
            else:
                st.text_area('Texto do chamado:', height=240, key='chamado_textarea')
                c1, c2 = st.columns(2)
                with c1:
                    if st.button('📨 Enviar', type='primary', use_container_width=True):
                        if handle_chamado_submission(): st.success('Enviado!'); st.session_state.active_view = None; st.rerun()
                        else: st.error('Erro ao enviar.')
                with c2:
                     if st.button('❌ Cancelar', use_container_width=True): st.session_state.active_view = None; st.rerun()

    if st.session_state.active_view == "atendimentos":
        with st.container(border=True):
            st.header('📝 Registro de Atendimentos')
            at_data = st.date_input('Data:', value=get_brazil_time().date())
            at_usuario = st.selectbox('Usuário:', REG_USUARIO_OPCOES); at_setor = st.text_input('Setor:'); at_sys = st.selectbox('Sistema:', REG_SISTEMA_OPCOES)
            at_desc = st.text_input('Descrição:'); at_canal = st.selectbox('Canal:', REG_CANAL_OPCOES); at_res = st.selectbox('Desfecho:', REG_DESFECHO_OPCOES); at_jira = st.text_input('Jira:')
            if st.button('Enviar', type='primary', use_container_width=True):
                if send_atendimento_to_chat(st.session_state.consultor_selectbox, at_data, at_usuario, at_setor, at_sys, at_desc, at_canal, at_res, at_jira):
                    st.success('Enviado!'); st.session_state.active_view = None; st.rerun()
                else: st.error('Erro.')
            if st.button('❌ Cancelar', use_container_width=True): st.session_state.active_view = None; st.rerun()

    if st.session_state.active_view == "hextras":
        with st.container(border=True):
            st.header("⏰ Horas Extras"); d_ex = st.date_input("Data:"); h_in = st.time_input("Início:"); t_ex = st.text_input("Tempo Total:"); mot = st.text_input("Motivo:")
            if st.button("Registrar"): 
                if send_horas_extras_to_chat(st.session_state.consultor_selectbox, d_ex, h_in, t_ex, mot): st.success("Registrado!"); st.session_state.active_view = None; st.rerun()
            if st.button("❌ Cancelar"): st.session_state.active_view = None; st.rerun()

    if st.session_state.active_view == "erro_novidade":
        with st.container(border=True):
            st.header("🐛 Erro/Novidade"); tit = st.text_input("Título:"); obj = st.text_area("Objetivo:"); rel = st.text_area("Relato:"); res = st.text_area("Resultado:")
            if st.button("Enviar"): 
                if handle_erro_novidade_submission(st.session_state.consultor_selectbox, tit, obj, rel, res): st.success("Enviado!"); st.session_state.active_view = None; st.rerun()
            if st.button("❌ Cancelar"): st.session_state.active_view = None; st.rerun()

    if st.session_state.active_view == "certidao":
        with st.container(border=True):
            st.header("🖨️ Registro de Certidão"); tipo_cert = st.selectbox("Tipo:", ["Física", "Eletrônica", "Geral"]); c_data = st.date_input("Data do Evento:", value=get_brazil_time().date())
            c_cons = st.session_state.consultor_selectbox
            if tipo_cert == "Geral": c_hora = st.text_input("Horário/Período:"); c_motivo = st.text_input("Motivo:"); c_proc = ""
            else: c_hora = ""; c1, c2 = st.columns(2); c_chamado = c1.text_input("Chamado:"); c_proc = c2.text_input("Processo:"); c_motivo = st.text_area("Motivo:")
            
            c1, c2 = st.columns(2)
            with c1:
                if st.button("📄 Gerar Word", use_container_width=True): st.session_state.word_buffer = gerar_docx_certidao_internal(tipo_cert, c_proc, c_data.strftime("%d/%m/%Y"), c_cons, c_motivo, c_chamado, c_hora)
                if st.session_state.word_buffer: st.download_button("⬇️ Baixar", st.session_state.word_buffer, file_name="certidao.docx")
            with c2:
                if st.button("💾 Salvar e Notificar", type="primary", use_container_width=True):
                    if verificar_duplicidade_certidao(tipo_cert, c_proc, c_data, c_hora): st.session_state.aviso_duplicidade = True
                    else:
                        payload = {"tipo": tipo_cert, "data_evento": c_data.isoformat(), "consultor": c_cons, "n_chamado": c_chamado, "n_processo": c_proc, "motivo": c_motivo, "hora_periodo": c_hora}
                        if salvar_certidao_db(payload):
                            # --- WEBHOOK CERTIDÃO AQUI ---
                            msg_cert = f"🖨️ **Nova Certidão Registrada**\n👤 **Autor:** {c_cons}\n📅 **Data:** {c_data.strftime('%d/%m/%Y')}\n📄 **Tipo:** {tipo_cert}"
                            try: send_to_chat("certidao", msg_cert)
                            except: pass
                            # -----------------------------
                            st.success("Salvo!"); time.sleep(1); st.session_state.active_view = None; st.session_state.word_buffer = None; st.rerun()
            if st.button("❌ Cancelar"): st.session_state.active_view = None; st.rerun()
            if st.session_state.get('aviso_duplicidade'): st.error("Registro já existe!"); st.button("Ok", on_click=st.rerun)

with col_disponibilidade:
    st.header('Status dos(as) Consultores(as)')
    ui_lists = {'fila': [], 'almoco': [], 'saida': [], 'ausente': [], 'atividade_especifica': [], 'sessao_especifica': [], 'projeto_especifico': [], 'reuniao_especifica': [], 'treinamento_especifico': [], 'indisponivel': [], 'presencial_especifico': []}
    for nome in CONSULTORES:
        if nome in st.session_state.bastao_queue: ui_lists['fila'].append(nome)
        status = st.session_state.status_texto.get(nome, 'Indisponível'); status = status if status is not None else 'Indisponível'
        if status in ('', None): pass
        elif status == 'Almoço': ui_lists['almoco'].append(nome)
        elif status == 'Ausente': ui_lists['ausente'].append(nome)
        elif status == 'Saída rápida': ui_lists['saida'].append(nome)
        elif status == 'Indisponível' and nome not in st.session_state.bastao_queue: ui_lists['indisponivel'].append(nome)
        if isinstance(status, str):
            if 'Sessão:' in status or status.strip() == 'Sessão': ui_lists['sessao_especifica'].append((nome, status.replace('Sessão:', '').strip()))
            if 'Reunião:' in status or status.strip() == 'Reunião': ui_lists['reuniao_especifica'].append((nome, status.replace('Reunião:', '').strip()))
            if 'Projeto:' in status or status.strip() == 'Projeto': ui_lists['projeto_especifico'].append((nome, status.replace('Projeto:', '').strip()))
            if 'Treinamento:' in status or status.strip() == 'Treinamento': ui_lists['treinamento_especifico'].append((nome, status.replace('Treinamento:', '').strip()))
            if 'Atividade:' in status or status.strip() == 'Atendimento': ui_lists['atividade_especifica'].append((nome, status.replace('Atividade:', '').strip()))
            if 'Atendimento Presencial:' in status: ui_lists['presencial_especifico'].append((nome, status.replace('Atendimento Presencial:', '').strip()))

    st.subheader(f'✅ Na Fila ({len(ui_lists["fila"])})')
    render_order = get_ordered_visual_queue(queue, st.session_state.status_texto)
    if not render_order and queue: render_order = list(queue)
    if not render_order: st.markdown('_Ninguém na fila._')
    else:
        for i, nome in enumerate(render_order):
            if nome not in ui_lists['fila']: continue
            col_nome, col_check = st.columns([0.85, 0.15], vertical_alignment='center')
            col_check.checkbox(' ', key=f'chk_fila_{nome}', value=True, on_change=toggle_queue, args=(nome,), label_visibility='collapsed')
            skip_flag = skips.get(nome, False); status_atual = st.session_state.status_texto.get(nome, '') or ''; extra = ''
            if 'Atividade' in status_atual: extra += ' 📋'
            if 'Projeto' in status_atual: extra += ' 🏗️'
            if nome == responsavel: display = f'<span style="background-color: #FFD700; color: #000; padding: 2px 6px; border-radius: 5px; font-weight: 800;">🥂 {nome}</span>'
            elif skip_flag: display = f'<strong>{i}º {nome}</strong>{extra} <span style="background-color: #FFECB3; padding: 2px 8px; border-radius: 10px;">Pulando ⏭️</span>'
            else: display = f'<strong>{i}º {nome}</strong>{extra} <span style="background-color: #BBDEFB; padding: 2px 8px; border-radius: 10px;">Aguardando</span>'
            col_nome.markdown(display, unsafe_allow_html=True)
    st.markdown('---')

    def _render_section(titulo, icon, itens, cor, key_rm):
        colors = {'orange': '#FFECB3', 'blue': '#BBDEFB', 'teal': '#B2DFDB', 'violet': '#E1BEE7', 'green': '#C8E6C9', 'red': '#FFCDD2', 'grey': '#EEEEEE', 'yellow': '#FFF9C4'}
        bg_hex = colors.get(cor, '#EEEEEE'); st.subheader(f'{icon} {titulo} ({len(itens)})')
        if not itens: st.markdown(f'_Nenhum._')
        else:
            for item in itens:
                nome = item[0] if isinstance(item, tuple) else item
                desc = item[1] if isinstance(item, tuple) else titulo
                col_n, col_c = st.columns([0.85, 0.15], vertical_alignment='center')
                if titulo == 'Indisponível': col_c.checkbox(' ', key=f'chk_{titulo}_{nome}', value=False, on_change=enter_from_indisponivel, args=(nome,), label_visibility='collapsed')
                else: col_c.checkbox(' ', key=f'chk_{titulo}_{nome}', value=True, on_change=leave_specific_status, args=(nome, key_rm), label_visibility='collapsed')
                col_n.markdown(f"<div style='font-size: 16px; margin: 2px 0;'><strong>{nome}</strong><span style='background-color: {bg_hex}; color: #333; padding: 2px 8px; border-radius: 12px; font-size: 14px; margin-left: 8px;'>{desc}</span></div>", unsafe_allow_html=True)
        st.markdown('---')
    _render_section('Atend. Presencial', '🤝', ui_lists['presencial_especifico'], 'yellow', 'Atendimento Presencial')
    _render_section('Em Demanda', '📋', ui_lists['atividade_especifica'], 'orange', 'Atividade')
    _render_section('Projetos', '🏗️', ui_lists['projeto_especifico'], 'blue', 'Projeto')
    _render_section('Treinamento', '🎓', ui_lists['treinamento_especifico'], 'teal', 'Treinamento')
    _render_section('Reuniões', '📅', ui_lists['reuniao_especifica'], 'violet', 'Reunião')
    _render_section('Almoço', '🍽️', ui_lists['almoco'], 'red', 'Almoço')
    _render_section('Sessão', '🎙️', ui_lists['sessao_especifica'], 'green', 'Sessão')
    _render_section('Saída rápida', '🚶', ui_lists['saida'], 'red', 'Saída rápida')
    _render_section('Ausente', '👤', ui_lists['ausente'], 'violet', 'Ausente')
    _render_section('Indisponível', '❌', ui_lists['indisponivel'], 'grey', '')
