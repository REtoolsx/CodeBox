from PyQt6.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton, QHBoxLayout, QApplication
from PyQt6.QtGui import QFont, QColor
from PyQt6.Qsci import QsciScintilla, QsciLexerPython, QsciLexerJavaScript, \
    QsciLexerJava, QsciLexerCPP, QsciLexerHTML, QsciLexerCSS, QsciLexerJSON
from app.utils.logger import get_logger

logger = get_logger(__name__)


class CodeViewer(QWidget):
    LEXERS = {
        'python': QsciLexerPython,
        'javascript': QsciLexerJavaScript,
        'typescript': QsciLexerJavaScript,
        'java': QsciLexerJava,
        'cpp': QsciLexerCPP,
        'c_sharp': QsciLexerCPP,
        'go': None,
        'rust': None,
        'html': QsciLexerHTML,
        'css': QsciLexerCSS,
        'json': QsciLexerJSON,
    }

    def __init__(self):
        super().__init__()
        self._init_ui()

    def _init_ui(self):
        layout = QVBoxLayout()

        header_layout = QHBoxLayout()

        self.file_label = QLabel("No code selected")
        self.file_label.setStyleSheet("font-weight: bold;")

        self.copy_btn = QPushButton("Copy Code")
        self.copy_btn.clicked.connect(self._copy_code)
        self.copy_btn.setMaximumWidth(100)

        header_layout.addWidget(self.file_label)
        header_layout.addStretch()
        header_layout.addWidget(self.copy_btn)

        layout.addLayout(header_layout)

        self.editor = QsciScintilla()
        self._configure_editor()

        layout.addWidget(self.editor)

        self.setLayout(layout)

    def _configure_editor(self):
        self.editor.setReadOnly(True)

        font = QFont("Consolas", 10)
        self.editor.setFont(font)

        self.editor.setMarginType(0, QsciScintilla.MarginType.NumberMargin)
        self.editor.setMarginWidth(0, "0000")
        self.editor.setMarginsForegroundColor(QColor("#888888"))
        self.editor.setMarginsBackgroundColor(QColor("#f0f0f0"))

        self.editor.setCaretLineVisible(True)
        self.editor.setCaretLineBackgroundColor(QColor("#f8f8f8"))

        self.editor.setIndentationGuides(True)
        self.editor.setTabWidth(4)

        self.editor.setFolding(QsciScintilla.FoldStyle.BoxedTreeFoldStyle)

        self.editor.setBraceMatching(QsciScintilla.BraceMatch.SloppyBraceMatch)

        self.editor.SendScintilla(QsciScintilla.SCI_SETSCROLLWIDTH, 1)
        self.editor.SendScintilla(QsciScintilla.SCI_SETSCROLLWIDTHTRACKING, True)

    def display_code(self, code: str, language: str = 'text', file_info: str = ''):
        self.file_label.setText(file_info or "Code Preview")

        self.editor.setText(code)

        lexer_class = self.LEXERS.get(language)
        if lexer_class:
            lexer = lexer_class(self.editor)
            lexer.setFont(self.editor.font())
            self.editor.setLexer(lexer)
        else:
            self.editor.setLexer(None)

        self.editor.SendScintilla(QsciScintilla.SCI_GOTOLINE, 0)

    def clear(self):
        self.editor.clear()
        self.file_label.setText("No code selected")

    def _copy_code(self):
        code = self.editor.text()
        if code:
            clipboard = QApplication.clipboard()
            clipboard.setText(code)
