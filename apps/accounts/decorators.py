# from django.http import HttpResponseForbidden
# from django.contrib.auth.decorators import login_required

# def role_required(role):
#     def decorator(view_func):
#         @login_required
#         def wrapper(request, *args, **kwargs):
#             if request.user.role != role:
#                 return HttpResponseForbidden("Access denied")
#             return view_func(request, *args, **kwargs)
#         return wrapper
#     return decorator
