import omni.ext
import omni.ui as ui
import omni.kit.commands
import omni.usd
from typing import Union
from pxr import Usd, Sdf, UsdGeom, UsdShade
import os
from .style import STOP_BUTTON, BUTTON, STRING_FIELD, TOOL_BUTTON
from omni.kit.widget.stage import StageWidget
from omni.kit.widget.stage import StageIcons

class VariantSetEditableDelegate(ui.AbstractItemDelegate):
    """
    Delegate is the representation layer. TreeView calls the methods
    of the delegate to create custom widgets for each item.
    """

    def __init__(self):
        super().__init__()
        self.subscription = None
        self.variant_set_name = None
        self.variant_set_path = "/VariantSwitcherCache"

    def build_branch(self, model, item, column_id, level, expanded):
        """Create a branch widget that opens or closes subtree"""
        pass

    def build_widget(self, model, item, column_id, level, expanded):
        """Create a widget per column per item"""
        stack = ui.ZStack(height=26)
        with stack:
            value_model = model.get_item_value_model(item, column_id)
            label = ui.Label(value_model.as_string)
            field = ui.StringField(value_model, visible=False)

        # Start editing when double clicked
        stack.set_mouse_double_clicked_fn(lambda x, y, b, m, f=field, l=label: self.on_double_click(b, f, l))

    def on_double_click(self, button, field, label):
        """Called when the user double-clicked the item in TreeView"""
        if button != 0:
            return

        # Make Field visible when double clicked
        field.visible = True
        field.focus_keyboard()
        # When editing is finished (enter pressed of mouse clicked outside of the viewport)
        self.subscription = field.model.subscribe_end_edit_fn(
            lambda m, f=field, l=label: self.on_end_edit(m, f, l)
        )
        self.variant_set_name = label.text

    def on_end_edit(self, model, field, label):
        """Called when the user is editing the item and pressed Enter or clicked outside of the item"""
        def find_prims_by_name(prim_name: str):
            stage = omni.usd.get_context().get_stage()
            found_prims = [x for x in stage.Traverse() if x.GetName() == prim_name]
            return found_prims
        
        if len(find_prims_by_name(field.model.get_value_as_string())) == 0:
            if not field.model.get_value_as_string().isdigit():
                if self.variant_set_name != model.as_string:
                    field.visible = False
                    label.text = model.as_string
                    self.subscription = None
                    
                    omni.kit.commands.execute('MovePrim',
                        path_from=f'{self.variant_set_path}/{self.variant_set_name}',
                        path_to=f'{self.variant_set_path}/{model.as_string}')
                    
                    self.variant_set_name = None
                field.visible = False
                self.subscription = None
            else:
                model.set_value(label.text) 
                field.visible = False
                self.subscription = None
        else:
            model.set_value(label.text) 
            field.visible = False
            self.subscription = None



class EditableDelegate(ui.AbstractItemDelegate):
    """
    Delegate is the representation layer. TreeView calls the methods
    of the delegate to create custom widgets for each item.
    """

    def __init__(self):
        super().__init__()
        self.subscription = None

    def build_branch(self, model, item, column_id, level, expanded):
        """Create a branch widget that opens or closes subtree"""
        pass

    def build_widget(self, model, item, column_id, level, expanded):
        """Create a widget per column per item"""
        def on_value_changed(m):
            visible_btn.checked = m.get_value_as_bool()
            visible_btn.image_url = StageIcons().get("check_off" if not visible_btn.checked else "check_on")

        stack = ui.HStack(height=20, width=20, style=TOOL_BUTTON)
        with stack:
            ui.Spacer(width=5)
            name_model = model.get_item_value_model(item, 0)
            value_model = model.get_item_value_model(item, 1)
            label = ui.Label(name_model.as_string, width=350)
            visible_btn = ui.ToolButton(value_model, 
                                        enabled=False,
                                        image_url=StageIcons().get("check_off" if value_model.get_value_as_bool() else "check_on")  ,
                                        image_width=15,
                                        image_height=15,
                                        name='tool_button')
        stack.set_mouse_double_clicked_fn(lambda x, y, b, m, model=model, l=label, item=item, visible_btn=visible_btn, value_model=value_model: self.on_double_click(b, model, l, item, visible_btn, value_model))
        self.subscription = value_model.add_value_changed_fn(on_value_changed)
        

    def on_double_click(self, button, model, label, item, visible_btn, value_model):
        """Called when the user double-clicked the item in TreeView"""
        if button != 0:
            return
              
        model.set_variant_on(item)
        