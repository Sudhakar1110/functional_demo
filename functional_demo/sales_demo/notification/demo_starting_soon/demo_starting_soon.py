import frappe

from functional_demo.portal import format_time_12h


def get_context(context):
	context.format_time_12h = format_time_12h
