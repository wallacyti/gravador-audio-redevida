# 🎙️ Gravador - REDEVIDA

Aplicativo de gravação de áudio profissional desenvolvido em Python para a emissora de TV Rede Vida. O programa oferece uma interface intuitiva e um editor de áudio visual para cortes rápidos.

## 📸 Screenshot

## ✨ Funcionalidades Principais

*   **Gravação de Alta Qualidade:** Grava áudio em formatos MP3 ou WAV com configurações personalizáveis.
*   **Interface Profissional:** Interface limpa e com a identidade visual da empresa, construída com `ttkbootstrap`.
*   **Editor de Áudio Visual:**
    *   Visualização da forma de onda (waveform) otimizada com `NumPy`.
    *   Seleção intuitiva de trechos com o mouse.
    *   Pré-visualização do áudio selecionado.
    *   Função para apagar trechos indesejados.
    *   Sistema de "Desfazer" (Undo).
*   **Hotkeys:** Atalhos de teclado para iniciar e parar gravações mesmo com o programa em segundo plano.
*   **Configurações Avançadas:** Permite escolher microfone, pasta de salvamento, formato de áudio e mais.

## 🛠️ Tecnologias Utilizadas

*   **Python 3**
*   **Tkinter / ttkbootstrap:** Para a interface gráfica.
*   **PyAudio:** Para gravação e reprodução de áudio.
*   **NumPy:** Para processamento e renderização otimizada da waveform.
*   **Pillow (PIL):** Para manipulação de logos e ícones.
*   **pynput:** Para o monitoramento global de teclas de atalho.
*   **FFmpeg:** Utilizado como dependência externa para a conversão para MP3.

## 🚀 Como Usar

1.  Certifique-se de ter o Python 3 instalado.
2.  Clone este repositório: `git clone [URL_DO_SEU_REPOSITORIO]`
3.  Instale as dependências: `pip install ttkbootstrap pyaudio numpy pillow pynput`
4.  Certifique-se de que o `ffmpeg.exe` está na mesma pasta do script.
5.  Execute o programa: `python gravador.py`