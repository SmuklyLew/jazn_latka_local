Łatka Jaźń — import surowej pamięci chat_*.html.7z

Paczka zawiera skompresowaną surową pamięć:

  memory/raw_chats/chat_*.html.7z

Nie zawiera rozpakowanego `memory/raw_chats/chat_*.html`, bo ten plik jest bardzo duży.

Wymagana zależność Python do rozpakowania 7z, jeżeli w systemie nie ma programu 7z/7za/7zr:

  py7zr>=0.21.0

Sprawdzenie zależności bez modyfikowania pamięci:

  python tools/bootstrap_dependencies.py

Instalacja brakujących zależności Python:

  python -m pip install -r requirements.txt

albo jawnie przez pomocniczy skrypt:

  python tools/bootstrap_dependencies.py --install

Rozpakowanie i import do SQLite:

  python tools/memory_repair.py --import-chat-html

Wymuszenie ponownego indeksowania po zmianie surowego pliku:

  python tools/memory_repair.py --import-chat-html --force-chat-html

Alternatywnie samo rozpakowanie:

  Get-ChildItem tools -File | Where-Object { $_.Name -match 'chat|7z|import' }
  python tools/import_chat_html_7z.py --force

Po poprawnym rozpakowaniu powinien istnieć:

  memory/raw_chats/chat_*.html

Po poprawnym imporcie `/status` powinien pokazać `legacy_messages` większe od zera oraz `chat_html_import_sha256: jest`.

Od tej poprawki świeży `python main.py` próbuje automatycznie aktywować `chat_*.html.7z`, ale tylko wtedy, gdy ekstraktor jest dostępny i SQLite nie ma jeszcze indeksu `legacy_messages`. Jeżeli brakuje py7zr i systemowego 7z, runtime nie udaje sukcesu — pokaże dokładny następny krok.

Diagnostyka bez zapisu do pamięci:

  python main.py --status-readonly

Można też wskazać inny katalog paczki:

  python main.py --root /ścieżka/do/paczki --status-readonly

Granica prawdy: dopóki `chat_*.html` nie jest rozpakowany i zaindeksowany, runtime widzi tylko warstwowe pamięci i kontrolnie zaimportowane/wyeksportowane dane, a nie pełną surową historię rozmów.
