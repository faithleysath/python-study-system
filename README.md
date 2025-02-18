data/codes.txt

pyinstaller --onefile --add-data "static:static" --add-data "templates:templates" --icon=logo.ico --noconsole --name my_app --version-file=version_info.rc main.py
