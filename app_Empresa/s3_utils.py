"""
Utilidades para subir archivos a AWS S3
"""
import boto3
from botocore.exceptions import ClientError
from django.conf import settings
import os
import uuid
from datetime import datetime


def get_s3_client():
    """
    Crear y retornar cliente de S3 con las credenciales del .env
    """
    return boto3.client(
        's3',
        aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
        aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY,
        region_name=settings.AWS_S3_REGION_NAME
    )


def upload_file_to_s3(file, folder='uploads'):
    """
    Subir un archivo a S3 y retornar la URL
    
    Args:
        file: Archivo de Django (InMemoryUploadedFile o TemporaryUploadedFile)
        folder: Carpeta dentro del bucket donde se guardará (default: 'uploads')
    
    Returns:
        str: URL del archivo en S3, o None si falla
    """
    if not file:
        return None
    
    try:
        s3_client = get_s3_client()
        
        # Generar nombre único para el archivo
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        unique_id = str(uuid.uuid4())[:8]
        file_extension = os.path.splitext(file.name)[1]
        
        # Nombre del archivo en S3: folder/timestamp_uniqueid_originalname.ext
        s3_filename = f"{folder}/{timestamp}_{unique_id}_{file.name}"
        
        # Subir archivo a S3 (sin ACL, confiamos en la política del bucket)
        s3_client.upload_fileobj(
            file,
            settings.AWS_STORAGE_BUCKET_NAME,
            s3_filename,
            ExtraArgs={
                'ContentType': file.content_type if hasattr(file, 'content_type') else 'application/octet-stream',
                # No usamos ACL porque el bucket tiene ObjectOwnership=BucketOwnerEnforced
                # En su lugar, la política del bucket permite lectura pública de todos los objetos
            }
        )
        
        # Construir URL pública del archivo
        url = f"https://{settings.AWS_STORAGE_BUCKET_NAME}.s3.{settings.AWS_S3_REGION_NAME}.amazonaws.com/{s3_filename}"
        
        print(f"✅ Archivo subido exitosamente a S3: {url}")
        return url
        
    except ClientError as e:
        print(f"Error al subir archivo a S3: {str(e)}")
        return None
    except Exception as e:
        print(f"Error inesperado al subir archivo: {str(e)}")
        return None


def upload_empresa_logo(file):
    """
    Subir logo de empresa a S3 en la carpeta 'empresas/logos'
    """
    return upload_file_to_s3(file, folder='empresas/logos')


def upload_user_avatar(file):
    """
    Subir avatar de usuario a S3 en la carpeta 'usuarios/avatars'
    """
    return upload_file_to_s3(file, folder='usuarios/avatars')


def upload_client_document(file):
    """
    Subir documento de cliente a S3 en la carpeta 'clientes/documentos'
    """
    return upload_file_to_s3(file, folder='clientes/documentos')


def upload_client_work_extract(file):
    """
    Subir extracto bancario laboral a S3 en la carpeta 'clientes/extractos'
    """
    return upload_file_to_s3(file, folder='clientes/extractos')


def upload_client_address_sketch(file):
    """
    Subir croquis de domicilio a S3 en la carpeta 'clientes/croquis'
    """
    return upload_file_to_s3(file, folder='clientes/croquis')


def delete_file_from_s3(file_url):
    """
    Eliminar un archivo de S3 usando su URL
    
    Args:
        file_url: URL completa del archivo en S3
    
    Returns:
        bool: True si se eliminó correctamente, False si falló
    """
    if not file_url:
        return False
    
    try:
        s3_client = get_s3_client()
        
        # Extraer el nombre del archivo (key) de la URL
        # Formato: https://bucket.s3.region.amazonaws.com/folder/file.ext
        parts = file_url.split(f"{settings.AWS_STORAGE_BUCKET_NAME}.s3.{settings.AWS_S3_REGION_NAME}.amazonaws.com/")
        if len(parts) < 2:
            return False
        
        s3_key = parts[1]
        
        # Eliminar archivo
        s3_client.delete_object(
            Bucket=settings.AWS_STORAGE_BUCKET_NAME,
            Key=s3_key
        )
        
        return True
        
    except ClientError as e:
        print(f"Error al eliminar archivo de S3: {str(e)}")
        return False
    except Exception as e:
        print(f"Error inesperado al eliminar archivo: {str(e)}")
        return False
