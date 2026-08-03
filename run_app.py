import sys
import os

# Nếu chạy dưới dạng file exe được đóng gói bởi PyInstaller
if getattr(sys, 'frozen', False):
    application_path = sys._MEIPASS
    sys.path.insert(0, application_path)
else:
    application_path = os.path.dirname(os.path.abspath(__file__))
    sys.path.insert(0, application_path)

from atm.main import main

if __name__ == '__main__':
    main()
