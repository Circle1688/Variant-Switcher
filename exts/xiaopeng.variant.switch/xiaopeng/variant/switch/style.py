from omni.ui import color as cl
import omni.ui as ui
BUTTON = {
    "Button": {
        "background_color": cl("#097eff"),
        "border_color": cl("#1d76fd"),
    },
    "Button.Label": {"color": cl.white},
    "Button:hovered": {"background_color": cl("#006eff")},
    "Button:pressed": {"background_color": cl("#6db2fa")},
}

STOP_BUTTON = {
    "Button": {
        "background_color": cl("#b53838"),
        "border_color": cl("#1d76fd"),
    },
    "Button.Label": {"color": cl.white},
    "Button:hovered": {"background_color": cl("#db3c3c")},
    "Button:pressed": {"background_color": cl("#8c2929")},
}

STRING_FIELD = {
    "Field": {
        "background_color": cl("#474747"),
        "border_color": cl("#1d76fd"),
    }
}

TOOL_BUTTON = {
    "Button::tool_button": {
        "background_color": cl(0, 0, 0, 0),
    },
    "Button:hovered": {"background_color": cl(0, 0, 0, 0)},
    "Button:pressed": {"background_color": cl(0, 0, 0, 0)},
    "Button:checked": {"background_color": cl(0, 0, 0, 0)},
}
