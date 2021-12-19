1. WYMAGANIA:

    1.1. Instalacja Flask'a:


2. DO WYKONANIA WYKORZYSTANO:

    Słownik SJP.PL - wersja do gier słownych

    Słownik udostępniany na licencjach GPL 2 oraz
    Creative Commons Attribution 4.0 International

    https://sjp.pl


3. DZIAŁANIE PROGRAMU:
    
    Aplikacja w oparciu o komunikację klient-serwer umożliwia rozgrywkę multiplayer w grę słowną. Zasady rozgrywki opisane są na stronie internetowej, którą apkikacja obsługuje na osobnym wątku. W sumie w wykorzystaniu są trzy wątki (strona internetowa + obsługa kolejki + konsola administratora) + po jednym na każdego klienta. Dane o użytkownikach oraz o historii rozgrywek przechowywane są w bazach danych (działania na bibliotece sqlite3). Opis baz danych znajduje się w pliku /databases/tables_cheatsheet.txt.

   - rejestracja, logowanie i kolejkowanie:

![img1]()

   - rozgrywka:

![img2]()

   - updatowanie wyników na stronie:

![img3]()

![img4]()

   - ponowne logowanie użytkowników:

![img5]()

   - zakańczanie gry po wyjściu osób zgadujących:
   
![img6]()


4. URUCHAMIANIE:

    Aplikacja składa się z częsći głównej - kodu serwera, oraz przykładowego klienta do udziału w rozgrywkach.
    
    -Serwer usuchowmić należy poleceniem: python3 server.py
    -Klienta uruchomić należy poleceniem: python3 client.py <nazwa użytkownika> <hasło>
    
    Wszelkie bazy danych i logi tworzone są automatycznie. Ich usunięcie nie wpłynie na działanie programu.
    Do rozpoczęcia lokalnego testowania zaleca się usunięcie zawartości katalogów /logs oraz /databases (ew. za wyjątkiem tables_cheatsheet.txt).
    
    Aby wyświetlić pomoc panelu administratora, po uruchomieniu pliku server.py należy wpisać h.
   
5. STRUKTURA PROJEKTU:
    - databases:        (zbiór baz danych i cheatsheet w formie tekstowej)
        - users
        - game_history
        - tables_cheatsheet.txt
    - logs:             (logi z gier, kolejkowania i aktywności graczy)
        - Game_<id>.txt
        - <username>.txt
        - Queue.txt
    - static:           (dane statyczne)
        - resources:    (dane wykorzystane do projektu - słownik SJP)
            - slowa.txt
        - stylesheets:  (pliki .css)
            - base.css
            - tables.css
    - templates:        (pliki .html)
        - base.html
        - history.html
        - index.html
        - ranking.html
    (pozostałe - m.in. pliki .py oraz README.md)
    - client.py
    - server.py
    - config.py         (do szybkiej zmiany ustawień)
    - tables.py         (do obsługi baz danych)
    - website.py        (do obsługi strony internetowej)
    - word_game.py      (do obsługi użytkownika i wydarzeń w grze)
    - README.md
    - inne

6. UWAGI:

    Aplikacja napisana pod narzucony konspekt. Zmieniona wersja pojawi się w przyszłości w osobnym repozytorium.