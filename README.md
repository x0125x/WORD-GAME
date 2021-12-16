1. WYMAGANIA:

    1.1. Instalacja Flask'a:


2. DO WYKONANIA WYKORZYSTANO:

    Słownik SJP.PL - wersja do gier słownych

    Słownik udostępniany na licencjach GPL 2 oraz
    Creative Commons Attribution 4.0 International

    https://sjp.pl


3. DZIAŁANIE PROGRAMU:
    
    Aplikacja w oparciu o komunikację klient-serwer umożliwia rozgrywkę multiplayer w grę słowną. Zasady rozgrywki opisane są na stronie internetowej, którą apkikacja obsługuje na osobnym wątku. W sumie w wykorzystaniu są dwa wątki (strona internetowa + obsługa kolejki) + po jednym na każdego klienta. Dane o użytkownikach oraz o historii rozgrywek przechowywane są w bazach danych (działania na bibliotece sqlite3). Opis baz danych znajduje się w pliku /databases/tables_cheatsheet.txt.

   - rejestracja i kolejkowanie:

![img](https://user-images.githubusercontent.com/68823168/146024798-333109b0-d0dd-43dd-82c5-e0d46bdedeb1.png)

   - rozgrywka, usuwanie z gry podczas nieobecności, zakańczanie gry po wyjściu osób zgadujących:

![img](https://user-images.githubusercontent.com/68823168/146025306-9df01ae9-95d9-4360-86c9-8f755d2a3321.png)

   - updatowanie wyników na stronie:

![img](https://user-images.githubusercontent.com/68823168/146025504-408d9b23-4db0-4289-8340-0b34637c856b.png)

![img](https://user-images.githubusercontent.com/68823168/146025581-990944a7-8640-4728-be03-c3bb183ead84.png)

   - ponowne logowanie użytkowników:

![img](https://user-images.githubusercontent.com/68823168/146026275-1122aedb-2f50-49a5-9564-dfdd891e761a.png)


4. URUCHAMIANIE:

    Aplikacja składa się z częsći głównej - kodu do działania serwera, oraz przykładowego klienta do udziału w rozgrywkach.
    
    -Serwer usuchowmić należy poleceniem: python3 server.py
    -Klienta uruchomić należy poleceniem: python3 client.py
    
    Pozostałe pliki z rozszerzeniem .py:
    - tables.py : do obsługi baz danych
    - website.py : do obsługi strony internetowej
    - word_game.py : do obsługi graczy (klasa Player) i rozgrywek (klasa Game)
   
   
5. UWAGI:

    Aplikacja jest w wersji podstawowej, co oznacza, że wciąż może być rozwijana. Przykładowo, zaimplementować można funkcję konwertującą numer id użytkownika na jego nazwę (do wykorzystania w wyświetlaniu historii rozgrywek - tam użytkownicy zapisywani są po numerach id na wypadek implementacji możliwośći edycji profili użytkowników). Można wprowadzić także zasady dotyczące wyboru haseł, czy rozwinąć stronę internetową.
