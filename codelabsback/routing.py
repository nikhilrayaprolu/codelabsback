from channels.auth import AuthMiddlewareStack
from channels.routing import ProtocolTypeRouter, URLRouter
from django.urls import path

import labs.routing

application = ProtocolTypeRouter({
    # Empty for now (http->django views is added by default)
    'websocket': URLRouter(
            labs.routing.websocket_urlpatterns
        )

})
