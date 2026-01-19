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
from supabase import create_client
from docx import Document
from docx.shared import Pt, Cm
from docx.enum.text import WD_ALIGN_PARAGRAPH

# Importações locais
from repository import load_state_from_db, save_state_to_db
from utils import (get_brazil_time, get_secret, send_to_chat, get_img_as_base64)

# ============================================
# 1. CONFIGURAÇÕES
# ============================================
CONSULTORES = sorted([
    "Alex Paulo", "Dirceu Gonçalves", "Douglas De Souza", "Farley Leandro", "Gleis Da Silva", 
    "Hugo Leonardo", "Igor Dayrell", "Jerry Marcos", "Jonatas Gomes", "Leandro Victor", 
    "Luiz Henrique", "Marcelo Dos Santos", "Marina Silva", "Marina Torres", "Vanessa Ligiane"
])

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
APP_URL_CLOUD = 'https://controle-bastao-cesupe.streamlit.app'
GIF_URL_ROTATION = 'https://media0.giphy.com/media/v1.Y2lkPTc5MGI3NjExdmx4azVxbGt4Mnk1cjMzZm5sMmp1YThteGJsMzcyYmhsdmFoczV0aSZlcD12MV9pbnRlcm5uYWxfZ2lmX2J5X2lkJmN0PWc/JpkZEKWY0s9QI4DGvF/giphy.gif'
GIF_URL_NEDRY = 'https://media0.giphy.com/media/v1.Y2lkPTc5MGI3NjExMGNkMGx3YnNkcXQ2bHJmNTZtZThraHhuNmVoOTNmbG0wcDloOXAybiZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/7kyWoqTue3po4/giphy.gif'
SOUND_URL = "https://github.com/matheusmg0550247-collab/controle-bastao-eproc2/raw/main/doorbell-223669.mp3"
PUG2026_FILENAME = "pug2026.png"

GOOGLE_CHAT_WEBHOOK_BACKUP = get_secret("chat", "backup")
CHAT_WEBHOOK_BASTAO = get_secret("chat", "bastao")
GOOGLE_CHAT_WEBHOOK_REGISTRO = get_secret("chat", "registro")

# --- CONEXÃO COM SUPABASE ---
def get_supabase():
    try:
        return create_client(st.secrets["supabase"]["url"], st.secrets["supabase"]["key"])
    except:
        return None

# --- FUNÇÕES DE BANCO PARA CERTIDÕES ---
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
            if hora_periodo:
                query = query.eq("hora_periodo", hora_periodo)
            response = query.execute()
            return len(response.data) > 0
    except Exception as e:
        print(f"Erro duplicidade: {e}")
        return False
    return False

def salvar_certidao_db(dados):
    sb = get_supabase()
    if not sb: return False
    try:
        sb.table("certidoes_registro").insert(dados).execute()
        return True
    except Exception as e:
        raise e

# --- GERADOR DE WORD OFICIAL ---
def gerar_docx_certidao_internal(tipo, numero, data, consultor, motivo, chamado="", hora=""):
    try:
        doc = Document()
        section = doc.sections[0]
        section.top_margin = Cm(2.5)
        section.bottom_margin = Cm(2.0)
        section.left_margin = Cm(3.0)
        section.right_margin = Cm(3.0)

        style = doc.styles['Normal']
        style.font.name = 'Arial'
        style.font.size = Pt(11)

        head_p = doc.add_paragraph()
        head_p.alignment = WD_ALIGN_PARAGRAPH.CENTER
        runner = head_p.add_run("TRIBUNAL DE JUSTIÇA DO ESTADO DE MINAS GERAIS\n")
        runner.bold = True
        head_p.add_run("Rua Ouro Preto, N° 1564 - Bairro Santo Agostinho - CEP 30170-041 - Belo Horizonte - MG\nwww.tjmg.jus.br - Andar: 3º e 4º PV")
        
        doc.add_paragraph("\n")
        p_num = doc.add_paragraph(f"Parecer Técnico GEJUD/DIRTEC/TJMG nº ____/2025.")
        p_num.runs[0].bold = True
        doc.add_paragraph("Assunto: Notifica erro no \"JPe - 2ª Instância\" ao peticionar.")
        
        data_atual = datetime.now().strftime("%d de %B de %Y")
        doc.add_paragraph(f"\nExmo(a). Senhor(a) Relator(a),\n\nBelo Horizonte, {data_atual}")
        
        corpo = doc.add_paragraph()
        corpo.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
        
        if tipo == 'Geral':
            txt = (f"Para fins de cumprimento dos artigos 13 e 14 da Resolução nº 780/2014 do Tribunal de Justiça do Estado de Minas Gerais, "
                   f"informamos que em {data} houve indisponibilidade do portal JPe, superior a uma hora, {hora}, que impossibilitou o peticionamento eletrônico de recursos em processos que já tramitavam no sistema.")
            corpo.add_run(txt)
        else:
            corpo.add_run(f"Informamos que no dia {data}, houve indisponibilidade específica do sistema para o peticionamento do processo nº {numero}.\n\n")
            corpo.add_run(f"O Chamado de número {chamado if chamado else '_____'}, foi aberto e encaminhado à DIRTEC (Diretoria Executiva de Tecnologia da Informação e Comunicação).\n\n")
            if tipo == 'Física':
                corpo.add_run("Diante da indisponibilidade específica, não havendo um prazo para solução do problema, a Primeira Vice-Presidência recomenda o ingresso dos autos físicos, nos termos do § 2º, do artigo 14º, da Resolução nº 780/2014, do Tribunal de Justiça do Estado de Minas Gerais.\n\n")
            else:
                corpo.add_run("Informamos a indisponibilidade para fins de restituição de prazo ou providências que V.Exa julgar necessárias, nos termos da legislação vigente.\n\n")
        
        corpo.add_run("\nColocamo-nos à disposição para outras informações que se fizerem necessárias.")
        doc.add_paragraph("\nRespeitosamente,")
        doc.add_paragraph("\n\n___________________________________\nWaner Andrade Silva\n0-009020-9\nCoordenação de Análise e Integração de Sistemas Judiciais Informatizados - COJIN\nGerência de Sistemas Judiciais - GEJUD\nDiretoria Executiva de Tecnologia da Informação e Comunicação - DIRTEC")

        buffer = io.BytesIO()
        doc.save(buffer)
        buffer.seek(0)
        return buffer
    except Exception as e:
        return None

# ============================================
# 2. LÓGICA DO APP (FILA/STATUS)
# ============================================
def save_state():
    try:
        last_run = st.session_state.report_last_run_date
        last_run_iso = last_run.isoformat() if isinstance(last_run, datetime) else datetime.min.isoformat()
        state_to_save = {
            'status_texto': st.session_state.status_texto, 'bastao_queue': st.session_state.bastao_queue,
            'skip_flags': st.session_state.skip_flags, 'current_status_starts': st.session_state.current_status_starts,
            'bastao_counts': st.session_state.bastao_counts, 'priority_return_queue': st.session_state.priority_return_queue,
            'bastao_start_time': st.session_state.bastao_start_time, 'report_last_run_date': last_run_iso, 
            'rotation_gif_start_time': st.session_state.get('rotation_gif_start_time'), 'lunch_warning_info': st.session_state.get('lunch_warning_info'),
            'auxilio_ativo': st.session_state.get('auxilio_ativo', False), 'daily_logs': st.session_state.daily_logs,
            'simon_ranking': st.session_state.get('simon_ranking', [])
        }
        save_state_to_db(state_to_save)
    except Exception as e: print(f"Erro save: {e}")

def load_logs(): return st.session_state.daily_logs
def format_time_duration(duration):
    if not isinstance(duration, timedelta): return '--:--:--'
    s = int(duration.total_seconds()); h, s = divmod(s, 3600); m, s = divmod(s, 60)
    return f'{h:02}:{m:02}:{s:02}'

# --- FUNÇÃO CRÍTICA: SINCRONIZAR COM BD NO REFRESH ---
def sync_state_from_db():
    try:
        # Se estivermos digitando (active_view não é None), EVITA sobrescrever para não perder dados.
        # Mas o autorefresh já bloqueia isso. Se chegamos aqui, podemos sincronizar.
        db_data = load_state_from_db()
        if not db_data: return

        # Lista de chaves críticas para atualizar
        keys = ['status_texto', 'bastao_queue', 'skip_flags', 'bastao_counts', 
                'priority_return_queue', 'daily_logs', 'simon_ranking']
        
        for k in keys:
            if k in db_data:
                st.session_state[k] = db_data[k]
        
        # Tratamento especial para DATAS (str -> datetime)
        if 'bastao_start_time' in db_data and db_data['bastao_start_time']:
            try:
                if isinstance(db_data['bastao_start_time'], str):
                    st.session_state['bastao_start_time'] = datetime.fromisoformat(db_data['bastao_start_time'])
                else:
                    st.session_state['bastao_start_time'] = db_data['bastao_start_time']
            except: pass
            
        if 'current_status_starts' in db_data:
            starts = db_data['current_status_starts']
            for nome, val in starts.items():
                if isinstance(val, str):
                    try:
                        st.session_state.current_status_starts[nome] = datetime.fromisoformat(val)
                    except: pass
                else:
                     st.session_state.current_status_starts[nome] = val

    except Exception as e:
        print(f"Erro sync: {e}")

def log_status_change(consultor, old_status, new_status, duration):
    if not isinstance(duration, timedelta): duration = timedelta(0)
    now_br = get_brazil_time()
    old_lbl = old_status if old_status else 'Fila Bastão'
    new_lbl = new_status if new_status else 'Fila Bastão'
    if consultor in st.session_state.bastao_queue:
        if 'Bastão' not in new_lbl and new_lbl != 'Fila Bastão': new_lbl = f"Fila | {new_lbl}"
    entry = {'timestamp': now_br, 'consultor': consultor, 'old_status': old_lbl, 'new_status': new_lbl, 'duration': duration, 'duration_s': duration.total_seconds()}
    st.session_state.daily_logs.append(entry)
    timestamp_str = now_br.strftime("%d/%m/%Y %H:%M:%S")
    duration_str = format_time_duration(duration)
    st.session_state.current_status_starts[consultor] = now_br

# --- HANDLERS ---
def on_auxilio_change(): save_state()


# --- STATUS RÁPIDO (Almoço / Saída / Ausente / Atividades etc.) ---
def update_status(novo_status: str, marcar_indisponivel: bool = False):
    selected = st.session_state.get('consultor_selectbox')
    if not selected or selected == 'Selecione um nome':
        st.warning('Selecione um(a) consultor(a) antes de alterar o status.')
        return

    ensure_daily_reset()
    now_br = get_brazil_time()
    current = st.session_state.status_texto.get(selected, '')

    # Se está com o Bastão e vai ficar indisponível, definimos um sucessor antes de remover
    forced_successor = None
    current_holder = next((c for c, s in st.session_state.status_texto.items() if 'Bastão' in (s or '')), None)
    if marcar_indisponivel and selected == current_holder and selected in st.session_state.bastao_queue:
        try:
            idx = st.session_state.bastao_queue.index(selected)
            nxt = find_next_holder_index(idx, st.session_state.bastao_queue, st.session_state.skip_flags)
            if nxt != -1:
                forced_successor = st.session_state.bastao_queue[nxt]
        except Exception:
            forced_successor = None

    # Marca check/skip e fila
    if marcar_indisponivel:
        st.session_state[f'check_{selected}'] = False
        st.session_state.skip_flags[selected] = True
        if selected in st.session_state.bastao_queue:
            st.session_state.bastao_queue.remove(selected)
            # volta com prioridade depois
            if selected not in st.session_state.priority_return_queue:
                st.session_state.priority_return_queue.append(selected)
    else:
        # Mantém disponível
        st.session_state[f'check_{selected}'] = True
        st.session_state.skip_flags[selected] = False

    # Monta status final (preserva 'Bastão |' se for o holder e NÃO estiver marcando indisponível)
    clean_new = (novo_status or '').strip()
    if clean_new == 'Fila Bastão':
        clean_new = ''
    if (not marcar_indisponivel) and selected == current_holder:
        final_status = ('Bastão | ' + clean_new).strip(' |') if clean_new else 'Bastão'
    else:
        final_status = clean_new
    if not final_status and (selected in st.session_state.bastao_queue):
        final_status = ''
    if not final_status and (selected not in st.session_state.bastao_queue):
        # Fora da fila sem status -> indisponível
        final_status = 'Indisponível'

    # Log + aplica
    try:
        started = st.session_state.current_status_starts.get(selected, now_br)
        log_status_change(selected, current, final_status, now_br - started)
    except Exception:
        pass
    st.session_state.status_texto[selected] = final_status

    # Se mexeu com bastão, revalida
    try:
        check_and_assume_baton(forced_successor=forced_successor)
    except Exception:
        pass

    save_state()
    st.rerun()



def send_chat_notification_internal(consultor, status):
    if CHAT_WEBHOOK_BASTAO and status == 'Bastão':
        msg = f"🎉 **BASTÃO GIRADO!** 🎉 \n\n- **Novo(a) Responsável:** {consultor}\n- **Acesse o Painel:** {APP_URL_CLOUD}"
        send_to_chat("bastao", msg); return True
    return False

def send_horas_extras_to_chat(consultor, data, inicio, tempo, motivo):
    msg = f"⏰ **Registro de Horas Extras**\n\n👤 **Consultor:** {consultor}\n📅 **Data:** {data.strftime('%d/%m/%Y')}\n🕐 **Início:** {inicio.strftime('%H:%M')}\n⏱️ **Tempo Total:** {tempo}\n📝 **Motivo:** {motivo}"
    send_to_chat("extras", msg); return True

def send_atendimento_to_chat(consultor, data, usuario, nome_setor, sistema, descricao, canal, desfecho, jira_opcional=""):
    jira_str = f"\n🔢 **Jira:** CESUPE-{jira_opcional}" if jira_opcional else ""
    msg = f"📋 **Novo Registro de Atendimento**\n\n👤 **Consultor:** {consultor}\n📅 **Data:** {data.strftime('%d/%m/%Y')}\n👥 **Usuário:** {usuario}\n🏢 **Nome/Setor:** {nome_setor}\n💻 **Sistema:** {sistema}\n📝 **Descrição:** {descricao}\n📞 **Canal:** {canal}\n✅ **Desfecho:** {desfecho}{jira_str}"
    send_to_chat("registro", msg); return True


# --- CHAMADOS / JIRA (rascunho para enviar ao chat) ---
def send_chamado_to_chat(consultor, texto):
    if not consultor or consultor == 'Selecione um nome':
        return False
    texto = (texto or '').strip()
    if not texto:
        return False
    data_envio = get_brazil_time().strftime('%d/%m/%Y %H:%M')
    msg = (
        f"🆘 **Rascunho de Chamado/Jira**\n"
        f"📅 **Data:** {data_envio}\n\n"
        f"👤 **Autor:** {consultor}\n\n"
        f"📝 **Texto:**\n{texto}"
    )
    try:
        send_to_chat('chamado', msg)
        return True
    except Exception:
        try:
            send_to_chat('registro', msg)
            return True
        except Exception:
            return False

def set_chamado_step(step):
    st.session_state.chamado_guide_step = int(step)

def handle_chamado_submission():
    consultor = st.session_state.get('consultor_selectbox')
    texto = st.session_state.get('chamado_textarea', '')
    ok = send_chamado_to_chat(consultor, texto)
    if ok:
        st.session_state.chamado_textarea = ''
        st.session_state.chamado_guide_step = 1
    return ok

def handle_erro_novidade_submission(consultor, titulo, objetivo, relato, resultado):
    data_envio = get_brazil_time().strftime("%d/%m/%Y %H:%M")
    msg = f"🐛 **Novo Relato de Erro/Novidade**\n📅 **Data:** {data_envio}\n\n👤 **Autor:** {consultor}\n📌 **Título:** {titulo}\n\n🎯 **Objetivo:**\n{objetivo}\n\n🧪 **Relato:**\n{relato}\n\n🏁 **Resultado:**\n{resultado}"
    send_to_chat("erro", msg); return True

def send_sessao_to_chat_fn(consultor, texto_mensagem):
    if not consultor or consultor == 'Selecione um nome': return False
    send_to_chat("sessao", texto_mensagem); return True

def play_sound_html(): return f'<audio autoplay="true"><source src="{SOUND_URL}" type="audio/mpeg"></audio>'
def render_fireworks(): st.markdown("""<style>...</style>""", unsafe_allow_html=True)

def auto_manage_time():
    now = get_brazil_time(); last_run = st.session_state.report_last_run_date
    if now.hour >= 23 and now.date() == last_run.date(): reset_day_state(); save_state()
    elif now.date() > last_run.date(): reset_day_state(); save_state()
    elif now.hour >= 20:
        if any(s != 'Indisponível' for s in st.session_state.status_texto.values()) or st.session_state.bastao_queue:
            st.session_state.bastao_queue = []; st.session_state.status_texto = {n: 'Indisponível' for n in CONSULTORES}
            for n in CONSULTORES: st.session_state[f'check_{n}'] = False
            save_state()

# --- LÓGICA DE FILA BLINDADA (AGRESSIVA) ---
def find_next_holder_index(current_index, queue, skips):
    if not queue: return -1
    n = len(queue)
    start_index = (current_index + 1) % n
    for i in range(n):
        idx = (start_index + i) % n
        consultor = queue[idx]
        if consultor == queue[current_index] and n > 1: continue
        if not skips.get(consultor, False): return idx
    if n > 1:
        proximo_imediato_idx = (current_index + 1) % n
        nome_escolhido = queue[proximo_imediato_idx]
        st.session_state.skip_flags[nome_escolhido] = False 
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
            if current_holder != target: 
                st.session_state.play_sound = True; send_chat_notification_internal(target, 'Bastão')
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
        'chamado_guide_step': 0, 'sessao_msg_preview': "", 'html_download_ready': False, 'html_content_cache': "",
        'auxilio_ativo': False, 'active_view': None, 'last_jira_number': "",
        'simon_sequence': [], 'simon_user_input': [], 'simon_status': 'start', 'simon_level': 1,
        'consultor_selectbox': "Selecione um nome",
        'status_texto': {nome: 'Indisponível' for nome in CONSULTORES},
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
        blocking = ['Almoço', 'Ausente', 'Saída rápida', 'Sessão', 'Reunião', 'Treinamento']
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
    now_hour = get_brazil_time().hour
    if now_hour >= 20 or now_hour < 6:
        st.toast("💤 Fora do expediente!", icon="🌙"); return False
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
    save_state(); return True

def leave_specific_status(consultor, status_type_to_remove):
    ensure_daily_reset(); st.session_state.gif_warning = False
    if status_type_to_remove in ['Almoço', 'Treinamento', 'Sessão', 'Reunião', 'Saída rápida', 'Ausente']:
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
    now_hour = get_brazil_time().hour
    if now_hour >= 20 or now_hour < 6: st.toast("💤 Fora do expediente!", icon="🌙"); time.sleep(1); st.rerun(); return
    ensure_daily_reset(); st.session_state.gif_warning = False
    if consultor not in st.session_state.bastao_queue: st.session_state.bastao_queue.append(consultor)
    st.session_state[f'check_{consultor}'] = True
    st.session_state.skip_flags[consultor] = False
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
        # --- CORREÇÃO: Limpar flag 'Pular' de quem foi pulado ---
        n_queue = len(queue)
        tmp_idx = (current_index + 1) % n_queue
        # Percorre do atual até o novo dono. Quem estiver no caminho, foi pulado.
        while tmp_idx != next_idx:
            skipped_name = queue[tmp_idx]
            if st.session_state.skip_flags.get(skipped_name, False):
                st.session_state.skip_flags[skipped_name] = False
            tmp_idx = (tmp_idx + 1) % n_queue
        # --------------------------------------------------------

        next_holder = queue[next_idx]
        st.session_state.skip_flags[next_holder] = False
        now_br = get_brazil_time()
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
        st.session_state.play_sound = True; st.session_state.rotation_gif_start_time = now_br
        send_chat_notification_internal(next_holder, 'Bastão'); save_state()
    else: st.warning('Ninguém elegível.'); check_and_assume_baton()


def manual_rerun(): st.session_state.gif_warning = False; st.rerun()
def toggle_view(v):
    # Alterna a exibição de painéis (tools/menus)
    if st.session_state.active_view == v:
        st.session_state.active_view = None
        return
    st.session_state.active_view = v
    if v == 'chamados':
        st.session_state.chamado_guide_step = 1

# --- SIMON GAME ---
def simon_game_ui():
    # Modo Descanso: mini jogo de memória (Simon)
    import random
    COLORS = ['🔴', '🔵', '🟢', '🟡']

    st.session_state.setdefault('simon_sequence', [])
    st.session_state.setdefault('simon_user_input', [])
    st.session_state.setdefault('simon_status', 'start')
    st.session_state.setdefault('simon_level', 1)
    st.session_state.setdefault('simon_ranking', [])

    st.markdown('### 🧠 Descanso: Jogo da Memória (Simon)')
    st.caption('Repita a sequência de cores!')

    status = st.session_state.simon_status

    if status == 'start':
        if st.button('▶️ Iniciar Jogo', type='primary', use_container_width=True):
            st.session_state.simon_sequence = [random.choice(COLORS)]
            st.session_state.simon_user_input = []
            st.session_state.simon_level = 1
            st.session_state.simon_status = 'showing'
            st.rerun()

    elif status == 'showing':
        st.info(f'Nível {st.session_state.simon_level}: memorize a sequência!')
        cols = st.columns(len(st.session_state.simon_sequence))
        for i, color in enumerate(st.session_state.simon_sequence):
            with cols[i]:
                st.markdown(f"<h1 style='text-align:center; margin:0;'>{color}</h1>", unsafe_allow_html=True)
        st.markdown('---')
        if st.button('🙈 Já decorei! Responder', use_container_width=True):
            st.session_state.simon_status = 'playing'
            st.session_state.simon_user_input = []
            st.rerun()

    elif status == 'playing':
        st.markdown(f'**Nível {st.session_state.simon_level}** - clique na ordem:')
        c1, c2, c3, c4 = st.columns(4)
        pressed = None
        if c1.button('🔴', use_container_width=True): pressed = '🔴'
        if c2.button('🔵', use_container_width=True): pressed = '🔵'
        if c3.button('🟢', use_container_width=True): pressed = '🟢'
        if c4.button('🟡', use_container_width=True): pressed = '🟡'

        if pressed:
            st.session_state.simon_user_input.append(pressed)
            idx = len(st.session_state.simon_user_input) - 1
            if st.session_state.simon_user_input[idx] != st.session_state.simon_sequence[idx]:
                st.session_state.simon_status = 'lost'
                st.rerun()
            elif len(st.session_state.simon_user_input) == len(st.session_state.simon_sequence):
                st.success('Correto! Próximo nível...')
                time.sleep(0.35)
                st.session_state.simon_sequence.append(random.choice(COLORS))
                st.session_state.simon_user_input = []
                st.session_state.simon_level += 1
                st.session_state.simon_status = 'showing'
                st.rerun()

        if st.session_state.simon_user_input:
            st.markdown('Sua resposta: ' + ' '.join(st.session_state.simon_user_input))

    elif status == 'lost':
        st.error(f'❌ Errou! Você chegou ao Nível {st.session_state.simon_level}.')
        st.markdown('Sequência correta era: ' + ' '.join(st.session_state.simon_sequence))

        consultor = st.session_state.get('consultor_selectbox')
        if consultor and consultor != 'Selecione um nome':
            score = st.session_state.simon_level
            ranking = st.session_state.simon_ranking
            # salva melhor score por consultor
            found = False
            for item in ranking:
                if item.get('consultor') == consultor:
                    item['score'] = max(int(item.get('score', 0)), int(score))
                    found = True
                    break
            if not found:
                ranking.append({'consultor': consultor, 'score': int(score)})
            ranking.sort(key=lambda x: int(x.get('score', 0)), reverse=True)
            st.session_state.simon_ranking = ranking[:10]
            save_state()

        if st.button('🔁 Jogar novamente', use_container_width=True):
            st.session_state.simon_status = 'start'
            st.rerun()

    if st.session_state.get('simon_ranking'):
        st.markdown('---')
        st.subheader('🏆 Ranking (Top 10)')
        for i, item in enumerate(st.session_state.simon_ranking, start=1):
            st.write(f"{i}. {item.get('consultor')} - Nível {item.get('score')}")

    if st.button('❌ Sair', use_container_width=True):
        st.session_state.active_view = None
        st.rerun()
# ============================================
# EXECUÇÃO PRINCIPAL
# ============================================
    
def toggle_skip():
    selected = st.session_state.consultor_selectbox
    if not selected or selected == 'Selecione um nome':
        st.warning('Selecione um(a) consultor(a).')
        return
    if not st.session_state.get(f'check_{selected}'):
        st.warning(f'{selected} não está disponível.')
        return
    novo = not st.session_state.skip_flags.get(selected, False)
    st.session_state.skip_flags[selected] = novo
    # --- CORREÇÃO: Pular mantém o lugar na fila (não move pro final) ---
    # Apenas marca a flag, sem reordenar a lista.
    # -------------------------------------------------------------------
    save_state()
    st.rerun()
st.set_page_config(page_title="Controle Bastão Cesupe 2026", layout="wide", page_icon="🥂")

# --- Ajuste visual: botões sempre proporcionais e na mesma linha ---
st.markdown("""
<style>
  div.stButton > button {
    width: 100%;
    white-space: nowrap;
    height: 3rem;
  }
</style>
""", unsafe_allow_html=True)
st.markdown("""
<style>
/* Mantém os botões dos atalhos (Checklist/Chamados/...) alinhados e proporcionais */
[data-testid='stHorizontalBlock'] div.stButton > button {
  white-space: nowrap;
  height: 3rem;
}
</style>
""", unsafe_allow_html=True)

init_session_state(); auto_manage_time()
st.components.v1.html("<script>window.scrollTo(0, 0);</script>", height=0)
render_fireworks()

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

# ---------------------------------------------------------
# LÓGICA DE ATUALIZAÇÃO AUTOMÁTICA (REFRESH + SYNC)
# ---------------------------------------------------------
# Se não estiver em nenhuma "view" de registro (active_view == None), atualiza a cada 20 segundos.
# Caso contrário, pausa para não atrapalhar a digitação.
if st.session_state.active_view is None:
    st_autorefresh(interval=20000, key='auto_rerun')
    # --- NOVO: Sincroniza dados do banco para que User B veja mudanças de User A ---
    sync_state_from_db() 
else:
    # Opcional: Mostra um aviso discreto de que a atualização está pausada
    st.caption("⏸️ Atualização automática pausada durante o registro.")


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
    
    # --- Nova Lógica de Exibição Horizontal ---
    
    # 1. Identificar quem pulou (que esteja na fila)
    lista_pularam = [n for n in queue if skips.get(n, False) and n != responsavel]

    # 2. Montar a fila ordenada para exibir "Demais"
    demais_na_fila = []
    # Se existe responsável na fila, rotacionamos para começar depois dele
    if responsavel and responsavel in queue:
        c_idx = queue.index(responsavel)
        raw_ordered = queue[c_idx+1:] + queue[:c_idx]
    else:
        # Se não tem responsável (ou ele não tá na fila), mostra a fila como está
        raw_ordered = list(queue)

    for n in raw_ordered:
        # Filtra: não pode ser o próximo, não pode ter pulado
        if n != proximo and not skips.get(n, False):
            demais_na_fila.append(n)

    # Exibição: Próximo Bastão
    if proximo:
        st.markdown(f"**Próximo Bastão:** {proximo}")
    else:
        st.markdown("**Próximo Bastão:** _Ninguém elegível_")

    # Exibição: Demais na fila
    if demais_na_fila:
        st.markdown(f"**Demais na fila:** {', '.join(demais_na_fila)}")
    else:
        st.markdown("**Demais na fila:** _Vazio_")

    # Exibição: Quem pulou
    if lista_pularam:
        st.markdown(f"**Consultor(es) pulou(pularam) o bastão:** {', '.join(lista_pularam)}")

    # --- Fim Nova Lógica ---
    
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

    if st.session_state.active_view == 'menu_atividades':
        with st.container(border=True):
            at_t = st.multiselect("Tipo:", OPCOES_ATIVIDADES_STATUS); at_e = st.text_input("Detalhe:")
            if st.button("Confirmar Atividade"): st.session_state.active_view = None; update_status(f"Atividade: {', '.join(at_t)} - {at_e}")
            if st.button("❌ Cancelar Registro"): st.session_state.active_view = None; st.rerun()

    if st.session_state.active_view == 'menu_projetos':
        with st.container(border=True):
            st.subheader('🏗️ Registrar Projeto')
            proj = st.selectbox('Projeto:', ['Selecione'] + OPCOES_PROJETOS, key='proj_opt')
            det = st.text_input('Detalhe (opcional):', key='proj_det')
            c_ok, c_cancel = st.columns(2)
            with c_ok:
                if st.button('✅ Confirmar Projeto', type='primary', use_container_width=True, key='btn_proj_ok'):
                    if proj == 'Selecione':
                        st.warning('Selecione um projeto.')
                    else:
                        st.session_state.active_view = None
                        status = f"Projeto: {proj}" + (f" - {det.strip()}" if det.strip() else "")
                        update_status(status, False)
            with c_cancel:
                if st.button('❌ Cancelar', use_container_width=True, key='btn_proj_cancel'):
                    st.session_state.active_view = None
                    st.rerun()

    if st.session_state.active_view == 'menu_treinamento':
        with st.container(border=True):
            st.subheader('🎓 Registrar Treinamento')
            tema = st.text_input('Tema/Conteúdo:', key='trein_tema')
            obs = st.text_input('Observação (opcional):', key='trein_obs')
            c_ok, c_cancel = st.columns(2)
            with c_ok:
                if st.button('✅ Confirmar Treinamento', type='primary', use_container_width=True, key='btn_trein_ok'):
                    if not tema.strip():
                        st.warning('Informe o tema do treinamento.')
                    else:
                        st.session_state.active_view = None
                        status = f"Treinamento: {tema.strip()}" + (f" - {obs.strip()}" if obs.strip() else "")
                        update_status(status, True)
            with c_cancel:
                if st.button('❌ Cancelar', use_container_width=True, key='btn_trein_cancel'):
                    st.session_state.active_view = None
                    st.rerun()

    if st.session_state.active_view == 'menu_reuniao':
        with st.container(border=True):
            st.subheader('📅 Registrar Reunião')
            assunto = st.text_input('Assunto:', key='reun_assunto')
            obs = st.text_input('Observação (opcional):', key='reun_obs')
            c_ok, c_cancel = st.columns(2)
            with c_ok:
                if st.button('✅ Confirmar Reunião', type='primary', use_container_width=True, key='btn_reun_ok'):
                    if not assunto.strip():
                        st.warning('Informe o assunto da reunião.')
                    else:
                        st.session_state.active_view = None
                        status = f"Reunião: {assunto.strip()}" + (f" - {obs.strip()}" if obs.strip() else "")
                        update_status(status, True)
            with c_cancel:
                if st.button('❌ Cancelar', use_container_width=True, key='btn_reun_cancel'):
                    st.session_state.active_view = None
                    st.rerun()

    if st.session_state.active_view == 'menu_sessao':
        with st.container(border=True):
            st.subheader('🎙️ Registrar Sessão')
            cam = st.selectbox('Câmara:', ['Selecione'] + CAMARAS_OPCOES, key='sess_camara')
            obs = st.text_input('Observação (opcional):', key='sess_obs')
            enviar_chat = st.checkbox('Enviar aviso no chat (sessao)', value=True, key='sess_chat')
            c_ok, c_cancel = st.columns(2)
            with c_ok:
                if st.button('✅ Confirmar Sessão', type='primary', use_container_width=True, key='btn_sess_ok'):
                    consultor = st.session_state.get('consultor_selectbox')
                    if not consultor or consultor == 'Selecione um nome':
                        st.error('Selecione um consultor no menu principal.')
                    elif cam == 'Selecione':
                        st.warning('Selecione uma câmara.')
                    else:
                        if enviar_chat:
                            data_envio = get_brazil_time().strftime('%d/%m/%Y %H:%M')
                            msg = (
                                f"🎙️ **Sessão registrada**\n\n"
                                f"👤 **Consultor:** {consultor}\n"
                                f"🏛️ **Câmara:** {cam}\n"
                                f"🕒 **Data/Hora:** {data_envio}"
                                + (f"\n📝 **Obs:** {obs.strip()}" if obs.strip() else "")
                            )
                            try:
                                send_sessao_to_chat_fn(consultor, msg)
                            except Exception:
                                pass
                        st.session_state.active_view = None
                        status = f"Sessão: {cam}" + (f" - {obs.strip()}" if obs.strip() else "")
                        update_status(status, True)
            with c_cancel:
                if st.button('❌ Cancelar', use_container_width=True, key='btn_sess_cancel'):
                    st.session_state.active_view = None
                    st.rerun()

    st.markdown("####"); st.button('🔄 Atualizar (Manual)', on_click=manual_rerun, use_container_width=True); st.markdown("---")
    c_tool1, c_tool2, c_tool3, c_tool4, c_tool5, c_tool6 = st.columns(6)

    c_tool1.button("📑 Checklist", help="Gerador de Checklist Eproc", use_container_width=True, on_click=toggle_view, args=("checklist",))
    c_tool2.button("🆘 Chamados", help="Guia de Abertura de Chamados", use_container_width=True, on_click=toggle_view, args=("chamados",))
    c_tool3.button("📝 Atendimentos", help="Registrar Atendimento", use_container_width=True, on_click=toggle_view, args=("atendimentos",))
    c_tool4.button("⏰ H. Extras", help="Registrar Horas Extras", use_container_width=True, on_click=toggle_view, args=("hextras",))
    c_tool5.button("🐛 Erro/Novidade", help="Relatar Erro ou Novidade", use_container_width=True, on_click=toggle_view, args=("erro_novidade",))
    c_tool6.button("🖨️ Certidão", help="Gerar Certidão de Indisponibilidade", use_container_width=True, on_click=toggle_view, args=("certidao",))

    if st.session_state.active_view == "checklist":
        with st.container(border=True):
            st.header("Gerador de Checklist"); data_eproc = st.date_input("Data:", value=get_brazil_time().date()); camara_eproc = st.selectbox("Câmara:", CAMARAS_OPCOES)
            if st.button("Gerar HTML"): st.write("Checklist registrado no chat!"); send_to_chat("sessao", f"Consultor {st.session_state.consultor_selectbox} acompanhando sessão {camara_eproc}")
            if st.button("❌ Cancelar Registro"): st.session_state.active_view = None; st.rerun()


    if st.session_state.active_view == "chamados":
        with st.container(border=True):
            st.header('🆘 Chamados (Padrão / Jira)')
            guide_step = st.session_state.get('chamado_guide_step', 1) or 1
            if guide_step == 1:
                st.subheader('Passo 1: Testes iniciais')
                st.markdown('Antes de abrir o chamado, realize os testes de suporte e registre evidências.')
                st.button('Próximo (Passo 2) ➡️', on_click=set_chamado_step, args=(2,), use_container_width=True)
            elif guide_step == 2:
                st.subheader('Passo 2: Checklist de abertura')
                st.markdown('- Dados do usuário\n- Dados do processo\n- Descrição do erro\n- Prints/Vídeo')
                st.button('Próximo (Passo 3) ➡️', on_click=set_chamado_step, args=(3,), use_container_width=True)
            elif guide_step == 3:
                st.subheader('Passo 3: Registrar e informar')
                st.markdown('Após abrir, informe o número do chamado ao usuário (e-mail institucional).')
                st.button('Próximo (Observações) ➡️', on_click=set_chamado_step, args=(4,), use_container_width=True)
            elif guide_step == 4:
                st.subheader('Observações')
                st.markdown('- Comunicação via e-mail institucional\n- Atualizar registro interno quando aplicável')
                st.button('Entendi! Abrir campo ➡️', on_click=set_chamado_step, args=(5,), use_container_width=True)
            else:
                st.subheader('Rascunho do Chamado/Jira')
                st.text_area('Cole aqui o texto do chamado/jira:', height=240, key='chamado_textarea')
                c_send, c_cancel = st.columns(2)
                with c_send:
                    if st.button('📨 Enviar para o Chat', type='primary', use_container_width=True):
                        ok = handle_chamado_submission()
                        if ok:
                            st.success('Rascunho enviado!')
                            st.session_state.active_view = None
                            st.rerun()
                        else:
                            st.error('Não foi possível enviar. Verifique o canal/webhook.')
                with c_cancel:
                    if st.button('❌ Cancelar', use_container_width=True):
                        st.session_state.active_view = None
                        st.rerun()

    if st.session_state.active_view == "atendimentos":
        with st.container(border=True):
            st.header('📝 Registro de Atendimentos')
            at_data = st.date_input('Data:', value=get_brazil_time().date(), key='at_data')
            at_usuario = st.selectbox('Usuário:', REG_USUARIO_OPCOES, key='at_user')
            at_nome_setor = st.text_input('Nome usuário - Setor:', key='at_setor')
            at_sistema = st.selectbox('Sistema:', REG_SISTEMA_OPCOES, key='at_sys')
            at_descricao = st.text_input('Descrição (até 7 palavras):', key='at_desc')
            at_canal = st.selectbox('Canal:', REG_CANAL_OPCOES, key='at_channel')
            at_desfecho = st.selectbox('Desfecho:', REG_DESFECHO_OPCOES, key='at_outcome')
            default_jira = st.session_state.get('last_jira_number', '')
            at_jira = st.text_input('Número do Jira:', value=default_jira, placeholder='Ex: 1234', key='at_jira_input')
            if st.button('Enviar Atendimento', type='primary', use_container_width=True):
                consultor = st.session_state.get('consultor_selectbox')
                if not consultor or consultor == 'Selecione um nome':
                    st.error('Selecione um consultor no menu principal.')
                else:
                    st.session_state['last_jira_number'] = at_jira
                    ok = send_atendimento_to_chat(consultor, at_data, at_usuario, at_nome_setor, at_sistema, at_descricao, at_canal, at_desfecho, at_jira)
                    if ok:
                        st.success('Atendimento registrado!')
                        st.session_state.active_view = None
                        st.rerun()
                    else:
                        st.error('Erro ao enviar. Verifique o canal/webhook.')
    if st.session_state.active_view == "hextras":
        with st.container(border=True):
            st.header("⏰ Horas Extras")
            d_ex = st.date_input("Data:"); h_in = st.time_input("Início:"); t_ex = st.text_input("Tempo Total:"); mot = st.text_input("Motivo:")
            if st.button("Registrar"): send_horas_extras_to_chat(st.session_state.consultor_selectbox, d_ex, h_in, t_ex, mot); st.success("Registrado!"); st.session_state.active_view = None; st.rerun()
            if st.button("❌ Cancelar Registro"): st.session_state.active_view = None; st.rerun()

    if st.session_state.active_view == "erro_novidade":
        with st.container(border=True):
            st.header("🐛 Erro/Novidade")
            tit = st.text_input("Título:"); obj = st.text_area("Objetivo:"); rel = st.text_area("Relato:"); res = st.text_area("Resultado:")
            if st.button("Enviar"): handle_erro_novidade_submission(st.session_state.consultor_selectbox, tit, obj, rel, res); st.success("Enviado!"); st.session_state.active_view = None; st.rerun()
            if st.button("❌ Cancelar Registro"): st.session_state.active_view = None; st.rerun()

    if st.session_state.active_view == "certidao":
        with st.container(border=True):
            st.header("🖨️ Registro de Certidão")
            tipo_cert = st.selectbox("Tipo:", ["Física", "Eletrônica", "Geral"])
            c_data = st.date_input("Data do Evento:", value=get_brazil_time().date())
            c_cons = st.session_state.consultor_selectbox
            if tipo_cert == "Geral":
                c_hora = st.text_input("Horário/Período (ex: a partir das 14:00):"); c_motivo = st.text_input("Motivo:"); c_proc = ""
            else:
                c_hora = ""; col_c1, col_c2 = st.columns(2)
                c_chamado = col_c1.text_input("Nº Chamado:"); c_proc = col_c2.text_input("Nº Processo:"); c_motivo = st.text_area("Motivo / Erro:")
            col_btn1, col_btn2 = st.columns(2)
            with col_btn1:
                if st.button("📄 Gerar Modelo Word", use_container_width=True):
                    st.session_state.word_buffer = gerar_docx_certidao_internal(tipo_cert, c_proc, c_data.strftime("%d/%m/%Y"), c_cons, c_motivo, c_chamado if tipo_cert != 'Geral' else '', c_hora)
                if st.session_state.word_buffer:
                    st.download_button("⬇️ Baixar DOCX", st.session_state.word_buffer, file_name=f"certidao.docx")
            with col_btn2:
                if st.button("💾 Salvar Registro", type="primary", use_container_width=True):
                    if verificar_duplicidade_certidao(tipo_cert, c_proc, c_data, c_hora): st.session_state.aviso_duplicidade = True
                    else:
                        payload = {"tipo": tipo_cert, "data_evento": c_data.isoformat(), "consultor": c_cons, "n_chamado": c_chamado if tipo_cert != 'Geral' else '', "n_processo": c_proc.strip().rstrip('.'), "motivo": c_motivo, "hora_periodo": c_hora}
                        if salvar_certidao_db(payload): st.success("✅ Salvo!"); time.sleep(2); st.session_state.active_view = None; st.session_state.word_buffer = None; st.rerun()
            if st.button("❌ Cancelar Registro", key="cancel_cert"): st.session_state.active_view = None; st.rerun()
            if st.session_state.get('aviso_duplicidade'):
                st.error("⚠️ ATENÇÃO: Registro já existe! Favor procurar Matheus ou Gilberto.")
                if st.button("Ciente"): st.session_state.aviso_duplicidade = False; st.rerun()

with col_disponibilidade:
    st.header('Status dos(as) Consultores(as)')

    ui_lists = {
        'fila': [], 'almoco': [], 'saida': [], 'ausente': [], 'atividade_especifica': [],
        'sessao_especifica': [], 'projeto_especifico': [], 'reuniao_especifica': [],
        'treinamento_especifico': [], 'indisponivel': []
    }

    for nome in CONSULTORES:
        if nome in st.session_state.bastao_queue:
            ui_lists['fila'].append(nome)

        status = st.session_state.status_texto.get(nome, 'Indisponível')
        status = status if status is not None else 'Indisponível'

        if status in ('', None):
            pass
        elif status == 'Almoço':
            ui_lists['almoco'].append(nome)
        elif status == 'Ausente':
            ui_lists['ausente'].append(nome)
        elif status == 'Saída rápida':
            ui_lists['saida'].append(nome)
        elif status == 'Indisponível' and nome not in st.session_state.bastao_queue:
            ui_lists['indisponivel'].append(nome)

        # Detalhados
        if isinstance(status, str):
            if 'Sessão:' in status or status.strip() == 'Sessão':
                match = re.search(r'Sessão:\s*(.*)', status)
                desc = match.group(1).split('|')[0].strip() if match else 'Sessão'
                ui_lists['sessao_especifica'].append((nome, desc))

            if 'Reunião:' in status or status.strip() == 'Reunião':
                match = re.search(r'Reunião:\s*(.*)', status)
                desc = match.group(1).split('|')[0].strip() if match else 'Reunião'
                ui_lists['reuniao_especifica'].append((nome, desc))

            if 'Projeto:' in status or status.strip() == 'Projeto':
                match = re.search(r'Projeto:\s*(.*)', status)
                desc = match.group(1).split('|')[0].strip() if match else 'Projeto'
                ui_lists['projeto_especifico'].append((nome, desc))

            if 'Treinamento:' in status or status.strip() == 'Treinamento':
                match = re.search(r'Treinamento:\s*(.*)', status)
                desc = match.group(1).split('|')[0].strip() if match else 'Treinamento'
                ui_lists['treinamento_especifico'].append((nome, desc))

            if 'Atividade:' in status or status.strip() == 'Atendimento':
                if status.strip() == 'Atendimento':
                    ui_lists['atividade_especifica'].append((nome, 'Atendimento'))
                else:
                    match = re.search(r'Atividade:\s*(.*)', status)
                    desc = match.group(1).split('|')[0].strip() if match else 'Em demanda'
                    ui_lists['atividade_especifica'].append((nome, desc))

    # ----------------------------
    # Fila
    # ----------------------------
    st.subheader(f'✅ Na Fila ({len(ui_lists["fila"])})')
    render_order = [c for c in queue if c in ui_lists['fila']]

    if not render_order:
        st.markdown('_Ninguém na fila._')
    else:
        for nome in render_order:
            col_nome, col_check = st.columns([0.85, 0.15], vertical_alignment='center')
            col_check.checkbox(' ', key=f'chk_fila_{nome}', value=True, on_change=toggle_queue, args=(nome,), label_visibility='collapsed')

            skip_flag = skips.get(nome, False)
            status_atual = st.session_state.status_texto.get(nome, '') or ''
            extra = ''
            if 'Atividade' in status_atual: extra += ' 📋'
            if 'Projeto' in status_atual: extra += ' 🏗️'

            if nome == responsavel:
                display = f'<span style="background-color: #FFD700; color: #000; padding: 2px 6px; border-radius: 5px; font-weight: 800;">🥂 {nome}</span>'
            elif skip_flag:
                display = f'<strong>{nome}</strong>{extra} <span style="background-color: #FFECB3; padding: 2px 8px; border-radius: 10px;">Pulando ⏭️</span>'
            else:
                display = f'<strong>{nome}</strong>{extra} <span style="background-color: #BBDEFB; padding: 2px 8px; border-radius: 10px;">Aguardando</span>'

            col_nome.markdown(display, unsafe_allow_html=True)

    st.markdown('---')

    # ----------------------------
    # Seções auxiliares
    # ----------------------------
    def _render_section_detalhada(titulo, icon, lista_tuplas, badge_color, keyword_removal):
        colors = {
            'orange': '#FFECB3', 'blue': '#BBDEFB', 'teal': '#B2DFDB',
            'violet': '#E1BEE7', 'green': '#C8E6C9', 'red': '#FFCDD2', 'grey': '#EEEEEE'
        }
        bg_hex = colors.get(badge_color, '#EEEEEE')
        st.subheader(f'{icon} {titulo} ({len(lista_tuplas)})')
        if not lista_tuplas:
            st.markdown(f'_Nenhum registro em {titulo.lower()}._')
        else:
            for nome, desc in sorted(lista_tuplas, key=lambda x: x[0]):
                col_nome, col_check = st.columns([0.85, 0.15], vertical_alignment='center')
                col_check.checkbox(' ', key=f'chk_{titulo}_{nome}', value=True, on_change=leave_specific_status, args=(nome, keyword_removal), label_visibility='collapsed')
                col_nome.markdown(
                    f"<div style='font-size: 16px; margin: 2px 0;'><strong>{nome}</strong><span style='background-color: {bg_hex}; color: #333; padding: 2px 8px; border-radius: 12px; font-size: 14px; margin-left: 8px;'>{desc}</span></div>",
                    unsafe_allow_html=True
                )
        st.markdown('---')

    def _render_section_simples(titulo, icon, nomes, badge_color):
        colors = {
            'orange': '#FFECB3', 'blue': '#BBDEFB', 'teal': '#B2DFDB',
            'violet': '#E1BEE7', 'green': '#C8E6C9', 'red': '#FFCDD2', 'grey': '#EEEEEE'
        }
        bg_hex = colors.get(badge_color, '#EEEEEE')
        st.subheader(f'{icon} {titulo} ({len(nomes)})')
        if not nomes:
            st.markdown(f'_Ninguém em {titulo.lower()}._')
        else:
            for nome in sorted(nomes):
                col_nome, col_check = st.columns([0.85, 0.15], vertical_alignment='center')
                if titulo == 'Indisponível':
                    col_check.checkbox(' ', key=f'chk_{titulo}_{nome}', value=False, on_change=enter_from_indisponivel, args=(nome,), label_visibility='collapsed')
                else:
                    col_check.checkbox(' ', key=f'chk_{titulo}_{nome}', value=True, on_change=leave_specific_status, args=(nome, titulo), label_visibility='collapsed')

                col_nome.markdown(
                    f"<div style='font-size: 16px; margin: 2px 0;'><strong>{nome}</strong><span style='background-color: {bg_hex}; color: #444; padding: 2px 6px; border-radius: 6px; font-size: 12px; margin-left: 6px; vertical-align: middle; text-transform: uppercase;'>{titulo}</span></div>",
                    unsafe_allow_html=True
                )
        st.markdown('---')

    _render_section_detalhada('Em Demanda', '📋', ui_lists['atividade_especifica'], 'orange', 'Atividade')
    _render_section_detalhada('Projetos', '🏗️', ui_lists['projeto_especifico'], 'blue', 'Projeto')
    _render_section_detalhada('Treinamento', '🎓', ui_lists['treinamento_especifico'], 'teal', 'Treinamento')
    _render_section_detalhada('Reuniões', '📅', ui_lists['reuniao_especifica'], 'violet', 'Reunião')

    _render_section_simples('Almoço', '🍽️', ui_lists['almoco'], 'red')
    _render_section_detalhada('Sessão', '🎙️', ui_lists['sessao_especifica'], 'green', 'Sessão')
    _render_section_simples('Saída rápida', '🚶', ui_lists['saida'], 'red')
    _render_section_simples('Ausente', '👤', ui_lists['ausente'], 'violet')
    _render_section_simples('Indisponível', '❌', ui_lists['indisponivel'], 'grey')
