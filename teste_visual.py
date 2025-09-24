import tkinter as tk
from tkinter import ttk, messagebox
import threading
import multiprocessing
import time
import os
import tempfile
import psutil
import gc
import sv_ttk
import sys

def resource_path(relative_path):
    """ Retorna o caminho absoluto para o recurso, funciona para dev e para PyInstaller """
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

def cpu_stress_worker():
    """Função que executa o cálculo pesado para estressar um núcleo de CPU."""
    while True:
        _ = 12345 * 54321

class StressTestApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Ferramenta de Teste de Estresse v1.0")
        self.root.geometry("450x420")
        self.root.iconbitmap(resource_path('cpu.ico'))
        self.root.resizable(False, False)

        sv_ttk.set_theme("dark")

        # Variáveis de estado
        self.is_running = False
        self.stop_event = None
        self.test_threads = []
        self.cpu_processes = []

        # Variáveis de controle da UI
        self.cpu_var = tk.BooleanVar(value=True)
        self.mem_var = tk.BooleanVar(value=True)
        self.ssd_var = tk.BooleanVar(value=True)

        self.create_widgets()
        self.update_monitor()
        
        self.root.protocol("WM_DELETE_WINDOW", self.on_closing)

    def create_widgets(self):
        # --- Frame de Controles ---
        control_frame = ttk.LabelFrame(self.root, text="Testes a Executar")
        control_frame.pack(padx=10, pady=10, fill="x")

        ttk.Checkbutton(control_frame, text="Estressar CPU", variable=self.cpu_var).pack(anchor="w", padx=10)
        ttk.Checkbutton(control_frame, text="Estressar Memória RAM", variable=self.mem_var).pack(anchor="w", padx=10)
        ttk.Checkbutton(control_frame, text="Estressar SSD/HD", variable=self.ssd_var).pack(anchor="w", padx=10)

        # --- Frame de Configuração de Ciclo ---
        cycle_frame = ttk.LabelFrame(self.root, text="Configuração do Ciclo")
        cycle_frame.pack(padx=10, pady=5, fill="x")
        
        ttk.Label(cycle_frame, text="Tempo de Estresse (segundos):").grid(row=0, column=0, padx=5, pady=5, sticky="w")
        self.stress_duration_entry = ttk.Entry(cycle_frame, width=10)
        self.stress_duration_entry.insert(0, "300")
        self.stress_duration_entry.grid(row=0, column=1, padx=5, pady=5)

        ttk.Label(cycle_frame, text="Tempo de Descanso (segundos):").grid(row=1, column=0, padx=5, pady=5, sticky="w")
        self.cooldown_duration_entry = ttk.Entry(cycle_frame, width=10)
        self.cooldown_duration_entry.insert(0, "60")
        self.cooldown_duration_entry.grid(row=1, column=1, padx=5, pady=5)

        # --- Frame de Monitoramento ---
        monitor_frame = ttk.LabelFrame(self.root, text="Monitoramento em Tempo Real")
        monitor_frame.pack(padx=10, pady=10, fill="x")

        self.cpu_label = ttk.Label(monitor_frame, text="CPU: 0.0%", font=("Helvetica", 10))
        self.cpu_label.pack(anchor="w", padx=10, pady=2)
        self.mem_label = ttk.Label(monitor_frame, text="RAM: 0.0% (0.0GB/0.0GB)", font=("Helvetica", 10))
        self.mem_label.pack(anchor="w", padx=10, pady=2)
        
        # --- Log de Status ---
        self.status_label = ttk.Label(self.root, text="Pronto para iniciar.", relief="sunken", anchor="w")
        self.status_label.pack(side="bottom", fill="x", ipady=2)

        # --- Botões de Ação ---
        action_frame = ttk.Frame(self.root)
        action_frame.pack(pady=10)

        self.start_button = ttk.Button(action_frame, text="Iniciar Teste", command=self.start_test, width=15)
        self.start_button.pack(side="left", padx=5)
        self.stop_button = ttk.Button(action_frame, text="Parar Teste", command=self.stop_test, state="disabled", width=15)
        self.stop_button.pack(side="left", padx=5)

    # O resto do código (lógica dos testes) permanece exatamente o mesmo
    def update_monitor(self):
        cpu_percent = psutil.cpu_percent()
        mem_info = psutil.virtual_memory()
        mem_used_gb = mem_info.used / (1024**3)
        mem_total_gb = mem_info.total / (1024**3)
        
        self.cpu_label.config(text=f"CPU: {cpu_percent:.1f}%")
        self.mem_label.config(text=f"RAM: {mem_info.percent:.1f}% ({mem_used_gb:.2f}GB / {mem_total_gb:.2f}GB)")
        
        self.root.after(1000, self.update_monitor)

    def start_test(self):
        try:
            stress_duration = int(self.stress_duration_entry.get())
            cooldown_duration = int(self.cooldown_duration_entry.get())
        except ValueError:
            messagebox.showerror("Erro", "Por favor, insira valores numéricos para a duração.")
            return

        self.is_running = True
        self.start_button.config(state="disabled")
        self.stop_button.config(state="normal")
        self.status_label.config(text="Teste em andamento...")
        
        self.stop_event = threading.Event()
        
        manager_thread = threading.Thread(target=self.test_manager, args=(stress_duration, cooldown_duration))
        manager_thread.daemon = True
        manager_thread.start()

    def stop_test(self):
        if self.is_running:
            self.status_label.config(text="Parando testes...")
            self.stop_event.set()
            self.is_running = False
            self.start_button.config(state="normal")
            self.stop_button.config(state="disabled")
    
    def on_closing(self):
        if self.is_running:
            if messagebox.askyesno("Sair", "O teste ainda está rodando. Deseja parar e sair?"):
                self.stop_test()
                self.root.destroy()
        else:
            self.root.destroy()
            
    def test_manager(self, stress_d, cooldown_d):
        while not self.stop_event.is_set():
            self.status_label.config(text=f"Ciclo de Estresse: {stress_d} segundos...")
            cycle_stop_event = threading.Event()
            
            if self.cpu_var.get(): self._start_cpu_stress()
            if self.mem_var.get(): self._start_worker(self._memory_worker, cycle_stop_event)
            if self.ssd_var.get(): self._start_worker(self._ssd_worker, cycle_stop_event)
            
            self.stop_event.wait(timeout=stress_d)
            if self.stop_event.is_set(): break
            
            cycle_stop_event.set()
            self._stop_cpu_stress()
            time.sleep(1)
            
            self.status_label.config(text=f"Ciclo de Descanso: {cooldown_d} segundos...")
            gc.collect()
            self.stop_event.wait(timeout=cooldown_d)

        self._stop_cpu_stress()
        self.status_label.config(text="Teste finalizado. Pronto para iniciar.")

    def _start_worker(self, target, stop_event):
        thread = threading.Thread(target=target, args=(stop_event,))
        thread.daemon = True
        thread.start()
        self.test_threads.append(thread)
    
    def _start_cpu_stress(self):
        num_cores = multiprocessing.cpu_count()
        self.cpu_processes = []
        for _ in range(num_cores):
            p = multiprocessing.Process(target=cpu_stress_worker)
            p.start()
            self.cpu_processes.append(p)
            
    def _stop_cpu_stress(self):
        for p in self.cpu_processes:
            p.terminate()
            p.join()
        self.cpu_processes = []
            
    def _memory_worker(self, stop_event):
        memory_hog = []
        try:
            while not stop_event.is_set():
                memory_hog.append(bytearray(10 * 1024 * 1024))
                time.sleep(0.05)
        except MemoryError:
            pass
        
        while not stop_event.is_set():
            time.sleep(0.5)
        del memory_hog

    def _ssd_worker(self, stop_event):
        fd, path = tempfile.mkstemp(suffix=".stress-test")
        os.close(fd)
        try:
            with open(path, "wb") as f:
                while not stop_event.is_set():
                    f.write(os.urandom(1024 * 1024))
        finally:
            if os.path.exists(path):
                os.remove(path)

if __name__ == "__main__":
    multiprocessing.freeze_support()
    root = tk.Tk()
    app = StressTestApp(root)
    root.mainloop()