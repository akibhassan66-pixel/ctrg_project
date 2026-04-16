# p3_services.py
import os
from django.conf import settings
from django.core.files.storage import default_storage
from django.utils import timezone

def save_upload_to_media(uploaded_file, folder="uploads"):
    """
    Saves file to MEDIA_ROOT/folder/ and returns the relative path to store in DB.
    """
    filename = f"{timezone.now().strftime('%Y%m%d_%H%M%S')}_{uploaded_file.name}"
    relative_path = os.path.join(folder, filename)
    saved_path = default_storage.save(relative_path, uploaded_file)
    return saved_path

def add_auditlog(AuditlogsModel, actor_user, action_type, target_entity, target_id, details=None):
    AuditlogsModel.objects.create(
        actor_user=actor_user,
        action_type=action_type,
        target_entity=target_entity,
        target_id=target_id,
        details=details or "",
        timestamp=timezone.now(),
    )

def require_role(user, allowed_roles):
    """
    Adjust this function to match your user model role field.
    Common patterns:
      - user.role in ("PI","REVIEWER","CHAIR")
      - user.user_type
      - user.is_staff / user.is_superuser
      - Django groups
    """
    role = getattr(user, "role", None) or getattr(user, "user_type", None)
    return role in allowed_roles