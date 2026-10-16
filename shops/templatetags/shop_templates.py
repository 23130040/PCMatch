"""Publish Shop HTML fragments as inert JSON for the browser demo."""

import re

from django import template
from django.template.loader import render_to_string
from django.utils.html import json_script

register = template.Library()
GROUPS = {'ui', 'app', 'auth', 'dashboard', 'products', 'orders', 'builds', 'aftersales'}
FRAGMENTS = re.compile(r'<template data-shop-template="([^"]+)">\n([\s\S]*?)\n</template>')


@register.simple_tag(takes_context=True)
def shop_templates(context, group):
    if group not in GROUPS:
        raise template.TemplateSyntaxError(f'Unknown Shop template group: {group}')
    source = render_to_string(
        f'includes/shop/{group}.html', context.flatten(), request=context.get('request'),
    )
    fragments = dict(FRAGMENTS.findall(source))
    return json_script(fragments, f'shop-templates-{group}')
