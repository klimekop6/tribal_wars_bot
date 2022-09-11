import tkinter as tk

import ttkbootstrap as ttk

from gui_functions import forget_row


class TopLevel(tk.Toplevel):
    def __init__(
        self, title_text: str = "", timer: tk.StringVar = None, *args, **kwargs
    ) -> None:
        super().__init__(*args, **kwargs)

        self.attributes("-alpha", 0.0)
        self.iconbitmap(default="icons//ikona.ico")
        self.overrideredirect(True)
        self.attributes("-topmost", 1)
        self.columnconfigure(0, weight=1)
        self.rowconfigure(0, weight=1)

        self.main_frame = ttk.Frame(self, borderwidth=1, relief="groove")
        self.main_frame.grid(row=0, column=0, sticky=("N", "S", "E", "W"))
        self.main_frame.columnconfigure(0, weight=1)
        self.main_frame.rowconfigure(1, weight=1)

        self.custom_bar = ttk.Frame(self.main_frame)
        self.custom_bar.grid(row=0, column=0, sticky=("E", "W"))
        self.custom_bar.columnconfigure(3, weight=1)

        self.content_frame = ttk.Frame(self.main_frame)
        self.content_frame.grid(row=1, column=0, sticky=("N", "S", "E", "W"))
        self.content_frame.columnconfigure(0, weight=1)
        self.content_frame.rowconfigure(0, weight=1)

        # custom_bar
        self.title_label = ttk.Label(self.custom_bar, text=title_text)
        self.title_label.grid(row=0, column=1, padx=(5, 0), sticky="W")

        if timer:
            self.title_timer = ttk.Label(self.custom_bar, textvariable=timer)
            self.title_timer.grid(row=0, column=2, padx=5)

        self.minimize = tk.PhotoImage(file="icons//minimize.png")
        self.minimize_button = ttk.Button(
            self.custom_bar,
            bootstyle="primary.Link.TButton",
            image=self.minimize,
            command=self._hide,
        )
        self.minimize_button.grid(row=0, column=4, padx=(5, 0), pady=5, sticky="E")

        self.exit = tk.PhotoImage(file="icons//exit.png")
        self.exit_button = ttk.Button(
            self.custom_bar,
            bootstyle="primary.Link.TButton",
            image=self.exit,
            command=self.destroy,
        )
        self.exit_button.grid(row=0, column=5, padx=(0, 5), pady=3, sticky="E")

        self.custom_bar.bind(
            "<Button-1>", lambda event: self._get_pos(event, "custom_bar")
        )
        self.title_label.bind(
            "<Button-1>", lambda event: self._get_pos(event, "title_label")
        )

        if timer:
            self.title_timer.bind(
                "<Button-1>", lambda event: self._get_pos(event, "title_timer")
            )

    def _hide(self):
        self.attributes("-alpha", 0.0)
        self.overrideredirect(False)
        self.iconify()

        def show(event=None):
            self.overrideredirect(True)
            self.attributes("-alpha", 1.0)

        self.minimize_button.bind("<Map>", show)

    def _get_pos(self, event, *args) -> None:
        xwin = self.winfo_x()
        ywin = self.winfo_y()
        startx = event.x_root
        starty = event.y_root

        ywin = ywin - starty
        xwin = xwin - startx

        def move_window(event):
            self.geometry(f"+{event.x_root + xwin}+{event.y_root + ywin}")

        startx = event.x_root
        starty = event.y_root

        for arg in args:
            getattr(self, arg).bind("<B1-Motion>", move_window)


class ScrollableFrame:
    """Create scrollable frame on top of canvas"""

    def __init__(
        self,
        parent: ttk.Frame = None,
        max_width: bool = True,
        max_height: bool = True,
        show: bool = False,
        **kwargs,
    ) -> None:

        self.parent = parent
        if max_width:
            parent.columnconfigure(0, weight=1)
        parent.rowconfigure(0, weight=1)

        def on_configure(event: tk.Event):
            # Update scrollregion after starting 'mainloop'
            # when all widgets are in canvas.
            self.canvas.configure(scrollregion=self.canvas.bbox("all"))
            if self.canvas.yview() == (0.0, 1.0):
                self.scrollbar.grid_remove()
            else:
                self.scrollbar.grid(row=0, column=1, sticky=tk.NS)

        def _frame_size(event: tk.Event):
            min_canvas_height = parent.winfo_height()
            if max_height and self.frame.winfo_height() < min_canvas_height:
                self.canvas.itemconfig(self.canvas_frame, height=min_canvas_height)
            # No need to create scroll on the right side
            _fix_width_depend_on_scrollbar_existence(event)

        def _fix_width_depend_on_scrollbar_existence(event: tk.Event) -> None:
            if self.canvas.yview() == (0.0, 1.0):
                self.canvas.itemconfig(self.canvas_frame, width=event.width)
                return
            self.canvas.itemconfig(self.canvas_frame, width=event.width - 11)
            self.canvas.update()

        # --- Create self.canvas with scrollbar ---

        self.canvas = tk.Canvas(parent)
        if show:
            self.canvas.grid(row=0, column=0, sticky=tk.NSEW)
        self.canvas.rowconfigure(0, weight=1)

        self.container = ttk.Frame(self.canvas)
        self.container.grid(row=0, column=0, sticky=tk.NSEW)
        self.container.rowconfigure(0, weight=1)
        self.container.grid_propagate(1)

        self.frame = ttk.Frame(self.container)
        self.frame.grid(row=0, column=0, sticky=tk.NSEW, **kwargs)
        self.frame.grid_propagate(1)

        if max_width:
            self.canvas.columnconfigure(0, weight=1)
            self.container.columnconfigure(0, weight=1)
            self.frame.columnconfigure(0, weight=1)
            self.frame.columnconfigure(1, weight=1)

        self.scrollbar = ttk.Scrollbar(self.canvas, command=self._yview)
        self.scrollbar.grid(row=0, column=1, sticky=tk.NS)

        self.canvas.configure(yscrollcommand=self.scrollbar.set)
        self.canvas.bind("<Enter>", lambda event: self._bound_to_mousewheel(event))
        self.canvas.bind("<Leave>", lambda event: self._unbound_to_mousewheel(event))

        # --- Put frame in self.canvas ---

        self.canvas_frame = self.canvas.create_window(
            (0, 0), window=self.container, anchor=tk.NW
        )

        # Update scrollregion after starting 'mainloop'
        # when all widgets are in self.canvas.
        self.frame.bind("<Configure>", on_configure)
        self.canvas.bind("<Configure>", _frame_size)

    def show(self) -> None:
        forget_row(self.parent, 0)
        self.canvas.grid(row=0, column=0, sticky=tk.NSEW)

    def _bound_to_mousewheel(self, event: tk.Event = None):
        self.canvas.bind_all("<MouseWheel>", lambda event: self._on_mousewheel(event))

    def _unbound_to_mousewheel(self, event: tk.Event = None):
        self.canvas.unbind_all("<MouseWheel>")

    def _on_mousewheel(self, event: tk.Event):
        self._yview("scroll", int(-1 * (event.delta / 120)), "units")

    def _yview(self, *args):
        if self.canvas.yview() == (0.0, 1.0):
            return
        self.canvas.yview(*args)
