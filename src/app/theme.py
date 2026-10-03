STATUS_COLORS = {
    "Below threshold": "#2a78d6",
    "Triggered stress test": "#eb6834",
    "Above threshold, blocked": "#1baf7a",
}
NEGATIVE = "#e34948"
POSITIVE = "#2a78d6"
NEUTRAL = "#898781"
FONT = "system-ui, -apple-system, Segoe UI, sans-serif"


def style_figure(figure, height: int = 360):
    figure.update_layout(
        height=height,
        margin={"l": 8, "r": 8, "t": 36, "b": 8},
        font={"family": FONT, "size": 13},
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        legend={"orientation": "h", "y": 1.08, "x": 0, "title": None},
        hoverlabel={"font_family": FONT},
    )
    figure.update_xaxes(showgrid=False, zeroline=False, linecolor="#c3c2b7")
    figure.update_yaxes(gridcolor="rgba(137,135,129,0.25)", zeroline=False)
    return figure
