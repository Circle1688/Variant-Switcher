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

class VisibilityModel(ui.AbstractValueModel):
    def __init__(self, path, visible):
        super().__init__()
        self._value = visible
        self._prim_path = path

    def destroy(self):
        pass

    def get_value_as_bool(self) -> bool:
        """Reimplemented get bool"""
        # Invisible when it's checked.
        return self._value or False

    def get_value_as_string(self):
        """Reimplemented get string"""
        # This string goes to the field.
        if self._value is None:
            return ""
        # General format. This prints the number as a fixed-point
        # number, unless the number is too large, in which case it
        # switches to 'e' exponent notation.
        return ""

    def set_value(self, value: bool):
        """Reimplemented set bool"""
        self._value = value
        prop_path = f"{self._prim_path}.visibility"
        omni.kit.commands.execute(
            "ChangeProperty", prop_path=Sdf.Path(prop_path), value='inherited' if value else 'invisible', prev=None
        )
        self._value_changed()
        
class VariantSetModel(ui.AbstractItemModel):
    def __init__(self):
        super().__init__()
        self._children = []
        # for i in range(2):
        #     self._children.append(CommandItem(text='hello', value=True))
    
    def add_set(self, name):
        self._children.append(VariantSetItem(text=name))
        self._item_changed(None)
        
    
    def clear_set(self):
        self._children = []
        self._item_changed(None)
    
    def remove_set(self, items):
        for item in items:
            self._children.remove(item)
        self._item_changed(None)
    
    def get_item_children(self, item):
        """Returns all the children when the widget asks it."""
        if item is not None:
            # Since we are doing a flat list, we return the children of root only.
            # If it's not root we return.
            return []

        return self._children

    def get_item_value_model_count(self, item):
        """The number of columns"""
        return 1

    def get_item_value_model(self, item, column_id):
        """
        Return value model.
        It's the object that tracks the specific value.
        In our case we use ui.SimpleStringModel for the first column
        and SimpleFloatModel for the second column.
        """
        return item.name_model

    
class VariantSetItem(ui.AbstractItem):
    def __init__(self, text):
        super().__init__()
        self.name_model = ui.SimpleStringModel(text)
    
    def __repr__(self):
        return f'"{self.name_model.as_string}"'
    
    def get_value_as_string(self):
        return self.name_model.as_string

class VariantItem(ui.AbstractItem):
    """Single item of the model"""

    def __init__(self, text, value, path):
        super().__init__()
        self.name_model = ui.SimpleStringModel(text)
        self.value_model = VisibilityModel(path, value)
        self.path = path
    
    def __repr__(self):
        return f'"{self.name_model.get_value_as_string()} {self.value_model.get_value_as_bool()}"'
    
    def get_path(self):
        return self.path

class VariantModel(ui.AbstractItemModel):
    """
    Represents the list of commands registered in Kit.
    It is used to make a single level tree appear like a simple list.
    """

    def __init__(self):
        super().__init__()
        self._children = []
        self.parent_variant_set_path = None
        # for i in range(2):
        #     self._children.append(CommandItem(text='hello', value=True))

    def add_item(self, name, value, path):
        self._children.append(VariantItem(text=name, value=value, path=path))
        self._item_changed(None)

    def clear_item(self):
        self._children = []
        self._item_changed(None)
    
    def remove_item(self, items):
        for item in items:
            self._children.remove(item)
        self._item_changed(None)

    def get_item_children(self, item):
        """Returns all the children when the widget asks it."""
        if item is not None:
            # Since we are doing a flat list, we return the children of root only.
            # If it's not root we return.
            return []

        return self._children

    def get_item_value_model_count(self, item):
        """The number of columns"""
        return 1

    def get_item_value_model(self, item, column_id):
        """
        Return value model.
        It's the object that tracks the specific value.
        In our case we use ui.SimpleStringModel for the first column
        and SimpleFloatModel for the second column.
        """
        if item and isinstance(item, VariantItem):
            return item.value_model if column_id == 1 else item.name_model
        
    def set_variant_on(self, item):
        for child in self._children:
            child.value_model.set_value(child == item)

    def get_drag_mime_data(self, item):
        """Returns Multipurpose Internet Mail Extensions (MIME) data for be able to drop this item somewhere"""
        # As we don't do Drag and Drop to the operating system, we return the string.
        return item.name_model.as_string

    def drop_accepted(self, target_item, source, drop_location=-1):
        """Reimplemented from AbstractItemModel. Called to highlight target when drag and drop."""
        # If target_item is None, it's the drop to root. Since it's
        # list model, we support reorganization of root only and we
        # don't want to create a tree.
        return not target_item and drop_location >= 0

    def drop(self, target_item, source, drop_location=-1):
        """Reimplemented from AbstractItemModel. Called when dropping something to the item."""
        try:
            source_id = self._children.index(source)
        except ValueError:
            # Not in the list. This is the source from another model.
            return

        if source_id == drop_location:
            # Nothing to do
            return

        self._children.remove(source)

        if drop_location > len(self._children):
            # Drop it to the end
            self._children.append(source)
        else:
            if source_id < drop_location:
                # Because when we removed source, the array became shorter
                drop_location = drop_location - 1

            self._children.insert(drop_location, source)

        self._item_changed(None)
        

        # delete all variant
        stage = omni.usd.get_context().get_stage()
        prim = stage.GetPrimAtPath(self.parent_variant_set_path)
        cache_prims = [_.GetPath() for _ in prim.GetAllChildren()]

        omni.kit.commands.execute('DeletePrims',
            paths=cache_prims,
            destructive=False)
        
        # rename

        for i, child in enumerate(self._children):
            path_name = '___'.join([_ for _ in child.path.split('/')])
                
            omni.kit.commands.execute('CreatePrimWithDefaultXform',
                    prim_type='Scope',
                    prim_path=f'{self.parent_variant_set_path}/{path_name}__num__{i}',
                    attributes={},
                    select_new_prim=False)