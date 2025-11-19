from rest_framework.serializers import ModelSerializer
from rest_framework import serializers
from django.contrib.auth.models import User  , Group , Permission 
from django.contrib.contenttypes.models import ContentType
from .models import Perfiluser

class UserSerializers(ModelSerializer): 
    password = serializers.CharField(write_only=True, required=False)
    class Meta:
        model = User
        fields = '__all__'
        extra_kwargs = {
            'password': {'write_only': True}
        }
    
    def create(self, validated_data):
        """Crear usuario con contraseña hasheada correctamente"""
        password = validated_data.pop('password', None)
        user = User.objects.create(**validated_data)
        
        if password:
            user.set_password(password)  # ← Hashea la contraseña
            user.save()
        
        return user
    def update(self, instance, validated_data):
        """Actualizar usuario manteniendo contraseña hasheada"""
        password = validated_data.pop('password', None)
        
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        
        if password:
            instance.set_password(password)  # ← Hashea la contraseña
        
        instance.save()
        return instance
class GroupSerializers(ModelSerializer):
    id = serializers.IntegerField(read_only=True)
    nombre = serializers.CharField(source='name', required=False, allow_blank=True, max_length=150)
    permisos = serializers.PrimaryKeyRelatedField(
        source='permissions',
        many=True,
        queryset=Permission.objects.all(),
        required=False
    )
    descripcion = serializers.SerializerMethodField()
    empresa_id = serializers.IntegerField(write_only=True, required=False)
    
    class Meta:
        model = Group
        fields = ['id', 'nombre', 'permisos', 'descripcion', 'empresa_id']
    
    def to_representation(self, instance):
        """Personalizar la representación para incluir descripción y mapear name -> nombre"""
        data = super().to_representation(instance)
        # Asegurar que el nombre del grupo se devuelve en 'nombre'
        if 'nombre' not in data or not data['nombre']:
            data['nombre'] = instance.name
        # Obtener descripción del modelo relacionado
        try:
            desc = instance.descripcion_obj.descripcion
            data['descripcion'] = desc
        except:
            data['descripcion'] = None
        return data
    
    def get_descripcion(self, obj):
        """Obtener descripción del grupo"""
        try:
            return obj.descripcion_obj.descripcion
        except:
            return None
        
    def create(self, validated_data):
        permissions_data = validated_data.pop('permissions', [])
        descripcion = self.initial_data.get('descripcion', '')
        empresa_id = self.initial_data.get('empresa_id', None)
        
        # Soportar tanto 'nombre' como 'name' en el input
        name = self.initial_data.get('nombre', '') or self.initial_data.get('name', '')
        name = name.strip() if name else ''
        
        # Si name viene vacío o no viene, generar uno de la descripción
        if not name:
            name = descripcion[:150].strip() if descripcion else f'Grupo {Group.objects.count() + 1}'
        
        print(f"📝 Creando grupo con nombre: '{name}', descripcion: '{descripcion}', empresa_id: {empresa_id}")
        
        # Crear el grupo con el nombre
        group = Group.objects.create(name=name)
        print(f"✅ Grupo creado con ID: {group.id}")
        
        # Asignar permisos
        if permissions_data:
            group.permissions.set(permissions_data)
            print(f"✅ Permisos asignados: {len(permissions_data)}")
        
        # Crear descripción del grupo con empresa
        from app_User.models import GroupDescripcion
        from app_Empresa.models import Empresa
        try:
            empresa = None
            if empresa_id:
                try:
                    empresa = Empresa.objects.get(id=empresa_id)
                    print(f"✅ Empresa encontrada: {empresa.razon_social}")
                except Empresa.DoesNotExist:
                    print(f"⚠️ Empresa con ID {empresa_id} no encontrada")
            
            desc_obj = GroupDescripcion.objects.create(
                group=group, 
                descripcion=descripcion, 
                empresa=empresa
            )
            print(f"✅ GroupDescripcion creado con ID: {desc_obj.id}")
            
        except Exception as e:
            import traceback
            print(f"❌ Error creando GroupDescripcion: {e}")
            traceback.print_exc()
            # Si falla la creación de la descripción, eliminar el grupo para mantener consistencia
            group.delete()
            raise serializers.ValidationError(f"Error al crear descripción del grupo: {str(e)}")
        
        return group
    
    def update(self, instance, validated_data):
        permissions_data = validated_data.pop('permissions', None)
        # Soportar tanto 'name' (from source='name') como 'nombre'
        name = validated_data.get('name', '').strip() if validated_data.get('name') else ''
        
        # Actualizar nombre si viene
        if name:
            instance.name = name
        
        instance.save()
        
        # Actualizar permisos
        if permissions_data is not None:
            instance.permissions.set(permissions_data)
        
        # Actualizar descripción
        descripcion = self.initial_data.get('descripcion', None)
        if descripcion is not None:
            try:
                desc_obj = instance.descripcion_obj
                desc_obj.descripcion = descripcion
                desc_obj.save()
            except:
                from app_User.models import GroupDescripcion
                GroupDescripcion.objects.create(group=instance, descripcion=descripcion)
        
        return instance

class PermissionSerializers(ModelSerializer):
    class Meta:
        model = Permission
        fields = '__all__'


class ContentTypeSerializers(ModelSerializer):
    class Meta:
        model = ContentType
        fields = '__all__'


class AdminLogSerializer(serializers.Serializer):
    """Serializer de solo-lectura para mostrar los campos del LogEntry
    en el formato solicitado: usuario, tipo_contenido, objeto, accion (texto), mensaje y action_time.
    """
    id = serializers.IntegerField(read_only=True)
    usuario = serializers.CharField(source='user.username', read_only=True, allow_null=True)
    tipo_contenido = serializers.CharField(source='content_type.model', read_only=True, allow_null=True)
    objeto = serializers.CharField(source='object_repr', read_only=True, allow_null=True)
    accion = serializers.SerializerMethodField()
    mensaje = serializers.CharField(source='change_message', read_only=True, allow_null=True)
    action_time = serializers.DateTimeField(read_only=True)

    def get_accion(self, obj):
        """Mapea action_flag a un nombre legible en español."""
        mapping = {
            1: 'Adición',
            2: 'Cambio',
            3: 'Eliminación',
        }
        return mapping.get(getattr(obj, 'action_flag', None), getattr(obj, 'action_flag', None))
    
class PerfilUserSerializer(ModelSerializer):
    class Meta:
        model = Perfiluser
        fields = '__all__'


class UserGroupSerializer(serializers.Serializer):
    """
    Serializer para la tabla intermedia auth_user_groups (relación muchos a muchos)
    Permite asignar/desasignar usuarios a grupos
    """
    id = serializers.IntegerField(read_only=True)
    user_id = serializers.IntegerField(required=True)
    group_id = serializers.IntegerField(required=True)
    
    # Campos adicionales para mostrar información completa (read only)
    username = serializers.CharField(source='user.username', read_only=True)
    user_email = serializers.CharField(source='user.email', read_only=True)
    group_name = serializers.CharField(source='group.name', read_only=True)
    
    def validate_user_id(self, value):
        """Validar que el usuario existe"""
        if not User.objects.filter(id=value).exists():
            raise serializers.ValidationError(f"Usuario con ID {value} no existe")
        return value
    
    def validate_group_id(self, value):
        """Validar que el grupo existe"""
        if not Group.objects.filter(id=value).exists():
            raise serializers.ValidationError(f"Grupo con ID {value} no existe")
        return value
    
    def validate(self, data):
        """Validar que la combinación usuario-grupo no exista ya"""
        if hasattr(self, 'instance') and self.instance:
            # Es una actualización, permitir
            return data
            
        user_id = data.get('user_id')
        group_id = data.get('group_id')
        
        try:
            user = User.objects.get(id=user_id)
            if user.groups.filter(id=group_id).exists():
                raise serializers.ValidationError(
                    f"El usuario {user.username} ya pertenece al grupo con ID {group_id}"
                )
        except User.DoesNotExist:
            pass
            
        return data
    
    def create(self, validated_data):
        """Asignar usuario a grupo"""
        user_id = validated_data['user_id']
        group_id = validated_data['group_id']
        
        user = User.objects.get(id=user_id)
        group = Group.objects.get(id=group_id)
        
        # Agregar el usuario al grupo
        user.groups.add(group)
        
        # Retornar un objeto simulado con la información
        return {
            'id': f"{user_id}_{group_id}",
            'user': user,
            'group': group,
            'user_id': user_id,
            'group_id': group_id,
        }
    
    def to_representation(self, instance):
        """Personalizar la representación de salida"""
        if isinstance(instance, dict):
            # Cuando viene del create
            return {
                'id': instance['id'],
                'user_id': instance['user_id'],
                'group_id': instance['group_id'],
                'username': instance['user'].username,
                'user_email': instance['user'].email,
                'group_name': instance['group'].name,
            }
        else:
            # Cuando viene de una query normal
            return super().to_representation(instance)
