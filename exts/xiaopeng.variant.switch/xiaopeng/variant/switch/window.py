import omni.ext
import omni.ui as ui
import omni.kit.commands
import omni.usd
from typing import Union, List
from pxr import Usd, Sdf, UsdGeom, UsdShade
import os
from .style import STOP_BUTTON, BUTTON, STRING_FIELD, TOOL_BUTTON
from omni.kit.widget.stage import StageWidget
from omni.kit.widget.stage import StageIcons
from .delegate import VariantSetEditableDelegate, EditableDelegate
from .model import VariantItem, VariantModel, VariantSetItem, VariantSetModel  

from omni.kit.window.filepicker import FilePickerDialog
from omni.kit.widget.filebrowser import FileBrowserItem
from omni.kit.window.popup_dialog import MessageDialog
from omni.kit.viewport.utility import get_active_viewport, capture_viewport_to_file

class VariantSwitchWindow(ui.Window):
    def __init__(self, title: str, delegate=None, **kwargs):
        super().__init__(title, **kwargs)

        self._usd_context = omni.usd.get_context()
        self._selection = self._usd_context.get_selection()

        self.current_select_variant_name = None
        self.current_variant_set_selections = None
        self.current_variant_selections = None

        self._filepicker = None
        self._filepicker_selected_folder = ""

        self.frame.set_build_fn(self._build_fn)

        self.add_frame_count = 0  # count the frame
        self._wait_frame = False
        self.current_switch_index = 0
        self.start_batch = False
        self.file_name = ""

        self.subscription_handle = omni.kit.app.get_app().get_update_event_stream().create_subscription_to_pop(self.on_update, name="UPDATE_SUB")

    def on_update(self, p):
        if self.start_batch:
            self._batch_progress_bar.visible = True
            if self.add_frame_count > 0:
                self.add_frame_count -= 1
                if self.add_frame_count == 0:  
                    path = os.path.join(self._filepicker_selected_folder, self.file_name)
                    self.screenshot(path)
                    self.current_switch_index += 1
                    self._wait_frame = False
                    self.add_frame_count = 0

            elif not self._wait_frame and self.add_frame_count == 0:
                items = self._variant_model._children
                if self.current_switch_index < len(items):
                    self._batch_progress_bar.model.set_value(self.current_switch_index / len(items))
                    item = items[self.current_switch_index]
                    self._variant_model.set_variant_on(item)
                    self.file_name = item.name_model.get_value_as_string() + ".png"
                    self._wait_frame = True
                    self.add_frame_count = 500
                else:
                    self.start_batch = False
                    self._batch_progress_bar.visible = False
                    dialog = MessageDialog(
                        title="Batch Render",
                        message="Done",
                        ok_handler=self._done_handler,
                        ok_label="OK",
                        disable_cancel_button=True
                    )
                    dialog.show()

    def _done_handler(self, dialog):
        dialog.hide()
                    

    def destroy(self):
        # It will destroy all the children
        super().destroy()

    def on_shutdown(self):
        self._win = None
        self.subscription_handle = None

    def show(self):
        self.visible = True
        self.focus()

    def hide(self):
        self.visible = False

    def _build_fn(self):

        with self.frame:
            with ui.VStack(spacing=5):
                with ui.HStack(spacing=5, height=0):
                    ui.Label('Variant Path', width=0)
                    with ui.VStack(height=0):
                        ui.Spacer(height=3)
                        self.variant_set_path = ui.StringField(width=ui.Fraction(2), height=22)
                        self.variant_set_path.model.set_value('/VariantSwitcherCache')
                    ui.Button(f" {omni.kit.ui.get_custom_glyph_code('${glyphs}/menu_refresh.svg')}  Load ",
                                 width=0, height=22, clicked_fn=self.load_cache)
                
                with ui.HStack(spacing=5, height=0):
                    ui.Button("Batch Screenshot", width=0, height=22, clicked_fn=self.show_screenshot_save_dir)
                    self._batch_progress_bar = ui.ProgressBar(visible=False)
                    
                with ui.HStack(spacing=5):
                    
                    with ui.VStack(spacing=5, width=200):
                        with ui.HStack(height=0): 
                            self._add_button = ui.Button(
                                f" {omni.kit.ui.get_custom_glyph_code('${glyphs}/menu_add.svg')}  Add ",
                                width=0,
                                clicked_fn=self.add_variant_set
                            )
                            ui.Separator()
                            ui.Button(
                                f" {omni.kit.ui.get_custom_glyph_code('${glyphs}/menu_delete.svg')}  Delete ", 
                                height=0, width=0, clicked_fn=self.delete_selection_variant_set)
                        with ui.ScrollingFrame(
                            horizontal_scrollbar_policy=ui.ScrollBarPolicy.SCROLLBAR_ALWAYS_OFF,
                            vertical_scrollbar_policy=ui.ScrollBarPolicy.SCROLLBAR_AS_NEEDED,
                            style_type_name_override="TreeView",
                        ):
                            self._variant_set_name_delegate = VariantSetEditableDelegate()
                            self._variant_set_model = VariantSetModel()          
                            variant_set_tree_view = ui.TreeView(
                                self._variant_set_model,
                                selection_changed_fn=self.variant_set_changed,
                                delegate=self._variant_set_name_delegate,
                                root_visible=False,
                                header_visible=False,
                                style_type_name_override="TreeView",
                            )

                    with ui.VStack(spacing=5, width=400):
                        with ui.HStack(height=0): 
                            self._add_button = ui.Button(
                                f" {omni.kit.ui.get_custom_glyph_code('${glyphs}/menu_add.svg')}  Add ",
                                width=0,
                                clicked_fn=self.add_group
                            )
                            ui.Separator()
                            ui.Button(
                                f" {omni.kit.ui.get_custom_glyph_code('${glyphs}/menu_delete.svg')}  Delete ", 
                                height=0, width=0, clicked_fn=self.delete_selection_variant)

                            
                        with ui.ScrollingFrame(
                            horizontal_scrollbar_policy=ui.ScrollBarPolicy.SCROLLBAR_ALWAYS_OFF,
                            vertical_scrollbar_policy=ui.ScrollBarPolicy.SCROLLBAR_AS_NEEDED,
                            style_type_name_override="TreeView",
                        ):
                            self._name_value_delegate = EditableDelegate()
                            self._variant_model = VariantModel()
                            self._varient_tree_view = ui.TreeView(
                                self._variant_model,
                                delegate=self._name_value_delegate,
                                selection_changed_fn=self.variant_changed,
                                root_visible=False,
                                header_visible=False,
                                style_type_name_override="TreeView",
                                drop_between_items=True,
                            )

    def show_screenshot_save_dir(self):
        items = self._variant_model._children
        if len(items) == 0:
            dialog = MessageDialog(
                title="Batch Render",
                message="Please select a variant set!",
                ok_handler=self._done_handler,
                ok_label="OK",
                disable_cancel_button=True
            )
            dialog.show()
        else:
            if self._filepicker is None:
                self._filepicker = FilePickerDialog(
                        "Select Save Folder",
                        # show_only_collections=["my-computer"],
                        apply_button_label="Select",
                        item_filter_fn=lambda item: self._on_filepicker_filter_item(item),
                        selection_changed_fn=lambda items: self._on_filepicker_selection_change(items),
                        click_apply_handler=lambda filename, dirname: self._on_dir_pick(self._filepicker, filename, dirname),
                    )
            self._filepicker.set_filebar_label_name("Folder Name: ")
            self._filepicker.refresh_current_directory()
            self._filepicker.show()
        
    def _on_filepicker_filter_item(self, item: FileBrowserItem) -> bool:
        if not item or item.is_folder:
            return True
        return False
    
    def _on_filepicker_selection_change(self, items: [FileBrowserItem] = []):
        last_item = items[-1]
        self._filepicker.set_filename(last_item.name)
        self._filepicker_selected_folder = last_item.path

    def _on_dir_pick(self, dialog: FilePickerDialog, filename: str, dirname: str):
        dialog.hide()
        self.current_switch_index = 0
        self.start_batch = True
        # items = self._variant_model._children
        # for item in items:
        #     self._wait_frame = True
        #     self._variant_model.set_variant_on(item)
        #     file_name = item.name_model.get_value_as_string() + ".png"
        #     path = os.path.join(self._filepicker_selected_folder, file_name)
        #     self.screenshot(path)
        #     print("screenshot" + file_name)

    def screenshot(self, filename: str):
        vp_api = get_active_viewport()
        capture_viewport_to_file(vp_api, filename)


    def variant_set_changed(self, selections):
        self.current_variant_set_selections = selections
        if len(selections) != 0:
            self.current_select_variant_name = selections[0].get_value_as_string()
            self.load_variant_set_cache(self.current_select_variant_name)
        else:
            self.current_select_variant_name = None
            self._variant_model.clear_item()

    def variant_changed(self, selections):
        self.current_variant_selections = selections
                
    def add_group(self):
        if self.current_select_variant_name:
            paths = self._selection.get_selected_prim_paths()
            if paths:
                path = str(paths[0])
                name = path.split('/')[-1]

                self.add_cache(path)
                self._variant_model.add_item(name, self.get_visible(path), path)

    def add_group_by_path(self, path):
        name = path.split('/')[-1]
        
        self._variant_model.add_item(name, self.get_visible(path), path)

    def get_visible(self, prim_path):
        stage = omni.usd.get_context().get_stage()
        prim = stage.GetPrimAtPath(Sdf.Path(prim_path))
        visibility_attribute = prim.GetAttribute("visibility")
        return visibility_attribute.Get() == "invisible"

    def load_cache(self):

        self._variant_set_model.clear_set()
        self._variant_model.clear_item()

        self._variant_set_name_delegate.variant_set_path = self.variant_set_path.model.get_value_as_string()

        stage = omni.usd.get_context().get_stage()
        prim = stage.GetPrimAtPath(Sdf.Path(self.variant_set_path.model.get_value_as_string()))

        if prim:
            cache_prims = [_.GetName() for _ in prim.GetAllChildren()]
            for cache_name in cache_prims:
                self.add_variant_set_by_name(cache_name)

    def load_variant_set_cache(self, name):
        stage = omni.usd.get_context().get_stage()
        variant_set_path = f'{self.variant_set_path.model.get_value_as_string()}/{name}'
        prim = stage.GetPrimAtPath(variant_set_path)

        self._variant_model.clear_item()
        self._variant_model.parent_variant_set_path = variant_set_path
        cache_prims = [_.GetName() for _ in prim.GetAllChildren()]
        for cache_name in cache_prims:
            cache_name = cache_name.split('__num__')[0]
            path = '/'.join(cache_name.split('___'))
            self.add_group_by_path(path)


    def add_cache(self, path):
        if self.current_select_variant_name:
            
            path_name = '___'.join([_ for _ in path.split('/')])
                
            omni.kit.commands.execute('CreatePrimWithDefaultXform',
                    prim_type='Scope',
                    prim_path=f'{self.variant_set_path.model.get_value_as_string()}/{self.current_select_variant_name}/{path_name}__num__{len(self._variant_model._children)}',
                    attributes={},
                    select_new_prim=False)
        
            
    def find_prims_by_name(self, prim_name: str):
        stage = omni.usd.get_context().get_stage()
        found_prims = [x for x in stage.Traverse() if x.GetName() == prim_name]
        return found_prims


                

    def get_current_select_prim_path(self, multi=False):
        """
        get the path of current select prim
        """

        # returns a list of prim path strings
        paths = self._selection.get_selected_prim_paths()
        if multi:
            return paths
            
        if paths:
            # Get path of the first selected prim
            return paths[0] if len(paths) > 0 else None        
        return None
    
    def add_variant_set(self):
        i = 1
        while True:
            name = f'Variant_{i}'
            prims = self.find_prims_by_name(name)
            if len(prims) == 0: 
                self.add_variant_set_by_name(name)
                break
            i += 1

    def add_variant_set_by_name(self, name):
        self.add_variant_set_cache(name)
        self._variant_set_model.add_set(name)

    def add_variant_set_cache(self, name):
        omni.kit.commands.execute('CreatePrimWithDefaultXform',
            prim_type='Scope',
            prim_path=self.variant_set_path.model.get_value_as_string(),
            attributes={},
            select_new_prim=False)
            
        omni.kit.commands.execute('CreatePrimWithDefaultXform',
                prim_type='Scope',
                prim_path=f'{self.variant_set_path.model.get_value_as_string()}/{name}',
                attributes={},
                select_new_prim=False)
        
    def delete_selection_variant_set(self):
        if self.current_select_variant_name:
            self._variant_set_model.remove_set(self.current_variant_set_selections)
            paths = [Sdf.Path(f'{self.variant_set_path.model.get_value_as_string()}/{_.get_value_as_string()}') for _ in self.current_variant_set_selections]
            omni.kit.commands.execute('DeletePrims',
                paths=paths,
                destructive=False)
            if len(self._variant_set_model._children) == 0:
                omni.kit.commands.execute('DeletePrims',
                    paths=[Sdf.Path(self.variant_set_path.model.get_value_as_string())],
                    destructive=False)
                self._variant_model.clear_item()


    def delete_selection_variant(self):
        
        if self.current_select_variant_name:
            
            paths = [Sdf.Path(f"{self.variant_set_path.model.get_value_as_string()}/{self.current_select_variant_name}/{'___'.join(_.get_path().split('/'))}__num__{self._variant_model._children.index(_)}") for _ in self.current_variant_selections]
            omni.kit.commands.execute('DeletePrims',
                paths=paths,
                destructive=False)
            
            self._variant_model.remove_item(self.current_variant_selections)
