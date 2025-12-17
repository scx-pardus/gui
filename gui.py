#!/usr/bin/env python3
import gi
import subprocess
import os
import threading
import signal

gi.require_version("Gtk", "4.0")
from gi.repository import Gtk, GLib


class SimpleBPFGUI(Gtk.Window):
    def __init__(self):
        super().__init__(title="BPF Scheduler Kontrol")
        self.set_default_size(420, 320)

        # Binary yolu (workspace root)
        self.binary_path = self.find_binary()

        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        vbox.set_margin_top(20)
        vbox.set_margin_bottom(20)
        vbox.set_margin_start(20)
        vbox.set_margin_end(20)

        title = Gtk.Label(label="BPF Scheduler Kontrol Paneli")
        title.set_css_classes(["title-1"])
        vbox.append(title)

        self.status_label = Gtk.Label(label="Durum: Hazır")
        vbox.append(self.status_label)

        if self.binary_path:
            info = Gtk.Label(label=f"Binary: {self.binary_path}")
            vbox.append(info)
        else:
            err = Gtk.Label(label="❌ scx_pardus binary bulunamadı")
            vbox.append(err)

        btn_box = Gtk.Box(spacing=10)

        self.start_btn = Gtk.Button(label="Başlat")
        self.start_btn.set_sensitive(self.binary_path is not None)
        self.start_btn.connect("clicked", self.start_scheduler)

        self.stop_btn = Gtk.Button(label="Durdur")
        self.stop_btn.set_sensitive(False)
        self.stop_btn.connect("clicked", self.stop_scheduler)

        btn_box.append(self.start_btn)
        btn_box.append(self.stop_btn)
        vbox.append(btn_box)

        quit_btn = Gtk.Button(label="Çıkış")
        quit_btn.connect("clicked", lambda _: self.close())
        vbox.append(quit_btn)

        self.log_view = Gtk.TextView(editable=False)
        self.log_buffer = self.log_view.get_buffer()

        scroll = Gtk.ScrolledWindow()
        scroll.set_vexpand(True)
        scroll.set_child(self.log_view)
        vbox.append(scroll)

        self.set_child(vbox)

        self.process = None

    def find_binary(self):
        # GUI repo kökünde çalışır
        path = "./target/release/scx_pardus"
        if os.path.exists(path) and os.access(path, os.X_OK):
            return os.path.abspath(path)
        return None

    def log(self, msg):
        end = self.log_buffer.get_end_iter()
        self.log_buffer.insert(end, msg + "\n")

    def start_scheduler(self, _):
        self.log(">>> Scheduler başlatılıyor...")
        self.status_label.set_label("Durum: Çalışıyor")
        self.start_btn.set_sensitive(False)
        self.stop_btn.set_sensitive(True)

        t = threading.Thread(target=self.run_scheduler, daemon=True)
        t.start()

    def run_scheduler(self):
        try:
            cmd = ["sudo", self.binary_path]

            self.process = subprocess.Popen(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True,
                preexec_fn=os.setsid  # Ctrl+C için process group
            )

            GLib.idle_add(self.log, f"✅ PID {self.process.pid} ile başlatıldı")

            for line in self.process.stdout:
                GLib.idle_add(self.log, line.rstrip())

        except Exception as e:
            GLib.idle_add(self.log, f"❌ Hata: {e}")
            GLib.idle_add(self.reset_buttons)

    def stop_scheduler(self, _):
        if not self.process:
            return

        self.log(">>> Ctrl+C (SIGINT) gönderiliyor...")

        try:
            os.killpg(os.getpgid(self.process.pid), signal.SIGINT)
            self.process.wait(timeout=5)
            self.log("✅ Scheduler durduruldu")
        except Exception as e:
            self.log(f"❌ Durdurma hatası: {e}")

        self.process = None
        self.status_label.set_label("Durum: Durduruldu")
        self.reset_buttons()

    def reset_buttons(self):
        self.start_btn.set_sensitive(True)
        self.stop_btn.set_sensitive(False)


if __name__ == "__main__":
    app = Gtk.Application(application_id="com.scx.pardus.gui")

    def on_activate(app):
        win = SimpleBPFGUI()
        win.set_application(app)
        win.present()

    app.connect("activate", on_activate)
    app.run()
