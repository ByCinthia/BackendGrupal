
from django.contrib import admin
from django.urls import path , include 
from django.http import JsonResponse

def home_view(request):
    """Vista simple para la raíz del servidor"""
    return JsonResponse({
        'message': 'Backend API funcionando correctamente',
        'status': 'online',
        'endpoints': {
            'admin': '/admin/',
            'empresas': '/api/',
            'usuarios': '/api/User/',
            'creditos': '/api/Creditos/',
            'clientes': '/api/Clientes/',
        }
    })

urlpatterns = [
    path('', home_view, name='home'),
    path('admin/', admin.site.urls),
    path('api/', include('app_Empresa.urls_E')),
    path('api/User/', include('app_User.urls')),
    path('api/Creditos/', include('app_Credito.url_Creditos')),
    path('api/Clientes/', include('app_Cliente.urls_cliente')),
]
