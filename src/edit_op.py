import bpy
from . props_containers import PropertiesContainer, get_properties_cache
from . enums import CustomProperty, PrimType
import time

def __setupProperly(cls):
    cls.bl_idname = "ndp.edit_{}".format(cls.prim_name).lower().replace(' ', '')
    cls.bl_label = "Edit {} (Non-Destructive)".format(cls.prim_name)
    cls.bl_description = "Edits a non-destructive {} primitive".format(cls.prim_name).lower()
    if not cls.bl_icon:
        cls.bl_icon = "MESH_{}".format(cls.prim_name.replace(' ', '').upper())

    return cls

def _set_values(props_from, props_to):
    for cp in CustomProperty:
        cp_name = cp.name
        if not hasattr(props_from, cp_name):
            continue
        if not hasattr(props_to, cp_name):
            continue
        val = getattr(props_from, cp_name)
        setattr(props_to, cp_name, val)

def _update_transform(props_transform, obj, context):
    if not props_transform._is_dirty:
        return

    obj.location[0] = props_transform.location_x
    obj.location[1] = props_transform.location_y
    obj.location[2] = props_transform.location_z
    obj.rotation_euler[0] = props_transform.rotation_x
    obj.rotation_euler[1] = props_transform.rotation_y
    obj.rotation_euler[2] = props_transform.rotation_z
    scene : bpy.types.Scene = context.scene
    scene.update()

    props_transform._is_dirty = False

def _on_transform_updated(self, context):
    self._is_dirty = True

class _PropsTransform(bpy.types.PropertyGroup):
    location_x : bpy.props.FloatProperty(
        name="X", subtype='DISTANCE', unit='LENGTH',
        update=_on_transform_updated)
    location_y : bpy.props.FloatProperty(
        name="Y", subtype='DISTANCE', unit='LENGTH',
        update=_on_transform_updated)
    location_z : bpy.props.FloatProperty(
        name="Z", subtype='DISTANCE', unit='LENGTH',
        update=_on_transform_updated)
    
    rotation_x : bpy.props.FloatProperty(
        name="X", subtype='ANGLE', unit='ROTATION',
        update=_on_transform_updated)
    rotation_y : bpy.props.FloatProperty(
        name="Y", subtype='ANGLE', unit='ROTATION',
        update=_on_transform_updated)
    rotation_z : bpy.props.FloatProperty(
        name="Z", subtype='ANGLE', unit='ROTATION',
        update=_on_transform_updated)
    
    _is_dirty = True

class _BaseOpEditPrim(bpy.types.Operator):
    bl_icon = ""
    prim_name = ""
    bl_options = {'REGISTER', 'UNDO', 'INTERNAL'}

    @classmethod
    def poll(cls, context):
        if (context.area is not None) and (context.area.type != 'VIEW_3D'):
            return False
        try:
            ndp_props = context.object.data.ndp_props
            if not ndp_props[CustomProperty.is_ndp.name]:
                return False
            return ndp_props.prim_type == cls.prim_name.upper()
        except:
            return False

    def execute(self, context):
        self._on_executing(context)
        obj = context.object
        mesh = obj.data
        _set_values(self.props, mesh.ndp_props)
        prim_name = self.props.prim_type
        cache = getattr(get_properties_cache(context), prim_name.lower())
        _set_values(self.props, cache)

        bpy.ops.ndp.update_geometry()
        _update_transform(self.props_transform, obj, context)
        # bpy.ops.ndp.update_geometry()
        return {'FINISHED'}
    
    def _on_executing(self, context):
        pass

    def _on_invoke(self, context, event):
        pass

    def invoke(self, context, event):
        bpy.ops.object.mode_set(mode='OBJECT', toggle=False)

        obj : bpy.types.Object = context.object
        mesh = obj.data
        _set_values(mesh.ndp_props, self.props)
        transform = self.props_transform
        location = obj.location
        setattr(transform, "location_x", location[0])
        setattr(transform, "location_y", location[1])
        setattr(transform, "location_z", location[2])
        rotation = obj.rotation_euler
        setattr(transform, "rotation_x", rotation[0])
        setattr(transform, "rotation_y", rotation[1])
        setattr(transform, "rotation_z", rotation[2])

        obj.show_wire = True
        obj.show_all_edges = True

        wm = context.window_manager
        if event.type == 'ESC':
            return {'CANCELLED'}

        wm : bpy.types.WindowManager = context.window_manager

        self._on_invoke(context, event)

        bpy.ops.ndp.update_geometry()

        w = wm.invoke_props_popup(self, event)

        return w
    
    def draw(self, context):
        layout = self.layout

        self._on_draw(context, layout)

        row = layout.row()
        row.prop(self.props, CustomProperty.calculate_uvs.name, text="Generate UVs")

        #for now this works inconsistently, commented it out:
        # transform = self.props_transform
        # row = layout.row()
        
        # row.label(text="Location")
        # row.prop(transform, "location_x", text="")
        # row.prop(transform, "location_y", text="")
        # row.prop(transform, "location_z", text="")

        # transform = self.props_transform
        # row = layout.row()
        # row.label(text="Rotation")
        # row.prop(transform, "rotation_x", text="")
        # row.prop(transform, "rotation_y", text="")
        # row.prop(transform, "rotation_z", text="")
    
    def _on_draw(self, context, layout):
        pass
    
    def _draw_size(self, context, layout):
        row = layout.row()
        row.label(text="Size(XYZ)")
        row.prop(self.props, CustomProperty.size_x.name, text="")
        row.prop(self.props, CustomProperty.size_y.name, text="")
        row.prop(self.props, CustomProperty.size_z.name, text="")

        
@__setupProperly
class OpEditPlane(_BaseOpEditPrim):
    prim_name = PrimType.Plane.name

@__setupProperly
class OpEditBox(_BaseOpEditPrim):
    prim_name = PrimType.Box.name
    props : bpy.props.PointerProperty(type=PropertiesContainer)
    props_transform : bpy.props.PointerProperty(type=_PropsTransform)

    def _on_draw(self, context, layout):
        obj = context.object
        layout : bpy.types.UILayout = self.layout
        props = self.props

        self._draw_size(self, context, layout)

        row = layout.row()
        row.label(text="Divisions")
        row.prop(props, CustomProperty.divisions_x.name, text="")
        row.prop(props, CustomProperty.divisions_y.name, text="")
        row.prop(props, CustomProperty.divisions_z.name, text="")
        
@__setupProperly
class OpEditCircle(_BaseOpEditPrim):
    prim_name = PrimType.Circle.name
    props : bpy.props.PointerProperty(type=PropertiesContainer)
    props_transform : bpy.props.PointerProperty(type=_PropsTransform)

    def _on_draw(self, context, layout):
        obj = context.object
        layout : bpy.types.UILayout = self.layout
        props = self.props

        row = layout.row()
        row.label(text="Vertices")
        row.prop(props, CustomProperty.divisions_x.name, text="")

        size_policy = props.size_policy
        if props.size_policy == 'AXIS_SCALE':
            self._draw_size(context, layout)
        elif props.size_policy == 'EXTERIOR_INTERIOR':
            row = layout.row()
            row.label("Radius")
            row.props(self, "radius_a")
        
@__setupProperly
class OpEditUvSphere(_BaseOpEditPrim):
    prim_name = PrimType.UvSphere.name
        
@__setupProperly
class OpEditIcoSphere(_BaseOpEditPrim):
    prim_name = PrimType.IcoSphere.name
        
@__setupProperly
class OpEditCylinder(_BaseOpEditPrim):
    prim_name = PrimType.Cylinder.name
        
@__setupProperly
class OpEditCone(_BaseOpEditPrim):
    prim_name = PrimType.Cone.name


CLASSES = [
    _PropsTransform,

    OpEditPlane,
    OpEditBox,
    OpEditCircle,
    OpEditUvSphere,
    OpEditIcoSphere,
    OpEditCylinder,
    OpEditCone
]