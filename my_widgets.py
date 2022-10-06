import tkinter as tk

import ttkbootstrap as ttk
from ttkbootstrap.scrolled import ScrolledFrame

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


class ScrollableFrame(ScrolledFrame):
    def __init__(
        self,
        master=None,
        padding=0,
        bootstyle=ttk.DEFAULT,
        autohide=True,
        height=200,
        width=300,
        scrollheight=None,
        max_height=False,
        **kwargs,
    ):
        super().__init__(
            master, padding, bootstyle, autohide, height, width, scrollheight, **kwargs
        )

        self.master = master
        self.max_height = max_height

    def show(self) -> None:
        forget_row(self.master, methods=("place",))
        if self.max_height:
            if hasattr(self, "height_fix"):
                getattr(self, "height_fix")()
            elif (self.master.winfo_height() - self.winfo_reqheight()) > 0:
                self.rowconfigure(
                    666,
                    minsize=(self.master.winfo_height() - self.winfo_reqheight()),
                )
        self.place(rely=0.0, relheight=1.0, relwidth=1.0)

    def scroll_to_widget_top(self, widget: tk.Widget):
        if self.winfo_height() > self.container.winfo_height():
            pos = widget.winfo_rooty() - self.winfo_rooty()
            height = self.winfo_height()
            self.yview_moveto(pos / height)


class CollapsingFrame(ttk.Frame):
    """A collapsible frame widget that opens and closes with a click."""

    def __init__(self, master, **kwargs):
        super().__init__(master, **kwargs)
        self.columnconfigure(0, weight=1)
        self.cumulative_rows = 0

        # widget images
        self.images = [
            ttk.PhotoImage(file="icons//right_arrow.png"),
            ttk.PhotoImage(file="icons//down_arrow.png"),
        ]

    def add(self, child: ttk.Frame, title="", bootstyle=ttk.PRIMARY, **kwargs):
        """Add a child to the collapsible frame

        Parameters:

            child (Frame):
                The child frame to add to the widget.

            title (str):
                The title appearing on the collapsible section header.

            bootstyle (str):
                The style to apply to the collapsible section header.

            **kwargs (Dict):
                Other optional keyword arguments.
        """
        if child.winfo_class() != "TFrame":
            return

        style_color = ttk.Bootstyle.ttkstyle_widget_color(bootstyle)
        frame = ttk.Frame(self, bootstyle=style_color)
        frame.grid(row=self.cumulative_rows, column=0, sticky=ttk.EW)

        # header title
        header = ttk.Label(
            master=frame, text=title, bootstyle=(style_color, ttk.INVERSE)
        )
        if kwargs.get("textvariable"):
            header.configure(textvariable=kwargs.get("textvariable"))
        header.pack(side=ttk.LEFT, fill=ttk.BOTH, padx=10)

        # header toggle button
        def _func(c=child):
            return self._toggle_open_close(c)

        btn = ttk.Button(
            master=frame, image=self.images[0], bootstyle=style_color, command=_func
        )
        btn.pack(side=ttk.RIGHT)

        # assign toggle button to child so that it can be toggled
        child.btn = btn

        # increment the row assignment
        self.cumulative_rows += 2

    def _toggle_open_close(self, child: ttk.Frame):
        """Open or close the section and change the toggle button
        image accordingly.

        Parameters:

            child (Frame):
                The child element to add or remove from grid manager.
        """
        if child.winfo_viewable():
            child.grid_remove()
            child.btn.configure(image=self.images[0])
        else:
            child.grid(row=self.cumulative_rows + 1, column=0, sticky=ttk.EW)
            child.btn.configure(image=self.images[1])


class Text:
    def __init__(self, collapsing_frame: CollapsingFrame) -> None:
        self.text_line = 1

        self.frame = ttk.Frame(collapsing_frame)
        self.frame.columnconfigure(0, weight=1)

        self.text = tk.Text(
            self.frame,
            autostyle=False,
            background="#222222",
            borderwidth=0,
            foreground="white",
            font=("TkFixedFont", 10),
            insertbackground="white",
            padx=15,
            height=5,
            wrap="word",
            spacing1=10,
            spacing2=5,
            spacing3=1,
        )
        self.text.grid(row=0, column=0, sticky=ttk.EW)

        # Tags
        self.text.tag_configure("h1", font=("TkFixedFont", 11), spacing1=20)
        self.text.tag_configure("left_margin", lmargin2=8)

        # Bindings
        self.text.bind("<Map>", lambda _: self.text.configure(state="disabled"))
        self.text.bind("<Map>", self._on_map, "+")
        self.text.bindtags((self.text.bindtags()[0],))

        # Delegate text methods to frame
        for method in vars(ttk.Text).keys():
            if any(["pack" in method, "grid" in method, "place" in method]):
                pass
            else:
                setattr(self, method, getattr(self.text, method))

    def add(self, line_of_text: str, *tags) -> None:
        self.text.insert(f"{self.text_line}.0", line_of_text, *tags)
        self.text_line += 1

    def _on_map(self, *_):
        """Callback for when the configure method is used"""

        self.text.update_idletasks()
        self.text.configure(height=self.text.count("1.0", "end", "displaylines"))
