# -*- coding: utf-8 -*-

import string
import random
import os
import locale

from django.conf import settings
from django.http import JsonResponse
from django.utils.http import url_has_allowed_host_and_scheme
from django.shortcuts import resolve_url
from django.utils.safestring import mark_safe

from sorl.thumbnail.shortcuts import get_thumbnail

try:
    from hashlib import sha1 as sha_constructor
except ImportError:
    from django.utils.hashcompat import sha_constructor

DISPLAY_EMPTY_VALUE = "---"


# Set the desired locale for formatting
def format_amount(decimal_value):
    locale.setlocale(locale.LC_ALL, '')
    # Format the decimal value with thousand separators and two decimal places
    formatted_value = locale.format_string('%.2f', decimal_value, grouping=True)

    # Return the formatted amount
    return formatted_value


def get_protocol():
    """
    Returns a string with the current protocol.

    This can be either 'http' or 'https' depending on setting.
    """
    protocol = 'http'
    if settings.USE_HTTPS:
        protocol = 'https'
    return protocol

def get_filename(filename, request):
    return filename.upper()

def generate_sha1(string, salt=None):
    if not salt:
        salt = sha_constructor(str(random.random()).encode('utf-8')).hexdigest()[:5]
    hash_key = sha_constructor("{0}{1}".format(str(salt), str(string)).encode('utf-8')).hexdigest()

    return (salt, hash_key)


def safe_referrer(request, default):
    """
    Takes the request and a default URL. Returns HTTP_REFERER if it's safe
    to use and set, and the default URL otherwise.

    The default URL can be a model with get_absolute_url defined, a urlname
    or a regular URL
    """
    referrer = request.META.get('HTTP_REFERER')
    if referrer and url_has_allowed_host_and_scheme(referrer, request.get_host()):
        return referrer
    if default:
        # Try to resolve. Can take a model instance, Django URL name or URL.
        return resolve_url(default)
    else:
        # Allow passing in '' and None as default
        return default


def get_img_extension(img):
    """Return ext based on given image."""
    ext = 'JPEG'
    try:
        aux_ext = str(img).split('.')
        if aux_ext[len(aux_ext) - 1].lower() == 'png':
            ext = 'PNG'
        elif aux_ext[len(aux_ext) - 1].lower() == 'gif':
            ext = 'GIF'
    except Exception:  # pragma: no cover
        pass

    return ext


def generate_thumbnail(img, img_size='x36'):
    """
    Generate image thumbnail based on given image.

    Return mark_safe string.
    """
    if img and hasattr(img, 'url'):
        ext = get_img_extension(img)
        thumb = get_thumbnail(img, img_size, upscale=False, format=ext)
        filename = os.path.basename(img.name)

        return mark_safe(
            f'<a href="{img.url}" data-fancybox="gallery" data-caption="{filename}" style="display: inline-block;">'
            f'<img width="{thumb.width}" height="{thumb.height}" src="{thumb.url}" '
            'style="border: 1px solid #CCC; padding: 2px;" />'
            "</a>"
        )
    else:
        return DISPLAY_EMPTY_VALUE


def random_string_generator(size, additional=None, chars=string.ascii_uppercase + string.digits + string.ascii_lowercase):
    return ''.join(random.choice(chars + str(additional)) for _ in range(size))


def remove_prefix(text, prefix):
    return text[len(prefix):] if text.startswith(prefix) else text