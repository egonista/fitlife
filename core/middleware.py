from .views import error_404_view


class Custom404Middleware:
    """
    Presenta la página corporativa 404 de FitLife en rutas web inexistentes
    incluso cuando DEBUG=True en entorno de desarrollo/evaluación.
    """
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)
        if (
            response.status_code == 404
            and not request.path.startswith('/api/')
            and 'text/html' in response.get('Content-Type', '')
        ):
            return error_404_view(request)
        return response
