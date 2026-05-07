
import webview
from app import app

if __name__ == '__main__':
    window = webview.create_window(
        'SylvieTours',
        app,
        width=1400,
        height=900
    )
    webview.start()
