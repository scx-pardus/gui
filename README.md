# scx-pardus-gui

GTK4 tabanlı bir kontrol arayüzüdür. Pardus üzerinde çalışan **scx_pardus (sched_ext / eBPF scheduler)** bileşenini hızlıca **başlatmak/durdurmak** ve log çıktısını izlemek için tasarlanmıştır.

## Özellikler
- Başlat / Durdur butonları ile scheduler kontrolü
- Stdout loglarını arayüzde canlı görüntüleme
- Binary bulunamazsa kullanıcıyı uyarma
- Pardus uyumlu Debian paketleme (debian/)

## Gereksinimler
- Python 3
- GTK4 (gir1.2-gtk-4.0) ve python3-gi
- root yetkisi gerektiren işlemler için pkexec/polkit altyapısı (Pardus’ta policykit-1 yerine pkexec/polkitd kullanılabilir)

## Kurulum (Release üzerinden .deb)
1) GitHub Releases sayfasından en güncel `.deb` dosyasını indirin.
2) Kurun:

```bash
sudo dpkg -i scx-pardus-gui_0.2.0_all.deb
sudo apt -f install
