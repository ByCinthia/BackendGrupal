from django.urls import include, path
from rest_framework import routers
from .api_user import UserViewSer, GroupViewSet, PermissionViewSer, ContentTypeViewSer, AdminLogViewSet, CreateUserView , PerfilUserViewSet, MeView, UserGroupView


router = routers.DefaultRouter()
router.register(r'user', UserViewSer, basename='user')
router.register(r'group', GroupViewSet, basename='group')
router.register(r'permission', PermissionViewSer, basename='permission')
router.register(r'content-type', ContentTypeViewSer, basename='content-type')
router.register(r'admin-log', AdminLogViewSet, basename='admin-log')
router.register(r'perfil-user', PerfilUserViewSet, basename='perfil-user')

urlpatterns = [
    path('', include(router.urls)),
    path('create-user/', CreateUserView.as_view(), name='create-user'),
    path('me/', MeView.as_view(), name='me'),
    path('user-groups/', UserGroupView.as_view(), name='user-groups'),
]