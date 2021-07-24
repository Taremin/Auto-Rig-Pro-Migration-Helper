import bpy
import json
import os
from pathlib import Path


bl_info = {
    'name': 'Auto-Rig Pro Migration Helper',
    'category': '3D View',
    'author': 'Taremin',
    'location': 'View 3D > UI > ARP',
    'description': "Auto-Rig Pro migration helper",
    'version': (0, 0, 1),
    'blender': (2, 80, 0),
    'wiki_url': '',
    'tracker_url': '',
    'warning': '',
}


def get_active(context):
    return context.view_layer.objects.active


def set_active(context, value):
    context.view_layer.objects.active = value


def select(obj, value):
    obj.select_set(value)


def get_object(name):
    return bpy.data.objects[name]


class ARPMH_OT_Migrate(bpy.types.Operator):
    bl_idname = "arpmh.migrate"
    bl_label = "migrate armature"
    bl_options = {'UNDO'}

    # 子孫にHumanoidボーンがなければ追加可能
    def is_addable_bone(self, context, bone, mapping):
        result = True

        for child in bone.children:
            if child.name in mapping:
                return False
            else:
                result = self.is_addable_bone(context, child, mapping)

        return result

    # ボーンを子孫までまとめて移植
    def copy_bone_recursive(self, context, src_bones, dst_bones, parent, child, depth=0):
        dst_child = dst_bones.new(child.name)
        dst_child.parent = parent
        dst_child.head = child.head.copy()
        dst_child.tail = child.tail.copy()
        dst_child.use_connect = child.use_connect

        dst_child["custom_bone"] = 1.0

        for src_child in child.children:
            self.copy_bone_recursive(
                context, src_bones, dst_bones, dst_child, src_child, depth+1)

    def get_edit_bones(self, context, armature):
        bpy.ops.object.mode_set(mode='OBJECT')
        set_active(context, armature)
        bpy.ops.object.mode_set(mode='EDIT')

        dict = {}
        for bone in armature.data.edit_bones:
            dict[bone.name] = {
                "head": bone.head.copy(),
                "tail": bone.tail.copy(),
            }

        return dict

    def copy_bone_position(self, context, src_armature, dst_armature, mapping):
        bpy.ops.object.mode_set(mode='OBJECT')
        bpy.ops.object.select_all(action='DESELECT')
        select(src_armature, True)
        set_active(context, dst_armature)
        bpy.ops.object.mode_set(mode='EDIT')

        dst_bones = dst_armature.data.edit_bones
        src_matrix = src_armature.matrix_world.inverted()
        dst_matrix = dst_armature.matrix_world

        for bone in src_armature.data.edit_bones:
            if bone.name not in mapping:
                continue

            dst_name = mapping[bone.name]
            name_parts = dst_name.split('.')
            if name_parts[-1] == 'r':
                continue
            if dst_name in dst_bones:
                dst_bone = dst_bones[dst_name]
                dst_bone.head = dst_matrix @ (src_matrix @ bone.head)
                dst_bone.tail = dst_matrix @ (src_matrix @ bone.tail)
            else:
                print("no match:", dst_name)

        return

    # 再帰的にアーマチュアをたどっていき、Humanoidボーン以外を追加していく
    def walkdown(self, context, bonename, src_armature, dst_armature, mapping, mapping2, depth=0):
        bpy.ops.object.mode_set(mode='OBJECT')
        bpy.ops.object.select_all(action='DESELECT')
        select(src_armature, True)
        set_active(context, dst_armature)
        bpy.ops.object.mode_set(mode='EDIT')

        src_bones = src_armature.data.edit_bones
        dst_bones = dst_armature.data.edit_bones
        bone = src_bones[bonename]
        if isinstance(bone, bpy.types.Bone):
            bone = src_bones[bone.name]

        children = [b.name for b in bone.children]
        for child_name in children:
            bone = src_bones[bonename]
            child = src_bones[child_name]
            if child.name in mapping:
                self.walkdown(context, child.name, src_armature,
                              dst_armature, mapping, mapping2, depth + 1)
            else:
                if self.is_addable_bone(context, child, mapping):
                    self.copy_bone_recursive(
                        context, src_bones, dst_bones, dst_bones[mapping2[bone.name]], child)

    def get_armature_objects(self, context, armature):
        objects = []

        for obj in context.view_layer.objects:
            for mod in obj.modifiers:
                if mod.type != 'ARMATURE':
                    continue
                if mod.object == armature:
                    objects.append(obj)
                    break

        return objects

    def execute(self, context):
        props = context.scene.taremin_arpmh

        reference_default_path = bpy.path.abspath(
            os.path.join(os.path.dirname(__file__), "./ARP_ReferenceBones.json"))
        export_default_path = bpy.path.abspath(
            os.path.join(os.path.dirname(__file__), "./ARP_ExportBones.json"))
        reference_path = {
            'DEFAULT': reference_default_path,
            'PATH': bpy.path.abspath(props.arp_humanoid),
        }[props.arp_humanoid_type]
        export_path = {
            'DEFAULT': export_default_path,
            'PATH': bpy.path.abspath(props.arp_export),
        }[props.arp_humanoid_type]

        armature = props.armature
        humanoid = json.load(open(bpy.path.abspath(props.humanoid)))
        arp_humanoid = json.load(open(reference_path))
        vertex_weight_humanoid = json.load(open(export_path))
        humanoid_mapping = self.create_convert_dict(humanoid, arp_humanoid)
        vertex_group_dict = self.create_convert_dict(
            humanoid, vertex_weight_humanoid)

        # create dummy markers
        try:
            bpy.ops.id.cancel_and_delete_markers()
        except:
            pass

        # get armature objects
        objs = self.get_armature_objects(context, armature)

        # set active
        for obj in objs:
            if obj.visible_get() and not obj.hide_get():
                set_active(context, obj)
                break

        # Set Target Meshes
        bpy.ops.object.mode_set(mode='OBJECT')
        bpy.ops.object.select_all(action='DESELECT')

        if len(objs) == 0:
            self.report(
                {'ERROR_INVALID_CONTEXT'},
                '対象のアーマチュアを使用しているオブジェクトが1つもありません'
            )
            return {'CANCELLED'}
        context.scene.arp_body_name = get_active(context).name

        for obj in objs:
            select(obj, True)

        bpy.ops.id.get_selected_objects()

        # Add markers
        body_parts = ("chin", "neck", "shoulder", "hand", "root", "foot")
        top_to_bottom = list(body_parts)
        top_to_bottom.reverse()

        marker_to_humanoid = {
            "chin": "Head",
            "neck": "Neck",
            "shoulder": "Shoulder",
            "hand": "Hand",
            "root": "Hips",
            "foot": "Foot",
        }

        bpy.ops.object.mode_set(mode='OBJECT')
        body = get_object('body_temp')
        set_active(context, body)
        for body_part in body_parts:
            bpy.ops.id.add_marker(body_part=body_part,
                                  body_height=body.dimensions[2])

        # fix marker position
        set_active(context, armature)
        armature.hide_set(False)
        bpy.ops.object.mode_set(mode='EDIT')
        bones = props.armature.data.edit_bones

        for child in get_object("arp_markers").children:
            marker_name = child.name.split("_")
            if marker_name[-1] == "sym":
                continue

            matrix = armature.matrix_world.inverted()
            if marker_name[0] in ("shoulder", "hand", "foot"):
                bone = bones[humanoid[
                    "Left" + marker_to_humanoid[marker_name[0]]
                ]]
                child.location = bone.head @ matrix
            else:
                bone = bones[humanoid[marker_to_humanoid[marker_name[0]]]]
                child.location = bone.head @ matrix

        # create ref bones
        bpy.ops.id.go_detect()

        # apply transform
        bpy.ops.object.mode_set(mode='OBJECT')
        new_armature = get_active(context)
        bpy.ops.object.transform_apply(
            location=True, rotation=True, scale=True)

        # fix bone positions
        bpy.ops.object.mode_set(mode='EDIT')
        self.copy_bone_position(
            context, armature, new_armature, humanoid_mapping)

        # match to rig
        bpy.ops.arp.match_to_rig()

        # add extra bones
        self.walkdown(
            context, humanoid['Hips'], armature, new_armature, humanoid_mapping, vertex_group_dict)

        # replace objects
        for obj in objs:
            # armature modifier target
            for mod in obj.modifiers:
                if mod.type != 'ARMATURE':
                    continue
                mod.object = new_armature

            # vertex group
            for group in obj.vertex_groups:
                if group.name in vertex_group_dict:
                    group.name = vertex_group_dict[group.name]

        bpy.ops.object.mode_set(mode='OBJECT')
        bpy.ops.object.select_all(action='DESELECT')

        # remove old armature
        if props.remove_old_armature:
            set_active(context, armature)
            select(armature, True)

            bpy.ops.object.delete(use_global=True)

        set_active(context, new_armature)
        select(new_armature, True)

        return {'FINISHED'}

    def create_convert_dict(self, from_dict, to_dict):
        convert_dict = {}
        for (key, value) in from_dict.items():
            if from_dict[key] is not None and to_dict[key] is not None:
                convert_dict[value] = to_dict[key]

        return convert_dict


class ARPMH_Props(bpy.types.PropertyGroup):
    humanoid: bpy.props.StringProperty(
        name="Base Humanoid", subtype='FILE_PATH', default="")
    arp_humanoid_type: bpy.props.EnumProperty(
        name="Auto-Rig Pro Humanoid", items=[
            ("DEFAULT", "標準", "", 0),
            ("PATH", "パス指定", "", 1),
        ])
    arp_humanoid: bpy.props.StringProperty(
        name="AutoRig Pro Humanoid", subtype='FILE_PATH', default="")
    arp_export_type: bpy.props.EnumProperty(
        name="Auto-Rig Pro Export", items=[
            ("DEFAULT", "標準", "", 0),
            ("PATH", "パス指定", "", 1),
        ])
    arp_export: bpy.props.StringProperty(
        name="AutoRig Pro Humanoid", subtype='FILE_PATH', default="")
    armature: bpy.props.PointerProperty(
        type=bpy.types.Object, name="Base Armature",
        poll=lambda self, object: object.type == 'ARMATURE')
    remove_old_armature: bpy.props.BoolProperty(
        name="Remove Old Armature",
        default=True
    )


class ARPMH_PT_Panel(bpy.types.Panel):
    bl_space_type = 'VIEW_3D'
    bl_region_type = 'UI'
    bl_category = "ARP"
    bl_label = "Auto-Rig Pro Migration Helper"

    def draw(self, context):
        props = context.scene.taremin_arpmh
        layout = self.layout
        layout.prop(props, 'humanoid')
        layout.prop(props, 'arp_humanoid_type')
        if props.arp_humanoid_type == 'PATH':
            box = layout.box()
            box.prop(props, 'arp_humanoid')
        layout.prop(props, 'arp_export_type')
        if props.arp_export_type == 'PATH':
            box = layout.box()
            box.prop(props, 'arp_export')
        layout.prop(props, 'armature')
        layout.prop(props, 'remove_old_armature')
        layout.operator(ARPMH_OT_Migrate.bl_idname)


# クラスの登録
classes = [
    # このファイル内のBlenderクラス
    ARPMH_OT_Migrate,
    ARPMH_Props,
    ARPMH_PT_Panel,
]


def register():
    for value in classes:
        retry = 0
        while True:
            try:
                bpy.utils.register_class(value)
                break
            except ValueError:
                bpy.utils.unregister_class(value)
                retry += 1
                if retry > 1:
                    break

    bpy.types.Scene.taremin_arpmh = bpy.props.PointerProperty(
        type=ARPMH_Props)


def unregister():
    for value in classes:
        try:
            bpy.utils.unregister_class(value)
        except RuntimeError:
            pass

    del bpy.types.Scene.taremin_arpmh
    Path(__file__).touch()


if __name__ == '__main__':
    register()
