import tkinter as tk
from tkinter import messagebox, filedialog
import ttkbootstrap as ttk
from ttkbootstrap.constants import *
from PIL import Image, ImageTk
import pyaudio
import wave
import threading
import os
import subprocess
import configparser
import struct
import time
import sys
from pynput import keyboard
import numpy as np

# --- CONFIGURAÇÕES GLOBAIS ---
CONFIG_FILE = 'config.ini'; config = configparser.ConfigParser(); gravando = False
audio_data_em_memoria = None; playback_active = False; is_paused = False
playback_position = 0; seek_request = -1; FORMAT = pyaudio.paInt16
COR_PRINCIPAL = "#004b8d"; COR_ACENTO = "#f6b223"; COR_BOTAO_TEXTO = "#ffffff"; COR_FUNDO_JANELA = "#f0f2f5"
COR_PRINCIPAL_DIM = "#b0c4de" 
COR_CURSOR = "#e74c3c"       
FONTE_PADRAO = ("Lato", 10); FONTE_LABEL = ("Lato", 11); FONTE_TITULO = ("Lato", 12, "bold")
playback_lock = threading.Lock(); p_audio = pyaudio.PyAudio()
hotkey_listener_thread = None
# --- CONSTANTES DO EDITOR ---
WAVEFORM_WIDTH = 700
WAVEFORM_HEIGHT = 150

# --- FUNÇÕES ---
def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

def format_time(seconds):
    if seconds is None: return "00:00"
    minutes = int(seconds // 60); secs = int(seconds % 60)
    return f"{minutes:02d}:{secs:02d}"

def center_window(win, parent):
    win.withdraw(); win.update()
    width = win.winfo_width(); height = win.winfo_height()
    parent_x = parent.winfo_x(); parent_y = parent.winfo_y()
    parent_width = parent.winfo_width(); parent_height = parent.winfo_height()
    x = parent_x + (parent_width // 2) - (width // 2); y = parent_y + (parent_height // 2) - (height // 2)
    win.geometry(f'{width}x{height}+{x}+{y}'); win.deiconify()

def load_settings():
    if not os.path.exists(CONFIG_FILE):
        config['DEFAULT'] = {'save_path': os.path.join(os.path.expanduser("~"), "Desktop"),
                             'mic_index': '0', 'formato': 'MP3', 'taxa': '44100',
                             'canais': 'Mono (1 canal)', 'hotkey_start': 'f9', 'hotkey_stop': 'f10'}
        save_settings_to_file()
    config.read(CONFIG_FILE)
    formato_var.set(config.get('DEFAULT', 'formato', fallback='MP3'))
    taxa_var.set(config.get('DEFAULT', 'taxa', fallback='44100'))
    canais_var.set(config.get('DEFAULT', 'canais', fallback='Mono (1 canal)'))

def save_settings_to_file():
    try:
        with open(CONFIG_FILE, 'w') as configfile: config.write(configfile)
        return True
    except Exception as e: messagebox.showerror("Erro de Configuração", f"Não foi possível salvar as configurações.\n\nErro: {e}"); return False

def list_microphones():
    mic_dict = {}; keywords = ["microphone", "mic", "headset", "webcam", "mapeador", "input"];
    try:
        for i in range(p_audio.get_device_count()):
            dev_info = p_audio.get_device_info_by_index(i); dev_name = dev_info.get('name', '').lower()
            if dev_info.get('maxInputChannels') > 0 and any(keyword in dev_name for keyword in keywords):
                mic_dict[dev_info.get('name')] = dev_info.get('index')
    except Exception as e: print(f"Erro ao listar microfones: {e}"); messagebox.showerror("Erro de Áudio", "Não foi possível acessar os dispositivos de áudio.")
    return mic_dict

def open_settings_window():
    settings_win = ttk.Toplevel(master=janela, title="Configurações"); settings_win.resizable(False, False); settings_win.transient(janela)
    main_settings_frame = ttk.Frame(settings_win, padding=20); main_settings_frame.pack(fill=BOTH, expand=YES); main_settings_frame.columnconfigure(0, weight=1)
    path_frame = ttk.LabelFrame(main_settings_frame, text=" Pasta de Salvamento ", padding=10); path_frame.grid(row=0, column=0, sticky="ew", pady=(0, 15)); path_frame.columnconfigure(0, weight=1)
    save_path_var_local = tk.StringVar(value=config.get('DEFAULT', 'save_path'))
    path_entry = ttk.Entry(path_frame, textvariable=save_path_var_local, font=FONTE_PADRAO); path_entry.grid(row=0, column=0, sticky="ew", padx=(0, 10))
    def browse_path():
        new_path = filedialog.askdirectory(title="Selecione a pasta");
        if new_path: save_path_var_local.set(new_path)
    browse_btn = ttk.Button(path_frame, text="Procurar...", command=browse_path); browse_btn.grid(row=0, column=1)
    mic_frame = ttk.LabelFrame(main_settings_frame, text=" Microfone de Gravação ", padding=10); mic_frame.grid(row=1, column=0, sticky="ew", pady=15); mic_frame.columnconfigure(0, weight=1)
    mics = list_microphones()
    if not mics: settings_win.destroy(); return
    mic_names = list(mics.keys()); mic_var_local = tk.StringVar()
    saved_mic_index = config.getint('DEFAULT', 'mic_index', fallback=0)
    for name, index in mics.items():
        if index == saved_mic_index: mic_var_local.set(name); break
    if not mic_var_local.get() and mic_names: mic_var_local.set(mic_names[0])
    mic_combo = ttk.Combobox(mic_frame, textvariable=mic_var_local, values=mic_names, state="readonly", font=FONTE_PADRAO); mic_combo.grid(row=0, column=0, sticky="ew")
    options_frame = ttk.LabelFrame(main_settings_frame, text=" Configurações Padrão do Áudio ", padding=10); options_frame.grid(row=2, column=0, sticky="ew", pady=15); options_frame.columnconfigure(1, weight=1)
    ttk.Label(options_frame, text="Formato:").grid(row=0, column=0, padx=10, pady=8, sticky="w")
    formato_var_local = tk.StringVar(value=formato_var.get());
    formato_combo = ttk.Combobox(options_frame, textvariable=formato_var_local, values=["WAV", "MP3"], state="readonly", font=FONTE_PADRAO); formato_combo.grid(row=0, column=1, padx=10, pady=8, sticky="ew")
    ttk.Label(options_frame, text="Taxa de Amostragem (Hz):").grid(row=1, column=0, padx=10, pady=8, sticky="w")
    taxa_var_local = tk.StringVar(value=taxa_var.get())
    taxa_combo = ttk.Combobox(options_frame, textvariable=taxa_var_local, values=["44100", "22050", "16000"], state="readonly", font=FONTE_PADRAO); taxa_combo.grid(row=1, column=1, padx=10, pady=8, sticky="ew")
    ttk.Label(options_frame, text="Canais:").grid(row=2, column=0, padx=10, pady=8, sticky="w")
    canais_var_local = tk.StringVar(value=canais_var.get())
    canais_combo = ttk.Combobox(options_frame, textvariable=canais_var_local, values=["Mono (1 canal)", "Estéreo (2 canais)"], state="readonly", font=FONTE_PADRAO); canais_combo.grid(row=2, column=1, padx=10, pady=8, sticky="ew")
    hotkey_frame = ttk.LabelFrame(main_settings_frame, text=" Teclas de Atalho (Hotkeys) ", padding=10); hotkey_frame.grid(row=3, column=0, sticky="ew", pady=15); hotkey_frame.columnconfigure(1, weight=1)
    hotkey_start_var = tk.StringVar(value=config.get('DEFAULT', 'hotkey_start', fallback='f9')); hotkey_stop_var = tk.StringVar(value=config.get('DEFAULT', 'hotkey_stop', fallback='f10'))
    def on_key_press(key, target_var, button, listener):
        key_name = get_key_name(key); target_var.set(key_name); button.config(text=f"Definir ({key_name.upper()})"); listener.stop(); return False
    def set_hotkey(target_var, button):
        button.config(text="Pressione uma tecla..."); listener = keyboard.Listener(on_press=lambda key: on_key_press(key, target_var, button, listener)); listener.start()
    ttk.Label(hotkey_frame, text="Iniciar Gravação:").grid(row=0, column=0, padx=10, pady=8, sticky="w")
    btn_set_start = ttk.Button(hotkey_frame, text=f"Definir ({hotkey_start_var.get().upper()})"); btn_set_start.grid(row=0, column=1, padx=10, pady=8, sticky="ew"); btn_set_start.config(command=lambda: set_hotkey(hotkey_start_var, btn_set_start))
    ttk.Label(hotkey_frame, text="Parar Gravação:").grid(row=1, column=0, padx=10, pady=8, sticky="w")
    btn_set_stop = ttk.Button(hotkey_frame, text=f"Definir ({hotkey_stop_var.get().upper()})"); btn_set_stop.grid(row=1, column=1, padx=10, pady=8, sticky="ew"); btn_set_stop.config(command=lambda: set_hotkey(hotkey_stop_var, btn_set_stop))
    def save_and_close():
        config.set('DEFAULT', 'save_path', save_path_var_local.get()); config.set('DEFAULT', 'mic_index', str(mics.get(mic_var_local.get(), 0)))
        config.set('DEFAULT', 'formato', formato_var_local.get()); config.set('DEFAULT', 'taxa', taxa_var_local.get()); config.set('DEFAULT', 'canais', canais_var_local.get())
        config.set('DEFAULT', 'hotkey_start', hotkey_start_var.get()); config.set('DEFAULT', 'hotkey_stop', hotkey_stop_var.get())
        if save_settings_to_file():
            load_settings(); messagebox.showinfo("Sucesso", "Configurações salvas!", parent=settings_win); settings_win.destroy()
    btn_frame = ttk.Frame(main_settings_frame); btn_frame.grid(row=4, column=0, sticky="se", pady=20)
    save_btn = ttk.Button(btn_frame, text="Salvar e Fechar", command=save_and_close, style="success.TButton"); save_btn.pack(side=LEFT, padx=10)
    cancel_btn = ttk.Button(btn_frame, text="Cancelar", command=settings_win.destroy, style="secondary.TButton"); cancel_btn.pack(side=LEFT, padx=10)
    center_window(settings_win, janela)

current_volume = 0
def gravar_audio():
    global current_volume, audio_data_em_memoria, gravando; frames_de_audio_local = []
    stream = None
    try:
        taxa = int(taxa_var.get()); canais = 1 if 'Mono' in canais_var.get() else 2; mic_index = config.getint('DEFAULT', 'mic_index', fallback=0)
        stream = p_audio.open(format=FORMAT, channels=canais, rate=taxa, input=True, frames_per_buffer=1024, input_device_index=mic_index)
        while gravando:
            data = stream.read(1024, exception_on_overflow=False); frames_de_audio_local.append(data); num_amostras = len(data) // 2
            formato_unpack = f'{num_amostras}h'; amostras = struct.unpack(formato_unpack, data)
            current_volume = max(abs(amostra) for amostra in amostras) if amostras else 0
        current_volume = 0; audio_data_em_memoria = b''.join(frames_de_audio_local)
    except Exception as e:
        janela.after(0, lambda: label_status.config(text=f"ERRO de gravação:\nVerifique o microfone.")); janela.after(0, lambda: mudar_estado_interface('inicial')); current_volume = 0; gravando = False
    finally:
        if stream and stream.is_active(): stream.stop_stream(); stream.close()

def open_editor_window():
    global playback_active, is_paused, audio_data_em_memoria
    if not audio_data_em_memoria: messagebox.showwarning("Atenção", "Nenhum áudio gravado."); return
    if playback_active: messagebox.showinfo("Atenção", "O editor já está aberto."); return

    editor_win = ttk.Toplevel(master=janela, title="Editor de Áudio"); editor_win.resizable(False, False); editor_win.transient(janela)
    selection_start_px = None
    selection_end_px = None
    is_playing_selection = False
    audio_history = []
    playback_head = None
    main_editor_frame = ttk.Frame(editor_win, padding=15); main_editor_frame.pack(fill=BOTH, expand=YES)
    waveform_canvas = tk.Canvas(main_editor_frame, width=WAVEFORM_WIDTH, height=WAVEFORM_HEIGHT, bg="#f0f2f5", highlightthickness=1, highlightbackground=COR_PRINCIPAL)
    waveform_canvas.pack(fill=X, expand=YES, pady=(0, 10))
    progress_frame = ttk.Frame(main_editor_frame); progress_frame.pack(fill=X, expand=YES, pady=5)
    time_label = ttk.Label(progress_frame, text="00:00 / 00:00", font=FONTE_PADRAO); time_label.pack()
    controls_container = ttk.Frame(main_editor_frame); controls_container.pack(fill=X, expand=YES, pady=10)
    playback_controls_frame = ttk.Frame(controls_container); playback_controls_frame.pack(side=LEFT, expand=YES, anchor="w")
    edit_controls_frame = ttk.Frame(controls_container); edit_controls_frame.pack(side=RIGHT, expand=YES, anchor="e")

    def toggle_pause():
        global is_paused
        nonlocal is_playing_selection
        with playback_lock:
            is_paused = not is_paused
            is_playing_selection = False
        if btn_play_pause['text'] != "🔄":
            btn_play_pause.config(text="▶" if is_paused else "⏸")

    btn_play_pause = ttk.Button(playback_controls_frame, text="▶", width=4, command=toggle_pause); btn_play_pause.pack(side=LEFT, padx=5)
    btn_play_selection = ttk.Button(playback_controls_frame, text="▶️ Ouvir Trecho", width=15, state=DISABLED); btn_play_selection.pack(side=LEFT, padx=5)

    def perform_delete():
        global audio_data_em_memoria
        nonlocal selection_start_px, selection_end_px
        if selection_start_px is None or selection_end_px is None: return
        audio_history.append(audio_data_em_memoria); btn_undo.config(state=NORMAL)
        start_px = min(selection_start_px, selection_end_px); end_px = max(selection_start_px, selection_end_px)
        start_byte = int((start_px / WAVEFORM_WIDTH) * len(audio_data_em_memoria)); end_byte = int((end_px / WAVEFORM_WIDTH) * len(audio_data_em_memoria))
        frame_size = (p_audio.get_sample_size(FORMAT) * (1 if 'Mono' in canais_var.get() else 2))
        if start_byte % frame_size != 0: start_byte = (start_byte // frame_size) * frame_size
        if end_byte % frame_size != 0: end_byte = (end_byte // frame_size) * frame_size
        audio_data_em_memoria = audio_data_em_memoria[:start_byte] + audio_data_em_memoria[end_byte:]
        update_editor_ui()

    def perform_undo():
        global audio_data_em_memoria
        if not audio_history: return
        audio_data_em_memoria = audio_history.pop()
        if not audio_history: btn_undo.config(state=DISABLED)
        update_editor_ui()

    btn_delete = ttk.Button(edit_controls_frame, text="🗑️ Apagar Seleção", state=DISABLED, command=perform_delete); btn_delete.pack(side=LEFT, padx=5)
    btn_undo = ttk.Button(edit_controls_frame, text="Desfazer", state=DISABLED, command=perform_undo); btn_undo.pack(side=LEFT, padx=5)
    btn_confirm_edit = ttk.Button(edit_controls_frame, text="✔️ Concluir Edição", style="success.TButton", command=lambda: on_editor_close()); btn_confirm_edit.pack(side=LEFT, padx=5)

    def draw_waveform(canvas, audio_data):
        nonlocal playback_head, selection_start_px, selection_end_px
        canvas.delete("wave")
        width, height = WAVEFORM_WIDTH, WAVEFORM_HEIGHT
        if playback_head: canvas.delete(playback_head)
        canvas.create_line(0, height / 2, width, height / 2, fill="#d9d9d9", tags="wave")
        if not audio_data or len(audio_data) < 2:
            playback_head = canvas.create_line(0, 0, 0, height, fill=COR_CURSOR, width=2)
            return
        try:
            samples = np.frombuffer(audio_data, dtype=np.int16)
            num_channels = 1 if 'Mono' in canais_var.get() else 2
            if num_channels == 2: samples = samples[::2]
            samples_per_pixel = len(samples) // width
            if samples_per_pixel < 1: samples_per_pixel = 1
            num_samples_to_process = width * samples_per_pixel
            usable_samples = samples[:num_samples_to_process]
            blocks = usable_samples.reshape((width, samples_per_pixel))
            min_vals, max_vals = blocks.min(axis=1), blocks.max(axis=1)
            min_normalized = min_vals / 32768.0
            max_normalized = max_vals / 32768.0
            half_height = height / 2
            y0 = half_height - (max_normalized * half_height * 0.95)
            y1 = half_height - (min_normalized * half_height * 0.95)
            start_x, end_x = -1, -1
            if selection_start_px is not None and selection_end_px is not None:
                start_x, end_x = min(selection_start_px, selection_end_px), max(selection_start_px, selection_end_px)
            for x, (val0, val1) in enumerate(zip(y0, y1)):
                color = COR_ACENTO if start_x <= x < end_x else COR_PRINCIPAL_DIM
                canvas.create_line(x, val0, x, val1, fill=color, width=1, tags="wave")
        except Exception as e:
            print(f"Erro ao desenhar waveform com NumPy: {e}")
            canvas.create_line(0, height / 2, width, height / 2, fill="red", tags="wave")
        canvas.tag_lower("wave")
        playback_head = canvas.create_line(0, 0, 0, height, fill=COR_CURSOR, width=2)

    def update_editor_ui():
        nonlocal selection_start_px, selection_end_px
        selection_start_px, selection_end_px = None, None
        draw_waveform(waveform_canvas, audio_data_em_memoria)
        btn_delete.config(state=DISABLED); btn_play_selection.config(state=DISABLED)
        taxa = int(taxa_var.get()); canais = 1 if 'Mono' in canais_var.get() else 2
        bytes_per_sample = p_audio.get_sample_size(FORMAT)
        bytes_per_second = taxa * canais * bytes_per_sample
        total_duration = len(audio_data_em_memoria) / bytes_per_second if bytes_per_second > 0 else 0
        time_label.config(text=f"00:00 / {format_time(total_duration)}")

    def start_selection(event):
        nonlocal selection_start_px, selection_end_px, is_playing_selection
        is_playing_selection = False
        selection_start_px = event.x
        selection_end_px = event.x
        btn_delete.config(state=DISABLED); btn_play_selection.config(state=DISABLED)
        draw_waveform(waveform_canvas, audio_data_em_memoria)

    def drag_selection(event):
        nonlocal selection_end_px
        if selection_start_px is None: return
        selection_end_px = event.x
        draw_waveform(waveform_canvas, audio_data_em_memoria)

    def end_selection(event):
        global seek_request
        nonlocal selection_start_px, selection_end_px
        if selection_start_px is None: return
        selection_end_px = event.x
        if abs(selection_end_px - selection_start_px) > 4:
            btn_delete.config(state=NORMAL); btn_play_selection.config(state=NORMAL)
        else:
            selection_start_px, selection_end_px = None, None
            draw_waveform(waveform_canvas, audio_data_em_memoria)
            percentage = event.x / WAVEFORM_WIDTH
            target_byte = int(len(audio_data_em_memoria) * percentage)
            frame_size = (p_audio.get_sample_size(FORMAT) * (1 if 'Mono' in canais_var.get() else 2))
            if target_byte % frame_size != 0:
                target_byte = (target_byte // frame_size) * frame_size
            with playback_lock: seek_request = target_byte

    def play_selection():
        nonlocal is_playing_selection
        global seek_request, is_paused
        if selection_start_px is None or selection_end_px is None: return
        start_px = min(selection_start_px, selection_end_px)
        start_byte = int((start_px / WAVEFORM_WIDTH) * len(audio_data_em_memoria))
        frame_size = (p_audio.get_sample_size(FORMAT) * (1 if 'Mono' in canais_var.get() else 2))
        if start_byte % frame_size != 0:
            start_byte = (start_byte // frame_size) * frame_size
        with playback_lock:
            is_playing_selection = True
            seek_request = start_byte
            is_paused = False
        if btn_play_pause['text'] != "⏸":
            btn_play_pause.config(text="⏸")

    btn_play_selection.config(command=play_selection)
    waveform_canvas.bind("<ButtonPress-1>", start_selection)
    waveform_canvas.bind("<B1-Motion>", drag_selection)
    waveform_canvas.bind("<ButtonRelease-1>", end_selection)

    def on_editor_close():
        global playback_active
        playback_active = False; editor_win.destroy()
    editor_win.protocol("WM_DELETE_WINDOW", on_editor_close)

    def update_playback_ui():
        if not playback_active or not editor_win.winfo_exists(): return
        current_pos = playback_position
        total_len = len(audio_data_em_memoria) if audio_data_em_memoria else 0
        if total_len > 0 and playback_head:
            head_x = (current_pos / total_len) * WAVEFORM_WIDTH
            waveform_canvas.coords(playback_head, head_x, 0, head_x, WAVEFORM_HEIGHT)
        taxa = int(taxa_var.get()); canais = 1 if 'Mono' in canais_var.get() else 2
        bytes_per_sample = p_audio.get_sample_size(FORMAT)
        bytes_per_second = taxa * canais * bytes_per_sample
        current_seconds = current_pos / bytes_per_second if bytes_per_second > 0 else 0
        total_duration = total_len / bytes_per_second if bytes_per_second > 0 else 0
        time_label.config(text=f"{format_time(current_seconds)} / {format_time(total_duration)}")
        editor_win.after(50, update_playback_ui)

    # ========================================================================
    # FUNÇÃO CORRIGIDA PARA O BUG DO "SEEK"
    # ========================================================================
    def playback_thread_editor_logic():
        nonlocal is_playing_selection, selection_start_px, selection_end_px
        global playback_active, is_paused, playback_position, seek_request
        playback_active = True; is_paused = True; playback_position = 0; seek_request = -1
        stream = None
        editor_win.after(0, lambda: btn_play_pause.config(text="▶"))
        try:
            taxa = int(taxa_var.get()); canais = 1 if 'Mono' in canais_var.get() else 2
            stream = p_audio.open(format=FORMAT, channels=canais, rate=taxa, output=True)
            
            while playback_active:
                # 1. VERIFICA PRIMEIRO O PEDIDO DE PULAR (SEEK)
                with playback_lock:
                    if seek_request != -1:
                        playback_position = seek_request
                        seek_request = -1
                
                # 2. VERIFICA SE ESTÁ PAUSADO
                if is_paused:
                    time.sleep(0.05)
                    continue # Volta ao topo do loop para poder checar um novo seek

                # 3. LÓGICA DE FIM DE ÁUDIO
                end_byte = len(audio_data_em_memoria)
                if is_playing_selection and selection_end_px is not None and selection_start_px is not None:
                    end_px = max(selection_start_px, selection_end_px)
                    end_byte = int((end_px / WAVEFORM_WIDTH) * len(audio_data_em_memoria))

                if playback_position >= end_byte:
                    with playback_lock:
                        is_paused = True
                        if is_playing_selection:
                            is_playing_selection = False
                            start_px = min(selection_start_px, selection_end_px)
                            playback_position = int((start_px / WAVEFORM_WIDTH) * len(audio_data_em_memoria))
                            editor_win.after(0, lambda: btn_play_pause.config(text="▶"))
                        else:
                            playback_position = 0
                            editor_win.after(0, lambda: btn_play_pause.config(text="🔄"))
                    continue # Volta ao topo

                # 4. TOCA O ÁUDIO
                chunk_size = 1024
                data_to_play = audio_data_em_memoria[playback_position : playback_position + chunk_size]
                if not data_to_play:
                    playback_position = end_byte
                    continue
                stream.write(data_to_play)
                playback_position += len(data_to_play)

        except Exception as e:
            if playback_active and editor_win.winfo_exists(): messagebox.showerror("Erro de Reprodução", f"Erro: {e}", parent=editor_win)
        finally:
            if stream and stream.is_active(): stream.stop_stream(); stream.close()
            playback_active = False

    threading.Thread(target=playback_thread_editor_logic, daemon=True).start()
    update_playback_ui()
    center_window(editor_win, janela)
    editor_win.after(100, lambda: update_editor_ui())

def descartar_gravacao():
    global audio_data_em_memoria; audio_data_em_memoria = None
    entry_nome.delete(0, tk.END); mudar_estado_interface('inicial')

def salvar_gravacao():
    if not audio_data_em_memoria: return
    if not entry_nome.get().strip():
        messagebox.showwarning("Atenção", "Por favor, digite um nome para o arquivo."); return
    nome_arquivo = entry_nome.get().strip()
    def save_thread():
        label_status.config(text=f"Salvando, por favor aguarde..."); janela.update_idletasks()
        try:
            caminho_destino = config.get('DEFAULT', 'save_path'); formato = formato_var.get(); taxa = int(taxa_var.get()); canais = 1 if 'Mono' in canais_var.get() else 2
            os.makedirs(caminho_destino, exist_ok=True)
            caminho_temp_wav = os.path.join(caminho_destino, f"temp_{nome_arquivo}.wav")
            with wave.open(caminho_temp_wav, 'wb') as wf:
                wf.setnchannels(canais); wf.setsampwidth(p_audio.get_sample_size(FORMAT)); wf.setframerate(taxa); wf.writeframes(audio_data_em_memoria)
            if formato == "WAV":
                caminho_final = os.path.join(caminho_destino, f"{nome_arquivo}.wav"); os.rename(caminho_temp_wav, caminho_final)
            elif formato == "MP3":
                ffmpeg_path = resource_path("assets/ffmpeg.exe")
                if not os.path.exists(ffmpeg_path):
                    label_status.config(text=f"ERRO: ffmpeg.exe não encontrado."); os.remove(caminho_temp_wav); return
                caminho_final = os.path.join(caminho_destino, f"{nome_arquivo}.mp3")
                command = [ffmpeg_path, '-i', caminho_temp_wav, '-y', '-b:a', '192k', caminho_final]
                startupinfo = subprocess.STARTUPINFO(); startupinfo.dwFlags |= subprocess.STARTF_USESHOWWINDOW
                subprocess.run(command, check=True, startupinfo=startupinfo, creationflags=subprocess.CREATE_NO_WINDOW)
                os.remove(caminho_temp_wav)
            label_status.config(text=f"Sucesso! Áudio salvo em:\n{caminho_final}"); descartar_gravacao()
        except Exception as e:
            label_status.config(text=f"ERRO durante o salvamento:\n{e}")
            if 'caminho_temp_wav' in locals() and os.path.exists(caminho_temp_wav): os.remove(caminho_temp_wav)
    threading.Thread(target=save_thread, daemon=True).start()

def iniciar_gravacao_ui():
    global gravando
    if gravando: return
    if not entry_nome.get().strip():
        messagebox.showwarning("Nome do Arquivo Inválido", "Por favor, digite um nome para o arquivo antes de iniciar a gravação."); return
    gravando = True; mudar_estado_interface('gravando')
    threading.Thread(target=gravar_audio, daemon=True).start()

def parar_gravacao_ui():
    global gravando
    if not gravando: return
    gravando = False; mudar_estado_interface('confirmacao')

def mudar_estado_interface(estado):
    if estado == 'inicial':
        label_status.config(text="Pronto para gravar.")
        controls_frame.pack(pady=20); confirmation_frame.pack_forget()
        btn_iniciar.config(state=NORMAL); btn_parar.config(state=DISABLED); btn_settings.config(state=NORMAL)
    elif estado == 'gravando':
        label_status.config(text="Gravando... Fale no microfone.")
        btn_iniciar.config(state=DISABLED); btn_parar.config(state=NORMAL); btn_settings.config(state=DISABLED)
        update_meter()
    elif estado == 'confirmacao':
        label_status.config(text="Gravação finalizada. O que deseja fazer?")
        controls_frame.pack_forget(); confirmation_frame.pack(pady=20)

def update_meter():
    if gravando:
        meter_level = (current_volume / 32767) * 100
        volume_bar['value'] = meter_level
        janela.after(50, update_meter)
    else:
        volume_bar['value'] = 0

def on_app_close():
    global gravando
    gravando = False;
    if p_audio: p_audio.terminate()
    janela.destroy()

def get_key_name(key):
    try: return key.char
    except AttributeError: return key.name

def start_hotkey_listener():
    def on_press_hotkey(key):
        key_name = get_key_name(key); hotkey_start = config.get('DEFAULT', 'hotkey_start', fallback='f9'); hotkey_stop = config.get('DEFAULT', 'hotkey_stop', fallback='f10')
        if key_name == hotkey_start: janela.after(0, iniciar_gravacao_ui)
        elif key_name == hotkey_stop: janela.after(0, parar_gravacao_ui)
    listener = keyboard.Listener(on_press=on_press_hotkey); listener.start(); return listener

janela = ttk.Window(themename="litera"); janela.title("Gravador OFF TV - REDEVIDA"); janela.geometry("550x580"); janela.resizable(False, False); janela.protocol("WM_DELETE_WINDOW", on_app_close)
try:
    janela.iconbitmap(resource_path("assets/mic_icon.ico"))
except tk.TclError: print("Aviso: Arquivo 'assets/mic_icon.ico' não encontrado.")
style = ttk.Style(); style.configure('.', background=COR_FUNDO_JANELA, font=FONTE_PADRAO); style.configure('TLabel', foreground=COR_PRINCIPAL, font=FONTE_LABEL)
style.configure('TLabelframe', bordercolor=COR_PRINCIPAL); style.configure('TLabelframe.Label', foreground=COR_PRINCIPAL, font=FONTE_TITULO)
style.configure('success.TButton', background=COR_PRINCIPAL, font=FONTE_TITULO, borderwidth=0); style.map('success.TButton', background=[('active', '#003a6e')], focuscolor=[('!active', COR_PRINCIPAL)])
style.configure('danger.TButton', background='#dc3545', font=FONTE_TITULO, borderwidth=0); style.map('danger.TButton', background=[('active', '#b02a37')], focuscolor=[('!active', '#dc3545')])
style.configure('info.TButton', background=COR_ACENTO, font=FONTE_TITULO, borderwidth=0); style.map('info.TButton', background=[('active', '#c58e1c')], focuscolor=[('!active', COR_ACENTO)])
style.configure('secondary.TButton', borderwidth=0); style.map('secondary.TButton', focuscolor=[('!active', '#cccccc')])

formato_var = tk.StringVar(); taxa_var = tk.StringVar(); canais_var = tk.StringVar()
load_settings()

main_frame = ttk.Frame(janela, padding=(30, 25)); main_frame.pack(fill=BOTH, expand=YES)
header_frame = ttk.Frame(main_frame); header_frame.pack(fill=X, pady=(0, 25))
try:
    LOGO_TARGET_HEIGHT = 52; img_pil = Image.open(resource_path("assets/logo_redevida.png")); aspect_ratio = img_pil.width / img_pil.height
    new_width = int(LOGO_TARGET_HEIGHT * aspect_ratio); janela.logo_image_pil = img_pil.resize((new_width, LOGO_TARGET_HEIGHT), Image.LANCZOS)
    janela.logo_image = ImageTk.PhotoImage(janela.logo_image_pil); ttk.Label(header_frame, image=janela.logo_image).pack(side=LEFT)
except Exception as e:
    print(f"Erro ao carregar logo: {e}"); ttk.Label(header_frame, text="Gravador OFF TV", font=("Lato", 18, "bold"), foreground=COR_PRINCIPAL).pack(side=LEFT)
try:
    janela.settings_icon_pil = Image.open(resource_path("assets/settings_icon.png")).resize((32, 32), Image.LANCZOS); janela.settings_icon = ImageTk.PhotoImage(janela.settings_icon_pil)
    btn_settings = ttk.Button(header_frame, image=janela.settings_icon, command=open_settings_window, style="light.TButton"); btn_settings.pack(side=RIGHT, anchor="ne")
except Exception as e:
    print(f"Erro ao carregar ícone de config: {e}"); btn_settings = ttk.Button(header_frame, text="⚙️", command=open_settings_window, style="light.TButton"); btn_settings.pack(side=RIGHT, anchor="ne")

input_frame = ttk.LabelFrame(main_frame, text=" NOME DO ARQUIVO "); input_frame.pack(fill=X, pady=12)
entry_nome = ttk.Entry(input_frame, font=FONTE_LABEL); entry_nome.pack(padx=15, pady=15, fill=X)
meter_frame = ttk.LabelFrame(main_frame, text=" NÍVEL DO MICROFONE "); meter_frame.pack(fill=X, pady=12)
volume_bar = ttk.Progressbar(meter_frame, maximum=100, style="info.Horizontal.TProgressbar"); volume_bar.pack(padx=15, pady=15, fill=X)

controls_frame = ttk.Frame(main_frame); controls_frame.pack(pady=30)
btn_iniciar = ttk.Button(controls_frame, text="Iniciar Gravação", command=iniciar_gravacao_ui, style="success.TButton", width=15, padding=12); btn_iniciar.pack(side=LEFT, padx=10)
btn_parar = ttk.Button(controls_frame, text="Parar Gravação", command=parar_gravacao_ui, state=DISABLED, style="danger.TButton", width=15, padding=12); btn_parar.pack(side=LEFT, padx=10)

confirmation_frame = ttk.Frame(main_frame)
btn_edit = ttk.Button(confirmation_frame, text="▶️ Ouvir / Editar", command=open_editor_window, style="info.TButton", width=12, padding=12); btn_edit.pack(side=LEFT, padx=5)
btn_save = ttk.Button(confirmation_frame, text="✔️ Salvar", command=salvar_gravacao, style="success.TButton", width=10, padding=12); btn_save.pack(side=LEFT, padx=5)
btn_discard = ttk.Button(confirmation_frame, text="❌ Descartar", command=descartar_gravacao, style="danger.TButton", width=10, padding=12); btn_discard.pack(side=LEFT, padx=5)

status_frame = ttk.LabelFrame(main_frame, text=" STATUS "); status_frame.pack(fill=X, pady=12)
label_status = ttk.Label(status_frame, text="Pronto para gravar.", justify=LEFT, font=FONTE_PADRAO); label_status.pack(padx=15, pady=15, fill=X)

mudar_estado_interface('inicial')
hotkey_listener_thread = start_hotkey_listener()
janela.mainloop()

