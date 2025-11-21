from .serializers import ClienteSerializer, DomicilioSerializer, TrabajoSerializer, DocumentacionSerializer
from .models import Cliente, Domicilio, Trabajo, Documentacion
from app_User.models import Perfiluser
from rest_framework import viewsets, permissions, status 
from rest_framework.response import Response
from rest_framework.parsers import JSONParser, FormParser, MultiPartParser


class ClienteViewSet(viewsets.ModelViewSet):
    serializer_class = ClienteSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        try:
            perfil = Perfiluser.objects.get(usuario=user)
            return Cliente.objects.filter(empresa=perfil.empresa)
        except Perfiluser.DoesNotExist:
            return Cliente.objects.none()

    def perform_create(self, serializer):
        try:
            perfil = Perfiluser.objects.get(usuario=self.request.user)
            serializer.save(empresa=perfil.empresa)
        except Perfiluser.DoesNotExist:
            pass


class DocumentacionViewSet(viewsets.ModelViewSet):
    serializer_class = DocumentacionSerializer
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [JSONParser, FormParser, MultiPartParser]

    def get_queryset(self):
        user = self.request.user
        try:
            perfil = Perfiluser.objects.get(usuario=user)
            return Documentacion.objects.filter(empresa=perfil.empresa)
        except Perfiluser.DoesNotExist:
            return Documentacion.objects.none()

    def create(self, request, *args, **kwargs):
        try:
            perfil = Perfiluser.objects.get(usuario=request.user)
            
            # Obtener archivo de documento si viene
            documento_file = request.FILES.get('documento_file', None)
            
            # Si viene archivo, subirlo a S3
            documento_url = request.data.get('documento_url', '')
            if documento_file:
                from app_Empresa.s3_utils import upload_client_document
                print(f"📤 Subiendo documento a S3: {documento_file.name}")
                documento_url = upload_client_document(documento_file)
                if documento_url:
                    print(f"✅ Documento subido: {documento_url}")
                else:
                    return Response({"error": "No se pudo subir el documento a S3"}, status=status.HTTP_400_BAD_REQUEST)
            
            # Crear copia mutable del request.data
            data = request.data.copy()
            data['documento_url'] = documento_url
            data['empresa'] = perfil.empresa.id
            
            serializer = self.get_serializer(data=data)
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            
            return Response(serializer.data, status=status.HTTP_201_CREATED)
            
        except Perfiluser.DoesNotExist:
            return Response({"error": "Usuario no tiene perfil asociado"}, status=status.HTTP_403_FORBIDDEN)
        except Exception as e:
            import traceback
            print(f"❌ Error al crear documentación: {str(e)}")
            traceback.print_exc()
            return Response({"error": f"Error al crear documentación: {str(e)}"}, status=status.HTTP_400_BAD_REQUEST)

    def perform_create(self, serializer):
        try:
            perfil = Perfiluser.objects.get(usuario=self.request.user)
            serializer.save(empresa=perfil.empresa)
        except Perfiluser.DoesNotExist:
            pass


class TrabajoViewSet(viewsets.ModelViewSet):
    serializer_class = TrabajoSerializer
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [JSONParser, FormParser, MultiPartParser]

    def get_queryset(self):
        user = self.request.user
        try:
            perfil = Perfiluser.objects.get(usuario=user)
            return Trabajo.objects.filter(empresa_rel=perfil.empresa)
        except Perfiluser.DoesNotExist:
            return Trabajo.objects.none()

    def create(self, request, *args, **kwargs):
        try:
            perfil = Perfiluser.objects.get(usuario=request.user)
            
            # Obtener archivo de extracto si viene
            extracto_file = request.FILES.get('extracto_file', None)
            
            # Si viene archivo, subirlo a S3
            extracto_url = request.data.get('extracto_url', '')
            if extracto_file:
                from app_Empresa.s3_utils import upload_client_work_extract
                print(f"📤 Subiendo extracto bancario a S3: {extracto_file.name}")
                extracto_url = upload_client_work_extract(extracto_file)
                if extracto_url:
                    print(f"✅ Extracto subido: {extracto_url}")
                else:
                    return Response({"error": "No se pudo subir el extracto a S3"}, status=status.HTTP_400_BAD_REQUEST)
            
            # Crear copia mutable del request.data
            data = request.data.copy()
            data['extracto_url'] = extracto_url
            data['empresa_rel'] = perfil.empresa.id
            
            serializer = self.get_serializer(data=data)
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            
            return Response(serializer.data, status=status.HTTP_201_CREATED)
            
        except Perfiluser.DoesNotExist:
            return Response({"error": "Usuario no tiene perfil asociado"}, status=status.HTTP_403_FORBIDDEN)
        except Exception as e:
            import traceback
            print(f"❌ Error al crear trabajo: {str(e)}")
            traceback.print_exc()
            return Response({"error": f"Error al crear trabajo: {str(e)}"}, status=status.HTTP_400_BAD_REQUEST)

    def perform_create(self, serializer):
        try:
            perfil = Perfiluser.objects.get(usuario=self.request.user)
            serializer.save(empresa_rel=perfil.empresa)
        except Perfiluser.DoesNotExist:
            pass


class DomicilioViewSet(viewsets.ModelViewSet):
    serializer_class = DomicilioSerializer
    permission_classes = [permissions.IsAuthenticated]
    parser_classes = [JSONParser, FormParser, MultiPartParser]

    def get_queryset(self):
        user = self.request.user
        try:
            perfil = Perfiluser.objects.get(usuario=user)
            return Domicilio.objects.filter(empresa=perfil.empresa)
        except Perfiluser.DoesNotExist:
            return Domicilio.objects.none()

    def create(self, request, *args, **kwargs):
        try:
            perfil = Perfiluser.objects.get(usuario=request.user)
            
            # Obtener archivo de croquis si viene
            croquis_file = request.FILES.get('croquis_file', None)
            
            # Si viene archivo, subirlo a S3
            croquis_url = request.data.get('croquis_url', '')
            if croquis_file:
                from app_Empresa.s3_utils import upload_client_address_sketch
                print(f"📤 Subiendo croquis a S3: {croquis_file.name}")
                croquis_url = upload_client_address_sketch(croquis_file)
                if croquis_url:
                    print(f"✅ Croquis subido: {croquis_url}")
                else:
                    return Response({"error": "No se pudo subir el croquis a S3"}, status=status.HTTP_400_BAD_REQUEST)
            
            # Crear copia mutable del request.data
            data = request.data.copy()
            data['croquis_url'] = croquis_url
            data['empresa'] = perfil.empresa.id
            
            serializer = self.get_serializer(data=data)
            serializer.is_valid(raise_exception=True)
            self.perform_create(serializer)
            
            return Response(serializer.data, status=status.HTTP_201_CREATED)
            
        except Perfiluser.DoesNotExist:
            return Response({"error": "Usuario no tiene perfil asociado"}, status=status.HTTP_403_FORBIDDEN)
        except Exception as e:
            import traceback
            print(f"❌ Error al crear domicilio: {str(e)}")
            traceback.print_exc()
            return Response({"error": f"Error al crear domicilio: {str(e)}"}, status=status.HTTP_400_BAD_REQUEST)

    def perform_create(self, serializer):
        try:
            perfil = Perfiluser.objects.get(usuario=self.request.user)
            serializer.save(empresa=perfil.empresa)
        except Perfiluser.DoesNotExist:
            pass
