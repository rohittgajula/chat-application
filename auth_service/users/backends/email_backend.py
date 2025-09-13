
from django.core.mail.backends.smtp import EmailBackend as DjangoEmailBackend
from django.utils.functional import cached_property
import ssl

class EmailBackend(DjangoEmailBackend):
    def __init__(self, *args, ssl_certfile=None, ssl_keyfile=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.ssl_certfile = ssl_certfile
        self.ssl_keyfile = ssl_keyfile

    @cached_property
    def ssl_context(self):
        if self.ssl_certfile or self.ssl_keyfile:
            ssl_context = ssl.SSLContext(protocol=ssl.PROTOCOL_TLS_CLIENT)
            ssl_context.load_cert_chain(self.ssl_certfile, self.ssl_keyfile)
            return ssl_context
        else:
            ssl_context = ssl.create_default_context()
            ssl_context.check_hostname = False
            ssl_context.verify_mode = ssl.CERT_NONE
            return ssl_context

