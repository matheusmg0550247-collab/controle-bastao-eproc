import streamlit as st
import pandas as pd
import subprocess
import time
from pyngrok import ngrok
from textwrap import dedent
import json
import os 
import requests 
from datetime import datetime, timedelta 
from operator import itemgetter

# --- 1. Instalação e Configuração ---

print("Instalando bibliotecas...")
!pip install streamlit pyngrok pandas requests -qq

# --- 2. Definição das Variáveis Globais ---
# TOKEN NGROK INSERIDO
NGROK_AUTH_TOKEN = "33qWVVUBttRjIByEhBsD0I9Z830_2vJSytCoeDRX4FpYHQX3q" 
# NOVO WEBHOOK PARA O RELATÓRIO DIÁRIO (ENVIADO APENAS PELO SCHEDULER)
GOOGLE_CHAT_WEBHOOK_URL = "https://chat.googleapis.com/v1/spaces/AAQA5CyNolU/messages?key=AIzaSyDdI0hCZtE6vySjMm-WEfRq3CPzqKqqsHI&token=Zolqmc0YfJ5bPzsqLrefwn8yBbNQLLfFBzLTwIkr7W4" 
BASTAO_EMOJI = "🌸" 

CONSULTORES = [
    "Barbara", "Bruno", "Claudia", "Douglas", "Fábio", "Glayce", "Isac", 
    "Isabela", "Ivana", "Leonardo", "Morôni", "Michael", "Pablo", "Ranyer", 
    "Rhuan", "Victoria"
]

# --- 3. Configuração do ngrok ---
try:
    ngrok.kill()
    ngrok.set_auth_token(NGROK_AUTH_TOKEN)
    print("Token do ngrok configurado.")
except Exception as e:
    print(f"Aviso: Erro ao configurar ngrok: {e}.")


# --- 4. CÓDIGO DO APP STREAMLIT (app.py) ---

def generate_app_code(consultores, emoji, webhook_url):
    app_code_lines = [
        "import streamlit as st",
        "import pandas as pd",
        "import requests",
        "import time",
        "import json",
        "from datetime import datetime, timedelta",
        "from operator import itemgetter",
        "",
        f"BASTAO_EMOJI = '{emoji}'",
        f"CONSULTORES = {consultores}",
        f"WEBHOOK_URL = '{webhook_url}'",
        "TIMER_RERUN_S = 10",
        "LOG_FILE = 'status_log.json'",
        "YOUTUBE_ID = 'yW0D5iK0i_A'",
        "START_TIME_S = 10",
        "PLAYBACK_TIME_MS = 10000",
        "STATUS_SAIDA_PRIORIDADE = ['Saída Temporária']",
        "STATUSES_DE_SAIDA = ['Atividade', 'Almoço', 'Saída Temporária']",
        "",
        "# --- Funções de Log e Ajuda ---",
        "",
        "def send_chat_notification_internal(consultor, status):",
        "    if WEBHOOK_URL and WEBHOOK_URL != 'SUA_URL_DO_WEBHOOK_DO_CHAT_AQUI':",
        '        message_text = "📢 **MUDANÇA DE BASTÃO CESUPE** \\n\\n- **Consultor:** {{consultor}}\\n- **Novo Status:** {{status}}\\n\\n*Acesse o Streamlit para mais detalhes.*"',
        '        chat_message = {{"text": message_text.format(consultor=consultor, status=status)}}',
        '        try:',
        '            requests.post(WEBHOOK_URL, json=chat_message)',
        '            return True',
        '        except requests.exceptions.RequestException:',
        '            return False',
        '    return False',
        "",
        "def play_sound_html():",
        '    return """',
        '<audio autoplay="true">',
        '    <source src="https://www.soundhelix.com/examples/mp3/SoundHelix-Song-1.mp3" type="audio/mp3">',
        '</audio>',
        '"""',
        "",
        "def load_logs():",
        "    try:",
        "        with open(LOG_FILE, 'r') as f:",
        "            return json.load(f)",
        "    except (FileNotFoundError, json.JSONDecodeError):",
        "        return []",
        "def save_logs(logs):\n",
        "    with open(LOG_FILE, 'w') as f: json.dump(logs, f, indent=4, default=str)",
        "def log_status_change(consultor, old_status, new_status, duration):",
        "    logs = load_logs()",
        "    log_entry = {",
        "        'consultor': consultor,",
        "        'old_status': old_status if old_status != '' else 'Disponível',",
        "        'new_status': new_status if new_status != '' else 'Disponível',",
        "        'duration_s': duration.total_seconds(),",
        "        'start_time': datetime.now().isoformat(),",
        "        'end_time': datetime.now().isoformat()",
        "    }",
        "    logs.append(log_entry)",
        "    save_logs(logs)",
        "    st.session_state['current_status_starts'][consultor] = datetime.now()",
        "",
        "def format_time_duration(duration):",
        "    total_seconds = int(duration.total_seconds())",
        "    hours = total_seconds // 3600",
        "    minutes = (total_seconds % 3600) // 60",
        "    seconds = total_seconds % 60",
        "    return f'{hours:02}:{minutes:02}:{seconds:02}'",
        "",
        "# --- Inicialização do Session State ---",
        "def init_session_state():",
        "    if 'status_texto' not in st.session_state:",
        "        st.session_state['status_texto'] = {nome: '' for nome in CONSULTORES}",
        "    if 'bastao_queue' not in st.session_state:",
        "        st.session_state['bastao_queue'] = []",
        "    if 'play_sound' not in st.session_state:",
        "        st.session_state['play_sound'] = False",
        "    if 'bastao_start_time' not in st.session_state:",
        "        st.session_state['bastao_start_time'] = None",
        "    if 'current_status_starts' not in st.session_state:",
        "        st.session_state['current_status_starts'] = {nome: datetime.now() for nome in CONSULTORES}",
        "    if 'report_last_run_date' not in st.session_state:",
        "        st.session_state['report_last_run_date'] = datetime.min",
        "    if 'last_rerun_time' not in st.session_state:",
        "        st.session_state['last_rerun_time'] = datetime.now()",
        "    if 'bastao_counts' not in st.session_state:", 
        "        st.session_state['bastao_counts'] = {nome: 0 for nome in CONSULTORES}",
        "    if 'priority_return_queue' not in st.session_state:", 
        "        st.session_state['priority_return_queue'] = []", 
        "",
        "init_session_state()",
        "",
        # LÓGICA DO BASTÃO: Checa se deve assumir o bastão (Round Robin Simples)
        "def check_and_assume_baton(consultor=None):\n",
        "    current_responsavel = st.session_state['bastao_queue'][0] if st.session_state['bastao_queue'] else ''\n",
        "    \n",
        "    # Se já há um titular ATIVO (com status 'Bastão'), não faz nada.\n",
        "    if current_responsavel and st.session_state['status_texto'].get(current_responsavel) == 'Bastão':\n",
        "        return\n",
        "    \n",
        "    # 1. Itera sobre a fila para encontrar o próximo consultor *REALMENTE* disponível\n",
        "    for index, nome in enumerate(st.session_state['bastao_queue']):",
        "        current_status = st.session_state['status_texto'].get(nome, '')\n",
        "        \n",
        "        # Promoção só deve ocorrer se o status for VAZIO ('')\n",
        "        if current_status == '':\n",
        "            novo_responsavel = nome\n",
        "            \n",
        "            # Limpa o status Bastão de quem quer que o estivesse segurando\n",
        "            for c in CONSULTORES:\n",
        "                if st.session_state['status_texto'].get(c) == 'Bastão':\n",
        "                    st.session_state['status_texto'][c] = ''\n",
        "                    \n",
        "            st.session_state['status_texto'][novo_responsavel] = 'Bastão'\n",
        "            st.session_state['bastao_start_time'] = datetime.now()\n",
        "            st.session_state['current_status_starts'][novo_responsavel] = datetime.now()\n",
        "            st.session_state['play_sound'] = True\n",
        "            st.rerun() # Garante a atualização imediata após a promoção\n",
        "            return\n",
        "    \n",
        "    # Se o Bastão ainda estiver com status de Saída, limpamos o Bastão\n",
        "    if current_responsavel and st.session_state['status_texto'].get(current_responsavel) in STATUSES_DE_SAIDA:\n",
        "        st.session_state['status_texto'][current_responsavel] = ''\n",
        "        st.session_state['bastao_start_time'] = None\n",
        "        st.rerun() # Garante que a caixa de Bastão fique limpa\n",
        "\n",
        "# --- Lógica de Fila e Status ---",
        "def update_queue(consultor):\n",
        "    checkbox_key = f'check_{consultor}'\n",
        "    is_checked = st.session_state.get(checkbox_key, False)\n",
        "    old_status = st.session_state['status_texto'].get(consultor, '') or 'Disponível'\n",
        "    \n",
        "    if is_checked and consultor not in st.session_state['bastao_queue']:\n",
        "        duration = datetime.now() - st.session_state['current_status_starts'][consultor]\n",
        "        log_status_change(consultor, old_status, 'Disponível na Fila', duration)\n",
        "        \n",
        "        # Round Robin: Adiciona ao final da fila\n",
        "        st.session_state['bastao_queue'].append(consultor)\n",
        "        st.session_state['status_texto'][consultor] = ''\n",
        "        check_and_assume_baton(consultor)\n",
        "    elif not is_checked and consultor in st.session_state['bastao_queue']:\n",
        "        # Se o checkbox é desmarcado, remove totalmente da fila (Indisponível).\n",
        "        duration = datetime.now() - st.session_state['current_status_starts'][consultor]\n",
        "        log_status_change(consultor, old_status, 'Indisponível', duration)\n",
        "        st.session_state['bastao_queue'].remove(consultor)\n",
        "        st.session_state['status_texto'][consultor] = ''\n",
        "        check_and_assume_baton()\n",
        "    st.rerun() # Rerun no final para garantir a atualização do display.\n",
        "\n",
        "def rotate_bastao():\n",
        "    selected_name = st.session_state.get('consultor_selectbox', 'Selecione um nome')\n",
        "    if selected_name != 'Selecione um nome' and selected_name in st.session_state['status_texto']:\n",
        "        if st.session_state['bastao_queue'] and selected_name == st.session_state['bastao_queue'][0]:\n",
        "            antigo_responsavel = selected_name\n",
        "            old_status = 'Bastão'\n",
        "            st.session_state['status_texto'][antigo_responsavel] = ''\n",
        "            \n",
        "            if selected_name in st.session_state['bastao_queue']:\n",
        "                duration = datetime.now() - st.session_state['current_status_starts'][antigo_responsavel]\n",
        "                log_status_change(antigo_responsavel, old_status, 'Disponível na Fila', duration)\n",
        "                \n",
        "                st.session_state['bastao_counts'][antigo_responsavel] = st.session_state['bastao_counts'].get(antigo_responsavel, 0) + 1\n",
        "                \n",
        "                st.session_state['bastao_queue'].remove(selected_name)\n",
        "                st.session_state['bastao_queue'].append(selected_name)\n",
        "                checkbox_key = f'check_{selected_name}'\n",
        "                st.session_state[checkbox_key] = True\n",
        "                st.session_state['play_sound'] = True\n",
        "                \n",
        "            check_and_assume_baton()\n",
        "            st.rerun()\n",
        "        else:\n",
        "            st.warning('Somente o Responsável Atual pode girar o Bastão.')",
        "\n",
        "def update_status(status_text, change_to_available):\n",
        "    selected_name = st.session_state.get('consultor_selectbox', 'Selecione um nome')\n",
        "    if selected_name != 'Selecione um nome' and selected_name in st.session_state['status_texto']:\n",
        "        old_status = st.session_state['status_texto'].get(selected_name, '') or 'Disponível'\n",
        "        new_status = status_text if status_text != '' else 'Disponível'\n",
        "        duration = datetime.now() - st.session_state['current_status_starts'][selected_name]\n",
        "        log_status_change(selected_name, old_status, new_status, duration)\n",
        "        \n",
        "        st.session_state['status_texto'][selected_name] = status_text\n",
        "        checkbox_key = f'check_{selected_name}'\n",
        "        \n",
        "        if change_to_available is not None:\n",
        "            st.session_state[checkbox_key] = change_to_available\n",
        "        \n",
        "        is_current_holder = selected_name == st.session_state['bastao_queue'][0] if st.session_state['bastao_queue'] else ''\n",
        "        \n",
        "        if is_current_holder and status_text != 'Bastão' and status_text != '':\n",
        "            # 1. Remove o titular da primeira posição\n",
        "            st.session_state['bastao_queue'].remove(selected_name)\n",
        "            \n",
        "            # 2. Reinsere o consultor no final da fila (Round Robin)\n",
        "            st.session_state['bastao_queue'].append(selected_name)\n",
        "            \n",
        "            check_and_assume_baton() # Promove o próximo\n",
        "        \n",
        "        st.rerun()",
        "\n",
        "def auto_rerun_for_timer():\n",
        "    if 'bastao_queue' in st.session_state and st.session_state['bastao_queue']:\n",
        "        time_since_last_run = datetime.now() - st.session_state.get('last_rerun_time', datetime.min)\n",
        "        if time_since_last_run.total_seconds() >= TIMER_RERUN_S:\n",
        "            st.session_state['last_rerun_time'] = datetime.now()\n",
        "            st.rerun()",
        "",
        "# --- INÍCIO DA APLICAÇÃO STREAMLIT ---",
        "# CSS para ocultar o aviso 'no-op' e garantir interface limpa\n",
        "st.markdown(\"""<style>div.stAlert { display: none !important; }</style>\"\"\", unsafe_allow_html=True)",
        
        'st.set_page_config(page_title="Controle Bastão Cesupe", layout="wide")',
        
        "st.title(f'Controle Bastão Cesupe {BASTAO_EMOJI}')",
        'st.markdown("<hr style=\'border: 1px solid #E75480;\'>", unsafe_allow_html=True)',
        'col_principal, col_disponibilidade = st.columns([1.5, 1])',
        
        "# RESPONSÁVEL PELO BASTÃO (LÓGICA DA FILA)",
        "responsavel = st.session_state['bastao_queue'][0] if st.session_state['bastao_queue'] else ''",
        "proximo_responsavel = st.session_state['bastao_queue'][1] if len(st.session_state['bastao_queue']) > 1 else ''",
        "fila_restante = st.session_state['bastao_queue'][2:]",
        
        "with col_principal:",
        '    st.header("Responsável pelo Bastão")',
        
        # CÁLCULO E EXIBIÇÃO DO TEMPORIZADOR (Com GIF)
        "    col_gif, col_time = st.columns([0.25, 0.75])",
        "    col_gif.image('https://media1.giphy.com/media/v1.Y2lkPTc5MGI3NjExYjlqeWg3bXpuZ2ltMXdsNXJ6OW13eWF5aXlqYnc1NGNjamFjczlpOSZlcD12MV9pbnRlcm5hbF9naWZfYnlfaWQmY3Q9Zw/xAFPuHVjmsBmU/giphy.gif', width=50)",
        
        "    bastao_duration = timedelta()",
        "    if responsavel and st.session_state.get('bastao_start_time'):",
        "        start_time = st.session_state['bastao_start_time']",
        "        try: bastao_duration = datetime.now() - start_time",
        "        except: pass",
        "        duration_text = format_time_duration(bastao_duration)",
        "        col_time.markdown(f'#### 🕒 Tempo: **{duration_text}**')",
        "    else:",
        "        col_time.markdown('#### 🕒 Tempo: --:--:--')",
        "",
        "    st.text_input(label='Responsável', value=responsavel, disabled=True, label_visibility='collapsed')",
        '    st.markdown("###")', 
        
        # EXIBIÇÃO DA FILA COMPLETA
        '    st.header("Próximos da Fila")',
        "    if proximo_responsavel:",
        "        st.markdown(f'1º: **{proximo_responsavel}**')",
        "        if fila_restante:",
        "            st.markdown(f'2º em diante: {', '.join(fila_restante)}')",
        "    else:",
        '        st.markdown("*Fila vazia. Marque consultores como Disponíveis.*")',
        '    st.markdown("###")',
        
        '    st.header("**Consultor**")',
        "    st.selectbox(",
        '        "Selecione o Consultor:",',
        "        options=['Selecione um nome'] + CONSULTORES,",
        "        index=0,",
        "        key='consultor_selectbox',",
        "        label_visibility='collapsed'",
        "    )",
        '    st.markdown("#### ")',
        '    st.markdown("**Mudar Status:**")',
        '    col_b1, col_b2, col_b3, col_b4, col_b5 = st.columns(5)',
        
        # Botões
        "    col_b1.button('✏️ Atividade', on_click=update_status, args=('Atividade', False,), use_container_width=True)",
        "    col_b3.button('🍽️ Almoço', on_click=update_status, args=('Almoço', False,), use_container_width=True)",
        "    col_b4.button('🚶 Saída', on_click=update_status, args=('Saída Temporária', False,), use_container_width=True)",
        "    col_b2.button('🎯 Bastão', on_click=rotate_bastao, use_container_width=True)",
        "    col_b5.button('✅ Voltar', on_click=update_status, args=('', True,), use_container_width=True)",
        '    st.markdown("---")',
        
        # Coluna de Disponibilidade
        "with col_disponibilidade:",
        '    st.header("**Disponível**")',
        '    st.subheader("Marque para Disponível | Status de Atividade:")',
        
        # Lógica de cores para os status
        "    STATUS_MAP = {",
        "        'Bastão': ('#E75480', '🏆'),",
        "        'Atividade': ('#ffc107', '✏️'),",
        "        'Almoço': ('#007bff', '🍽️'),",
        "        'Saída Temporária': ('#dc3545', '🚶'),",
        "        '': ('#6c757d', ''),",
        "    }",
        
        "    for nome in CONSULTORES:",
        '        col_status, col_nome, col_check = st.columns([0.2, 1, 0.2])',
        "        checkbox_key = f'check_{nome}'",
        
        "        if checkbox_key not in st.session_state:",
        "            st.session_state[checkbox_key] = False",
        "            ",
        "        is_available = col_check.checkbox(label=' ', key=checkbox_key, on_change=update_queue, args=(nome,))",
        "        current_status_text = st.session_state['status_texto'].get(nome, '')",
        "        ",
        # LÓGICA DE EXIBIÇÃO VISUAL
        "        status_color, status_emoji = STATUS_MAP.get(current_status_text, ('#6c757d', ''))",
        "        display_name = nome",
        "        display_status = ''",
        "        \n",
        "        # Lógica de exibição de Prioridade de Retorno\n",
        "        if current_status_text == 'Bastão':",
        "            display_status = f'<span style=\"color:{status_color};\">**{status_emoji} BASTÃO**</span>'",
        "        elif current_status_text != '' and not is_available:",
        "            display_status = f'<span style=\"color:{status_color};\">{status_emoji} {current_status_text}</span>'",
        "        elif current_status_text == '' and is_available and nome != responsavel:",
        "            display_status = '<span style=\"color:#007bff;\">✅ Disponível na Fila</span>'",
        "        elif not is_available:",
        "            display_status = '<span style=\"color:#dc3545;\">❌ Indisponível</span>'",
        "        ",
        "        col_status.markdown(f'<span style=\"font-size: 1.5em; color:{status_emoji};\">{status_emoji}</span>', unsafe_allow_html=True)",
        "        col_nome.markdown(f'**{display_name}** {display_status}', unsafe_allow_html=True)",
        
        # LÓGICA DE GATILHO DO RELATÓRIO 20H
        "    current_hour = datetime.now().hour",
        "    today = datetime.now().date()",
        "    last_run_date = st.session_state['report_last_run_date'].date()",
        "    if current_hour >= 20 and today > last_run_date:",
        "        pass",
        "",
        "auto_rerun_for_timer()",
        ""
    ]
    
    return "\n".join(app_code_lines)

# 5. Salva o código no arquivo 'app.py'
app_code_final = generate_app_code(CONSULTORES, BASTAO_EMOJI, GOOGLE_CHAT_WEBHOOK_URL)

with open('app.py', 'w') as f:
    f.write(app_code_final)

# 6. Execução do ngrok e Streamlit
print("\nIniciando servidor Streamlit...")

try:
    public_url = ngrok.connect(8501)
    subprocess.Popen(['streamlit', 'run', 'app.py'])

    time.sleep(3)
    print(f"\n✅ **APLICAÇÃO PRONTA!**\n")
    print(f"🔗 **Clique no link para acessar:** {public_url}")
    print("\n⚠️ Mantenha esta célula em execução no Colab para que o link funcione.")

except Exception as e:
    print(f"\n❌ ERRO FATAL na execução. Por favor, REINICIE O AMBIENTE DE EXECUÇÃO:\n{e}")
