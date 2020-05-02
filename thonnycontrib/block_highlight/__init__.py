import ast
import tkinter as tk
from thonny import get_workbench


class Plugin:
    def __init__(self, workbench):
        self.workbench = workbench
        self.indent_guides = []

        events = ['CursorMove', 'Modified', 'TextChange', 'VerticalScroll', 'FocusIn']
        for event in events:
            self.workbench.bind_class(
                'CodeViewText', f'<<{event}>>', self.place_indent_guide, True)

        self.workbench.bind_class('CodeViewText', 'FocusOut', self.remove_indent_guides, True)

    def find_last_line(self, node):
        max_line = None
        if hasattr(node, 'lineno'):
            max_line = node.lineno
        for child_node in ast.walk(node):
            if hasattr(child_node, 'lineno') and child_node.lineno > (max_line or 0):
                max_line = child_node.lineno
        return max_line

    def build_index(self, node, index=None):
        if index is None:
            index = {}

        if hasattr(node, 'lineno'):
            if not index.get(node.lineno):
                index[node.lineno] = node

        if hasattr(node, 'body'):
            node.lastline = self.find_last_line(node)
            for item in node.body:
                item.parent_node = node
                if not hasattr(node, 'firstchild'):
                    node.firstchild = item
                self.build_index(item, index)

        return index

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

    def place_indent_guide(self, event=None):
        self.remove_indent_guides()

        nb = self.workbench.get_editor_notebook()
        editor = nb.get_current_child()

        if editor is None:
            return

        code_view = editor.get_code_view()
        text = code_view.text

        src = text.get('1.0', 'end')
        code_index = self.build_index(ast.parse(src))
        current_line = int(text.index('insert').split('.')[0])

        if current_line not in code_index:
            return

        node = code_index[current_line]
        parent = node.parent_node

        if not hasattr(parent, 'lineno'):
            return

        text.update_idletasks()

        bbox_start = text.bbox(f'{parent.lineno}.{parent.col_offset}')
        bbox_end = text.bbox(f'{parent.lastline}.end')

        left = bbox_start[0] - text["padx"] + 2
        top = bbox_start[1] + bbox_start[3] - text["pady"]
        bottom = bbox_end[1] + text["pady"] + 5

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
