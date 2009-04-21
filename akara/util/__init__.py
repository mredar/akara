from urllib import quote
from functools import wraps

class iterwrapper:
    """
    Wraps the response body iterator from the application to meet WSGI
    requirements.
    """
    def __init__(self, wrapped, responder):
        """
        wrapped - the iterator coming from the application
        response_chunk_handler - a callable for any processing of a
            response body chunk before passing it on to the server.
        """
        self._wrapped = iter(wrapped)
        self._responder = responder(self._wrapped)
        if hasattr(wrapped, 'close'):
            self.close = self._wrapped.close

    def __iter__(self):
        return self

    def next(self):
        return self._responder.next()


def geturl(environ, relative=''):
    """
    Constructs a portable URL for your application.  If relative is omitted or '',
    Just return the current base URL. Otherwise resolve the relative portion against
    the present base and return the resulting URL.

    (Inspired by url functions in CherryPy and Pylons, and Ian Bicking's code in PEP 333)

    If you have a proxy that forwards the HOST but not the original HTTP request path
    you might have to set akara.proxy-base in environ (e.g. through .ini)  See

    http://wiki.xml3k.org/Akara/Configuration
    """

    #Manually set proxy base URI for non-well-behaved proxies, such as Apache < 1.3.33,
    #Or for cases where the proxy is not mounted at the root of a host, and thus the original
    #request path info is lost
    if environ.get('akara.proxy-base'):
        url = environ['akara.proxy-base']
        if relative: url = Uri.Absolutize(relative, url)
        return url

    url = environ['wsgi.url_scheme']+'://'
    #Apache 1.3.33 and later mod_proxy uses X-Forwarded-Host
    if environ.get('HTTP_X_FORWARDED_HOST'):
        url += environ['HTTP_X_FORWARDED_HOST']
    #Lighttpd uses X-Host
    elif environ.get('HTTP_X_HOST'):
        url += environ['HTTP_X_HOST']
    elif environ.get('HTTP_HOST'):
        url += environ['HTTP_HOST']
    else:
        url += environ['SERVER_NAME']

        if environ['wsgi.url_scheme'] == 'https':
            if environ['SERVER_PORT'] != '443':
               url += ':' + environ['SERVER_PORT']
        else:
            if environ['SERVER_PORT'] != '80':
               url += ':' + environ['SERVER_PORT']

    #Can't use the more strict Uri.PercentEncode because it would quote the '/'
    url += urllib.quote(environ.get('SCRIPT_NAME', '').rstrip('/')) + '/'
    if relative: url = Uri.Absolutize(relative, url)
    return url


def http_method_handler(method):
    '''
    A decorator maker to flag a function as suitable for a given HTTP method
    '''
    def wrap(f):
        #@wraps(f)
        #def wrapper(*args, **kwargs):
        #    return f()
        f.method = method
        return f
    return wrap


class wsgibase(object):
    def __init__(self):
        self._method_handlers = {}
        if not hasattr(self, 'dispatch'):
            self.dispatch = self.dispatch_by_lookup
        #if not hasattr(self, 'dispatch'):
        #    self.dispatch = self.dispatch_by_lookup if hasattr(self, '_methods') else self.dispatch_simply
        for obj in ( getattr(self, name) for name in dir(self) ):
            method = getattr(obj, 'method', None)
            if method:
                self._method_handlers[method] = obj
        return

    def __call__(self, environ, start_response):
        self.environ = environ
        self.start_response = start_response
        return self

    def __iter__(self):
        func = self.dispatch()
        if func is None:
            response_headers = [('Content-type','text/plain')]
            self.start_response(response(httplib.METHOD_NOT_ALLOWED), response_headers)
            yield 'HTTP method Not Allowed'
        else:
            yield func()

    def dispatch_simply(self):
        func = 'do_%s' % self.environ['REQUEST_METHOD']
        if not hasattr(self, func):
            return None
        else:
            return func

    def dispatch_by_lookup(self):
        return self._method_handlers.get(self.environ['REQUEST_METHOD'])

    def parse_fields(self):
        s = self.environ['wsgi.input'].read(int(self.environ['CONTENT_LENGTH']))
        return cgi.parse_qs(s)

        
