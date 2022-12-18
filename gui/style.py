import ttkbootstrap as ttk


def configure_style(style: ttk.Style) -> None:

    # primary.TButton
    style.map(
        "TButton",
        bordercolor=[
            ("active", "#315172"),
            ("pressed", "#1f3247"),
            ("focus", "#315172"),
            ("disabled", "#383838"),
        ],
        background=[
            ("active", "#315172"),
            ("pressed", "#1f3247"),
            ("focus", "#315172"),
            ("disabled", "#383838"),
        ],
    )
    # primary.Link.TButton
    style.configure(
        "primary.Link.TButton",
        foreground="white",
        shiftrelief="",
    )
    style.map(
        "primary.Link.TButton",
        background=[("active", "gray24")],
        bordercolor=[("active", "gray50"), ("pressed", "gray50"), ("focus", "")],
        foreground=[("active", "white")],
        focuscolor=[("pressed", ""), ("focus", ""), ("active", "gray50")],
        shiftrelief=[("pressed", "")],
    )
    # danger.primary.Link.TButton
    style.configure("danger.primary.Link.TButton", foreground="white", padding=(6, 0))
    style.map(
        "danger.primary.Link.TButton",
        background=[("active", "#e74c3c")],
    )
    # copy.primary.Link.TButton
    style.configure(
        "copy.primary.Link.TButton",
        padding=(0, 0),
        background="#2f2f2f",
        bordercolor="#2f2f2f",
        lightcolor="#2f2f2f",
        darkcolor="#2f2f2f",
    )
    style.map(
        "copy.primary.Link.TButton",
        background=[("active", "gray24")],
        bordercolor=[
            ("alternate", "#2f2f2f"),
            ("active", "gray50"),
            ("pressed", "gray50"),
            ("focus", ""),
        ],
    )
    # default.TSeparator
    style.configure(
        "default.TSeparator",
        borderwidth=0,
    )
    # str_progress_in.Horizontal.TProgressbar
    style.layout(
        "str_progress_in.Horizontal.TProgressbar",
        [
            (
                "Horizontal.Progressbar.trough",
                {
                    "children": [
                        (
                            "Horizontal.Progressbar.pbar",
                            {"side": "left", "sticky": "ns"},
                        )
                    ],
                    "sticky": "nswe",
                },
            ),
            ("Horizontal.Progressbar.label", {"sticky": "nswe"}),
        ],
    )
    style.configure(
        "str_progress_in.Horizontal.TProgressbar",
        anchor="center",
        foreground="white",
    )
    # hide_or_show_password register_window
    style.configure(
        "pure.TButton", background="#2f2f2f", bordercolor="", padding=(4, 2)
    )
    style.map(
        "pure.TButton",
        background=[("active", "#2f2f2f")],
    )

    # padded frames
    style.configure("padded.TFrame", padding=[5, 15, 5, 15])
