import re
import tkinter as tk
from thonny import get_workbench


class Plugin:
    def __init__(self, workbench):
        self.workbench = workbench
        self.indent_guides = []
        self.lines = []

        place_guide_events = ['CursorMove', 'Modified', 'TextChange', 'VerticalScroll', 'FocusIn']
        for event in place_guide_events:
            self.workbench.bind_class(
                'CodeViewText', f'<<{event}>>', self.place_indent_guide, True)

        update_lines_events = ['Modified', 'TextChange']
        for event in update_lines_events:
            self.workbench.bind_class(
                'CodeViewText', f'<<{event}>>', self.update_lines, True)

        self.workbench.bind_class('CodeViewText', '<<FocusOut>>', self.remove_indent_guides, True)

        self.update_lines()

    def get_text_widget(self):
        if not hasattr(self.workbench, '_editor_notebook'):
            return

        nb = self.workbench.get_editor_notebook()
        editor = nb.get_current_child()

        if editor is None:
            return

        code_view = editor.get_code_view()
        return code_view.text

    def update_lines(self, event=None):
        self.lines = []
        text = self.get_text_widget()
        if text is not None:
            self.lines = text.get('1.0', 'end').splitlines()

    def get_syntax_theme(self, name=None):
        name = name or self.workbench.get_option('view.syntax_theme')
        try:
            parent, settings = self.workbench._syntax_themes[name]
        except KeyError:
            self.workbench.report_exception("Can't find theme '%s'" % name)
            return {}

        if callable(settings):
            settings = settings()

        if parent is None:
            return settings
        else:
            result = self.get_syntax_theme(parent)
            for key in settings:
                if key in result:
                    result[key].update(settings[key])
                else:
                    result[key] = settings[key]
            return result

    def find_block_line(self, lineno, direction):
        """
        Find the start or end of the block for the given line.

        direction: -1 for the start, 1 for the end
        """
        text = self.get_text_widget()
        if text is None:
            return

        line_indent = len(re.match(r'^(\s*)', self.lines[lineno - 1]).group(1))
        last_indent = line_indent
        last_matching_line = lineno
        while last_indent >= line_indent and lineno > 0 and lineno <= len(self.lines) - 2:
            lineno += direction
            line_text = self.lines[lineno - 1]
            if re.match(r'^\s*$', line_text):
                # Skip blank lines
                continue
            last_indent = len(re.match(r'^(\s*)', line_text).group(1))
            if direction == -1 or last_indent >= line_indent:
                last_matching_line = lineno

        if direction == -1:
            return last_matching_line
        else:
            return last_matching_line - 1
    def place_indent_guide(self, event=None):
        import tkinter.font as tkfont

        # Get the font used in the editor
        font = tkfont.nametofont('EditorFont')
        linespace = font.metrics('linespace')  # This typically corresponds to the font's height

        # Scale the offset proportionally (25 is the offset when the font's linespace is 24)
        offset = int(25 * linespace / 24)

        self.remove_indent_guides()

        text = self.get_text_widget()
        if text is None:
            return

        if len(self.lines) == 0:
            return

        current_line = int(text.index('insert').split('.')[0])
        if current_line < 0 or current_line > len(self.lines) - 1:
            return

        current_line_text = self.lines[current_line - 1]
        if not re.match(r'\s+', current_line_text):
            return

        start_line = self.find_block_line(current_line, -1)
        end_line = self.find_block_line(current_line, 1)

        # Get indent of start line
        start_line_text = self.lines[start_line - 1]
        indent = len(re.match(r'^(\s*)', start_line_text).group(1))

        text.update_idletasks()

        top_visible_line = int(text.index('@0,0').split('.')[0])
        bottom_visible_line = int(text.index(f'@0,{text.winfo_height()}').split('.')[0])

        # Find start of block
        if start_line > bottom_visible_line or end_line < top_visible_line:
            # Region is totally outside viewport; do nothing.
            return

        if start_line < top_visible_line:
            # Start line is above viewport.
            top = 0
        else:
            bbox_start = text.bbox(f'{start_line}.{indent}')
            if bbox_start is None:
                # If the bounding box isn't available, skip drawing the guide.
                return
            try:
                pady = int(text.cget('pady'))
            except (TypeError, ValueError):
                pady = 0
            top = bbox_start[1] + bbox_start[3] - pady

        if end_line > bottom_visible_line:
            # End line is below viewport.
            bottom = text.winfo_height()
        else:
            bbox_end = text.bbox(f'{end_line}.end')
            if bbox_end is None:
                return
            try:
                pady = int(text.cget('pady'))
            except (TypeError, ValueError):
                pady = 0
            bottom = bbox_end[1] + bbox_end[3] + pady + offset//2

        # Calculate the horizontal position for the guide.
        charwidth = tk.font.nametofont('EditorFont').measure(' ')
        left = indent * charwidth

        syntax_theme = self.get_syntax_theme()
        line_color = syntax_theme["surrounding_parens"]["foreground"]

        indent_guide = tk.Canvas(
            text,
            borderwidth=0,
            width=1,
            height=(bottom - top),
            highlightthickness=0,
            background=line_color,
        )

        self.indent_guides.append(indent_guide)
        indent_guide.place(y=top, x=left)

    def remove_indent_guides(self, event=None):
        for indent_guide in self.indent_guides:
            indent_guide.place_forget()
        self.indent_guides = []


def load_plugin():
    workbench = get_workbench()
    Plugin(workbench)
