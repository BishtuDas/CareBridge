from django.urls import path

from .views import add_child, child_list, edit_child

urlpatterns = [
    path("children/", child_list, name="child_list"),
    path("children/add/", add_child, name="add_child"),
    path("children/<int:child_id>/edit/", edit_child, name="edit_child"),
]
