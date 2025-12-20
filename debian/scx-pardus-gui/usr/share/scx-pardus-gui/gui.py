#! /usr/bin/python3
import gi
import subprocess
import threading

gi.require_version("Gtk", "4.0")
gi.require_version("Gdk", "4.0")
from gi.repository import Gtk, GLib, Gdk


APP_ID = "com.scx.pardus.gui"
SERVICE = "scx-pardus.service"

CTL_PATH = "/usr/libexec/scx-pardus-ctl"  # root helper (pkexec bunun üzerinden çalışacak)


class SimpleBPFGUI(Gtk.Window):
    def __init__(self):
        super().__init__(title="SCX-Pardus Zamanlayıcısı")
        self.set_default_size(520, 360)

        self.log_proc = None

        self.load_css()

        vbox = Gtk.Box(orientation=Gtk.Orientation.VERTICAL, spacing=10)
        vbox.set_margin_top(16)
        vbox.set_margin_bottom(16)
        vbox.set_margin_start(16)
        vbox.set_margin_end(16)

        title = Gtk.Label(label="SCX-Pardus Zamanlayıcısı Kontrol Paneli")
        title.set_css_classes(["title"])
        vbox.append(title)

        self.status_label = Gtk.Label(label="Durum: Bilinmiyor")
        vbox.append(self.status_label)

        btn_box = Gtk.Box(spacing=10)

        self.start_btn = Gtk.Button(label="Başlat")
        self.start_btn.connect("clicked", self.start_scheduler)

        self.stop_btn = Gtk.Button(label="Durdur")
        self.stop_btn.set_sensitive(False)
        self.stop_btn.connect("clicked", self.stop_scheduler)

        self.refresh_btn = Gtk.Button(label="Durum Yenile")
        self.refresh_btn.connect("clicked", self.refresh_status)

        btn_box.append(self.start_btn)
        btn_box.append(self.stop_btn)
        btn_box.append(self.refresh_btn)
        vbox.append(btn_box)

        quit_btn = Gtk.Button(label="Çıkış")
        quit_btn.connect("clicked", lambda _: self.close())
        vbox.append(quit_btn)

        self.log_view = Gtk.TextView(editable=False, monospace=True)
        self.log_buffer = self.log_view.get_buffer()

        scroll = Gtk.ScrolledWindow()
        scroll.set_vexpand(True)
        scroll.set_child(self.log_view)
        vbox.append(scroll)

        self.set_child(vbox)

        # İlk açılışta durum çek
        GLib.idle_add(self.refresh_status)

    def load_css(self):
        provider = Gtk.CssProvider()
        css_path = "/usr/share/scx-pardus-gui/style.css"
        try:
            provider.load_from_path(css_path)
            display = Gdk.Display.get_default()
            if display:
                Gtk.StyleContext.add_provider_for_display(
                    display,
                    provider,
                    Gtk.STYLE_PROVIDER_PRIORITY_APPLICATION
                )
        except Exception:
            # CSS yüklenemezse uygulama yine de çalışsın
            pass

    def log(self, msg: str):
        end = self.log_buffer.get_end_iter()
        self.log_buffer.insert(end, msg + "\n")
        # otomatik aşağı kaydır
        mark = self.log_buffer.create_mark(None, self.log_buffer.get_end_iter(), False)
        self.log_view.scroll_mark_onscreen(mark)

    def run_cmd(self, cmd, log_prefix=""):
        """Komut çalıştırır; stdout+stderr'i tek string döndürür."""
        try:
            p = subprocess.run(cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True, check=False)
            out = (p.stdout or "").strip()
            if out:
                self.log(f"{log_prefix}{out}")
            return p.returncode
        except Exception as e:
            self.log(f"❌ Komut hatası: {e}")
            return 1

    def refresh_status(self, *_):
        # systemctl is-active normal kullanıcıda genelde okunabilir
        rc = subprocess.call(["systemctl", "is-active", "--quiet", SERVICE])
        if rc == 0:
            self.status_label.set_label("Durum: Çalışıyor")
            self.start_btn.set_sensitive(False)
            self.stop_btn.set_sensitive(True)
        else:
            self.status_label.set_label("Durum: Durduruldu")
            self.start_btn.set_sensitive(True)
            self.stop_btn.set_sensitive(False)

    def start_scheduler(self, *_):
        self.log(">>> Servis başlatılıyor (pkexec)...")
        self.start_btn.set_sensitive(False)

        # root helper üzerinden systemd start
        rc = self.run_cmd(["pkexec", CTL_PATH, "start"])
        if rc == 0:
            self.log("✅ Başlatma komutu gönderildi.")
            self.status_label.set_label("Durum: Çalışıyor")
            self.stop_btn.set_sensitive(True)
            self.start_log_tail()
        else:
            self.log("❌ Başlatma başarısız.")
            self.start_btn.set_sensitive(True)

        self.refresh_status()

    def stop_scheduler(self, *_):
        self.log(">>> Servis durduruluyor (pkexec)...")
        self.stop_btn.set_sensitive(False)

        self.stop_log_tail()

        rc = self.run_cmd(["pkexec", CTL_PATH, "stop"])
        if rc == 0:
            self.log("✅ Durdurma komutu gönderildi.")
        else:
            self.log("❌ Durdurma başarısız.")

        self.refresh_status()

    def start_log_tail(self):
        if self.log_proc and self.log_proc.poll() is None:
            return

        self.log(">>> Loglar (journalctl) izleniyor...")
        try:
            self.log_proc = subprocess.Popen(
                ["pkexec", CTL_PATH, "logs"],
                stdout=subprocess.PIPE,
                stderr=subprocess.STDOUT,
                text=True
            )
        except Exception as e:
            self.log(f"❌ Log başlatılamadı: {e}")
            self.log_proc = None
            return

        t = threading.Thread(target=self._read_log_stream, daemon=True)
        t.start()

    def _read_log_stream(self):
        try:
            for line in self.log_proc.stdout:
                GLib.idle_add(self.log, line.rstrip())
        except Exception as e:
            GLib.idle_add(self.log, f"❌ Log okuma hatası: {e}")

    def stop_log_tail(self):
        if not self.log_proc:
            return
        try:
            self.log(">>> Log izleme kapatılıyor...")
            self.log_proc.terminate()
            self.log_proc.wait(timeout=2)
        except Exception:
            pass
        finally:
            self.log_proc = None


if __name__ == "__main__":
    app = Gtk.Application(application_id=APP_ID)

    def on_activate(app):
        win = SimpleBPFGUI()
        win.set_application(app)
        win.present()

    app.connect("activate", on_activate)
    app.run()

