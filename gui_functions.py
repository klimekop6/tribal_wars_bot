import textwrap
import tkinter as tk

import ttkbootstrap as ttk

from app_logging import get_logger

logger = get_logger(__name__)


def center(window: tk.Toplevel, parent: tk.Toplevel = None) -> None:
    """Place window in the center of a screen or parent widget"""

    window.update_idletasks()
    if parent:
        window_geometry = window.winfo_geometry()
        parent_geometry = parent.winfo_geometry()
        window_x, window_y = window_geometry[: window_geometry.find("+")].split("x")
        parent_x, parent_y = parent_geometry[: parent_geometry.find("+")].split("x")
        window.geometry(
            f"+{int(int(parent.winfo_rootx()) + int(parent_x)/2 - int(window_x)/2)}"
            f"+{int(int(parent.winfo_rooty()) + int(parent_y)/2 - int(window_y)/2)}"
        )
    else:
        if isinstance(window, tk.Tk):
            window.geometry(
                f"+{int(window.winfo_screenwidth()/2 - window.winfo_width()/2)}"
                f"+{int(window.winfo_screenheight()/2 - window.winfo_height()/2)}"
            )
        else:
            window.geometry(
                f"+{int(window.winfo_screenwidth()/2 - window.winfo_reqwidth()/2)}"
                f"+{int(window.winfo_screenheight()/2 - window.winfo_reqheight()/2)}"
            )


def change_state(parent, value, entries_content, reverse=False, *ommit) -> None:
    def disableChildren(parent):
        if not parent.winfo_children():
            if parent.winfo_class() not in ("TFrame", "TLabelframe", "TSeparator"):
                parent.config(state="disabled")
        for child in parent.winfo_children():
            wtype = child.winfo_class()
            if wtype not in ("TFrame", "TLabelframe", "TSeparator"):
                if child not in ommit:
                    child.configure(state="disable")
            else:
                disableChildren(child)

    def enableChildren(parent):
        if not parent.winfo_children():
            if parent.winfo_class() not in ("TFrame", "TLabelframe", "TSeparator"):
                parent.config(state="normal")
        for child in parent.winfo_children():
            wtype = child.winfo_class()
            if wtype not in ("TFrame", "TLabelframe", "TSeparator"):
                if child not in ommit:
                    if wtype == "TCombobox":
                        child.configure(state="readonly")
                    else:
                        child.configure(state="normal")
            else:
                enableChildren(child)

    def check_button_fix(parent):
        for child in parent.winfo_children():
            wtype = child.winfo_class()
            if wtype not in ("TFrame"):
                if wtype in ("TCheckbutton"):
                    if child not in ommit:
                        child.invoke()
                        child.invoke()
            else:
                check_button_fix(child)

    if not isinstance(value, int):
        value = int(entries_content[value].get())

    if not isinstance(parent, list):
        parent = [parent]

    for parent_ in parent:
        if not reverse:
            if value:
                disableChildren(parent_)
            else:
                enableChildren(parent_)
                check_button_fix(parent_)
        else:
            if value:
                enableChildren(parent_)
                check_button_fix(parent_)
            else:
                disableChildren(parent_)


def change_state_on_settings_load(
    parent, name, entries_content: dict, reverse=False, *ommit
) -> None:
    if name in entries_content:
        if not entries_content[name].get():
            return
        if int(entries_content[name].get()) or reverse:
            change_state(
                parent,
                int(entries_content[name].get()),
                entries_content,
                reverse,
                *ommit,
            )


def custom_error(
    message: str, auto_hide: bool = False, parent=None, justify=None, sticky=None
) -> None:

    master = tk.Toplevel(borderwidth=1, relief="groove")
    master.attributes("-alpha", 0.0)
    master.overrideredirect(True)
    master.attributes("-topmost", 1)
    master.bell()

    message = message.splitlines()
    if not auto_hide:
        if len(message) == 1:
            message = textwrap.fill(message[0], width=80)
            message_label = ttk.Label(master, text=message, justify=justify)
            message_label.grid(row=0, column=0, padx=10, pady=10, sticky=sticky)

            ok_button = ttk.Button(master, text="Ok", command=master.destroy)
            ok_button.grid(row=1, column=0, padx=10, pady=(0, 10))
        else:
            for index, text_line in enumerate(message):
                text_line = textwrap.fill(text_line, width=80)
                if index == 0:
                    message_label = ttk.Label(master, text=text_line, justify=justify)
                    message_label.grid(
                        row=index, column=0, padx=10, pady=(10, 5), sticky=sticky
                    )
                else:
                    message_label = ttk.Label(master, text=text_line, justify=justify)
                    message_label.grid(
                        row=index, column=0, padx=10, pady=(0, 5), sticky=sticky
                    )
            ok_button = ttk.Button(master, text="Ok", command=master.destroy)
            ok_button.grid(row=len(message), column=0, padx=10, pady=(5, 10))

        master.focus_force()
        master.bind("<Return>", lambda event: master.destroy())
        center(master, parent=parent)
        master.attributes("-alpha", 1.0)
        master.grab_set()
        ok_button.wait_window(master)

    if auto_hide:
        message_label = ttk.Label(master, text=message[0])
        message_label.grid(row=1, column=0, padx=10, pady=8)
        center(master, parent=parent)
        master.attributes("-alpha", 1.0)
        master.after(ms=2000, func=lambda: master.destroy())


def fill_entry_from_settings(entries: dict, settings: dict) -> None:
    def loop_over_entries(entries: dict | tk.StringVar, settings: dict | str):
        for key in entries:
            if key in settings:
                if isinstance(entries[key], dict):
                    loop_over_entries(entries[key], settings[key])
                else:
                    entries[key].set(settings[key])
            # If not in settings set default to 0
            else:
                if isinstance(entries[key], dict):
                    loop_over_entries(entries[key], settings)
                else:
                    entries[key].set(0)

    loop_over_entries(entries=entries, settings=settings)


def forget_row(widget_name, row_number: int = 0, rows_beetwen: tuple = None) -> None:
    for label in widget_name.grid_slaves():
        if rows_beetwen:
            if rows_beetwen[0] < int(label.grid_info()["row"]) < rows_beetwen[1]:
                label.grid_forget()
        elif int(label.grid_info()["row"]) == row_number:
            label.grid_forget()


def get_pos(self, event, *args) -> None:
    xwin = self.master.winfo_x()
    ywin = self.master.winfo_y()
    startx = event.x_root
    starty = event.y_root

    ywin = ywin - starty
    xwin = xwin - startx

    def move_window(event):
        self.master.geometry(f"+{event.x_root + xwin}+{event.y_root + ywin}")

    startx = event.x_root
    starty = event.y_root

    for arg in args:
        getattr(self, arg).bind("<B1-Motion>", move_window)


def invoke_checkbuttons(parent) -> None:
    def call_widget(parent) -> None:
        for child in parent.winfo_children():
            wtype = child.winfo_class()
            if wtype == "TCheckbutton":
                child.invoke()
                child.invoke()
            else:
                call_widget(parent=child)

    call_widget(parent=parent)


def on_button_release(event: tk.Event, master: tk.Tk) -> None:
    """Adds function to some widgets like Entry, Text, Spinbox etc.
    It is selecting all text inside widget after button_release event.
    Also it loes focus and clear selection if user click outside of widget.
    """

    widget: ttk.Entry = event.widget
    widget.selection_range(0, "end")
    widget.focus()
    widget_class = widget.winfo_class()
    widget.unbind_class(widget_class, "<ButtonRelease-1>")

    def on_leave(event: tk.Event = None) -> None:
        def on_enter(event: tk.Event = None) -> None:
            master.unbind_all("<Button-1>")
            master.unbind_class(widget_class, "<ButtonRelease-1>")

        def on_click_outside(event: tk.Event) -> None:
            if not widget.winfo_exists():
                master.unbind_all("<Button-1>")
                return
            widget.select_clear()
            widget.nametowidget(widget.winfo_parent()).focus()
            master.unbind_all("<Button-1>")
            widget.unbind("<Enter>")
            widget.unbind("<Leave>")

        widget.bind("<Enter>", on_enter)
        master.bind_class(
            widget_class,
            "<ButtonRelease-1>",
            lambda event: on_button_release(event, master),
        )
        master.bind_all("<Button-1>", on_click_outside, add="+")

    widget.bind("<Leave>", on_leave)


def save_entry_to_settings(
    entries: dict, settings: dict, settings_by_worlds: dict = None
) -> None:
    def loop_over_entries(entries: dict | tk.StringVar, settings: dict | str):
        for key, value in entries.items():
            if isinstance(value, dict):
                if key not in settings:
                    settings[key] = {}
                loop_over_entries(entries=entries[key], settings=settings[key])
            else:
                settings[key] = value.get()

    loop_over_entries(entries=entries, settings=settings)
    if settings_by_worlds:
        loop_over_entries(
            entries=entries, settings=settings_by_worlds[settings["server_world"]]
        )


def show_or_hide_password(parent, entry: ttk.Entry, button: ttk.Button) -> None:
    """Show or hide password after user click eye icon"""

    if entry.cget("show") == "":
        entry.config(show="*")
        button.config(image=parent.hide_image)
    else:
        entry.config(show="")
        button.config(image=parent.show_image)
    entry.focus_set()
