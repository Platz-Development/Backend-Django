from .models import Cart

class CartMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        
        if request.user.is_authenticated and not hasattr(request.user, 'cart'):
            Cart.objects.create(learner=request.user)
            
        return response