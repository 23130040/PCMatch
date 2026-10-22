from django.db import transaction
from django.utils import timezone

from .models import Address, User


@transaction.atomic
def save_address(user, cleaned_data, address_id=None):
    # Serialize address book changes, including concurrent first-address saves on SQLite.
    User.objects.filter(pk=user.pk).update(updated_at=timezone.now())
    addresses = Address.objects.filter(user=user, is_archived=False)
    address = addresses.select_for_update().get(pk=address_id) if address_id else Address(user=user)
    make_default = bool(cleaned_data['is_default']) or not addresses.exclude(pk=address.pk).filter(is_default=True).exists()
    values = {key: cleaned_data[key] for key in ['receiver_name', 'receiver_phone', 'province', 'district', 'ward', 'detail_address']}
    if address.pk and address.orders.exists():
        # Orders keep referencing the original, immutable recipient details.
        address.is_archived = True
        address.is_default = False
        address.save(update_fields=['is_archived', 'is_default'])
        address = Address(user=user)
    if make_default:
        addresses.filter(is_default=True).update(is_default=False)
    for field, value in values.items():
        setattr(address, field, value)
    address.is_default = make_default
    address.save()
    return address


@transaction.atomic
def set_default_address(user, address_id):
    User.objects.filter(pk=user.pk).update(updated_at=timezone.now())
    addresses = Address.objects.filter(user=user, is_archived=False)
    address = addresses.select_for_update().get(pk=address_id)
    addresses.filter(is_default=True).update(is_default=False)
    address.is_default = True
    address.save(update_fields=['is_default'])
    return address
