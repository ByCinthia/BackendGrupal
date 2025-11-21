from django.contrib.auth.models import User , Group , Permission
from django.contrib.contenttypes.models import ContentType
from django.contrib.admin.models import LogEntry
from .serializers import (
    UserSerializers , GroupSerializers , PermissionSerializers , ContentTypeSerializers,
    AdminLogSerializer, PerfilUserSerializer, UserGroupSerializer
)
from rest_framework import viewsets , permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.parsers import JSONParser, FormParser, MultiPartParser
from rest_framework.authtoken.models import Token
from rest_framework.exceptions import ValidationError
from app_User.models import Perfiluser
from app_Empresa.models import Empresa
from .models import Perfiluser


# drf-spectacular is optional; if not installed, provide a no-op decorator.
try:
    from drf_spectacular.utils import extend_schema
except Exception:
    def extend_schema(*args, **kwargs):
        def _decorator(obj):
            return obj
        return _decorator


class UserViewSer(viewsets.ModelViewSet):
    serializer_class = UserSerializers
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """Filtrar usuarios por empresa del usuario autenticado (multitenancy)"""
        try:
            perfil = Perfiluser.objects.get(usuario=self.request.user)
            # Retornar solo los usuarios de la empresa del usuario
            return User.objects.filter(
                perfiluser__empresa=perfil.empresa
            ).order_by("id")
        except Perfiluser.DoesNotExist:
            # Si no tiene perfil, retornar vacío
            return User.objects.none()

    def perform_create(self, serializer):
        """Auto-asignar la empresa al crear usuario"""
        try:
            perfil = Perfiluser.objects.get(usuario=self.request.user)
            serializer.save(empresa=perfil.empresa)
        except Perfiluser.DoesNotExist:
            raise ValidationError("Usuario no tiene perfil asociado")


class GroupViewSet(viewsets.ModelViewSet):
    serializer_class = GroupSerializers
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        """Filtrar grupos por empresa del usuario autenticado (multitenancy)"""
        try:
            perfil = Perfiluser.objects.get(usuario=self.request.user)
            # Retornar solo los grupos de la empresa del usuario
            return Group.objects.filter(
                descripcion_obj__empresa=perfil.empresa
            ).order_by("id")
        except Perfiluser.DoesNotExist:
            # Si no tiene perfil, retornar vacío
            return Group.objects.none()

    def create(self, request, *args, **kwargs):
        """Crear grupo asociado a la empresa del usuario autenticado"""
        try:
            # Verificar que el usuario tiene perfil
            perfil = Perfiluser.objects.get(usuario=request.user)
            
            # Hacer una copia mutable del request.data si es necesario
            if hasattr(request.data, '_mutable'):
                request.data._mutable = True
            
            # Agregar la empresa al request data
            request.data['empresa_id'] = perfil.empresa.id
            
            if hasattr(request.data, '_mutable'):
                request.data._mutable = False
            
            return super().create(request, *args, **kwargs)
        except Perfiluser.DoesNotExist:
            return Response({"error": "Usuario no tiene perfil asociado"}, status=status.HTTP_403_FORBIDDEN)
        except Exception as e:
            import traceback
            print(f"❌ Error al crear grupo: {str(e)}")
            traceback.print_exc()
            return Response({"error": f"Error al crear grupo: {str(e)}"}, status=status.HTTP_400_BAD_REQUEST)

class PermissionViewSer(viewsets.ModelViewSet):
    queryset = Permission.objects.all()
    serializer_class = PermissionSerializers
    permission_classes = [permissions.IsAuthenticated]

class ContentTypeViewSer(viewsets.ModelViewSet):
    queryset = ContentType.objects.all()
    serializer_class = ContentTypeSerializers
    permission_classes = [permissions.IsAuthenticated]


class AdminLogViewSet(viewsets.ReadOnlyModelViewSet):
    """API read-only que expone las entradas del log de administrador en el formato solicitado.

    GET /api/User/admin-log/  -> lista paginada por defecto (si DRF lo aplica)
    """
    queryset = LogEntry.objects.select_related('user', 'content_type').order_by('-action_time')
    serializer_class = AdminLogSerializer
    permission_classes = [permissions.AllowAny]


class CreateUserView(APIView):
    """
    API para crear usuarios normales dentro de la misma empresa del administrador autenticado.
    Solo un administrador (is_staff=True) puede crear usuarios para su propia empresa.
    """
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [JSONParser, FormParser, MultiPartParser]
    
    def post(self, request):
        # Solo administradores pueden crear usuarios normales
        if not request.user.is_authenticated or not request.user.is_staff:
            return Response({'error': 'No autorizado'}, status=status.HTTP_403_FORBIDDEN)

        # Obtener empresa del admin (perfil)
        try:
            admin_perfil = Perfiluser.objects.get(usuario=request.user)
        except Perfiluser.DoesNotExist:
            return Response({'error': 'Administrador no tiene perfil asociado'}, status=status.HTTP_403_FORBIDDEN)

        # Obtener datos del request
        username = request.data.get('username')
        password = request.data.get('password')
        email = request.data.get('email')
        first_name = request.data.get('first_name', '')
        last_name = request.data.get('last_name', '')
        # Forzamos que la empresa sea la del admin, o puede recibirse para validación
        empresa_id = request.data.get('empresa_id', admin_perfil.empresa.id)
        imagen_url = request.data.get('imagen_url', '')
        
        # Obtener archivo de imagen si viene
        imagen_perfil_file = request.FILES.get('imagen_perfil', None)

        # Validaciones básicas
        if not all([username, password, email]):
            return Response({'error': 'username, password y email son requeridos'}, status=status.HTTP_400_BAD_REQUEST)

        # Verificar que la empresa solicitada coincide con la del admin
        if int(empresa_id) != admin_perfil.empresa.id:
            return Response({'error': 'Solo puede crear usuarios para su propia empresa'}, status=status.HTTP_403_FORBIDDEN)

        # Verificar que el username y email no existan
        if User.objects.filter(username=username).exists():
            return Response({'error': 'El username ya existe'}, status=status.HTTP_400_BAD_REQUEST)

        if User.objects.filter(email=email).exists():
            return Response({'error': 'El email ya está registrado'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            # Si viene una imagen, subirla a S3
            if imagen_perfil_file:
                from app_Empresa.s3_utils import upload_user_avatar
                print(f"📤 Subiendo imagen de perfil a S3: {imagen_perfil_file.name}")
                imagen_url = upload_user_avatar(imagen_perfil_file)
                if imagen_url:
                    print(f"✅ Imagen subida exitosamente: {imagen_url}")
                else:
                    print("⚠️ No se pudo subir la imagen a S3, se continuará sin imagen")
                    imagen_url = ''
            
            # Crear usuario normal (no admin)
            user = User.objects.create_user(
                username=username,
                password=password,
                email=email,
                first_name=first_name,
                last_name=last_name,
            )

            # Crear perfil de usuario vinculado a la misma empresa del admin
            perfil_user = Perfiluser.objects.create(empresa=admin_perfil.empresa, usuario=user, imagen_url=imagen_url)

            # Crear token
            token, created = Token.objects.get_or_create(user=user)

            response_data = {
                'message': 'Usuario creado exitosamente',
                'user': {
                    'id': user.id,
                    'username': user.username,
                    'email': user.email,
                    'first_name': user.first_name,
                    'last_name': user.last_name,
                    'is_staff': user.is_staff,
                    'is_superuser': user.is_superuser,
                    'empresa_id': admin_perfil.empresa.id,
                    'empresa_nombre': admin_perfil.empresa.razon_social,
                    'imagen_url': imagen_url,
                },
                'token': token.key
            }

            return Response(response_data, status=status.HTTP_201_CREATED)

        except Exception as e:
            return Response({'error': f'Error al crear usuario: {str(e)}'}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

class PerfilUserViewSet(viewsets.ModelViewSet):
    queryset = Perfiluser.objects.all()
    serializer_class = PerfilUserSerializer
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [JSONParser, FormParser, MultiPartParser]
    
    def update(self, request, *args, **kwargs):
        """Override update para manejar subida de avatar a S3"""
        from app_Empresa.s3_utils import upload_user_avatar
        
        instance = self.get_object()
        
        # Si viene una imagen de perfil, subirla a S3
        imagen_perfil_file = request.FILES.get('imagen_perfil', None) or request.FILES.get('imagen_url', None)
        if imagen_perfil_file:
            print(f"🖼️ [PerfilUserViewSet] Subiendo avatar: {imagen_perfil_file.name}")
            avatar_url = upload_user_avatar(imagen_perfil_file)
            if avatar_url:
                print(f"✅ [PerfilUserViewSet] Avatar subido: {avatar_url}")
                # Actualizar el campo directamente en la instancia
                instance.imagen_url = avatar_url
                instance.save()
                print(f"💾 [PerfilUserViewSet] Avatar guardado en BD: {avatar_url}")
        
        return super().update(request, *args, **kwargs)


class MeView(APIView):
    """
    API para obtener información completa del usuario autenticado:
    - Datos del usuario (id, username, email, etc.)
    - Si es staff y superuser
    - Grupos a los que pertenece (id y nombre de cada grupo)
    - Información de la empresa asociada
    - Perfil del usuario
    
    GET /api/User/me/
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        user = request.user
        
        # Obtener perfil y empresa
        try:
            perfil = Perfiluser.objects.get(usuario=user)
            empresa_data = {
                'id': perfil.empresa.id,
                'razon_social': perfil.empresa.razon_social,
                'nombre_comercial': perfil.empresa.nombre_comercial,
                'email_contacto': perfil.empresa.email_contacto,
            }
            perfil_data = {
                'id': perfil.id,
                'imagen_url': perfil.imagen_url,
            }
        except Perfiluser.DoesNotExist:
            empresa_data = None
            perfil_data = None
        
        # Obtener grupos del usuario
        grupos = []
        for group in user.groups.all():
            grupo_info = {
                'id': group.id,
                'nombre': group.name,
            }
            
            # Intentar obtener la descripción del grupo
            try:
                grupo_info['descripcion'] = group.descripcion_obj.descripcion
            except:
                grupo_info['descripcion'] = None
            
            grupos.append(grupo_info)
        
        # Construir respuesta completa
        response_data = {
            'id': user.id,
            'username': user.username,
            'email': user.email,
            'first_name': user.first_name,
            'last_name': user.last_name,
            'nombre_completo': f"{user.first_name} {user.last_name}".strip(),
            'is_staff': user.is_staff,
            'is_superuser': user.is_superuser,
            'is_active': user.is_active,
            'date_joined': user.date_joined,
            'grupos': grupos,
            'total_grupos': len(grupos),
            'empresa': empresa_data,
            'perfil': perfil_data,
        }
        
        return Response(response_data, status=status.HTTP_200_OK)


class UserGroupView(APIView):
    """
    API CRUD para gestionar la relación entre usuarios y grupos (auth_user_groups)
    
    GET /api/User/user-groups/ - Lista todas las relaciones usuario-grupo
    POST /api/User/user-groups/ - Asignar un usuario a un grupo
    DELETE /api/User/user-groups/ - Quitar un usuario de un grupo
    """
    permission_classes = [permissions.IsAuthenticated]
    
    def get(self, request):
        """Listar todas las relaciones usuario-grupo (filtradas por empresa en multitenancy)"""
        try:
            # Filtrar por empresa del usuario autenticado
            perfil = Perfiluser.objects.get(usuario=request.user)
            
            # Obtener todos los usuarios de la misma empresa
            usuarios_empresa = User.objects.filter(perfiluser__empresa=perfil.empresa)
            
            # Construir lista de relaciones
            relaciones = []
            for user in usuarios_empresa:
                for group in user.groups.all():
                    relaciones.append({
                        'id': f"{user.id}_{group.id}",
                        'user_id': user.id,
                        'group_id': group.id,
                        'username': user.username,
                        'user_email': user.email,
                        'group_name': group.name,
                    })
            
            return Response(relaciones, status=status.HTTP_200_OK)
            
        except Perfiluser.DoesNotExist:
            return Response({'error': 'Usuario no tiene perfil asociado'}, status=status.HTTP_403_FORBIDDEN)
    
    def post(self, request):
        """Asignar un usuario a un grupo"""
        serializer = UserGroupSerializer(data=request.data)
        
        if serializer.is_valid():
            try:
                # Validar que el usuario pertenece a la misma empresa (multitenancy)
                perfil_request = Perfiluser.objects.get(usuario=request.user)
                user_id = serializer.validated_data['user_id']
                
                try:
                    perfil_target = Perfiluser.objects.get(usuario_id=user_id)
                    if perfil_target.empresa.id != perfil_request.empresa.id:
                        return Response(
                            {'error': 'No puedes asignar grupos a usuarios de otras empresas'}, 
                            status=status.HTTP_403_FORBIDDEN
                        )
                except Perfiluser.DoesNotExist:
                    return Response(
                        {'error': 'El usuario objetivo no tiene perfil asociado'}, 
                        status=status.HTTP_400_BAD_REQUEST
                    )
                
                # Crear la relación
                result = serializer.save()
                return Response(
                    UserGroupSerializer(result).data, 
                    status=status.HTTP_201_CREATED
                )
                
            except Exception as e:
                return Response(
                    {'error': f'Error al asignar usuario a grupo: {str(e)}'}, 
                    status=status.HTTP_500_INTERNAL_SERVER_ERROR
                )
        
        return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)
    
    def delete(self, request):
        """Quitar un usuario de un grupo"""
        user_id = request.data.get('user_id')
        group_id = request.data.get('group_id')
        
        if not user_id or not group_id:
            return Response(
                {'error': 'user_id y group_id son requeridos'}, 
                status=status.HTTP_400_BAD_REQUEST
            )
        
        try:
            # Validar que el usuario pertenece a la misma empresa (multitenancy)
            perfil_request = Perfiluser.objects.get(usuario=request.user)
            
            try:
                perfil_target = Perfiluser.objects.get(usuario_id=user_id)
                if perfil_target.empresa.id != perfil_request.empresa.id:
                    return Response(
                        {'error': 'No puedes modificar grupos de usuarios de otras empresas'}, 
                        status=status.HTTP_403_FORBIDDEN
                    )
            except Perfiluser.DoesNotExist:
                return Response(
                    {'error': 'El usuario objetivo no tiene perfil asociado'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Obtener usuario y grupo
            try:
                user = User.objects.get(id=user_id)
                group = Group.objects.get(id=group_id)
            except User.DoesNotExist:
                return Response({'error': f'Usuario con ID {user_id} no existe'}, status=status.HTTP_404_NOT_FOUND)
            except Group.DoesNotExist:
                return Response({'error': f'Grupo con ID {group_id} no existe'}, status=status.HTTP_404_NOT_FOUND)
            
            # Verificar que el usuario está en el grupo
            if not user.groups.filter(id=group_id).exists():
                return Response(
                    {'error': f'El usuario {user.username} no pertenece al grupo {group.name}'}, 
                    status=status.HTTP_400_BAD_REQUEST
                )
            
            # Quitar el usuario del grupo
            user.groups.remove(group)
            
            return Response(
                {'message': f'Usuario {user.username} removido del grupo {group.name} exitosamente'}, 
                status=status.HTTP_200_OK
            )
            
        except Perfiluser.DoesNotExist:
            return Response({'error': 'Usuario no tiene perfil asociado'}, status=status.HTTP_403_FORBIDDEN)
        except Exception as e:
            return Response(
                {'error': f'Error al remover usuario del grupo: {str(e)}'}, 
                status=status.HTTP_500_INTERNAL_SERVER_ERROR
            )