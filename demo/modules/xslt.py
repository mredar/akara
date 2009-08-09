# -*- encoding: utf-8 -*-
'''
Module name: xslt
Defined REST entry points:

http://purl.org/akara/services/builtin/xslt (akara.xslt)
http://purl.org/akara/services/builtin/xpath (akara.xpath)

Notes on security:

In order to prevent these services from being used for cross-site attacks,
the URI_SPACE config parameter establishes a (space separated) list of base URIs outside of
which it will not travel.  The default is http://hg.akara.info/
'''

import amara
from amara.xslt import transform
from amara.xpath.util import simplify
from amara.bindery import html
from amara.lib import irihelpers, inputsource

from akara.services import simple_service, response

XSLT_SERVICE_ID = 'http://purl.org/akara/services/builtin/xslt'
XPATH_SERVICE_ID = 'http://purl.org/akara/services/builtin/xpath'

#AKARA_MODULE_CONFIG is automatically defined at global scope for a module running within Akara
DEFAULT_TRANSFORM = AKARA_MODULE_CONFIG.get('default_transform')
URI_SPACE = AKARA_MODULE_CONFIG.get('uri_space', 'http://hg.akara.info/').split()
#print DEFAULT_TRANSFORM

#FIXME! The core URI auth code is tested, but not the use in this module
if URI_SPACE == '*':
    #Allow all URI access
    ALLOWED = [(True, True)]
else:
    ALLOWED = []
    for baseuri in URI_SPACE:
        #dAd a rule that permits URIs starting with this URISPACE item
        #FIXME: Technically should normalize uri and base, but this will work for most cases
        ALLOWED.append((lambda uri, base=baseuri: uri.startswith(base), True))
    

@simple_service('POST', XSLT_SERVICE_ID, 'akara.xslt')
def akara_xslt(body, ctype, **params):
    '''
    @xslt - URL to the XSLT transform to be applied
    all other query parameters are passed ot the XSLT processor as top-level params
    
    Sample request:
    curl --request POST --data-binary "@foo.xml" --header "Content-Type: application/xml" "http://localhost:8880/akara.xslt?@xslt=http://hg.akara.info/amara/trunk/raw-file/tip/demo/data/identity.xslt"
    '''
    if "@xslt" in params:
        akaraxslttransform = params["@xslt"][0]
    else:
        if not DEFAULT_TRANSFORM:
            raise ValueError('XSLT transform required')
        akaraxslttransform = DEFAULT_TRANSFORM
    restricted_resolver = irihelpers.resolver(authorizations=ALLOWED)
    #Using restricted_resolver should forbid Any URI access outside the specified "jails"
    #Including access through imports and includes
    body = inputsource(body, resolver=restricted_resolver)
    akaraxslttransform = inputsource(akaraxslttransform, resolver=restricted_resolver)
    result = transform(body, akaraxslttransform)
    return response(str(result), result.parameters.media_type)


@simple_service('POST', XPATH_SERVICE_ID, 'akara.xpath', 'text/xml')
def akara_xpath(body, ctype, **params):
    '''
    select - XPath expression to be evaluated against the document
    tidy - 'yes' to tidy HTML, or 'no'

    Sample request:
    curl --request POST --data-binary "@foo.xml" --header "Content-Type: application/xml" "http://localhost:8880/akara.xpath?select=/html/head/title&tidy=yes"
    '''
    if params.get("tidy") == ['yes']:
        doc = html.parse(body)
    else:
        doc = amara.parse(body)
    result = simplify(doc.xml_select(params['select'][0].decode('utf-8')))
    return str(result)

